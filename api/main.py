import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.routes.health import router as health_router
from api.routes.memory import router as memory_router
from api.routes.wiki import router as wiki_router
from api.routes.web import router as web_router
from api.validation import register_validation_exception_handler
from core.config import Settings, get_settings
from core.logging import setup_logging
from core.metrics import (
  MEMORY_QUERY_DURATION,
  MEMORY_QUERY_TOTAL,
  PrometheusMiddleware,
  register_candidate_metrics_collector,
  register_fact_extraction_metrics_collector,
  register_ingestion_metrics_collector,
  register_reflection_metrics_collector,
)
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from pipelines.extract.fact_llm_client import build_fact_llm_client
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.reflect.reflection_llm_client import build_reflection_llm_client
from pipelines.reflect.reflection_runner import ReflectionRunner
from pipelines.wiki.wiki_llm_client import build_wiki_llm_client
from pipelines.wiki.wiki_runner import WikiBuildRunner
from services.memory_governance_service import MemoryGovernanceService
from services.memory_service import MemoryService
from services.retrieval_service import RetrievalService
from vector.qdrant_client import MnemosQdrantClient
from workers.pipeline_worker import PipelineWorker


def register_metrics(app: FastAPI) -> None:
  @app.get("/metrics", include_in_schema=False)
  async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def create_app(settings: Settings | None = None) -> FastAPI:
  settings = settings or get_settings()
  setup_logging(settings.mnemos_log_level)

  @asynccontextmanager
  async def lifespan(app: FastAPI):
    worker = getattr(app.state, "pipeline_worker", None)
    task = None
    if app.state.settings.pipeline_worker_enabled and worker is not None:
      task = asyncio.create_task(worker.run(), name="mnemos-pipeline-worker")
      app.state.pipeline_worker_task = task
    try:
      yield
    finally:
      if worker is not None:
        worker.stop()
      if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
          await task

  app = FastAPI(title="mnemos", version="0.1.0", lifespan=lifespan)
  app.add_middleware(PrometheusMiddleware)
  app.state.settings = settings
  register_validation_exception_handler(app)

  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  app.state.engine = engine
  app.state.session_factory = session_factory
  app.state.qdrant = qdrant
  app.state.embedder = embedder
  app.state.memory_service = MemoryService(session_factory, qdrant, embedder, settings)
  app.state.governance_service = MemoryGovernanceService(session_factory)
  app.state.fact_llm_client = build_fact_llm_client(settings)
  app.state.fact_runner = FactExtractionRunner(app.state.memory_service, app.state.fact_llm_client, settings)
  app.state.reflection_llm_client = build_reflection_llm_client(settings)
  app.state.reflection_runner = ReflectionRunner(
    app.state.memory_service,
    app.state.reflection_llm_client,
    settings,
  )
  app.state.wiki_llm_client = build_wiki_llm_client(settings)
  app.state.wiki_runner = WikiBuildRunner(app.state.memory_service, app.state.wiki_llm_client, settings)
  app.state.pipeline_worker = PipelineWorker(
    memory_service=app.state.memory_service,
    fact_runner=app.state.fact_runner,
    reflection_runner=app.state.reflection_runner,
    wiki_runner=app.state.wiki_runner,
    interval_seconds=settings.pipeline_worker_interval_seconds,
  )
  app.state.pipeline_worker_task = None
  app.state.retrieval_service = RetrievalService(
    session_factory,
    qdrant,
    embedder,
    settings,
    MEMORY_QUERY_TOTAL,
    MEMORY_QUERY_DURATION,
  )
  register_ingestion_metrics_collector(session_factory)
  register_fact_extraction_metrics_collector(session_factory)
  register_reflection_metrics_collector(session_factory)
  register_candidate_metrics_collector(session_factory)

  register_metrics(app)
  app.include_router(web_router)
  app.include_router(health_router)
  app.include_router(memory_router)
  app.include_router(wiki_router)
  return app


app = create_app()

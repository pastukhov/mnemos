from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.routes.health import router as health_router
from api.routes.memory import router as memory_router
from core.config import Settings, get_settings
from core.logging import get_logger, setup_logging
from core.metrics import (
  MEMORY_QUERY_DURATION,
  MEMORY_QUERY_TOTAL,
  PrometheusMiddleware,
  register_fact_extraction_metrics_collector,
  register_ingestion_metrics_collector,
  register_reflection_metrics_collector,
)
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from services.memory_service import MemoryService
from services.retrieval_service import RetrievalService
from vector.qdrant_client import MnemosQdrantClient

def register_metrics(app: FastAPI) -> None:
  @app.get("/metrics", include_in_schema=False)
  async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@asynccontextmanager
async def lifespan(app: FastAPI):
  settings: Settings = app.state.settings
  logger = get_logger(__name__)
  logger.info("startup", extra={"event": "startup", "env": settings.mnemos_env})
  yield
  logger.info("shutdown", extra={"event": "shutdown"})


def create_app(settings: Settings | None = None) -> FastAPI:
  settings = settings or get_settings()
  setup_logging(settings.mnemos_log_level)

  app = FastAPI(title="mnemos", version="0.1.0", lifespan=lifespan)
  app.add_middleware(PrometheusMiddleware)
  app.state.settings = settings

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

  register_metrics(app)
  app.include_router(health_router)
  app.include_router(memory_router)
  return app


app = create_app()

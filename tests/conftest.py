from collections import defaultdict
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import Settings
from db.base import Base
from embeddings.mock import MockEmbedder
from pipelines.extract.fact_llm_client import MockFactLLMClient
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.reflect.reflection_llm_client import MockReflectionLLMClient
from pipelines.reflect.reflection_runner import ReflectionRunner
from pipelines.wiki.wiki_llm_client import MockWikiLLMClient
from pipelines.wiki.wiki_runner import WikiBuildRunner
from workers.pipeline_worker import PipelineWorker


class FakeCollections:
  def __init__(self, names):
    self.collections = [type("Collection", (), {"name": name}) for name in names]


class FakeQdrant:
  def __init__(self, settings: Settings) -> None:
    self.settings = settings
    self.collections: dict[str, list[dict[str, object]]] = defaultdict(list)

  def ping(self) -> None:
    return None

  def ensure_collection(self, collection_name: str) -> None:
    self.collections.setdefault(collection_name, [])

  def upsert_item(self, *, collection_name: str, item_id: str, vector: list[float], payload: dict[str, str]) -> None:
    self.ensure_collection(collection_name)
    self.collections[collection_name] = [
      point for point in self.collections[collection_name] if point["item_id"] != item_id
    ]
    self.collections[collection_name].append(
      {"item_id": item_id, "vector": vector, **payload}
    )

  def query_items(self, *, collection_name: str, vector: list[float], limit: int) -> list[dict[str, str]]:
    points = self.collections.get(collection_name, [])

    def score(point: dict[str, object]) -> float:
      point_vector = point["vector"]
      return sum(left * right for left, right in zip(vector, point_vector))

    ranked = sorted(points, key=score, reverse=True)
    return [
      {
        "item_id": point["item_id"],
        "domain": point["domain"],
        "kind": point["kind"],
        "status": point["status"],
      }
      for point in ranked[:limit]
    ]


@pytest.fixture
def client():
  os.environ.setdefault("EMBEDDING_BASE_URL", "http://example.test/v1")
  from api.main import create_app

  settings = Settings(
    postgres_host="localhost",
    postgres_port=5432,
    postgres_db="mnemos_test",
    postgres_user="postgres",
    postgres_password="postgres",
    qdrant_url="http://fake-qdrant",
    embedding_base_url="http://example.test/v1",
    qdrant_vector_size=8,
    pipeline_worker_enabled=False,
  )
  settings.pipeline_worker_enabled = False
  engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
  )
  Base.metadata.create_all(engine)
  session_factory = sessionmaker(bind=engine, expire_on_commit=False)

  app = create_app(settings)
  app.state.settings.pipeline_worker_enabled = False
  app.state.engine = engine
  app.state.session_factory = session_factory
  app.state.qdrant = FakeQdrant(settings)
  app.state.embedder = MockEmbedder(vector_size=settings.qdrant_vector_size)
  from services.memory_service import MemoryService
  from services.memory_governance_service import MemoryGovernanceService
  from services.retrieval_service import RetrievalService
  from core.metrics import MEMORY_QUERY_DURATION, MEMORY_QUERY_TOTAL

  app.state.memory_service = MemoryService(
    session_factory=session_factory,
    qdrant=app.state.qdrant,
    embedder=app.state.embedder,
    settings=settings,
  )
  app.state.retrieval_service = RetrievalService(
    session_factory=session_factory,
    qdrant=app.state.qdrant,
    embedder=app.state.embedder,
    settings=settings,
    query_counter=MEMORY_QUERY_TOTAL,
    query_duration=MEMORY_QUERY_DURATION,
  )
  app.state.governance_service = MemoryGovernanceService(session_factory)
  app.state.fact_llm_client = MockFactLLMClient()
  app.state.fact_runner = FactExtractionRunner(app.state.memory_service, app.state.fact_llm_client, settings)
  app.state.reflection_llm_client = MockReflectionLLMClient()
  app.state.reflection_runner = ReflectionRunner(
    app.state.memory_service,
    app.state.reflection_llm_client,
    settings,
  )
  app.state.wiki_llm_client = MockWikiLLMClient()
  app.state.wiki_runner = WikiBuildRunner(app.state.memory_service, app.state.wiki_llm_client, settings)
  app.state.pipeline_worker = PipelineWorker(
    memory_service=app.state.memory_service,
    fact_runner=app.state.fact_runner,
    reflection_runner=app.state.reflection_runner,
    wiki_runner=app.state.wiki_runner,
    interval_seconds=settings.pipeline_worker_interval_seconds,
  )
  app.state.pipeline_worker_task = None
  with TestClient(app) as test_client:
    yield test_client

from api.schemas import MemoryCreateRequest
from core.config import get_settings
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from services.memory_service import MemoryService
from vector.qdrant_client import MnemosQdrantClient


SEED_ITEMS = [
  {
    "domain": "self",
    "kind": "note",
    "statement": "User prefers building automated systems.",
    "confidence": 0.95,
    "metadata": {"source": "manual_seed"},
  },
  {
    "domain": "self",
    "kind": "note",
    "statement": "User prefers direct, concise communication.",
    "confidence": 0.9,
    "metadata": {"source": "manual_seed"},
  },
  {
    "domain": "self",
    "kind": "fact",
    "statement": "User values pragmatic engineering over abstractions.",
    "confidence": 0.88,
    "metadata": {"source": "manual_seed"},
  },
  {
    "domain": "project",
    "kind": "decision",
    "statement": "PostgreSQL is the source of truth for memory items.",
    "confidence": 0.99,
    "metadata": {"source": "manual_seed"},
  },
  {
    "domain": "project",
    "kind": "note",
    "statement": "Qdrant stores search vectors and lookup payload only.",
    "confidence": 0.97,
    "metadata": {"source": "manual_seed"},
  },
  {
    "domain": "project",
    "kind": "tension",
    "statement": "Phase 1 must stay modular without implementing future ingestion logic.",
    "confidence": 0.86,
    "metadata": {"source": "manual_seed"},
  },
]


def main() -> None:
  settings = get_settings()
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  service = MemoryService(
    session_factory=session_factory,
    qdrant=qdrant,
    embedder=build_embedder(settings),
    settings=settings,
  )
  for item in SEED_ITEMS:
    service.create_item(MemoryCreateRequest.model_validate(item))


if __name__ == "__main__":
  main()

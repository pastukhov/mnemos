from __future__ import annotations

from core.config import ALLOWED_DOMAINS, get_settings
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from services.memory_service import MemoryService
from vector.qdrant_client import MnemosQdrantClient


def main() -> None:
  settings = get_settings()
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  memory_service = MemoryService(
    session_factory=session_factory,
    qdrant=qdrant,
    embedder=embedder,
    settings=settings,
  )

  for domain in ALLOWED_DOMAINS:
    collection_name = settings.collection_for_domain(domain)
    if qdrant.has_collection(collection_name):
      qdrant.client.delete_collection(collection_name=collection_name)
      qdrant._known_collections.discard(collection_name)
    qdrant.ensure_collection(collection_name)

    items = memory_service.list_items_by_domain(domain)
    for item in items:
      vector = embedder.embed_text(item.statement)
      qdrant.upsert_item(
        collection_name=collection_name,
        item_id=str(item.id),
        vector=vector,
        payload={
          "item_id": str(item.id),
          "domain": item.domain,
          "kind": item.kind,
          "status": item.status,
        },
      )
    print(f"{domain}: reindexed {len(items)} items")


if __name__ == "__main__":
  main()

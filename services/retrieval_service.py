from uuid import UUID

from sqlalchemy.orm import sessionmaker

from api.schemas import MemoryItemResponse, MemoryQueryRequest, MemoryQueryResponse
from core.config import Settings
from core.logging import get_logger
from db.repositories.memory_items import MemoryItemRepository
from embeddings.base import Embedder
from vector.qdrant_client import MnemosQdrantClient

logger = get_logger(__name__)


class RetrievalService:
  def __init__(
    self,
    session_factory: sessionmaker,
    qdrant: MnemosQdrantClient,
    embedder: Embedder,
    settings: Settings,
    query_counter,
    query_duration,
  ) -> None:
    self.session_factory = session_factory
    self.qdrant = qdrant
    self.embedder = embedder
    self.settings = settings
    self.query_counter = query_counter
    self.query_duration = query_duration

  def query(self, payload: MemoryQueryRequest) -> MemoryQueryResponse:
    self.query_counter.inc()
    logger.info("memory query received", extra={"event": "memory_query"})
    with self.query_duration.time():
      vector = self.embedder.embed_text(payload.query)
      collection_name = self.settings.collection_for_domain(payload.domain)
      results = self.qdrant.query_items(
        collection_name=collection_name,
        vector=vector,
        limit=payload.top_k,
      )
      ids_in_order = [UUID(result["item_id"]) for result in results if result.get("item_id")]
      with self.session_factory() as session:
        repository = MemoryItemRepository(session)
        items = repository.list_by_ids(ids_in_order)

      item_by_id = {item.id: item for item in items}
      hydrated = []
      orphan_count = 0
      for item_id in ids_in_order:
        item = item_by_id.get(item_id)
        if item is None:
          orphan_count += 1
          continue
        if payload.kinds and item.kind not in payload.kinds:
          continue
        if item.status != "accepted":
          continue
        hydrated.append(MemoryItemResponse.model_validate(item))

      if orphan_count:
        logger.warning(
          "orphaned vector results detected",
          extra={"event": "vector_orphans"},
        )

      return MemoryQueryResponse(query=payload.query, domain=payload.domain, items=hydrated)

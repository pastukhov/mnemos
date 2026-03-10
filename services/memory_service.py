from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import sessionmaker

from api.schemas import MemoryCreateRequest
from core.config import Settings
from core.logging import get_logger
from core.metrics import MEMORY_CREATE_TOTAL
from db.repositories.fact_extraction_metrics import FactExtractionMetricRepository
from db.repositories.ingestion_metrics import IngestionMetricRepository
from db.repositories.memory_items import MemoryItemRepository
from db.repositories.memory_relations import MemoryRelationRepository
from embeddings.base import Embedder
from vector.qdrant_client import MnemosQdrantClient

logger = get_logger(__name__)


class MemoryService:
  def __init__(
    self,
    session_factory: sessionmaker,
    qdrant: MnemosQdrantClient,
    embedder: Embedder,
    settings: Settings,
  ) -> None:
    self.session_factory = session_factory
    self.qdrant = qdrant
    self.embedder = embedder
    self.settings = settings

  def create_item(self, payload: MemoryCreateRequest):
    MEMORY_CREATE_TOTAL.inc()
    try:
      return self._create_item(payload)
    except Exception as exc:
      logger.exception(
        "memory item creation failed",
        extra={"event": "memory_item_create_failed"},
      )
      raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="failed to create and index memory item",
      ) from exc

  def get_item(self, item_id: str):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      try:
        parsed_id = UUID(item_id)
      except ValueError:
        return None
      return repository.get(parsed_id)

  def create_item_record(self, payload: MemoryCreateRequest):
    return self._create_item(payload)

  def get_item_by_source_ref(self, *, source_type: str, source_id: str):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.get_by_source_ref(source_type=source_type, source_id=source_id)

  def list_items_by_domain_kind(self, *, domain: str, kind: str):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_by_domain_kind(domain=domain, kind=kind)

  def list_facts_by_source_item_id(self, *, source_item_id: str):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_facts_by_source_item_id(source_item_id=source_item_id)

  def record_ingestion_metrics(
    self,
    *,
    source_type: str,
    loaded: int = 0,
    duplicates: int = 0,
    errors: int = 0,
  ) -> None:
    with self.session_factory() as session:
      repository = IngestionMetricRepository(session)
      repository.increment(
        source_type=source_type,
        loaded=loaded,
        duplicates=duplicates,
        errors=errors,
      )
      session.commit()

  def record_fact_extraction_metrics(
    self,
    *,
    domain: str,
    runs: int = 0,
    facts_created: int = 0,
    errors: int = 0,
  ) -> None:
    with self.session_factory() as session:
      repository = FactExtractionMetricRepository(session)
      repository.increment(
        domain=domain,
        runs=runs,
        facts_created=facts_created,
        errors=errors,
      )
      session.commit()

  def create_related_item_record(
    self,
    payload: MemoryCreateRequest,
    *,
    target_item_id: UUID,
    relation_type: str,
  ):
    vector = self.embedder.embed_text(payload.statement)
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      relation_repository = MemoryRelationRepository(session)
      item = repository.create(
        domain=payload.domain,
        kind=payload.kind,
        statement=payload.statement,
        confidence=payload.confidence,
        metadata=payload.metadata,
      )
      relation_repository.create(
        source_item_id=item.id,
        target_item_id=target_item_id,
        relation_type=relation_type,
      )
      self.qdrant.ensure_collection(self.settings.collection_for_domain(payload.domain))
      self.qdrant.upsert_item(
        collection_name=self.settings.collection_for_domain(payload.domain),
        item_id=str(item.id),
        vector=vector,
        payload={
          "item_id": str(item.id),
          "domain": item.domain,
          "kind": item.kind,
          "status": item.status,
        },
      )
      session.commit()
      session.refresh(item)
      return item

  def _create_item(self, payload: MemoryCreateRequest):
    vector = self.embedder.embed_text(payload.statement)
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      item = repository.create(
        domain=payload.domain,
        kind=payload.kind,
        statement=payload.statement,
        confidence=payload.confidence,
        metadata=payload.metadata,
      )
      self.qdrant.ensure_collection(self.settings.collection_for_domain(payload.domain))
      self.qdrant.upsert_item(
        collection_name=self.settings.collection_for_domain(payload.domain),
        item_id=str(item.id),
        vector=vector,
        payload={
          "item_id": str(item.id),
          "domain": item.domain,
          "kind": item.kind,
          "status": item.status,
        },
      )
      session.commit()
      session.refresh(item)
      logger.info("memory item created", extra={"event": "memory_item_created"})
      return item

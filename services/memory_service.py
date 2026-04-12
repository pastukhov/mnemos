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
from db.repositories.reflection_metrics import ReflectionMetricRepository
from db.repositories.wiki_page_cache import WikiPageCacheRepository
from embeddings.base import Embedder
from pipelines.wiki.wiki_schema import WikiSchema
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

  def list_items_by_domain(self, domain: str, *, status: str | None = "accepted"):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_by_domain(domain=domain, status=status)

  def list_domains_with_items(
    self,
    *,
    kind: str,
    status: str | None = "accepted",
    min_count: int = 1,
  ) -> list[str]:
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_domains_with_kind(
        kind=kind,
        status=status,
        min_count=min_count,
      )

  def list_facts_by_source_item_id(self, *, source_item_id: str):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_facts_by_source_item_id(source_item_id=source_item_id)

  def list_reflections_by_fingerprint(
    self,
    *,
    domain: str,
    theme: str,
    source_fact_fingerprint: str,
  ):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_reflections_by_fingerprint(
        domain=domain,
        theme=theme,
        source_fact_fingerprint=source_fact_fingerprint,
      )

  def get_wiki_page(self, page_name: str):
    with self.session_factory() as session:
      repository = WikiPageCacheRepository(session)
      return repository.get(page_name)

  def list_wiki_pages(self):
    with self.session_factory() as session:
      repository = WikiPageCacheRepository(session)
      return repository.list_pages()

  def list_invalidated_wiki_pages(self):
    with self.session_factory() as session:
      repository = WikiPageCacheRepository(session)
      return repository.list_invalidated_pages()

  def upsert_wiki_page(
    self,
    *,
    page_name: str,
    title: str,
    content_md: str,
    facts_count: int,
    reflections_count: int,
    generated_at=None,
    invalidated_at=None,
  ):
    with self.session_factory() as session:
      repository = WikiPageCacheRepository(session)
      page = repository.upsert_page(
        page_name=page_name,
        title=title,
        content_md=content_md,
        facts_count=facts_count,
        reflections_count=reflections_count,
        generated_at=generated_at,
        invalidated_at=invalidated_at,
      )
      session.commit()
      session.refresh(page)
      return page

  def invalidate_wiki_pages_for_item(self, *, item) -> list[str]:
    wiki_invalidation_kinds = set(self.settings.wiki_facts_kinds) | set(self.settings.wiki_reflections_kinds)
    if item.kind not in wiki_invalidation_kinds:
      return []

    schema = self._load_wiki_schema()
    if schema is None:
      return []

    page_names: list[str] = []
    theme = None
    if item.metadata_json:
      theme = item.metadata_json.get("theme")

    with self.session_factory() as session:
      repository = WikiPageCacheRepository(session)
      for page_def in schema.pages:
        if item.domain not in page_def.domains:
          continue
        if item.kind not in page_def.kinds:
          continue
        if page_def.themes:
          if theme not in page_def.themes:
            continue
        page = repository.mark_invalidated(page_def.name)
        if page is not None:
          page_names.append(page_def.name)
      session.commit()
    return page_names

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

  def record_reflection_metrics(
    self,
    *,
    domain: str,
    runs: int = 0,
    reflections_created: int = 0,
    skipped: int = 0,
    errors: int = 0,
  ) -> None:
    with self.session_factory() as session:
      repository = ReflectionMetricRepository(session)
      repository.increment(
        domain=domain,
        runs=runs,
        reflections_created=reflections_created,
        skipped=skipped,
        errors=errors,
      )
      session.commit()

  def create_item_with_relations(
    self,
    payload: MemoryCreateRequest,
    *,
    relations: list[tuple[UUID, str]],
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
      for target_item_id, relation_type in relations:
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
      self.invalidate_wiki_pages_for_item(item=item)
      session.refresh(item)
      return item

  def create_related_item_record(
    self,
    payload: MemoryCreateRequest,
    *,
    target_item_id: UUID,
    relation_type: str,
  ):
    return self.create_item_with_relations(
      payload,
      relations=[(target_item_id, relation_type)],
    )

  def supersede_item(
    self,
    *,
    item_id: UUID,
    replacement_item_id: UUID,
  ):
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      relation_repository = MemoryRelationRepository(session)
      item = repository.get(item_id)
      replacement = repository.get(replacement_item_id)
      if item is None or replacement is None:
        return None
      metadata = dict(item.metadata_json or {})
      metadata["superseded_by_item_id"] = str(replacement_item_id)
      repository.update_status(item, status="superseded", metadata=metadata)
      relation_repository.create(
        source_item_id=replacement_item_id,
        target_item_id=item_id,
        relation_type="supersedes",
      )
      session.commit()
      self.invalidate_wiki_pages_for_item(item=item)
      self.invalidate_wiki_pages_for_item(item=replacement)
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
      self.invalidate_wiki_pages_for_item(item=item)
      session.refresh(item)
      logger.info("memory item created", extra={"event": "memory_item_created"})
      return item

  def _load_wiki_schema(self) -> WikiSchema | None:
    try:
      return WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
    except Exception:
      logger.warning(
        "wiki schema unavailable for invalidation",
        extra={
          "event": "wiki_schema_unavailable_for_invalidation",
          "path": self.settings.wiki_schema_path,
        },
      )
      return None

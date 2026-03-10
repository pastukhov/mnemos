from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MemoryItem


class MemoryItemRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def create(
    self,
    *,
    domain: str,
    kind: str,
    statement: str,
    confidence: float | None,
    metadata: dict[str, object] | None,
    status: str = "accepted",
  ) -> MemoryItem:
    item = MemoryItem(
      domain=domain,
      kind=kind,
      statement=statement,
      confidence=confidence,
      metadata_json=metadata,
      status=status,
    )
    self.session.add(item)
    self.session.flush()
    return item

  def get(self, item_id: UUID) -> MemoryItem | None:
    return self.session.get(MemoryItem, item_id)

  def get_by_source_ref(self, *, source_type: str, source_id: str) -> MemoryItem | None:
    query = select(MemoryItem).where(
      MemoryItem.metadata_json["source_type"].as_string() == source_type,
      MemoryItem.metadata_json["source_id"].as_string() == source_id,
    )
    return self.session.execute(query).scalar_one_or_none()

  def list_by_domain_kind(self, *, domain: str, kind: str, status: str = "accepted") -> list[MemoryItem]:
    query = (
      select(MemoryItem)
      .where(
        MemoryItem.domain == domain,
        MemoryItem.kind == kind,
        MemoryItem.status == status,
      )
      .order_by(MemoryItem.created_at.asc())
    )
    return list(self.session.execute(query).scalars())

  def list_by_domain(self, *, domain: str, status: str = "accepted") -> list[MemoryItem]:
    query = (
      select(MemoryItem)
      .where(
        MemoryItem.domain == domain,
        MemoryItem.status == status,
      )
      .order_by(MemoryItem.created_at.asc())
    )
    return list(self.session.execute(query).scalars())

  def list_facts_by_source_item_id(self, *, source_item_id: str) -> list[MemoryItem]:
    query = (
      select(MemoryItem)
      .where(
        MemoryItem.kind == "fact",
        MemoryItem.metadata_json["source_type"].as_string() == "fact_extraction",
        MemoryItem.metadata_json["source_item_id"].as_string() == source_item_id,
      )
      .order_by(MemoryItem.created_at.asc())
    )
    return list(self.session.execute(query).scalars())

  def list_reflections_by_fingerprint(
    self,
    *,
    domain: str,
    theme: str,
    source_fact_fingerprint: str,
    status: str = "accepted",
  ) -> list[MemoryItem]:
    query = (
      select(MemoryItem)
      .where(
        MemoryItem.domain == domain,
        MemoryItem.kind == "reflection",
        MemoryItem.status == status,
        MemoryItem.metadata_json["source_type"].as_string() == "reflection_generation",
        MemoryItem.metadata_json["theme"].as_string() == theme,
        MemoryItem.metadata_json["source_fact_fingerprint"].as_string() == source_fact_fingerprint,
      )
      .order_by(MemoryItem.created_at.asc())
    )
    return list(self.session.execute(query).scalars())

  def list_by_ids(self, ids: Sequence[UUID]) -> list[MemoryItem]:
    if not ids:
      return []
    query = select(MemoryItem).where(MemoryItem.id.in_(ids))
    return list(self.session.execute(query).scalars())

  def touch(self, item: MemoryItem) -> MemoryItem:
    item.updated_at = datetime.now(UTC)
    self.session.add(item)
    self.session.flush()
    return item

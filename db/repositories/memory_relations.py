from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MemoryRelation


class MemoryRelationRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def create(
    self,
    *,
    source_item_id: UUID,
    target_item_id: UUID,
    relation_type: str,
  ) -> MemoryRelation:
    relation = MemoryRelation(
      source_item_id=source_item_id,
      target_item_id=target_item_id,
      relation_type=relation_type,
    )
    self.session.add(relation)
    self.session.flush()
    return relation

  def list_for_source(self, source_item_id: UUID) -> list[MemoryRelation]:
    query = select(MemoryRelation).where(MemoryRelation.source_item_id == source_item_id)
    return list(self.session.execute(query).scalars())

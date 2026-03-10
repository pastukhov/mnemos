from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MemoryCandidate


class MemoryCandidateRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def create(
    self,
    *,
    domain: str,
    kind: str,
    statement: str,
    confidence: float | None,
    agent_id: str | None,
    evidence: dict[str, object] | None,
    metadata: dict[str, object] | None,
    status: str = "pending",
  ) -> MemoryCandidate:
    candidate = MemoryCandidate(
      domain=domain,
      kind=kind,
      statement=statement,
      confidence=confidence,
      agent_id=agent_id,
      evidence_json=evidence,
      metadata_json=metadata,
      status=status,
    )
    self.session.add(candidate)
    self.session.flush()
    return candidate

  def get(self, candidate_id: UUID) -> MemoryCandidate | None:
    return self.session.get(MemoryCandidate, candidate_id)

  def list_candidates(
    self,
    *,
    status: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
  ) -> list[MemoryCandidate]:
    query = select(MemoryCandidate).order_by(MemoryCandidate.created_at.asc())
    if status is not None:
      query = query.where(MemoryCandidate.status == status)
    if domain is not None:
      query = query.where(MemoryCandidate.domain == domain)
    if kind is not None:
      query = query.where(MemoryCandidate.kind == kind)
    return list(self.session.execute(query).scalars())

  def list_pending_by_ids(self, ids: Sequence[UUID]) -> list[MemoryCandidate]:
    if not ids:
      return []
    query = select(MemoryCandidate).where(
      MemoryCandidate.id.in_(ids),
      MemoryCandidate.status == "pending",
    )
    return list(self.session.execute(query).scalars())

  def touch_review(
    self,
    candidate: MemoryCandidate,
    *,
    status: str,
    metadata: dict[str, object] | None = None,
  ) -> MemoryCandidate:
    candidate.status = status
    candidate.reviewed_at = datetime.now(UTC)
    if metadata is not None:
      candidate.metadata_json = metadata
    self.session.add(candidate)
    self.session.flush()
    return candidate

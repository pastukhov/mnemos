from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import sessionmaker

from api.schemas import MemoryCandidateCreateRequest
from core.logging import get_logger
from db.repositories.candidate_metrics import CandidateMetricRepository
from db.repositories.memory_candidates import MemoryCandidateRepository
from db.repositories.memory_items import MemoryItemRepository

logger = get_logger(__name__)


class MemoryGovernanceService:
  def __init__(self, session_factory: sessionmaker) -> None:
    self.session_factory = session_factory

  def create_candidate(self, payload: MemoryCandidateCreateRequest):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      metric_repository = CandidateMetricRepository(session)
      candidate = repository.create(
        domain=payload.domain,
        kind=payload.kind,
        statement=payload.statement,
        confidence=payload.confidence,
        agent_id=payload.agent_id,
        evidence=payload.evidence,
        metadata=payload.metadata,
      )
      metric_repository.increment(domain=payload.domain, created=1)
      session.commit()
      session.refresh(candidate)
      logger.info(
        "candidate created",
        extra={
          "event": "candidate_created",
          "candidate_id": str(candidate.id),
          "agent_id": candidate.agent_id,
          "domain": candidate.domain,
        },
      )
      return candidate

  def list_candidates(self, *, status: str | None = None, domain: str | None = None, kind: str | None = None):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      return repository.list_candidates(status=status, domain=domain, kind=kind)

  def require_pending_candidate(self, candidate_id: str):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      candidate = repository.get(_parse_candidate_id(candidate_id))
      if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
      if candidate.status != "pending":
        raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail=f"candidate is already {candidate.status}",
        )
      return candidate

  def load_evidence_items(self, candidate) -> list:
    evidence = candidate.evidence_json or {}
    source_fact_ids = evidence.get("source_fact_ids")
    if not isinstance(source_fact_ids, list):
      return []
    parsed_ids = []
    for value in source_fact_ids:
      if isinstance(value, str) and value.strip():
        parsed_ids.append(UUID(value))
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      return repository.list_by_ids(parsed_ids)

  def accept_candidate(self, candidate_id: str, *, merged_item_id: str):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      metric_repository = CandidateMetricRepository(session)
      candidate = repository.get(_parse_candidate_id(candidate_id))
      if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
      metadata = dict(candidate.metadata_json or {})
      metadata["merged_item_id"] = merged_item_id
      repository.touch_review(candidate, status="accepted", metadata=metadata)
      metric_repository.increment(domain=candidate.domain, accepted=1)
      session.commit()
      session.refresh(candidate)
      logger.info(
        "candidate accepted",
        extra={"event": "candidate_accepted", "candidate_id": str(candidate.id)},
      )
      return candidate

  def reject_candidate(self, candidate_id: str, *, reason: str, validation_failure: bool = False):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      metric_repository = CandidateMetricRepository(session)
      candidate = repository.get(_parse_candidate_id(candidate_id))
      if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
      if candidate.status != "pending":
        raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail=f"candidate is already {candidate.status}",
        )
      metadata = dict(candidate.metadata_json or {})
      metadata["rejection_reason"] = reason
      repository.touch_review(candidate, status="rejected", metadata=metadata)
      metric_repository.increment(
        domain=candidate.domain,
        rejected=1,
        validation_failures=1 if validation_failure else 0,
      )
      session.commit()
      session.refresh(candidate)
      logger.info(
        "candidate rejected",
        extra={
          "event": "candidate_rejected",
          "candidate_id": str(candidate.id),
          "reason": reason,
        },
      )
      return candidate


def _parse_candidate_id(candidate_id: str) -> UUID:
  try:
    return UUID(candidate_id)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found") from exc

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from api.schemas import (
  CandidateDedupeHint,
  MemoryCandidateCreateRequest,
  MemoryCandidatePreview,
  MemoryCandidateShortlistItem,
  MemoryCandidateShortlistResponse,
  MemoryCandidateValidateResponse,
  MemoryCandidateValidationIssue,
  ReviewSessionInfo,
  ReviewSessionListResponse,
  ReviewSessionSummary,
)
from core.logging import get_logger
from db.repositories.candidate_metrics import CandidateMetricRepository
from db.repositories.memory_candidates import MemoryCandidateRepository
from db.repositories.memory_items import MemoryItemRepository
from pipelines.governance.validate_candidate import normalize_statement, validate_candidate

logger = get_logger(__name__)


@dataclass(slots=True)
class CandidatePreviewResult:
  valid: bool
  candidate: MemoryCandidateCreateRequest
  errors: list[MemoryCandidateValidationIssue]
  preview: MemoryCandidatePreview
  dedupe_hints: list[CandidateDedupeHint]


class MemoryGovernanceService:
  def __init__(self, session_factory: sessionmaker) -> None:
    self.session_factory = session_factory

  def create_candidate(self, payload: MemoryCandidateCreateRequest):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      metric_repository = CandidateMetricRepository(session)
      evidence, metadata = self._prepare_candidate_enrichment(payload)
      candidate = repository.create(
        domain=payload.domain,
        kind=payload.kind,
        statement=payload.statement,
        confidence=payload.confidence,
        agent_id=payload.agent_id,
        evidence=evidence,
        metadata=metadata,
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

  def create_candidates(self, payloads: list[MemoryCandidateCreateRequest]) -> list:
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      metric_repository = CandidateMetricRepository(session)
      candidates = []
      for payload in payloads:
        evidence, metadata = self._prepare_candidate_enrichment(payload)
        candidate = repository.create(
          domain=payload.domain,
          kind=payload.kind,
          statement=payload.statement,
          confidence=payload.confidence,
          agent_id=payload.agent_id,
          evidence=evidence,
          metadata=metadata,
        )
        metric_repository.increment(domain=payload.domain, created=1)
        candidates.append(candidate)
      session.commit()
      for candidate in candidates:
        session.refresh(candidate)
      logger.info(
        "bulk candidates created",
        extra={
          "event": "bulk_candidates_created",
          "count": len(candidates),
        },
      )
      return candidates

  def validate_candidate_payload(self, payload: dict[str, object]) -> MemoryCandidateValidateResponse:
    try:
      candidate = MemoryCandidateCreateRequest.model_validate(payload)
    except ValidationError as exc:
      return MemoryCandidateValidateResponse(
        valid=False,
        errors=[
          MemoryCandidateValidationIssue(
            loc=[str(part) for part in error["loc"]] or ["__root__"],
            message=error["msg"],
          )
          for error in exc.errors()
        ],
      )
    preview = self.preview_candidate(candidate)
    return MemoryCandidateValidateResponse(
      valid=preview.valid,
      candidate=preview.candidate,
      errors=preview.errors,
      preview=preview.preview,
      dedupe_hints=preview.dedupe_hints,
    )

  def preview_candidate(self, payload: MemoryCandidateCreateRequest) -> CandidatePreviewResult:
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      accepted_items = repository.list_by_domain(domain=payload.domain, status="accepted")
      evidence, metadata = self._prepare_candidate_enrichment(payload)
      candidate_model = self._build_transient_candidate(
        payload=payload,
        evidence=evidence,
        metadata=metadata,
      )
      evidence_items = self._load_evidence_items_from_payload(payload, session=session)
      validation = validate_candidate(
        candidate_model,
        accepted_items=accepted_items,
        evidence_items=evidence_items,
      )
      session_info = self._build_review_session_info(metadata)
      preview = MemoryCandidatePreview(
        normalized_statement=normalize_statement(payload.statement),
        write_mode=payload.write_mode,
        will_create_status="accepted" if validation.valid else "rejected",
        preview_metadata=metadata,
        review_session=session_info,
        dedupe_hints=[CandidateDedupeHint.model_validate(item) for item in validation.dedupe_hints],
        suggested_action=validation.suggested_action,
        suggested_replacement_item_id=(
          str(validation.supersede_target_item.id)
          if validation.supersede_target_item is not None
          else None
        ),
      )
      return CandidatePreviewResult(
        valid=validation.valid,
        candidate=payload,
        errors=[
          MemoryCandidateValidationIssue(loc=["candidate"], message=reason)
          for reason in validation.reasons
        ],
        preview=preview,
        dedupe_hints=[CandidateDedupeHint.model_validate(item) for item in validation.dedupe_hints],
      )

  def shortlist_candidates(self, payloads: list[MemoryCandidateCreateRequest]) -> MemoryCandidateShortlistResponse:
    session_id = None
    session_label = None
    for payload in payloads:
      if payload.review_session_id:
        session_id = payload.review_session_id
      if payload.review_session_label:
        session_label = payload.review_session_label
    if session_id is None:
      session_id = f"review-{uuid4()}"
    items: list[MemoryCandidateShortlistItem] = []
    ready_count = 0
    for index, payload in enumerate(payloads, start=1):
      enriched_payload = payload.model_copy(
        update={
          "review_session_id": payload.review_session_id or session_id,
          "review_session_label": payload.review_session_label or session_label,
        }
      )
      preview = self.preview_candidate(enriched_payload)
      if preview.valid:
        ready_count += 1
      items.append(
        MemoryCandidateShortlistItem(
          index=index,
          valid=preview.valid,
          candidate=preview.candidate,
          errors=preview.errors,
          preview=preview.preview,
          dedupe_hints=preview.dedupe_hints,
        )
      )
    return MemoryCandidateShortlistResponse(
      review_session=ReviewSessionInfo(id=session_id, label=session_label),
      ready_count=ready_count,
      invalid_count=len(items) - ready_count,
      items=items,
    )

  def list_candidates(
    self,
    *,
    status: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
    review_session_id: str | None = None,
  ):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      items = repository.list_candidates(status=status, domain=domain, kind=kind)
      if review_session_id is None:
        return items
      return [
        item
        for item in items
        if (item.metadata_json or {}).get("review_session_id") == review_session_id
      ]

  def list_review_sessions(self) -> ReviewSessionListResponse:
    items = self.list_candidates(status=None)
    grouped: dict[str, list] = defaultdict(list)
    for item in items:
      metadata = item.metadata_json or {}
      session_id = metadata.get("review_session_id")
      if isinstance(session_id, str) and session_id:
        grouped[session_id].append(item)
    summaries: list[ReviewSessionSummary] = []
    for session_id, candidates in grouped.items():
      metadata = candidates[0].metadata_json or {}
      summaries.append(
        ReviewSessionSummary(
          review_session=ReviewSessionInfo(
            id=session_id,
            label=metadata.get("review_session_label"),
            kind=metadata.get("review_session_kind", "review"),
            created_by=metadata.get("review_session_created_by"),
          ),
          candidate_count=len(candidates),
          pending_count=sum(1 for item in candidates if item.status == "pending"),
          accepted_count=sum(1 for item in candidates if item.status == "accepted"),
          rejected_count=sum(1 for item in candidates if item.status == "rejected"),
          superseded_count=sum(1 for item in candidates if item.status == "superseded"),
          latest_created_at=max(item.created_at for item in candidates),
        )
      )
    summaries.sort(key=lambda item: item.latest_created_at, reverse=True)
    return ReviewSessionListResponse(items=summaries)

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

  def load_source_note_item(self, candidate):
    evidence = candidate.evidence_json or {}
    source_note_id = evidence.get("source_note_id")
    if not isinstance(source_note_id, str) or not source_note_id.strip():
      return None
    with self.session_factory() as session:
      repository = MemoryItemRepository(session)
      try:
        return repository.get(UUID(source_note_id))
      except ValueError:
        return None

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

  def supersede_candidate(self, candidate_id: str, *, reason: str):
    with self.session_factory() as session:
      repository = MemoryCandidateRepository(session)
      candidate = repository.get(_parse_candidate_id(candidate_id))
      if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
      metadata = dict(candidate.metadata_json or {})
      metadata["superseded_reason"] = reason
      repository.touch_review(candidate, status="superseded", metadata=metadata)
      session.commit()
      session.refresh(candidate)
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

  def _prepare_candidate_enrichment(
    self,
    payload: MemoryCandidateCreateRequest,
  ) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    evidence = dict(payload.evidence or {})
    metadata = dict(payload.metadata or {})
    metadata["write_mode"] = payload.write_mode
    if payload.review_session_id:
      metadata["review_session_id"] = payload.review_session_id
      metadata["review_session_kind"] = metadata.get("review_session_kind", "review")
      if payload.agent_id:
        metadata["review_session_created_by"] = payload.agent_id
    if payload.review_session_label:
      metadata["review_session_label"] = payload.review_session_label
    if payload.source_note_id:
      evidence["source_note_id"] = payload.source_note_id
    if payload.evidence_ref:
      evidence["evidence_ref"] = payload.evidence_ref
    if payload.source_excerpt:
      evidence["source_excerpt"] = payload.source_excerpt
    return (evidence or None, metadata or None)

  def _build_transient_candidate(
    self,
    *,
    payload: MemoryCandidateCreateRequest,
    evidence: dict[str, object] | None,
    metadata: dict[str, object] | None,
  ):
    return type(
      "TransientCandidate",
      (),
      {
        "domain": payload.domain,
        "kind": payload.kind,
        "statement": payload.statement,
        "confidence": payload.confidence,
        "evidence_json": evidence,
        "metadata_json": metadata,
      },
    )()

  def _build_review_session_info(self, metadata: dict[str, object] | None) -> ReviewSessionInfo | None:
    if not metadata:
      return None
    session_id = metadata.get("review_session_id")
    if not isinstance(session_id, str) or not session_id:
      return None
    return ReviewSessionInfo(
      id=session_id,
      label=metadata.get("review_session_label"),
      kind=metadata.get("review_session_kind", "review"),
      created_by=metadata.get("review_session_created_by"),
    )

  def _load_evidence_items_from_payload(self, payload: MemoryCandidateCreateRequest, *, session):
    evidence = dict(payload.evidence or {})
    source_fact_ids = evidence.get("source_fact_ids")
    if not isinstance(source_fact_ids, list):
      return []
    parsed_ids = []
    for value in source_fact_ids:
      if isinstance(value, str) and value.strip():
        try:
          parsed_ids.append(UUID(value))
        except ValueError:
          continue
    repository = MemoryItemRepository(session)
    return repository.list_by_ids(parsed_ids)


def _parse_candidate_id(candidate_id: str) -> UUID:
  try:
    return UUID(candidate_id)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found") from exc

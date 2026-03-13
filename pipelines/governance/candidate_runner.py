from __future__ import annotations

from dataclasses import dataclass

from db.models import MemoryCandidate, MemoryItem
from pipelines.governance.merge_candidate import merge_candidate_into_memory
from pipelines.governance.validate_candidate import validate_candidate
from services.memory_governance_service import MemoryGovernanceService
from services.memory_service import MemoryService


@dataclass(slots=True)
class CandidateDecision:
  candidate: MemoryCandidate
  merged_item: MemoryItem | None
  validation_errors: list[str]
  dedupe_hints: list[dict] | None = None


class CandidateRunner:
  def __init__(
    self,
    governance_service: MemoryGovernanceService,
    memory_service: MemoryService,
  ) -> None:
    self.governance_service = governance_service
    self.memory_service = memory_service

  def accept(self, candidate_id: str) -> CandidateDecision:
    candidate = self.governance_service.require_pending_candidate(candidate_id)
    accepted_items = self.memory_service.list_items_by_domain(candidate.domain, status="accepted")
    evidence_items = self.governance_service.load_evidence_items(candidate)
    source_note_item = self.governance_service.load_source_note_item(candidate)
    validation = validate_candidate(
      candidate,
      accepted_items=accepted_items,
      evidence_items=evidence_items,
    )
    if not validation.valid:
      rejected = self.governance_service.reject_candidate(
        candidate_id,
        reason="; ".join(validation.reasons),
        validation_failure=True,
      )
      return CandidateDecision(
        candidate=rejected,
        merged_item=None,
        validation_errors=validation.reasons,
        dedupe_hints=validation.dedupe_hints,
      )

    merged_item = merge_candidate_into_memory(
      self.memory_service,
      candidate=candidate,
      evidence_items=validation.evidence_items,
      source_note_item=source_note_item,
    )
    if validation.supersede_target_item is not None:
      self.memory_service.supersede_item(
        item_id=validation.supersede_target_item.id,
        replacement_item_id=merged_item.id,
      )
    accepted = self.governance_service.accept_candidate(candidate_id, merged_item_id=str(merged_item.id))
    return CandidateDecision(
      candidate=accepted,
      merged_item=merged_item,
      validation_errors=[],
      dedupe_hints=validation.dedupe_hints,
    )

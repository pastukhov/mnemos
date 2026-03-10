from __future__ import annotations

from api.schemas import MemoryCreateRequest
from db.models import MemoryCandidate, MemoryItem
from services.memory_service import MemoryService


def merge_candidate_into_memory(
  memory_service: MemoryService,
  *,
  candidate: MemoryCandidate,
  evidence_items: list[MemoryItem],
) -> MemoryItem:
  metadata = dict(candidate.metadata_json or {})
  metadata.update(
    {
      "source_type": "candidate_merge",
      "source_id": str(candidate.id),
      "candidate_id": str(candidate.id),
    }
  )
  if evidence_items:
    metadata["source_fact_ids"] = [str(item.id) for item in evidence_items]

  payload = MemoryCreateRequest(
    domain=candidate.domain,
    kind=candidate.kind,
    statement=candidate.statement,
    confidence=candidate.confidence,
    metadata=metadata,
  )
  relations = [(item.id, "supported_by") for item in evidence_items]
  return memory_service.create_item_with_relations(payload, relations=relations)

from __future__ import annotations

from api.schemas import MemoryCreateRequest
from db.models import MemoryCandidate, MemoryItem
from services.memory_service import MemoryService


def merge_candidate_into_memory(
  memory_service: MemoryService,
  *,
  candidate: MemoryCandidate,
  evidence_items: list[MemoryItem],
  source_note_item: MemoryItem | None = None,
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
  evidence = dict(candidate.evidence_json or {})
  if evidence.get("source_note_id"):
    metadata["source_note_id"] = evidence["source_note_id"]
  if evidence.get("evidence_ref"):
    metadata["evidence_ref"] = evidence["evidence_ref"]
  if evidence.get("source_excerpt"):
    metadata["source_excerpt"] = evidence["source_excerpt"]

  payload = MemoryCreateRequest(
    domain=candidate.domain,
    kind=candidate.kind,
    statement=candidate.statement,
    confidence=candidate.confidence,
    metadata=metadata,
  )
  relations = [(item.id, "supported_by") for item in evidence_items]
  if source_note_item is not None:
    relations.append((source_note_item.id, "derived_from"))
  return memory_service.create_item_with_relations(payload, relations=relations)

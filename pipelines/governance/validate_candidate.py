from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from db.models import MemoryCandidate, MemoryItem

NORMALIZE_RE = re.compile(r"[\W_]+", re.UNICODE)
NEGATIVE_VERBS = ("dislikes", "hates", "avoids", "rejects")
POSITIVE_VERBS = ("likes", "prefers", "enjoys", "values")


def normalize_statement(text: str) -> str:
  return NORMALIZE_RE.sub("", " ".join(text.lower().split()))


@dataclass(slots=True)
class CandidateValidationResult:
  valid: bool
  reasons: list[str] = field(default_factory=list)
  evidence_items: list[MemoryItem] = field(default_factory=list)
  dedupe_hints: list[dict[str, Any]] = field(default_factory=list)
  suggested_action: str | None = None
  supersede_target_item: MemoryItem | None = None


def validate_candidate(
  candidate: MemoryCandidate,
  *,
  accepted_items: list[MemoryItem],
  evidence_items: list[MemoryItem],
) -> CandidateValidationResult:
  reasons: list[str] = []
  dedupe_hints: list[dict[str, Any]] = []
  best_hint: tuple[float, MemoryItem] | None = None
  write_mode = _get_metadata_value(candidate, "write_mode") or "create"

  normalized_candidate = normalize_statement(candidate.statement)
  for item in accepted_items:
    if item.domain != candidate.domain or item.kind != candidate.kind:
      continue
    normalized_existing = normalize_statement(item.statement)
    if not normalized_existing:
      continue
    similarity = SequenceMatcher(None, normalized_candidate, normalized_existing).ratio()
    if similarity >= 0.75:
      action = "consider_upsert"
      dedupe_hints.append(
        {
          "existing_item_id": str(item.id),
          "similarity": round(similarity, 3),
          "statement": item.statement,
          "status": item.status,
          "action": action,
        }
      )
      if best_hint is None or similarity > best_hint[0]:
        best_hint = (similarity, item)
    if similarity >= 0.97:
      reasons.append("candidate duplicates existing accepted memory")
      break

  source_fact_ids = _extract_source_fact_ids(candidate)
  if source_fact_ids:
    evidence_id_set = {str(item.id) for item in evidence_items}
    for fact_id in source_fact_ids:
      if fact_id not in evidence_id_set:
        reasons.append(f"candidate references missing evidence fact: {fact_id}")
    for item in evidence_items:
      if item.kind != "fact":
        reasons.append(f"evidence item is not a fact: {item.id}")
      if item.domain != candidate.domain:
        reasons.append(f"evidence item domain mismatch: {item.id}")

  if _has_basic_contradiction(candidate.statement, accepted_items, candidate.domain):
    reasons.append("candidate may contradict accepted memory")

  supersede_target = None
  suggested_action = None
  if write_mode == "upsert" and best_hint is not None and best_hint[0] >= 0.75:
    supersede_target = best_hint[1]
    suggested_action = "upsert_existing_memory"
  elif best_hint is not None and best_hint[0] >= 0.75:
    suggested_action = "consider_upsert_existing_memory"
  elif dedupe_hints:
    suggested_action = "review_possible_duplicate"

  return CandidateValidationResult(
    valid=not reasons,
    reasons=reasons,
    evidence_items=evidence_items,
    dedupe_hints=dedupe_hints,
    suggested_action=suggested_action,
    supersede_target_item=supersede_target,
  )


def _extract_source_fact_ids(candidate: MemoryCandidate) -> list[str]:
  evidence = candidate.evidence_json or {}
  fact_ids = evidence.get("source_fact_ids")
  if not isinstance(fact_ids, list):
    return []
  return [fact_id for fact_id in fact_ids if isinstance(fact_id, str) and fact_id.strip()]


def _get_metadata_value(candidate: MemoryCandidate, key: str) -> Any:
  metadata = candidate.metadata_json or {}
  return metadata.get(key)


def _has_basic_contradiction(statement: str, accepted_items: list[MemoryItem], domain: str) -> bool:
  normalized = statement.lower()
  for item in accepted_items:
    if item.domain != domain:
      continue
    existing = item.statement.lower()
    for positive in POSITIVE_VERBS:
      for negative in NEGATIVE_VERBS:
        if positive in existing and negative in normalized:
          existing_tail = existing.split(positive, 1)[1].strip(" .")
          candidate_tail = normalized.split(negative, 1)[1].strip(" .")
          if existing_tail and existing_tail == candidate_tail:
            return True
        if negative in existing and positive in normalized:
          existing_tail = existing.split(negative, 1)[1].strip(" .")
          candidate_tail = normalized.split(positive, 1)[1].strip(" .")
          if existing_tail and existing_tail == candidate_tail:
            return True
  return False

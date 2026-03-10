from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

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


def validate_candidate(
  candidate: MemoryCandidate,
  *,
  accepted_items: list[MemoryItem],
  evidence_items: list[MemoryItem],
) -> CandidateValidationResult:
  reasons: list[str] = []

  normalized_candidate = normalize_statement(candidate.statement)
  for item in accepted_items:
    if item.domain != candidate.domain:
      continue
    normalized_existing = normalize_statement(item.statement)
    if not normalized_existing:
      continue
    similarity = SequenceMatcher(None, normalized_candidate, normalized_existing).ratio()
    if similarity >= 0.92:
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

  return CandidateValidationResult(
    valid=not reasons,
    reasons=reasons,
    evidence_items=evidence_items,
  )


def _extract_source_fact_ids(candidate: MemoryCandidate) -> list[str]:
  evidence = candidate.evidence_json or {}
  fact_ids = evidence.get("source_fact_ids")
  if not isinstance(fact_ids, list):
    return []
  return [fact_id for fact_id in fact_ids if isinstance(fact_id, str) and fact_id.strip()]


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

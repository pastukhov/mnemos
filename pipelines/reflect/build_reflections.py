from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from db.models import MemoryItem
from services.memory_service import MemoryService
from pipelines.reflect.reflection_schema import GeneratedReflection

NON_WORD_RE = re.compile(r"[\W_]+", re.UNICODE)


def compute_fact_fingerprint(facts: list[MemoryItem]) -> str:
  joined = "|".join(sorted(str(fact.id) for fact in facts))
  return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def normalize_theme(value: str | None) -> str:
  if not value:
    return "general"
  normalized = NON_WORD_RE.sub("_", value.strip().lower()).strip("_")
  return normalized or "general"


def group_facts_by_theme(memory_service: MemoryService, facts: list[MemoryItem]) -> dict[str, list[MemoryItem]]:
  groups: dict[str, list[MemoryItem]] = defaultdict(list)
  for fact in facts:
    groups[resolve_fact_theme(memory_service, fact)].append(fact)
  return dict(groups)


def resolve_fact_theme(memory_service: MemoryService, fact: MemoryItem) -> str:
  metadata = fact.metadata_json or {}
  for key in ("theme", "topic"):
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
      return normalize_theme(value)

  source_item_id = metadata.get("source_item_id")
  if isinstance(source_item_id, str) and source_item_id.strip():
    source_item = memory_service.get_item(source_item_id)
    if source_item is not None:
      source_metadata = source_item.metadata_json or {}
      for key in ("theme", "topic"):
        value = source_metadata.get(key)
        if isinstance(value, str) and value.strip():
          return normalize_theme(value)
  return "general"


def normalize_statement(text: str) -> str:
  collapsed = " ".join(text.lower().split())
  return NON_WORD_RE.sub("", collapsed)


def validate_generated_reflections(
  reflections: list[GeneratedReflection],
  *,
  input_fact_ids: set[str],
  max_reflections_per_batch: int,
  min_chars: int,
  max_chars: int,
) -> list[GeneratedReflection]:
  if not reflections:
    return []

  valid: list[GeneratedReflection] = []
  seen_statements: set[str] = set()

  for reflection in reflections[:max_reflections_per_batch]:
    statement = " ".join(reflection.statement.split())
    evidence_fact_ids = list(dict.fromkeys(reflection.evidence_fact_ids))
    if not min_chars <= len(statement) <= max_chars:
      continue
    if not 0.0 <= reflection.confidence <= 1.0:
      continue
    if len(evidence_fact_ids) < 2:
      continue
    if any(fact_id not in input_fact_ids for fact_id in evidence_fact_ids):
      continue
    normalized_statement = normalize_statement(statement)
    if not normalized_statement or normalized_statement in seen_statements:
      continue
    seen_statements.add(normalized_statement)
    valid.append(
      GeneratedReflection(
        statement=statement,
        confidence=reflection.confidence,
        evidence_fact_ids=evidence_fact_ids,
      )
    )
  return valid

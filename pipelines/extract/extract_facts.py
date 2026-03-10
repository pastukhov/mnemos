from __future__ import annotations

from pipelines.extract.fact_schema import ExtractedFact


def validate_extracted_facts(
  facts: list[ExtractedFact],
  *,
  max_facts_per_item: int,
  min_chars: int,
  max_chars: int,
) -> list[ExtractedFact]:
  valid: list[ExtractedFact] = []
  for fact in facts:
    statement = " ".join(fact.statement.split())
    if len(statement) < min_chars:
      continue
    if len(statement) > max_chars:
      continue
    valid.append(
      ExtractedFact(
        statement=statement,
        confidence=fact.confidence,
        evidence_reference=fact.evidence_reference,
      )
    )
    if len(valid) >= max_facts_per_item:
      break
  return valid

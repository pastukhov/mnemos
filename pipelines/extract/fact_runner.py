from __future__ import annotations

from dataclasses import dataclass

from api.schemas import MemoryCreateRequest
from core.config import Settings
from core.logging import get_logger
from pipelines.extract.extract_facts import validate_extracted_facts
from pipelines.extract.fact_llm_client import FactLLMClient
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class FactExtractionReport:
  items_processed: int = 0
  facts_created: int = 0
  skipped: int = 0
  errors: int = 0

  def render(self) -> str:
    lines = [
      f"Items processed: {self.items_processed}",
      f"Facts created: {self.facts_created}",
      f"Skipped: {self.skipped}",
    ]
    if self.errors:
      lines.append(f"Errors: {self.errors}")
    return "\n".join(lines)


class FactExtractionRunner:
  def __init__(
    self,
    memory_service: MemoryService,
    llm_client: FactLLMClient,
    settings: Settings,
  ) -> None:
    self.memory_service = memory_service
    self.llm_client = llm_client
    self.settings = settings

  def run(self, *, domain: str = "self") -> FactExtractionReport:
    report = FactExtractionReport()
    raw_items = self.memory_service.list_items_by_domain_kind(domain=domain, kind="raw")
    report.items_processed = len(raw_items)

    for raw_item in raw_items:
      existing_facts = self.memory_service.list_facts_by_source_item_id(source_item_id=str(raw_item.id))
      if existing_facts:
        report.skipped += 1
        continue

      try:
        extracted = self.llm_client.extract_facts(raw_item.statement)
        valid_facts = validate_extracted_facts(
          extracted,
          max_facts_per_item=self.settings.fact_max_facts_per_item,
          min_chars=self.settings.fact_min_chars,
          max_chars=self.settings.fact_max_chars,
        )
        if not valid_facts:
          report.errors += 1
          logger.warning(
            "fact extraction produced no valid facts",
            extra={"event": "fact_extraction_empty", "raw_item_id": str(raw_item.id)},
          )
          continue

        for index, fact in enumerate(valid_facts, start=1):
          payload = MemoryCreateRequest(
            domain=raw_item.domain,
            kind="fact",
            statement=fact.statement,
            confidence=fact.confidence,
            metadata={
              "source_type": "fact_extraction",
              "source_id": f"fact_extraction:{raw_item.id}:{index}",
              "source_item_id": str(raw_item.id),
              "evidence_reference": fact.evidence_reference or raw_item.statement,
            },
          )
          self.memory_service.create_related_item_record(
            payload,
            target_item_id=raw_item.id,
            relation_type="derived_from",
          )
          report.facts_created += 1
      except Exception:
        report.errors += 1
        logger.exception(
          "fact extraction failed",
          extra={"event": "fact_extraction_failed", "raw_item_id": str(raw_item.id)},
        )

    self.memory_service.record_fact_extraction_metrics(
      domain=domain,
      runs=1,
      facts_created=report.facts_created,
      errors=report.errors,
    )
    logger.info(
      "fact extraction run completed",
      extra={
        "event": "fact_extraction",
        "domain": domain,
        "items_processed": report.items_processed,
        "facts_created": report.facts_created,
        "skipped": report.skipped,
        "errors": report.errors,
      },
    )
    return report

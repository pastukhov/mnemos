from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from api.schemas import MemoryCreateRequest
from core.config import Settings
from core.logging import get_logger
from pipelines.reflect.build_reflections import (
  compute_fact_fingerprint,
  group_facts_by_theme,
  normalize_theme,
  validate_generated_reflections,
)
from pipelines.reflect.reflection_llm_client import ReflectionLLMClient
from pipelines.reflect.reflection_schema import ReflectionFactInput
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class ReflectionBuildReport:
  facts_loaded: int = 0
  themes_processed: int = 0
  reflections_created: int = 0
  skipped: int = 0
  errors: int = 0

  def render(self) -> str:
    lines = [
      f"Facts loaded: {self.facts_loaded}",
      f"Themes processed: {self.themes_processed}",
      f"Reflections created: {self.reflections_created}",
      f"Skipped: {self.skipped}",
    ]
    if self.errors:
      lines.append(f"Errors: {self.errors}")
    return "\n".join(lines)


class ReflectionRunner:
  def __init__(
    self,
    memory_service: MemoryService,
    llm_client: ReflectionLLMClient,
    settings: Settings,
  ) -> None:
    self.memory_service = memory_service
    self.llm_client = llm_client
    self.settings = settings

  def run(self, *, domain: str = "self", theme: str | None = None) -> ReflectionBuildReport:
    report = ReflectionBuildReport()
    facts = self.memory_service.list_items_by_domain_kind(domain=domain, kind="fact")
    report.facts_loaded = len(facts)
    grouped_facts = group_facts_by_theme(self.memory_service, facts)
    selected_theme = normalize_theme(theme) if theme else None
    theme_batches = {
      batch_theme: batch_facts
      for batch_theme, batch_facts in grouped_facts.items()
      if selected_theme is None or batch_theme == selected_theme
    }
    report.themes_processed = len(theme_batches)

    logger.info(
      "reflection generation facts loaded",
      extra={"event": "reflection_generation", "domain": domain, "facts_loaded": report.facts_loaded},
    )

    for batch_theme, batch_facts in theme_batches.items():
      if len(batch_facts) < 2:
        report.skipped += 1
        continue

      fingerprint = compute_fact_fingerprint(batch_facts)
      existing = self.memory_service.list_reflections_by_fingerprint(
        domain=domain,
        theme=batch_theme,
        source_fact_fingerprint=fingerprint,
      )
      if existing:
        report.skipped += 1
        continue

      try:
        generated = self.llm_client.generate_reflections(
          theme=batch_theme,
          facts=[
            ReflectionFactInput(id=str(fact.id), statement=fact.statement)
            for fact in batch_facts
          ],
        )
        valid_reflections = validate_generated_reflections(
          generated,
          input_fact_ids={str(fact.id) for fact in batch_facts},
          max_reflections_per_batch=self.settings.reflection_max_per_theme,
          min_chars=self.settings.reflection_min_chars,
          max_chars=self.settings.reflection_max_chars,
        )
        if not valid_reflections:
          report.errors += 1
          logger.warning(
            "reflection generation produced no valid reflections",
            extra={
              "event": "reflection_generation_empty",
              "domain": domain,
              "theme": batch_theme,
              "fingerprint": fingerprint,
            },
          )
          continue

        for index, reflection in enumerate(valid_reflections, start=1):
          payload = MemoryCreateRequest(
            domain=domain,
            kind="reflection",
            statement=reflection.statement,
            confidence=reflection.confidence,
            metadata={
              "source_type": "reflection_generation",
              "source_id": f"reflection_generation:{batch_theme}:{fingerprint}:{index}",
              "theme": batch_theme,
              "source_fact_ids": reflection.evidence_fact_ids,
              "source_fact_fingerprint": fingerprint,
            },
          )
          relations = [
            (UUID(fact_id), "supported_by")
            for fact_id in reflection.evidence_fact_ids
          ]
          self.memory_service.create_item_with_relations(payload, relations=relations)
          report.reflections_created += 1
      except Exception:
        report.errors += 1
        logger.exception(
          "reflection generation failed",
          extra={
            "event": "reflection_generation_failed",
            "domain": domain,
            "theme": batch_theme,
            "fingerprint": fingerprint,
          },
        )

    self.memory_service.record_reflection_metrics(
      domain=domain,
      runs=1,
      reflections_created=report.reflections_created,
      skipped=report.skipped,
      errors=report.errors,
    )
    logger.info(
      "reflection generation run completed",
      extra={
        "event": "reflection_generation",
        "domain": domain,
        "facts_loaded": report.facts_loaded,
        "themes_processed": report.themes_processed,
        "reflections_created": report.reflections_created,
        "skipped": report.skipped,
        "errors": report.errors,
      },
    )
    return report

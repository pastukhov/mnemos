from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from core.logging import get_logger
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.reflect.reflection_runner import ReflectionRunner
from pipelines.wiki.wiki_canonicalization_runner import WikiCanonicalizationRunner
from pipelines.wiki.wiki_lint_runner import WikiLintRunner
from pipelines.wiki.wiki_query_runner import WikiQueryRunner
from pipelines.wiki.wiki_runner import WikiBuildRunner
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class PipelineWorkerRunReport:
  fact_domains: list[str] = field(default_factory=list)
  reflection_domains: list[str] = field(default_factory=list)
  wiki_domains: list[str] = field(default_factory=list)
  wiki_pages: list[str] = field(default_factory=list)
  lint_stale_pages: list[str] = field(default_factory=list)
  lint_empty_pages: list[str] = field(default_factory=list)
  lint_orphan_facts_count: int = 0
  lint_contradictions: list[str] = field(default_factory=list)
  lint_unresolved_source_refs: list[str] = field(default_factory=list)
  lint_low_source_coverage_pages: list[str] = field(default_factory=list)
  lint_canonical_drift_pages: list[str] = field(default_factory=list)
  lint_orphaned_query_pages: list[str] = field(default_factory=list)
  lint_stale_navigation_pages: list[str] = field(default_factory=list)
  lint_overmerged_query_pages: list[str] = field(default_factory=list)
  lint_canonicalization_candidates: list[str] = field(default_factory=list)
  lint_missing_page_candidates: list[str] = field(default_factory=list)
  lint_action_required_findings: list[str] = field(default_factory=list)
  lint_warning_findings: list[str] = field(default_factory=list)
  refreshed_query_pages: list[str] = field(default_factory=list)
  pruned_query_pages: list[str] = field(default_factory=list)
  deduped_query_pages: list[str] = field(default_factory=list)
  promoted_query_pages: list[str] = field(default_factory=list)
  canonicalized_query_pages: list[str] = field(default_factory=list)
  canonicalized_targets: list[str] = field(default_factory=list)
  errors: int = 0


class PipelineWorker:
  def __init__(
    self,
    *,
    memory_service: MemoryService,
    fact_runner: FactExtractionRunner,
    reflection_runner: ReflectionRunner,
    wiki_runner: WikiBuildRunner,
    wiki_lint_runner: WikiLintRunner | None = None,
    wiki_query_runner: WikiQueryRunner | None = None,
    wiki_canonicalization_runner: WikiCanonicalizationRunner | None = None,
    interval_seconds: float,
  ) -> None:
    self.memory_service = memory_service
    self.fact_runner = fact_runner
    self.reflection_runner = reflection_runner
    self.wiki_runner = wiki_runner
    self.wiki_lint_runner = wiki_lint_runner
    self.wiki_query_runner = wiki_query_runner
    self.wiki_canonicalization_runner = wiki_canonicalization_runner
    self.interval_seconds = interval_seconds
    self._stop_event = asyncio.Event()
    self._last_report: PipelineWorkerRunReport | None = None

  async def run(self) -> None:
    logger.info(
      "pipeline worker started",
      extra={
        "event": "pipeline_worker_started",
        "interval_seconds": self.interval_seconds,
      },
    )
    try:
      while not self._stop_event.is_set():
        await self.run_once()
        try:
          await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
        except asyncio.TimeoutError:
          continue
    except asyncio.CancelledError:
      logger.info("pipeline worker cancelled", extra={"event": "pipeline_worker_cancelled"})
      raise
    finally:
      logger.info("pipeline worker stopped", extra={"event": "pipeline_worker_stopped"})

  async def run_once(self) -> PipelineWorkerRunReport:
    report = await asyncio.to_thread(self._run_once_sync)
    self._last_report = report
    return report

  def stop(self) -> None:
    self._stop_event.set()

  def _run_once_sync(self) -> PipelineWorkerRunReport:
    report = PipelineWorkerRunReport()
    wiki_domains_seen: set[str] = set()
    wiki_pages_seen: set[str] = set()

    try:
      fact_domains = self.memory_service.list_domains_with_items(kind="raw")
      for domain in fact_domains:
        fact_report = self.fact_runner.run(domain=domain)
        if fact_report.items_processed:
          report.fact_domains.append(domain)
          if domain not in wiki_domains_seen:
            wiki_domains_seen.add(domain)
            report.wiki_domains.append(domain)

      reflection_domains = self.memory_service.list_domains_with_items(kind="fact", min_count=2)
      for domain in reflection_domains:
        reflection_report = self.reflection_runner.run(domain=domain)
        if reflection_report.facts_loaded:
          report.reflection_domains.append(domain)
          if domain not in wiki_domains_seen:
            wiki_domains_seen.add(domain)
            report.wiki_domains.append(domain)

      for domain in report.wiki_domains:
        self.wiki_runner.run(domain=domain)

      invalidated_pages = self.memory_service.list_invalidated_wiki_pages()
      for page in invalidated_pages:
        if page.page_name in wiki_pages_seen:
          continue
        self.wiki_runner.run(page_name=page.page_name)
        wiki_pages_seen.add(page.page_name)
        report.wiki_pages.append(page.page_name)

      if self.wiki_query_runner is not None:
        refreshed, pruned, deduped, promoted = self.wiki_query_runner.refresh_auto_persisted_pages()
        report.refreshed_query_pages = refreshed
        report.pruned_query_pages = pruned
        report.deduped_query_pages = deduped
        report.promoted_query_pages = promoted
      lint_report = None
      if self.wiki_lint_runner is not None:
        lint_report = self.wiki_lint_runner.run()
      if self.wiki_canonicalization_runner is not None and lint_report is not None:
        canonicalization_report = self.wiki_canonicalization_runner.run(
          candidates=lint_report.canonicalization_candidates,
        )
        report.canonicalized_query_pages = canonicalization_report.canonicalized_pages
        report.canonicalized_targets = canonicalization_report.canonical_targets
        if canonicalization_report.canonicalized_pages and self.wiki_lint_runner is not None:
          lint_report = self.wiki_lint_runner.run()
      if lint_report is not None:
        report.lint_stale_pages = lint_report.stale_pages
        report.lint_empty_pages = lint_report.empty_pages
        report.lint_orphan_facts_count = lint_report.orphan_facts_count
        report.lint_contradictions = lint_report.contradictions
        report.lint_unresolved_source_refs = lint_report.unresolved_source_refs
        report.lint_low_source_coverage_pages = lint_report.low_source_coverage_pages
        report.lint_canonical_drift_pages = lint_report.canonical_drift_pages
        report.lint_orphaned_query_pages = lint_report.orphaned_query_pages
        report.lint_stale_navigation_pages = lint_report.stale_navigation_pages
        report.lint_overmerged_query_pages = lint_report.overmerged_query_pages
        report.lint_canonicalization_candidates = lint_report.canonicalization_candidates
        report.lint_missing_page_candidates = lint_report.missing_page_candidates
        report.lint_action_required_findings = lint_report.finding_codes(severity="action")
        report.lint_warning_findings = lint_report.finding_codes(severity="warn")
    except Exception:
      report.errors += 1
      logger.exception("pipeline worker cycle failed", extra={"event": "pipeline_worker_failed"})

    logger.info(
      "pipeline worker cycle completed",
      extra={
        "event": "pipeline_worker_cycle",
        "fact_domains": report.fact_domains,
        "reflection_domains": report.reflection_domains,
        "wiki_domains": report.wiki_domains,
        "wiki_pages": report.wiki_pages,
        "lint_stale_pages": report.lint_stale_pages,
        "lint_empty_pages": report.lint_empty_pages,
        "lint_orphan_facts_count": report.lint_orphan_facts_count,
        "lint_contradictions": report.lint_contradictions,
        "lint_unresolved_source_refs": report.lint_unresolved_source_refs,
        "lint_low_source_coverage_pages": report.lint_low_source_coverage_pages,
        "lint_canonical_drift_pages": report.lint_canonical_drift_pages,
        "lint_orphaned_query_pages": report.lint_orphaned_query_pages,
        "lint_stale_navigation_pages": report.lint_stale_navigation_pages,
        "lint_overmerged_query_pages": report.lint_overmerged_query_pages,
        "lint_canonicalization_candidates": report.lint_canonicalization_candidates,
        "lint_missing_page_candidates": report.lint_missing_page_candidates,
        "lint_action_required_findings": report.lint_action_required_findings,
        "lint_warning_findings": report.lint_warning_findings,
        "refreshed_query_pages": report.refreshed_query_pages,
        "pruned_query_pages": report.pruned_query_pages,
        "deduped_query_pages": report.deduped_query_pages,
        "promoted_query_pages": report.promoted_query_pages,
        "canonicalized_query_pages": report.canonicalized_query_pages,
        "canonicalized_targets": report.canonicalized_targets,
        "errors": report.errors,
      },
    )
    return report

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from core.logging import get_logger
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.reflect.reflection_runner import ReflectionRunner
from pipelines.wiki.wiki_runner import WikiBuildRunner
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class PipelineWorkerRunReport:
  fact_domains: list[str] = field(default_factory=list)
  reflection_domains: list[str] = field(default_factory=list)
  wiki_domains: list[str] = field(default_factory=list)
  wiki_pages: list[str] = field(default_factory=list)
  errors: int = 0


class PipelineWorker:
  def __init__(
    self,
    *,
    memory_service: MemoryService,
    fact_runner: FactExtractionRunner,
    reflection_runner: ReflectionRunner,
    wiki_runner: WikiBuildRunner,
    interval_seconds: float,
  ) -> None:
    self.memory_service = memory_service
    self.fact_runner = fact_runner
    self.reflection_runner = reflection_runner
    self.wiki_runner = wiki_runner
    self.interval_seconds = interval_seconds
    self._stop_event = asyncio.Event()

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
    return await asyncio.to_thread(self._run_once_sync)

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
        "errors": report.errors,
      },
    )
    return report

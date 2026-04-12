"""Wiki build runner for generating wiki pages from facts and reflections."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings
from core.logging import get_logger
from pipelines.wiki.build_page import (
  compute_page_fingerprint,
  encode_cached_page_content,
  extract_cached_page_fingerprint,
  strip_cached_page_metadata,
)
from pipelines.wiki.wiki_llm_client import WikiLLMClient
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class WikiBuildReport:
  """Report of wiki build run."""

  pages_built: int = 0
  pages_updated: int = 0
  pages_skipped: int = 0
  errors: int = 0

  def render(self) -> str:
    """Render human-readable report."""
    lines = [
      f"Pages built: {self.pages_built}",
      f"Pages updated: {self.pages_updated}",
      f"Pages skipped: {self.pages_skipped}",
    ]
    if self.errors:
      lines.append(f"Errors: {self.errors}")
    return "\n".join(lines)


class WikiBuildRunner:
  """Runner for building wiki pages from facts and reflections."""

  def __init__(
    self,
    memory_service: MemoryService,
    wiki_llm_client: WikiLLMClient,
    settings: Settings,
  ) -> None:
    """Initialize wiki build runner."""
    self.memory_service = memory_service
    self.llm_client = wiki_llm_client
    self.settings = settings
    self.schema: WikiSchema | None = None

  def run(
    self,
    domain: str | None = None,
    page_name: str | None = None,
  ) -> WikiBuildReport:
    """Run wiki build pipeline."""
    report = WikiBuildReport()

    if self.schema is None:
      try:
        self.schema = WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
      except FileNotFoundError:
        logger.error(
          "wiki schema file not found",
          extra={
            "event": "wiki_build_schema_not_found",
            "path": self.settings.wiki_schema_path,
          },
        )
        report.errors += 1
        return report

    logger.info(
      "wiki build starting",
      extra={
        "event": "wiki_build",
        "pages_total": len(self.schema.pages),
        "domain_filter": domain,
        "page_name_filter": page_name,
      },
    )

    for page_def in self.schema.pages:
      if page_name and page_def.name != page_name:
        report.pages_skipped += 1
        continue

      if domain and domain not in page_def.domains:
        report.pages_skipped += 1
        continue

      self._build_page(page_def, report, domain)

    logger.info(
      "wiki build completed",
      extra={
        "event": "wiki_build",
        "pages_built": report.pages_built,
        "pages_updated": report.pages_updated,
        "pages_skipped": report.pages_skipped,
        "errors": report.errors,
      },
    )

    return report

  def _build_page(
    self,
    page_def: WikiPageDefinition,
    report: WikiBuildReport,
    domain_filter: str | None = None,
  ) -> None:
    """Build a single wiki page from facts and reflections."""
    try:
      facts_list, reflections_list = self._load_items_for_page(
        page_def,
        domain_filter,
      )

      if len(facts_list) < self.settings.wiki_min_facts_per_page:
        report.pages_skipped += 1
        logger.info(
          "wiki page skipped: insufficient facts",
          extra={
            "event": "wiki_build_skip_insufficient_facts",
            "page_name": page_def.name,
            "facts_count": len(facts_list),
            "min_required": self.settings.wiki_min_facts_per_page,
          },
        )
        return

      fingerprint = compute_page_fingerprint(page_def, facts_list, reflections_list)
      existing_page = self.memory_service.get_wiki_page(page_def.name)
      existing_fingerprint = None
      if existing_page is not None:
        existing_fingerprint = extract_cached_page_fingerprint(existing_page.content_md)

      if (
        existing_page is not None
        and existing_page.invalidated_at is None
        and existing_fingerprint == fingerprint
      ):
        report.pages_skipped += 1
        logger.info(
          "wiki page skipped: fingerprint unchanged",
          extra={
            "event": "wiki_build_skip_unchanged",
            "page_name": page_def.name,
            "fingerprint": fingerprint,
          },
        )
        return

      markdown_content = self.llm_client.synthesize_page(
        page_def=page_def,
        facts=facts_list,
        reflections=reflections_list,
        existing_content=(
          strip_cached_page_metadata(existing_page.content_md)
          if existing_page is not None
          else None
        ),
      )

      cached_content = encode_cached_page_content(
        fingerprint=fingerprint,
        content_md=markdown_content,
      )
      self.memory_service.upsert_wiki_page(
        page_name=page_def.name,
        title=page_def.title,
        content_md=cached_content,
        facts_count=len(facts_list),
        reflections_count=len(reflections_list),
        invalidated_at=None,
      )

      if existing_page is None:
        report.pages_built += 1
        log_event = "wiki_build_created"
      else:
        report.pages_updated += 1
        log_event = "wiki_build_updated"

      logger.info(
        f"wiki page {log_event.split('_')[-1]}",
        extra={
          "event": log_event,
          "page_name": page_def.name,
          "facts_count": len(facts_list),
          "reflections_count": len(reflections_list),
          "fingerprint": fingerprint,
        },
      )

    except Exception:
      report.errors += 1
      logger.exception(
        "wiki page synthesis failed",
        extra={
          "event": "wiki_build_failed",
          "page_name": page_def.name,
        },
      )

  def _load_items_for_page(
    self,
    page_def: WikiPageDefinition,
    domain_filter: str | None = None,
  ) -> tuple[list[str], list[str]]:
    """Load facts and reflections for a page definition."""
    facts_list: list[str] = []
    reflections_list: list[str] = []

    domains_to_load = [domain_filter] if domain_filter else page_def.domains

    for domain in domains_to_load:
      for kind in page_def.kinds:
        items = self.memory_service.list_items_by_domain_kind(
          domain=domain,
          kind=kind,
        )

        if page_def.themes:
          items = [
            item
            for item in items
            if item.metadata_json and item.metadata_json.get("theme") in page_def.themes
          ]

        item_statements = [item.statement for item in items]

        if kind in self.settings.wiki_facts_kinds:
          facts_list.extend(item_statements)
        elif kind in self.settings.wiki_reflections_kinds:
          reflections_list.extend(item_statements)

    return facts_list, reflections_list

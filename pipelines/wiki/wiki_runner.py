"""Wiki build runner for generating wiki pages from facts and reflections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from core.config import Settings
from core.logging import get_logger
from pipelines.wiki.build_page import (
  compute_page_fingerprint,
  encode_cached_page_content,
  enrich_page_markdown,
  extract_cached_page_fingerprint,
  strip_cached_page_metadata,
)
from pipelines.wiki.constants import NAVIGATION_PAGE_NAMES
from pipelines.wiki.navigation_pages import (
  build_index_page,
  build_log_page,
  compute_content_fingerprint,
)
from pipelines.wiki.wiki_llm_client import WikiLLMClient
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema
from services.memory_service import MemoryService

logger = get_logger(__name__)

_DESCRIPTION_STOP_WORDS = frozenset({
  "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
  "get", "gets", "got", "has", "have", "how", "in", "into", "is", "it",
  "its", "not", "of", "on", "or", "s", "that", "the", "their", "they",
  "this", "to", "was", "what", "when", "which", "who", "with",
})


def _description_tokens(text: str) -> frozenset[str]:
  """Return meaningful keyword tokens from a description, title, or theme list."""
  return frozenset(
    t for t in re.findall(r"[a-z0-9]+", text.lower())
    if t not in _DESCRIPTION_STOP_WORDS and len(t) > 2
  )


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
    self._built_pages: set[str] = set()

  def run(
    self,
    domain: str | None = None,
    page_name: str | None = None,
  ) -> WikiBuildReport:
    """Run wiki build pipeline."""
    report = WikiBuildReport()
    self.schema = None
    self._built_pages = {
      p.page_name for p in self.memory_service.list_wiki_pages()
      if p.invalidated_at is None
    }

    try:
      schema = WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
      self.schema = schema
    except FileNotFoundError:
      schema = WikiSchema(pages=[])
      logger.error(
        "wiki schema file not found",
        extra={
          "event": "wiki_build_schema_not_found",
          "path": self.settings.wiki_schema_path,
        },
      )
      if page_name not in NAVIGATION_PAGE_NAMES:
        report.errors += 1
        if page_name is not None:
          return report

    logger.info(
      "wiki build starting",
      extra={
        "event": "wiki_build",
        "pages_total": len(schema.pages),
        "domain_filter": domain,
        "page_name_filter": page_name,
      },
    )

    if page_name in NAVIGATION_PAGE_NAMES:
      self._build_navigation_page(page_name=page_name, report=report, schema=schema)
      return report

    for page_def in schema.pages:
      if page_name and page_def.name != page_name:
        report.pages_skipped += 1
        continue

      if domain and domain not in page_def.domains:
        report.pages_skipped += 1
        continue

      self._build_page(page_def, report, domain)

    if page_name is None:
      for synthetic_page_name in ("log", "index"):
        self._build_navigation_page(page_name=synthetic_page_name, report=report, schema=schema)

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
      source_refs = self._load_source_refs_for_page(
        page_def,
        domain_filter,
      )
      source_highlights = self._load_source_highlights_for_page(
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

      related_pages = self._related_pages_for(page_def)
      fingerprint = compute_page_fingerprint(
        page_def,
        facts_list,
        reflections_list,
        related_page_names=[page["name"] for page in related_pages],
        source_refs=source_refs,
      )
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
        related_pages=related_pages if related_pages else None,
      )

      enriched_markdown = enrich_page_markdown(
        content_md=markdown_content,
        page_def=page_def,
        facts_count=len(facts_list),
        reflections_count=len(reflections_list),
        related_pages=related_pages,
        source_refs=source_refs,
        source_highlights=source_highlights,
      )
      cached_content = encode_cached_page_content(
        fingerprint=fingerprint,
        content_md=enriched_markdown,
      )
      self.memory_service.upsert_wiki_page(
        page_name=page_def.name,
        title=page_def.title,
        content_md=cached_content,
        facts_count=len(facts_list),
        reflections_count=len(reflections_list),
        metadata={
          "page_kind": "canonical",
          "origin": "schema",
          "domains": list(page_def.domains),
          "themes": list(page_def.themes),
          "canonical_target": None,
          "merge_count": 0,
          "superseded_by": None,
          "last_maintained_at": datetime.now(UTC).isoformat(),
        },
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

      if "summary" not in page_def.kinds:
        canonical_summary_items = self.memory_service.list_items_by_domain_kind(
          domain=domain,
          kind="summary",
        )
        canonical_summary_items = [
          item
          for item in canonical_summary_items
          if item.metadata_json and item.metadata_json.get("canonical_page") == page_def.name
        ]
        facts_list.extend(item.statement for item in canonical_summary_items)

    return facts_list, reflections_list

  def _load_source_refs_for_page(
    self,
    page_def: WikiPageDefinition,
    domain_filter: str | None = None,
  ) -> list[str]:
    domains_to_load = [domain_filter] if domain_filter else page_def.domains
    source_refs: list[str] = []
    seen: set[str] = set()

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
        for item in items:
          source_ref = self._source_ref_for_item(item)
          if source_ref in seen:
            continue
          seen.add(source_ref)
          source_refs.append(source_ref)

      if "summary" not in page_def.kinds:
        canonical_summary_items = self.memory_service.list_items_by_domain_kind(
          domain=domain,
          kind="summary",
        )
        canonical_summary_items = [
          item
          for item in canonical_summary_items
          if item.metadata_json and item.metadata_json.get("canonical_page") == page_def.name
        ]
        for item in canonical_summary_items:
          source_ref = self._source_ref_for_item(item)
          if source_ref in seen:
            continue
          seen.add(source_ref)
          source_refs.append(source_ref)

    return source_refs

  def _load_source_highlights_for_page(
    self,
    page_def: WikiPageDefinition,
    domain_filter: str | None = None,
  ) -> list[dict[str, str]]:
    domains_to_load = [domain_filter] if domain_filter else page_def.domains
    highlights: list[dict[str, str]] = []
    seen: set[str] = set()

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
        for item in items:
          source_ref = self._source_ref_for_item(item)
          if source_ref in seen:
            continue
          seen.add(source_ref)
          highlights.append(
            {
              "source_ref": source_ref,
              "statement": self._truncate_source_statement(item.statement),
            }
          )
          if len(highlights) >= 5:
            return highlights

      if "summary" not in page_def.kinds:
        canonical_summary_items = self.memory_service.list_items_by_domain_kind(
          domain=domain,
          kind="summary",
        )
        canonical_summary_items = [
          item
          for item in canonical_summary_items
          if item.metadata_json and item.metadata_json.get("canonical_page") == page_def.name
        ]
        for item in canonical_summary_items:
          source_ref = self._source_ref_for_item(item)
          if source_ref in seen:
            continue
          seen.add(source_ref)
          highlights.append(
            {
              "source_ref": source_ref,
              "statement": self._truncate_source_statement(item.statement),
            }
          )
          if len(highlights) >= 5:
            return highlights

    return highlights

  def _source_ref_for_item(self, item) -> str:
    metadata = item.metadata_json or {}
    source_type = metadata.get("source_type")
    source_id = metadata.get("source_id")
    if source_type and source_id:
      return f"{source_type}:{source_id}"
    return f"memory:{item.id}"

  def _truncate_source_statement(self, statement: str, *, limit: int = 140) -> str:
    normalized = " ".join(statement.split())
    if len(normalized) <= limit:
      return normalized
    return f"{normalized[: limit - 1].rstrip()}…"

  def _related_pages_for(self, page_def: WikiPageDefinition) -> list[dict[str, str]]:
    if self.schema is None:
      return []

    page_desc_tokens = _description_tokens(
      " ".join([page_def.title, page_def.description, *page_def.themes])
    )
    current_domains = set(page_def.domains)
    current_themes = set(page_def.themes)
    current_kinds = set(page_def.kinds)

    related: list[tuple[int, str, str]] = []
    for candidate in self.schema.pages:
      if candidate.name == page_def.name:
        continue
      domain_overlap = len(current_domains & set(candidate.domains))
      theme_overlap = len(current_themes & set(candidate.themes))
      kind_overlap = len(current_kinds & set(candidate.kinds))
      score = (theme_overlap * 10) + (domain_overlap * 3) + kind_overlap
      if score <= 0:
        continue
      # Bonus for description/title/theme keyword overlap — prefer semantically closer pages.
      candidate_desc_tokens = _description_tokens(
        " ".join([candidate.title, candidate.description, *candidate.themes])
      )
      score += len(page_desc_tokens & candidate_desc_tokens) * 2
      # Small bonus for pages that are already built — prefer linking to pages that exist.
      if candidate.name in self._built_pages:
        score += 1
      related.append((score, candidate.name, candidate.title))

    related.sort(key=lambda item: (-item[0], item[2].lower(), item[1]))
    return [
      {"name": name, "title": title}
      for _, name, title in related[:5]
    ]

  def _build_navigation_page(
    self,
    *,
    page_name: str,
    report: WikiBuildReport,
    schema: WikiSchema,
  ) -> None:
    try:
      cached_pages = self.memory_service.list_wiki_pages()
      if page_name == "index":
        content = build_index_page(
          schema_pages=schema.pages,
          cached_pages=cached_pages,
        )
      elif page_name == "log":
        content = build_log_page(
          items=self.memory_service.list_recent_items(
            status="accepted",
          )
        )
      else:
        report.pages_skipped += 1
        return

      fingerprint = compute_content_fingerprint(content.content_md)
      existing_page = self.memory_service.get_wiki_page(page_name)
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
          "wiki navigation page skipped: fingerprint unchanged",
          extra={
            "event": "wiki_navigation_skip_unchanged",
            "page_name": page_name,
            "fingerprint": fingerprint,
          },
        )
        return

      cached_content = encode_cached_page_content(
        fingerprint=fingerprint,
        content_md=content.content_md,
      )
      self.memory_service.upsert_wiki_page(
        page_name=page_name,
        title=content.title,
        content_md=cached_content,
        facts_count=content.facts_count,
        reflections_count=content.reflections_count,
        metadata={
          "page_kind": "navigation",
          "origin": "synthetic",
          "domains": [],
          "themes": [],
          "canonical_target": None,
          "merge_count": 0,
          "superseded_by": None,
          "last_maintained_at": datetime.now(UTC).isoformat(),
        },
        invalidated_at=None,
      )

      if existing_page is None:
        report.pages_built += 1
        log_event = "wiki_navigation_created"
      else:
        report.pages_updated += 1
        log_event = "wiki_navigation_updated"

      logger.info(
        "wiki navigation page maintained",
        extra={
          "event": log_event,
          "page_name": page_name,
          "fingerprint": fingerprint,
          "facts_count": content.facts_count,
          "reflections_count": content.reflections_count,
        },
      )
    except Exception:
      report.errors += 1
      logger.exception(
        "wiki navigation page build failed",
        extra={
          "event": "wiki_navigation_failed",
          "page_name": page_name,
        },
      )

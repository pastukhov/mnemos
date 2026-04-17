from __future__ import annotations

from dataclasses import dataclass, field
import re

from pipelines.wiki.build_page import strip_cached_page_metadata
from core.config import Settings
from pipelines.wiki.constants import NAVIGATION_PAGE_NAMES
from pipelines.wiki.wiki_schema import WikiPageDefinition
from pipelines.wiki.wiki_schema import WikiSchema
from services.memory_service import MemoryService

WIKI_LINK_PATTERN = re.compile(r"\]\(wiki:([a-z0-9_-]+)\)", re.IGNORECASE)
SOURCE_REF_PATTERN = re.compile(r"^- source_ref:\s+.+$", re.MULTILINE)
SOURCE_REF_CAPTURE_PATTERN = re.compile(r"^- source_ref:\s+(.+)$", re.MULTILINE)
SOURCE_HIGHLIGHT_PATTERN = re.compile(r"^## Source Highlights$", re.MULTILINE)
SOURCE_HIGHLIGHT_SECTION_PATTERN = re.compile(r"## Source Highlights\s+(.+?)(?:\n## |\Z)", re.DOTALL)
SOURCE_HIGHLIGHT_ITEM_PATTERN = re.compile(r"^- \[[^\]]+\]\s+.+$", re.MULTILINE)
MERGE_PROVENANCE_SECTION_PATTERN = re.compile(r"## Merge Provenance\s+(.+?)(?:\n## |\Z)", re.DOTALL)
RELATED_PAGES_SECTION_PATTERN = re.compile(r"## Related Pages\s+(.*?)(?:\n## |\Z)", re.DOTALL)
QUERY_SECTION_PATTERN = re.compile(r"## Query\s+(.+?)(?:\n## |\Z)", re.DOTALL)
QUERY_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9\s]")
QUERY_STOP_WORDS = {
  "a",
  "an",
  "and",
  "are",
  "build",
  "builds",
  "can",
  "do",
  "does",
  "for",
  "how",
  "in",
  "is",
  "kind",
  "of",
  "the",
  "to",
  "user",
  "what",
  "which",
  "with",
}
ANTONYM_CANONICAL_MAP = {
  "likes": "prefer",
  "dislikes": "prefer",
  "prefers": "prefer",
  "rejects": "prefer",
  "enjoys": "enjoy",
  "hates": "enjoy",
  "works remotely": "work_mode",
  "works on site": "work_mode",
  "works onsite": "work_mode",
}
ANTONYM_POLARITY_MAP = {
  "likes": 1,
  "dislikes": -1,
  "prefers": 1,
  "rejects": -1,
  "enjoys": 1,
  "hates": -1,
  "works remotely": 1,
  "works on site": -1,
  "works onsite": -1,
}
QUANTIFIER_POLARITY_MAP = {
  "always": 1,
  "often": 1,
  "frequently": 1,
  "never": -1,
  "rarely": -1,
  "seldom": -1,
}
NEGATION_PATTERNS = (
  re.compile(r"\bdoes not\b"),
  re.compile(r"\bdo not\b"),
  re.compile(r"\bdid not\b"),
  re.compile(r"\bis not\b"),
  re.compile(r"\bare not\b"),
  re.compile(r"\bcannot\b"),
  re.compile(r"\bcan not\b"),
  re.compile(r"\bnever\b"),
  re.compile(r"\bno longer\b"),
  re.compile(r"\bnot\b"),
)


@dataclass(slots=True)
class WikiLintFinding:
  code: str
  severity: str
  count: int
  items: list[str] = field(default_factory=list)


CANONICAL_REQUIRED_SECTIONS = frozenset({
  "## Provenance",
  "## Source Highlights",
})
CANONICAL_CONTENT_SECTIONS = frozenset({
  "## Overview",
  "## Key Points",
  "## Summary",
  "## Notes",
  "## Background",
  "## Details",
  "## Context",
  "## Facts",
  "## Reflections",
})


@dataclass(slots=True)
class WikiLintReport:
  stale_pages: list[str] = field(default_factory=list)
  empty_pages: list[str] = field(default_factory=list)
  orphan_facts_count: int = 0
  contradictions: list[str] = field(default_factory=list)
  fixed_pages: list[str] = field(default_factory=list)
  missing_related_pages: list[str] = field(default_factory=list)
  missing_provenance_pages: list[str] = field(default_factory=list)
  missing_source_refs_pages: list[str] = field(default_factory=list)
  missing_source_highlights_pages: list[str] = field(default_factory=list)
  low_source_coverage_pages: list[str] = field(default_factory=list)
  unresolved_source_refs: list[str] = field(default_factory=list)
  broken_wiki_links: list[str] = field(default_factory=list)
  canonical_drift_pages: list[str] = field(default_factory=list)
  orphaned_query_pages: list[str] = field(default_factory=list)
  stale_navigation_pages: list[str] = field(default_factory=list)
  overmerged_query_pages: list[str] = field(default_factory=list)
  canonicalization_candidates: list[str] = field(default_factory=list)
  missing_page_candidates: list[str] = field(default_factory=list)
  weakly_connected_pages: list[str] = field(default_factory=list)
  editorial_structure_issues: list[str] = field(default_factory=list)

  def findings(self) -> list[WikiLintFinding]:
    findings: list[WikiLintFinding] = []
    specs = (
      ("stale_pages", "warn", len(self.stale_pages), self.stale_pages),
      ("empty_pages", "action", len(self.empty_pages), self.empty_pages),
      ("orphan_facts", "warn", self.orphan_facts_count, []),
      ("contradictions", "action", len(self.contradictions), self.contradictions),
      ("missing_related_pages", "info", len(self.missing_related_pages), self.missing_related_pages),
      (
        "missing_provenance_pages",
        "warn",
        len(self.missing_provenance_pages),
        self.missing_provenance_pages,
      ),
      (
        "missing_source_refs_pages",
        "action",
        len(self.missing_source_refs_pages),
        self.missing_source_refs_pages,
      ),
      (
        "missing_source_highlights_pages",
        "warn",
        len(self.missing_source_highlights_pages),
        self.missing_source_highlights_pages,
      ),
      (
        "low_source_coverage_pages",
        "warn",
        len(self.low_source_coverage_pages),
        self.low_source_coverage_pages,
      ),
      (
        "unresolved_source_refs",
        "action",
        len(self.unresolved_source_refs),
        self.unresolved_source_refs,
      ),
      ("broken_wiki_links", "action", len(self.broken_wiki_links), self.broken_wiki_links),
      ("canonical_drift_pages", "action", len(self.canonical_drift_pages), self.canonical_drift_pages),
      ("orphaned_query_pages", "action", len(self.orphaned_query_pages), self.orphaned_query_pages),
      ("stale_navigation_pages", "warn", len(self.stale_navigation_pages), self.stale_navigation_pages),
      (
        "overmerged_query_pages",
        "warn",
        len(self.overmerged_query_pages),
        self.overmerged_query_pages,
      ),
      (
        "canonicalization_candidates",
        "action",
        len(self.canonicalization_candidates),
        self.canonicalization_candidates,
      ),
      ("missing_page_candidates", "info", len(self.missing_page_candidates), self.missing_page_candidates),
      (
        "weakly_connected_pages",
        "warn",
        len(self.weakly_connected_pages),
        self.weakly_connected_pages,
      ),
      (
        "editorial_structure_issues",
        "warn",
        len(self.editorial_structure_issues),
        self.editorial_structure_issues,
      ),
    )
    for code, severity, count, items in specs:
      if count <= 0:
        continue
      findings.append(WikiLintFinding(code=code, severity=severity, count=count, items=list(items)))
    return findings

  def finding_codes(self, *, severity: str) -> list[str]:
    return [finding.code for finding in self.findings() if finding.severity == severity]

  def render(self) -> str:
    findings = self.findings()
    lines = [
      f"Stale pages: {len(self.stale_pages)}",
      f"Empty pages: {len(self.empty_pages)}",
      f"Orphan facts: {self.orphan_facts_count}",
      f"Contradictions: {len(self.contradictions)}",
      f"Missing related pages sections: {len(self.missing_related_pages)}",
      f"Missing provenance sections: {len(self.missing_provenance_pages)}",
      f"Missing source refs: {len(self.missing_source_refs_pages)}",
      f"Missing source highlights: {len(self.missing_source_highlights_pages)}",
      f"Low source coverage: {len(self.low_source_coverage_pages)}",
      f"Unresolved source refs: {len(self.unresolved_source_refs)}",
      f"Broken wiki links: {len(self.broken_wiki_links)}",
      f"Canonical drift pages: {len(self.canonical_drift_pages)}",
      f"Orphaned query pages: {len(self.orphaned_query_pages)}",
      f"Stale navigation pages: {len(self.stale_navigation_pages)}",
      f"Overmerged query pages: {len(self.overmerged_query_pages)}",
      f"Canonicalization candidates: {len(self.canonicalization_candidates)}",
      f"Missing page candidates: {len(self.missing_page_candidates)}",
      f"Weakly connected pages: {len(self.weakly_connected_pages)}",
      f"Editorial structure issues: {len(self.editorial_structure_issues)}",
      f"Action findings: {len([finding for finding in findings if finding.severity == 'action'])}",
      f"Warning findings: {len([finding for finding in findings if finding.severity == 'warn'])}",
    ]
    if self.fixed_pages:
      lines.append(f"Fixed pages: {', '.join(self.fixed_pages)}")
    return "\n".join(lines)


class WikiLintRunner:
  def __init__(
    self,
    memory_service: MemoryService,
    settings: Settings,
    *,
    wiki_runner=None,
  ) -> None:
    self.memory_service = memory_service
    self.settings = settings
    self.wiki_runner = wiki_runner

  def run(self, domain: str | None = None, *, fix: bool = False) -> WikiLintReport:
    report = WikiLintReport()
    pages = self.memory_service.list_wiki_pages()
    schema = self._load_schema()
    known_page_names = self._known_page_names(pages=pages, schema=schema)
    backlinks_by_target = self._build_backlink_index(pages=pages)

    for page in pages:
      if domain and not self._page_matches_domain(page.page_name, domain=domain, schema=schema):
        continue
      if page.invalidated_at is not None:
        report.stale_pages.append(page.page_name)
      if page.page_name not in NAVIGATION_PAGE_NAMES and page.facts_count < self.settings.wiki_min_facts_per_page:
        report.empty_pages.append(page.page_name)
      self._lint_page_content(
        page=page,
        report=report,
        schema=schema,
        known_page_names=known_page_names,
      )

    report.orphan_facts_count = self._count_orphan_facts(domain=domain, schema=schema)
    report.contradictions = self._find_contradictions(domain=domain)
    report.canonical_drift_pages = self._find_canonical_drift_pages(
      pages=pages,
      domain=domain,
      schema=schema,
    )
    report.orphaned_query_pages = self._find_orphaned_query_pages(
      pages=pages,
      domain=domain,
      schema=schema,
      backlinks_by_target=backlinks_by_target,
    )
    report.stale_navigation_pages = self._find_stale_navigation_pages(
      pages=pages,
      domain=domain,
    )
    report.missing_page_candidates = self._find_missing_page_candidates(domain=domain, schema=schema)
    report.weakly_connected_pages = self._find_weakly_connected_pages(
      pages=pages,
      domain=domain,
      backlinks_by_target=backlinks_by_target,
    )
    report.editorial_structure_issues = self._find_editorial_structure_issues(
      pages=pages,
      domain=domain,
      schema=schema,
    )

    if fix and self.wiki_runner is not None:
      for page_name in report.stale_pages:
        self.wiki_runner.run(page_name=page_name)
        report.fixed_pages.append(page_name)

    return report

  def _load_schema(self) -> WikiSchema | None:
    try:
      return WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
    except FileNotFoundError:
      return None

  def _page_matches_domain(
    self,
    page_name: str,
    *,
    domain: str,
    schema: WikiSchema | None,
  ) -> bool:
    if page_name in NAVIGATION_PAGE_NAMES:
      return True
    if schema is None:
      return False
    page_def = schema.get_page(page_name)
    if page_def is None:
      return False
    return domain in page_def.domains

  def _count_orphan_facts(self, *, domain: str | None, schema: WikiSchema | None) -> int:
    if schema is None:
      return 0

    facts = []
    domains = [domain] if domain else sorted({page_domain for page in schema.pages for page_domain in page.domains})
    for current_domain in domains:
      facts.extend(self.memory_service.list_items_by_domain_kind(domain=current_domain, kind="fact"))

    orphan_count = 0
    for fact in facts:
      matched = False
      fact_theme = fact.metadata_json.get("theme") if fact.metadata_json else None
      for page_def in schema.pages:
        if fact.domain not in page_def.domains:
          continue
        if "fact" not in page_def.kinds:
          continue
        if page_def.themes and fact_theme not in page_def.themes:
          continue
        matched = True
        break
      if not matched:
        orphan_count += 1
    return orphan_count

  def _known_page_names(self, *, pages, schema: WikiSchema | None) -> set[str]:
    names = {page.page_name for page in pages}
    names.update(NAVIGATION_PAGE_NAMES)
    if schema is not None:
      names.update(page.name for page in schema.pages)
    return names

  def _build_backlink_index(self, *, pages) -> dict[str, set[str]]:
    backlinks: dict[str, set[str]] = {}
    for page in pages:
      content = strip_cached_page_metadata(page.content_md)
      for target in WIKI_LINK_PATTERN.findall(content):
        backlinks.setdefault(target, set()).add(page.page_name)
    return backlinks

  def _lint_page_content(
    self,
    *,
    page,
    report: WikiLintReport,
    schema: WikiSchema | None,
    known_page_names: set[str],
  ) -> None:
    content = strip_cached_page_metadata(page.content_md)
    if page.page_name not in NAVIGATION_PAGE_NAMES and "## Provenance" not in content:
      report.missing_provenance_pages.append(page.page_name)
    if (
      page.page_name not in NAVIGATION_PAGE_NAMES
      and page.facts_count + page.reflections_count > 0
      and not SOURCE_REF_PATTERN.search(content)
    ):
      report.missing_source_refs_pages.append(page.page_name)
    if (
      page.page_name not in NAVIGATION_PAGE_NAMES
      and page.facts_count + page.reflections_count > 0
      and not SOURCE_HIGHLIGHT_PATTERN.search(content)
    ):
      report.missing_source_highlights_pages.append(page.page_name)
    coverage_issue = self._source_coverage_issue(page=page, content=content)
    if coverage_issue is not None:
      report.low_source_coverage_pages.append(coverage_issue)
    for source_ref in SOURCE_REF_CAPTURE_PATTERN.findall(content):
      resolved = self._source_ref_resolves(source_ref.strip())
      if not resolved:
        report.unresolved_source_refs.append(f"{page.page_name} -> {source_ref.strip()}")
    overmerged_issue = self._overmerged_query_issue(page=page, content=content)
    if overmerged_issue is not None:
      report.overmerged_query_pages.append(overmerged_issue)
      canonical_target = self._canonical_target_for_query_page(page=page, content=content, schema=schema)
      if canonical_target is not None:
        report.canonicalization_candidates.append(f"{page.page_name} -> {canonical_target}")

    page_def = schema.get_page(page.page_name) if schema is not None else None
    if page.page_name not in NAVIGATION_PAGE_NAMES and page_def is not None:
      expected_related = self._expected_related_pages_for(page_def=page_def, schema=schema)
      if expected_related:
        if "## Related Pages" not in content:
          report.missing_related_pages.append(page.page_name)
        elif expected_related[0] not in self._extract_links_from_related_section(content):
          # Section exists but the top expected related page is not linked.
          report.missing_related_pages.append(page.page_name)

    for target in WIKI_LINK_PATTERN.findall(content):
      if target not in known_page_names:
        report.broken_wiki_links.append(f"{page.page_name} -> {target}")

  def _overmerged_query_issue(self, *, page, content: str) -> str | None:
    prefix = f"{self.settings.wiki_query_auto_persist_prefix.strip('-_') or 'qa'}-"
    if not page.page_name.startswith(prefix):
      return None
    match = MERGE_PROVENANCE_SECTION_PATTERN.search(content)
    if not match:
      return None
    entries = [line.strip() for line in match.group(1).splitlines() if line.strip().startswith("- ")]
    if len(entries) <= self.settings.wiki_query_merge_provenance_max_entries:
      return None
    return (
      f"{page.page_name} ({len(entries)}/{self.settings.wiki_query_merge_provenance_max_entries})"
    )

  def _canonical_target_for_query_page(
    self,
    *,
    page,
    content: str,
    schema: WikiSchema | None,
  ) -> str | None:
    query_match = QUERY_SECTION_PATTERN.search(content)
    if query_match is None:
      return None
    query_tokens = {
      token
      for token in QUERY_TOKEN_PATTERN.findall(query_match.group(1).lower())
      if token not in QUERY_STOP_WORDS and len(token) > 1
    }
    linked_pages = [
      target for target in WIKI_LINK_PATTERN.findall(content) if target not in NAVIGATION_PAGE_NAMES
    ]
    if not linked_pages:
      return None
    scored_candidates: list[tuple[int, str]] = []
    for candidate_name in sorted(set(linked_pages)):
      score = linked_pages.count(candidate_name) * 5
      if schema is not None:
        page_def = schema.get_page(candidate_name)
        if page_def is not None:
          candidate_tokens = {
            token
            for token in QUERY_TOKEN_PATTERN.findall(
              " ".join(
                [page_def.name, page_def.title, page_def.description, *page_def.themes]
              ).lower()
            )
            if token not in QUERY_STOP_WORDS and len(token) > 1
          }
          score += len(query_tokens & candidate_tokens)
      scored_candidates.append((score, candidate_name))
    if not scored_candidates:
      return None
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))
    return scored_candidates[0][1]

  def _expected_related_pages_for(
    self,
    *,
    page_def: WikiPageDefinition,
    schema: WikiSchema | None,
  ) -> list[str]:
    if schema is None:
      return []

    related: list[tuple[int, str]] = []
    current_domains = set(page_def.domains)
    current_themes = set(page_def.themes)
    current_kinds = set(page_def.kinds)
    for candidate in schema.pages:
      if candidate.name == page_def.name:
        continue
      domain_overlap = len(current_domains & set(candidate.domains))
      theme_overlap = len(current_themes & set(candidate.themes))
      kind_overlap = len(current_kinds & set(candidate.kinds))
      score = (theme_overlap * 10) + (domain_overlap * 3) + kind_overlap
      if score <= 0:
        continue
      related.append((score, candidate.name))

    related.sort(key=lambda item: (-item[0], item[1]))
    return [name for _, name in related[:5]]

  def _find_contradictions(self, *, domain: str | None) -> list[str]:
    grouped: dict[tuple[str, str | None], dict[tuple[int, str], list[str]]] = {}
    domains = [domain] if domain else list(("self", "project", "operational", "interaction"))
    for current_domain in domains:
      for fact in self.memory_service.list_items_by_domain_kind(domain=current_domain, kind="fact"):
        theme = fact.metadata_json.get("theme") if fact.metadata_json else None
        for normalized in self._normalized_variants(fact.statement):
          polarity, canonical = normalized
          theme_bucket = grouped.setdefault((current_domain, theme), {})
          theme_bucket.setdefault((polarity, canonical), []).append(fact.statement)

    contradictions: list[str] = []
    for (current_domain, theme), variants in grouped.items():
      for (_, canonical), positive_statements in variants.items():
        negative_key = (-1, canonical)
        positive_key = (1, canonical)
        if positive_key not in variants or negative_key not in variants:
          continue
        positive_example = sorted(variants[positive_key])[0]
        negative_example = sorted(variants[negative_key])[0]
        label = f"{current_domain}"
        if theme:
          label = f"{label}/{theme}"
        contradiction = f"{label}: '{positive_example}' <-> '{negative_example}'"
        if contradiction not in contradictions:
          contradictions.append(contradiction)

    contradictions.sort()
    return contradictions

  def _normalized_variants(self, statement: str) -> list[tuple[int, str]]:
    variants: list[tuple[int, str]] = []
    default_variant = self._normalize_statement(statement)
    if default_variant is not None:
      variants.append(default_variant)
    structured_variant = self._normalize_structured_statement(statement)
    if structured_variant is not None and structured_variant not in variants:
      variants.append(structured_variant)
    return variants

  def _normalize_statement(self, statement: str) -> tuple[int, str] | None:
    text = statement.strip().lower()
    if not text:
      return None
    polarity = -1 if any(pattern.search(text) for pattern in NEGATION_PATTERNS) else 1
    canonical = text
    for pattern in NEGATION_PATTERNS:
      canonical = pattern.sub(" ", canonical)
    canonical = PUNCTUATION_PATTERN.sub(" ", canonical)
    canonical = " ".join(self._normalize_token(token) for token in canonical.split())
    if not canonical:
      return None
    return polarity, canonical

  def _normalize_structured_statement(self, statement: str) -> tuple[int, str] | None:
    text = statement.strip().lower()
    if not text:
      return None
    text = PUNCTUATION_PATTERN.sub(" ", text)
    text = " ".join(text.split())
    for phrase, canonical in ANTONYM_CANONICAL_MAP.items():
      prefix = f"user {phrase}"
      if text != prefix and not text.startswith(f"{prefix} "):
        continue
      obj = text.removeprefix(prefix).strip()
      normalized_object = " ".join(self._normalize_token(token) for token in obj.split())
      canonical_text = f"user {canonical}" if not normalized_object else f"user {canonical} {normalized_object}"
      return (ANTONYM_POLARITY_MAP[phrase], canonical_text)
    for quantifier, polarity in QUANTIFIER_POLARITY_MAP.items():
      if not text.startswith(f"user {quantifier} "):
        continue
      obj = text.removeprefix(f"user {quantifier} ").strip()
      if not obj:
        return None
      normalized_object = " ".join(self._normalize_token(token) for token in obj.split())
      return (polarity, f"user habit {normalized_object}")
    return None

  def _normalize_token(self, token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
      return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
      return token[:-1]
    return token

  def _extract_links_from_related_section(self, content: str) -> set[str]:
    match = RELATED_PAGES_SECTION_PATTERN.search(content)
    if not match:
      return set()
    return set(WIKI_LINK_PATTERN.findall(match.group(1)))

  def _source_ref_resolves(self, source_ref: str) -> bool:
    if source_ref.startswith("memory:"):
      memory_id = source_ref.split(":", 1)[1]
      return self.memory_service.get_item(memory_id) is not None
    source_type, sep, source_id = source_ref.partition(":")
    if not sep or not source_type or not source_id:
      return False
    return self.memory_service.get_item_by_source_ref(
      source_type=source_type,
      source_id=source_id,
    ) is not None

  def _source_coverage_issue(self, *, page, content: str) -> str | None:
    if page.page_name in NAVIGATION_PAGE_NAMES:
      return None
    total_items = page.facts_count + page.reflections_count
    if total_items <= 0:
      return None
    section_match = SOURCE_HIGHLIGHT_SECTION_PATTERN.search(content)
    if section_match is None:
      return None
    highlights_count = len(SOURCE_HIGHLIGHT_ITEM_PATTERN.findall(section_match.group(1)))
    expected = min(self.settings.wiki_source_highlights_target_count, total_items)
    if highlights_count >= expected:
      return None
    return f"{page.page_name} ({highlights_count}/{expected})"

  def _find_canonical_drift_pages(
    self,
    *,
    pages,
    domain: str | None,
    schema: WikiSchema | None,
  ) -> list[str]:
    if schema is None:
      return []
    drifted: list[str] = []
    for page in pages:
      if page.page_name in NAVIGATION_PAGE_NAMES:
        continue
      page_def = schema.get_page(page.page_name)
      if page_def is None:
        continue
      if domain and not self._page_matches_domain(page.page_name, domain=domain, schema=schema):
        continue
      content = strip_cached_page_metadata(page.content_md)
      if self._canonical_drift_issue(page=page, content=content, page_def=page_def):
        drifted.append(page.page_name)
        continue
      latest_update = self._latest_source_update_for_page(page_name=page.page_name, page_def=page_def)
      if latest_update is None:
        continue
      if latest_update > page.generated_at:
        drifted.append(page.page_name)
    return sorted(set(drifted))

  def _latest_source_update_for_page(
    self,
    *,
    page_name: str,
    page_def: WikiPageDefinition,
  ):
    latest = None
    candidate_kinds = set(page_def.kinds) | {"summary"}
    for current_domain in page_def.domains:
      for kind in candidate_kinds:
        for item in self.memory_service.list_items_by_domain_kind(domain=current_domain, kind=kind):
          metadata = item.metadata_json or {}
          item_theme = metadata.get("theme")
          canonical_page = metadata.get("canonical_page")
          if canonical_page == page_name:
            latest = item.updated_at if latest is None or item.updated_at > latest else latest
            continue
          if kind not in page_def.kinds:
            continue
          if page_def.themes and item_theme not in page_def.themes:
            continue
          latest = item.updated_at if latest is None or item.updated_at > latest else latest
    return latest

  def _canonical_drift_issue(
    self,
    *,
    page,
    content: str,
    page_def: WikiPageDefinition,
  ) -> bool:
    metadata = getattr(page, "metadata_json", None) or {}
    if metadata.get("page_kind") != "canonical":
      return True
    if metadata.get("origin") != "schema":
      return True
    if metadata.get("canonical_target") is not None:
      return True
    if int(metadata.get("merge_count") or 0) != 0:
      return True
    if metadata.get("superseded_by") is not None:
      return True
    if page.title != page_def.title:
      return True
    if sorted(metadata.get("domains") or []) != sorted(page_def.domains):
      return True
    if sorted(metadata.get("themes") or []) != sorted(page_def.themes):
      return True
    if any(section in content for section in ("## Query", "## Answer", "## Sources", "## Merge Provenance")):
      return True
    return False

  def _find_orphaned_query_pages(
    self,
    *,
    pages,
    domain: str | None,
    schema: WikiSchema | None,
    backlinks_by_target: dict[str, set[str]],
  ) -> list[str]:
    prefix = f"{self.settings.wiki_query_auto_persist_prefix.strip('-_') or 'qa'}-"
    orphaned: list[str] = []
    for page in pages:
      metadata = getattr(page, "metadata_json", None) or {}
      if not (
        page.page_name.startswith(prefix)
        or metadata.get("page_kind") == "query"
      ):
        continue
      if metadata.get("superseded_by"):
        continue
      if domain and metadata.get("domains") and domain not in metadata.get("domains", []):
        continue
      content = strip_cached_page_metadata(page.content_md)
      question = QUERY_SECTION_PATTERN.search(content)
      canonical_target = self._canonical_target_for_query_page(page=page, content=content, schema=schema)
      backlinks = backlinks_by_target.get(page.page_name, set()) - {page.page_name}
      if (
        question is not None
        and metadata.get("canonical_target") is None
        and int(metadata.get("merge_count") or 0) == 0
        and not backlinks
        and canonical_target is None
      ):
        orphaned.append(page.page_name)
    return sorted(set(orphaned))

  def _find_stale_navigation_pages(
    self,
    *,
    pages,
    domain: str | None,
  ) -> list[str]:
    pages_by_name = {page.page_name: page for page in pages}
    stale_navigation: list[str] = []
    if "index" in pages_by_name:
      index_page = pages_by_name["index"]
      if index_page.invalidated_at is not None:
        stale_navigation.append("index")
      else:
        latest_page_generated_at = None
        for page in pages:
          if page.page_name in NAVIGATION_PAGE_NAMES:
            continue
          metadata = getattr(page, "metadata_json", None) or {}
          if domain and metadata.get("domains") and domain not in metadata.get("domains", []):
            continue
          latest_page_generated_at = (
            page.generated_at
            if latest_page_generated_at is None or page.generated_at > latest_page_generated_at
            else latest_page_generated_at
          )
          if page.invalidated_at is not None:
            stale_navigation.append("index")
            break
        if (
          latest_page_generated_at is not None
          and "index" not in stale_navigation
          and index_page.generated_at < latest_page_generated_at
        ):
          stale_navigation.append("index")
    if "log" in pages_by_name:
      log_page = pages_by_name["log"]
      if log_page.invalidated_at is not None:
        stale_navigation.append("log")
      else:
        latest_item_created_at = None
        for item in self.memory_service.list_recent_items(status="accepted", limit=50):
          if domain and item.domain != domain:
            continue
          latest_item_created_at = (
            item.created_at
            if latest_item_created_at is None or item.created_at > latest_item_created_at
            else latest_item_created_at
          )
        if latest_item_created_at is not None and log_page.generated_at < latest_item_created_at:
          stale_navigation.append("log")
    return sorted(set(stale_navigation))

  def _find_weakly_connected_pages(
    self,
    *,
    pages,
    domain: str | None,
    backlinks_by_target: dict[str, set[str]],
  ) -> list[str]:
    weakly_connected: list[str] = []
    for page in pages:
      if page.page_name in NAVIGATION_PAGE_NAMES:
        continue
      metadata = getattr(page, "metadata_json", None) or {}
      if metadata.get("page_kind") != "canonical":
        continue
      if domain and metadata.get("domains") and domain not in metadata.get("domains", []):
        continue
      inbound = backlinks_by_target.get(page.page_name, set()) - NAVIGATION_PAGE_NAMES
      if not inbound:
        weakly_connected.append(page.page_name)
    return sorted(set(weakly_connected))

  def _find_editorial_structure_issues(
    self,
    *,
    pages,
    domain: str | None,
    schema: WikiSchema | None,
  ) -> list[str]:
    issues: list[str] = []
    for page in pages:
      if page.page_name in NAVIGATION_PAGE_NAMES:
        continue
      metadata = getattr(page, "metadata_json", None) or {}
      if metadata.get("page_kind") != "canonical":
        continue
      if domain and metadata.get("domains") and domain not in metadata.get("domains", []):
        continue
      content = strip_cached_page_metadata(page.content_md)
      issue = self._editorial_structure_issue(page=page, content=content)
      if issue is not None:
        issues.append(issue)
    return sorted(set(issues))

  def _editorial_structure_issue(self, *, page, content: str) -> str | None:
    # A canonical page must have at least one recognisable content section
    # (something other than metadata/provenance sections generated automatically).
    has_content_section = any(section in content for section in CANONICAL_CONTENT_SECTIONS)
    # Also accept any ## heading that is not a system/provenance heading
    system_headings = {
      "## Provenance",
      "## Source Highlights",
      "## Related Pages",
      "## Query",
      "## Answer",
      "## Sources",
      "## Merge Provenance",
    }
    lines = content.splitlines()
    for line in lines:
      stripped = line.strip()
      if stripped.startswith("## ") and stripped not in system_headings:
        has_content_section = True
        break
    if not has_content_section and page.facts_count + page.reflections_count > 0:
      return f"{page.page_name} (missing content section)"
    return None

  def _find_missing_page_candidates(self, *, domain: str | None, schema: WikiSchema | None) -> list[str]:
    if schema is None:
      return []
    counts: dict[tuple[str, str], int] = {}
    domains = [domain] if domain else sorted({page_domain for page in schema.pages for page_domain in page.domains})
    for current_domain in domains:
      for fact in self.memory_service.list_items_by_domain_kind(domain=current_domain, kind="fact"):
        metadata = fact.metadata_json or {}
        theme = metadata.get("theme")
        if not isinstance(theme, str) or not theme.strip():
          continue
        matched = False
        for page_def in schema.pages:
          if current_domain not in page_def.domains:
            continue
          if "fact" not in page_def.kinds:
            continue
          if page_def.themes and theme not in page_def.themes:
            continue
          matched = True
          break
        if not matched:
          key = (current_domain, theme)
          counts[key] = counts.get(key, 0) + 1
    candidates = [
      f"{current_domain}/{theme} -> create canonical page ({count} facts)"
      for (current_domain, theme), count in sorted(counts.items())
    ]
    return candidates

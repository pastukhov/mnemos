from __future__ import annotations

from dataclasses import dataclass
import re

from api.schemas import MemoryCreateRequest
from core.logging import get_logger
from pipelines.wiki.constants import NAVIGATION_PAGE_NAMES
from services.memory_service import MemoryService

logger = get_logger(__name__)

QUERY_SECTION_PATTERN = re.compile(r"## Query\s+(.+?)(?:\n## |\Z)", re.DOTALL)
ANSWER_SECTION_PATTERN = re.compile(r"## Answer\s+(.+?)(?:\n## |\Z)", re.DOTALL)
MERGE_PROVENANCE_SECTION_PATTERN = re.compile(r"## Merge Provenance\s+(.+?)(?:\n## |\Z)", re.DOTALL)
WIKI_LINK_PATTERN = re.compile(r"\]\(wiki:([a-z0-9_-]+)\)", re.IGNORECASE)


@dataclass(slots=True)
class WikiCanonicalizationReport:
  canonicalized_pages: list[str]
  canonical_targets: list[str]
  skipped_pages: list[str]


class WikiCanonicalizationRunner:
  def __init__(
    self,
    memory_service: MemoryService,
    settings,
    *,
    wiki_runner=None,
  ) -> None:
    self.memory_service = memory_service
    self.settings = settings
    self.wiki_runner = wiki_runner

  def run(self, *, candidates: list[str]) -> WikiCanonicalizationReport:
    canonicalized_pages: list[str] = []
    canonical_targets: list[str] = []
    skipped_pages: list[str] = []
    for candidate in candidates:
      source_page_name, canonical_target = self._parse_candidate(candidate)
      if source_page_name is None or canonical_target is None:
        skipped_pages.append(candidate)
        continue
      outcome = self.canonicalize_page(
        source_page_name=source_page_name,
        canonical_target=canonical_target,
      )
      if outcome:
        canonicalized_pages.append(source_page_name)
        canonical_targets.append(canonical_target)
      else:
        skipped_pages.append(source_page_name)
    return WikiCanonicalizationReport(
      canonicalized_pages=sorted(canonicalized_pages),
      canonical_targets=sorted(set(canonical_targets)),
      skipped_pages=sorted(skipped_pages),
    )

  def canonicalize_page(
    self,
    *,
    source_page_name: str,
    canonical_target: str,
  ) -> bool:
    page = self.memory_service.get_wiki_page(source_page_name)
    if page is None:
      return False
    question = self._extract_section(page.content_md, QUERY_SECTION_PATTERN)
    answer = self._extract_section(page.content_md, ANSWER_SECTION_PATTERN)
    if question is None or answer is None:
      return False
    domain = self._extract_domain_from_auto_page_name(source_page_name)
    linked_pages = sorted(
      target
      for target in set(WIKI_LINK_PATTERN.findall(page.content_md))
      if target not in NAVIGATION_PAGE_NAMES
    )
    merge_provenance_count = self._merge_provenance_count(page.content_md)
    statement = self._build_summary_statement(
      canonical_target=canonical_target,
      question=question,
      answer=answer,
      linked_pages=linked_pages,
      merge_provenance_count=merge_provenance_count,
    )
    source_id = f"{canonical_target}:{source_page_name}"
    payload = MemoryCreateRequest(
      domain=domain,
      kind="summary",
      statement=statement,
      confidence=0.8,
      metadata={
        "source_type": "wiki_canonicalization",
        "source_id": source_id,
        "canonical_page": canonical_target,
        "source_page_name": source_page_name,
        "source_question": question,
        "theme": canonical_target,
        "linked_pages": linked_pages,
        "merge_provenance_count": merge_provenance_count,
      },
    )
    self.memory_service.upsert_item_by_source_ref(
      payload,
      source_type="wiki_canonicalization",
      source_id=source_id,
    )
    deleted = self.memory_service.delete_wiki_page(source_page_name)
    if self.wiki_runner is not None:
      for page_name in (canonical_target, "log", "index"):
        self.wiki_runner.run(page_name=page_name)
    logger.info(
      "wiki query page canonicalized",
      extra={
        "event": "wiki_query_page_canonicalized",
        "source_page_name": source_page_name,
        "canonical_target": canonical_target,
        "deleted_source_page": deleted,
      },
    )
    return True

  def _extract_section(self, content_md: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(content_md)
    if not match:
      return None
    section = " ".join(match.group(1).strip().split())
    return section or None

  def _merge_provenance_count(self, content_md: str) -> int:
    match = MERGE_PROVENANCE_SECTION_PATTERN.search(content_md)
    if not match:
      return 0
    return len([line for line in match.group(1).splitlines() if line.strip().startswith("- ")])

  def _build_summary_statement(
    self,
    *,
    canonical_target: str,
    question: str,
    answer: str,
    linked_pages: list[str],
    merge_provenance_count: int,
  ) -> str:
    linked = ", ".join(linked_pages) if linked_pages else "none"
    return (
      f"Canonicalized wiki Q&A for '{canonical_target}'. "
      f"Question: {question} "
      f"Answer: {answer} "
      f"Linked source pages: {linked}. "
      f"Merge provenance count: {merge_provenance_count}."
    )

  def _parse_candidate(self, candidate: str) -> tuple[str | None, str | None]:
    source_page_name, separator, canonical_target = candidate.partition(" -> ")
    if not separator:
      return None, None
    source_page_name = source_page_name.strip()
    canonical_target = canonical_target.strip()
    if not source_page_name or not canonical_target:
      return None, None
    return source_page_name, canonical_target

  def _extract_domain_from_auto_page_name(self, page_name: str) -> str:
    prefix = f"{self.settings.wiki_query_auto_persist_prefix.strip('-_') or 'qa'}-"
    if not page_name.startswith(prefix):
      return "self"
    remainder = page_name[len(prefix):]
    domain, _, _ = remainder.partition("-")
    if domain in {"self", "project", "operational", "interaction"}:
      return domain
    return "self"

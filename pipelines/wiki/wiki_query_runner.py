from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from unicodedata import normalize

from api.schemas import MemoryCreateRequest
from api.schemas import MemoryQueryRequest
from pipelines.wiki.constants import NAVIGATION_PAGE_NAMES
from pipelines.wiki.wiki_schema import WikiSchema
from services.memory_service import MemoryService
from services.retrieval_service import RetrievalService

WIKI_LINK_PATTERN = re.compile(r"\]\(wiki:([a-z0-9_-]+)\)", re.IGNORECASE)
QUERY_SECTION_PATTERN = re.compile(r"## Query\s+(.+?)(?:\n## |\Z)", re.DOTALL)
SECTION_PATTERN_TEMPLATE = r"(^## {heading}\s*\n+)(.*?)(?=^## |\Z)"
QUESTION_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
QUESTION_STOP_WORDS = {
  "a",
  "an",
  "and",
  "are",
  "can",
  "do",
  "does",
  "for",
  "how",
  "i",
  "in",
  "is",
  "kind",
  "me",
  "of",
  "the",
  "their",
  "they",
  "to",
  "what",
  "which",
  "who",
  "why",
  "with",
  "work",
  "works",
  "user",
}


QUERY_OUTCOME_EPHEMERAL = "ephemeral"
QUERY_OUTCOME_QUERY_PAGE = "query_page"
QUERY_OUTCOME_CANONICAL_PROMOTION = "canonical_promotion"


@dataclass(slots=True)
class WikiQueryResult:
  answer: str
  sources: list[str]
  confidence: float
  persisted_page_name: str | None = None
  promoted_canonical_target: str | None = None
  pruned_page_name: str | None = None
  outcome: str = QUERY_OUTCOME_EPHEMERAL


class WikiQueryRunner:
  def __init__(
    self,
    memory_service: MemoryService,
    retrieval_service: RetrievalService,
    settings,
    *,
    wiki_runner=None,
  ) -> None:
    self.memory_service = memory_service
    self.retrieval_service = retrieval_service
    self.settings = settings
    self.wiki_runner = wiki_runner

  def query(
    self,
    question: str,
    *,
    domain: str = "self",
    top_k: int = 5,
    auto_persist: bool | None = None,
    persist_page_name: str | None = None,
    persist_title: str | None = None,
  ) -> WikiQueryResult:
    retrieval = self.retrieval_service.query(
      MemoryQueryRequest(query=question, domain=domain, top_k=top_k, kinds=["fact", "reflection", "summary", "decision", "task", "note"])
    )
    schema = self._load_schema()
    seed_page_names = self._match_page_names(items=retrieval.items, domain=domain, schema=schema)
    page_names = self._collect_page_names(
      seed_page_names=seed_page_names,
      domain=domain,
      max_pages=max(4, top_k + 2),
    )

    if not page_names:
      result = WikiQueryResult(
        answer="No relevant wiki pages found for this question yet.",
        sources=[],
        confidence=0.0,
      )
      self._persist_answer(
        result=result,
        question=question,
        domain=domain,
        auto_persist=auto_persist,
        page_name=persist_page_name,
        title=persist_title,
      )
      return result

    seed_set = set(seed_page_names)
    related_set = set(page_names) - seed_set - NAVIGATION_PAGE_NAMES
    index_snippet: str | None = None
    log_snippet: str | None = None
    seed_snippets: list[str] = []
    related_snippets: list[str] = []
    resolved_sources: list[str] = []
    for page_name in page_names:
      page = self._resolve_page(page_name)
      if page is None:
        continue
      resolved_sources.append(page_name)
      snippet = self._snippet(page.content_md)
      formatted = f"[{page_name}] {snippet}"
      if page_name == "index":
        index_snippet = formatted
      elif page_name == "log":
        log_snippet = formatted
      elif page_name in seed_set:
        seed_snippets.append(formatted)
      elif page_name in related_set:
        related_snippets.append(formatted)

    if not resolved_sources:
      result = WikiQueryResult(
        answer="Relevant wiki pages are stale or unavailable. Rebuild the wiki and try again.",
        sources=[],
        confidence=0.0,
      )
      self._persist_answer(
        result=result,
        question=question,
        domain=domain,
        auto_persist=auto_persist,
        page_name=persist_page_name,
        title=persist_title,
      )
      return result

    answer_lines = [
      f"Question: {question}",
      "",
      "Wiki synthesis:",
    ]
    if index_snippet is not None:
      answer_lines.extend(["", "Index overview:", index_snippet])
    if seed_snippets:
      answer_lines.extend(["", "Relevant pages:"])
      answer_lines.extend(seed_snippets)
    if related_snippets:
      answer_lines.extend(["", "Related pages:"])
      answer_lines.extend(related_snippets)
    if log_snippet is not None:
      answer_lines.extend(["", "Recent activity:", log_snippet])

    confidence = min(1.0, 0.35 + 0.15 * len(resolved_sources))
    result = WikiQueryResult(
      answer="\n".join(answer_lines),
      sources=resolved_sources,
      confidence=round(confidence, 2),
    )
    self._persist_answer(
      result=result,
      question=question,
      domain=domain,
      auto_persist=auto_persist,
      page_name=persist_page_name,
      title=persist_title,
    )
    return result

  def _load_schema(self) -> WikiSchema | None:
    try:
      return WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
    except FileNotFoundError:
      return None

  def _match_page_names(self, *, items, domain: str, schema: WikiSchema | None) -> list[str]:
    matched: list[str] = []
    seen: set[str] = set()
    if schema is not None:
      for item in items:
        item_theme = item.metadata.get("theme") if item.metadata else None
        for page_def in schema.pages:
          if page_def.name in seen:
            continue
          if domain not in page_def.domains:
            continue
          if item.kind not in page_def.kinds:
            continue
          if page_def.themes and item_theme not in page_def.themes:
            continue
          seen.add(page_def.name)
          matched.append(page_def.name)
    return matched

  def _collect_page_names(
    self,
    *,
    seed_page_names: list[str],
    domain: str,
    max_pages: int,
  ) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(page_name: str) -> None:
      if page_name in seen:
        return
      seen.add(page_name)
      ordered.append(page_name)

    if self.memory_service.get_wiki_page("index") is not None:
      add("index")
    if self.memory_service.get_wiki_page("log") is not None:
      add("log")
    for page_name in seed_page_names:
      add(page_name)

    for page_name in list(seed_page_names):
      page = self._resolve_page(page_name)
      if page is None:
        continue
      for linked_page_name in self._extract_linked_pages(page.content_md):
        if linked_page_name in NAVIGATION_PAGE_NAMES:
          add(linked_page_name)
          continue
        if self._page_matches_domain(linked_page_name, domain=domain):
          add(linked_page_name)
        if len(ordered) >= max_pages:
          break
      if len(ordered) >= max_pages:
        break

    return ordered[:max_pages]

  def _snippet(self, content_md: str, *, limit: int = 280) -> str:
    lines = []
    for raw_line in content_md.splitlines():
      line = raw_line.strip()
      if not line or line.startswith("<!--"):
        continue
      lines.append(line)
      if len(" ".join(lines)) >= limit:
        break
    text = " ".join(lines)
    if len(text) <= limit:
      return text
    return f"{text[: limit - 1].rstrip()}…"

  def _resolve_page(self, page_name: str):
    page = self.memory_service.get_wiki_page(page_name)
    if page is not None and page.invalidated_at is None:
      return page
    if self.wiki_runner is None:
      return None
    self.wiki_runner.run(page_name=page_name)
    page = self.memory_service.get_wiki_page(page_name)
    if page is None or page.invalidated_at is not None:
      return None
    return page

  def _extract_linked_pages(self, content_md: str) -> list[str]:
    return WIKI_LINK_PATTERN.findall(content_md)

  def _page_matches_domain(self, page_name: str, *, domain: str) -> bool:
    if page_name in NAVIGATION_PAGE_NAMES:
      return True
    schema = self._load_schema()
    if schema is None:
      return False
    page_def = schema.get_page(page_name)
    if page_def is None:
      return False
    return domain in page_def.domains

  def _persist_answer(
    self,
    *,
    result: WikiQueryResult,
    question: str,
    domain: str,
    auto_persist: bool | None,
    page_name: str | None,
    title: str | None,
  ) -> None:
    should_auto_persist = self.settings.wiki_query_auto_persist_enabled if auto_persist is None else auto_persist
    resolved_page_name = page_name
    resolved_title = title
    if (
      resolved_page_name is None
      and should_auto_persist
      and self.settings.wiki_query_promote_to_canonical_enabled
    ):
      canonical_target = self._suggest_canonical_target(
        question=question,
        domain=domain,
        sources=result.sources,
      )
      if canonical_target is not None and self._promote_answer_to_canonical(
        result=result,
        question=question,
        domain=domain,
        canonical_target=canonical_target,
      ):
        result.outcome = QUERY_OUTCOME_CANONICAL_PROMOTION
        return
    if resolved_page_name is None and should_auto_persist:
      resolved_page_name = self._auto_page_name(question=question, domain=domain)
      resolved_title = resolved_title or self._auto_page_title(question=question)
    if not resolved_page_name:
      return
    if resolved_page_name in NAVIGATION_PAGE_NAMES:
      return
    min_confidence = self.settings.wiki_query_auto_persist_min_confidence if page_name is None else 0.5
    min_sources = self.settings.wiki_query_auto_persist_min_sources if page_name is None else 1
    if len(result.sources) < min_sources or result.confidence < min_confidence:
      return
    page_title = resolved_title or resolved_page_name.replace("-", " ").replace("_", " ").title()
    source_lines = "\n".join(f"- [{source}](wiki:{source})" for source in result.sources)
    content_md = (
      f"# {page_title}\n\n"
      "## Query\n\n"
      f"{question}\n\n"
      "## Answer\n\n"
      f"{result.answer}\n\n"
      "## Sources\n\n"
      f"{source_lines}\n"
    )
    existing_page = self.memory_service.get_wiki_page(resolved_page_name)
    if existing_page is None:
      lifecycle_state = "fresh"
    else:
      existing_lifecycle = (getattr(existing_page, "metadata_json", None) or {}).get("lifecycle_state", "fresh")
      lifecycle_state = "refreshable" if existing_lifecycle in ("fresh", "refreshable") else existing_lifecycle
    self.memory_service.upsert_wiki_page(
      page_name=resolved_page_name,
      title=page_title,
      content_md=content_md,
      facts_count=len(result.sources),
      reflections_count=0,
      metadata={
        "page_kind": "query",
        "origin": "query_answer",
        "domains": [domain],
        "themes": [],
        "canonical_target": None,
        "merge_count": 0,
        "superseded_by": None,
        "query": question,
        "lifecycle_state": lifecycle_state,
        "last_maintained_at": datetime.now(UTC).isoformat(),
      },
      invalidated_at=None,
    )
    result.persisted_page_name = resolved_page_name
    result.outcome = QUERY_OUTCOME_QUERY_PAGE

  def _suggest_canonical_target(
    self,
    *,
    question: str,
    domain: str,
    sources: list[str],
  ) -> str | None:
    schema = self._load_schema()
    if schema is None:
      return None
    candidate_pages = [
      source
      for source in sources
      if source not in NAVIGATION_PAGE_NAMES
      and (page_def := schema.get_page(source)) is not None
      and domain in page_def.domains
    ]
    if not candidate_pages:
      return None

    question_tokens = self._question_tokens(question)
    scored: list[tuple[int, str]] = []
    for source in candidate_pages:
      page_def = schema.get_page(source)
      if page_def is None:
        continue
      descriptor = " ".join([page_def.name, page_def.title, page_def.description, *page_def.themes]).lower()
      descriptor_tokens = self._question_tokens(descriptor)
      overlap = len(question_tokens & descriptor_tokens)
      scored.append((overlap, source))

    if not scored:
      return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    winner_overlap, winner_name = scored[0]

    # Require at least one meaningful token overlap with the page descriptor;
    # purely off-topic questions must not be promoted.
    if winner_overlap < 1:
      return None

    # Multi-candidate: winner must strictly dominate the runner-up on overlap;
    # tied scores indicate an ambiguous question.
    if len(scored) > 1 and winner_overlap <= scored[1][0]:
      return None

    return winner_name

  def _promote_answer_to_canonical(
    self,
    *,
    result: WikiQueryResult,
    question: str,
    domain: str,
    canonical_target: str,
  ) -> bool:
    min_confidence = self.settings.wiki_query_auto_persist_min_confidence
    min_sources = self.settings.wiki_query_auto_persist_min_sources
    if len(result.sources) < min_sources or result.confidence < min_confidence:
      return False
    source_id = f"{canonical_target}:{self._slugify(question, limit=64)}"
    source_pages = [source for source in result.sources if source not in NAVIGATION_PAGE_NAMES]
    payload = MemoryCreateRequest(
      domain=domain,
      kind="summary",
      statement=(
        f"Promoted wiki query for '{canonical_target}'. "
        f"Question: {question} "
        f"Answer: {result.answer} "
        f"Source pages: {', '.join(source_pages) if source_pages else 'none'}."
      ),
      confidence=result.confidence,
      metadata={
        "source_type": "wiki_query_promotion",
        "source_id": source_id,
        "canonical_page": canonical_target,
        "source_question": question,
        "source_pages": source_pages,
        "theme": canonical_target,
      },
    )
    self.memory_service.upsert_item_by_source_ref(
      payload,
      source_type="wiki_query_promotion",
      source_id=source_id,
    )
    if self.wiki_runner is not None:
      self.wiki_runner.run(page_name=canonical_target)
      self.wiki_runner.run(page_name="log")
      self.wiki_runner.run(page_name="index")
    result.promoted_canonical_target = canonical_target
    return True

  def _auto_page_name(self, *, question: str, domain: str) -> str:
    slug = self._slugify(question)
    prefix = self.settings.wiki_query_auto_persist_prefix.strip("-_") or "qa"
    return f"{prefix}-{domain}-{slug}"

  def _auto_page_title(self, question: str) -> str:
    normalized = " ".join(question.split()).strip()
    return f"Q&A: {normalized}" if normalized else "Q&A"

  def _slugify(self, value: str, *, limit: int = 48) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if not slug:
      slug = "query"
    return slug[:limit].rstrip("-")

  def refresh_auto_persisted_pages(self) -> tuple[list[str], list[str], list[str], list[str]]:
    if not self.settings.wiki_query_maintenance_enabled:
      return [], [], [], []

    prefix = f"{self.settings.wiki_query_auto_persist_prefix.strip('-_') or 'qa'}-"
    deduped = self._dedupe_auto_persisted_pages(prefix=prefix)
    refreshed: list[str] = []
    pruned: list[str] = []
    promoted: list[str] = []
    for page in self.memory_service.list_wiki_pages():
      metadata = getattr(page, "metadata_json", None) or {}
      is_query_page = page.page_name.startswith(prefix) or metadata.get("page_kind") == "query"
      if not is_query_page:
        continue
      if page.page_name in deduped:
        continue
      lifecycle_state = metadata.get("lifecycle_state")
      if lifecycle_state == "superseded":
        continue
      if len(refreshed) + len(pruned) + len(deduped) + len(promoted) >= self.settings.wiki_query_maintenance_max_pages_per_cycle:
        break
      outcome = self.refresh_auto_persisted_page(page.page_name)
      if outcome == "refreshed":
        refreshed.append(page.page_name)
      elif outcome == "pruned":
        pruned.append(page.page_name)
      elif outcome == "promoted":
        promoted.append(page.page_name)
    return refreshed, pruned, deduped, promoted

  def refresh_auto_persisted_page(self, page_name: str) -> str:
    page = self.memory_service.get_wiki_page(page_name)
    if page is None:
      return "skipped"
    question = self._extract_query_from_page(page.content_md)
    if question is None:
      return "skipped"
    domain = self._extract_domain_from_auto_page_name(page_name)
    result = self.query(
      question,
      domain=domain,
      top_k=5,
      auto_persist=False,
    )
    if (
      len(result.sources) < self.settings.wiki_query_auto_persist_min_sources
      or result.confidence < self.settings.wiki_query_auto_persist_min_confidence
    ):
      deleted = self.memory_service.delete_wiki_page(page_name)
      if deleted:
        result.pruned_page_name = page_name
        return "pruned"
      return "skipped"

    # Try canonical promotion before refreshing the qa-* page.
    if self.settings.wiki_query_promote_to_canonical_enabled:
      canonical_target = self._suggest_canonical_target(
        question=question,
        domain=domain,
        sources=result.sources,
      )
      if canonical_target is not None and self._promote_answer_to_canonical(
        result=result,
        question=question,
        domain=domain,
        canonical_target=canonical_target,
      ):
        self._mark_page_superseded(page_name, superseded_by=canonical_target)
        return "promoted"

    self._persist_answer(
      result=result,
      question=question,
      domain=domain,
      auto_persist=False,
      page_name=page_name,
      title=page.title,
    )
    refreshed_page = self.memory_service.get_wiki_page(page_name)
    if refreshed_page is not None:
      self._merge_auto_query_page_into_target(
        target_page=refreshed_page,
        source_page=page,
        source_question=question,
        record_source_page=False,
      )
    return "refreshed"

  def _mark_page_superseded(self, page_name: str, *, superseded_by: str) -> None:
    page = self.memory_service.get_wiki_page(page_name)
    if page is None:
      return
    metadata = dict(getattr(page, "metadata_json", None) or {})
    metadata["lifecycle_state"] = "superseded"
    metadata["superseded_by"] = superseded_by
    metadata["last_maintained_at"] = datetime.now(UTC).isoformat()
    self.memory_service.upsert_wiki_page(
      page_name=page.page_name,
      title=page.title,
      content_md=page.content_md,
      facts_count=page.facts_count,
      reflections_count=page.reflections_count,
      metadata=metadata,
      invalidated_at=page.invalidated_at,
    )

  def _extract_query_from_page(self, content_md: str) -> str | None:
    match = QUERY_SECTION_PATTERN.search(content_md)
    if not match:
      return None
    question = " ".join(match.group(1).strip().split())
    return question or None

  def _dedupe_auto_persisted_pages(self, *, prefix: str) -> list[str]:
    if not self.settings.wiki_query_dedupe_enabled:
      return []

    grouped: dict[str, list[tuple[object, str, set[str], set[str]]]] = {}
    for page in self.memory_service.list_wiki_pages():
      if not page.page_name.startswith(prefix):
        continue
      question = self._extract_query_from_page(page.content_md)
      if question is None:
        continue
      domain = self._extract_domain_from_auto_page_name(page.page_name)
      grouped.setdefault(domain, []).append(
        (
          page,
          self._normalize_query_text(question),
          self._question_tokens(question),
          self._extract_source_page_names(page.content_md),
        )
      )

    deleted: list[str] = []
    for domain_pages in grouped.values():
      if len(domain_pages) < 2:
        continue
      domain_pages.sort(
        key=lambda entry: (
          -(entry[0].facts_count + entry[0].reflections_count),
          -entry[0].generated_at.timestamp(),
          entry[0].page_name,
        )
      )
      kept: list[tuple[object, str, set[str], set[str]]] = []
      for entry in domain_pages:
        page, normalized_question, question_tokens, source_page_names = entry
        duplicate_target = next(
          (
            kept_entry[0]
            for kept_entry in kept
            if self._questions_are_near_duplicates(
              normalized_question=normalized_question,
              normalized_other_question=kept_entry[1],
              question_tokens=question_tokens,
              other_question_tokens=kept_entry[2],
              source_page_names=source_page_names,
              other_source_page_names=kept_entry[3],
            )
          ),
          None,
        )
        if duplicate_target is not None:
          duplicate_question = self._extract_query_from_page(page.content_md) or normalized_question
          self._merge_auto_query_page_into_target(
            target_page=duplicate_target,
            source_page=page,
            source_question=duplicate_question,
          )
          if self.memory_service.delete_wiki_page(page.page_name):
            deleted.append(page.page_name)
          continue
        kept.append(entry)

    deleted.sort()
    return deleted

  def _normalize_query_text(self, question: str) -> str:
    return " ".join(question.lower().split())

  def _question_tokens(self, question: str) -> set[str]:
    tokens = {
      token
      for token in QUESTION_TOKEN_PATTERN.findall(question.lower())
      if token not in QUESTION_STOP_WORDS and len(token) > 1
    }
    return tokens

  def _extract_source_page_names(self, content_md: str) -> set[str]:
    return set(WIKI_LINK_PATTERN.findall(content_md))

  def _extract_merge_provenance_entries(self, content_md: str) -> set[str]:
    section = self._extract_section(content_md, heading="Merge Provenance")
    if section is None:
      return set()
    return {line.strip() for line in section.splitlines() if line.strip().startswith("- ")}

  def _merge_auto_query_page_into_target(
    self,
    *,
    target_page,
    source_page,
    source_question: str,
    record_source_page: bool = True,
  ) -> None:
    merged_sources = sorted(
      self._extract_source_page_names(target_page.content_md)
      | self._extract_source_page_names(source_page.content_md)
    )
    merged_provenance = (
      self._extract_merge_provenance_entries(target_page.content_md)
      | self._extract_merge_provenance_entries(source_page.content_md)
    )
    if record_source_page:
      merged_provenance.add(f"- {source_page.page_name} :: {source_question}")

    content_md = target_page.content_md
    if merged_sources:
      sources_body = "\n".join(f"- [{page_name}](wiki:{page_name})" for page_name in merged_sources)
      content_md = self._upsert_section(content_md, heading="Sources", body=sources_body)
    if merged_provenance:
      provenance_body = "\n".join(sorted(merged_provenance))
      content_md = self._upsert_section(content_md, heading="Merge Provenance", body=provenance_body)

    self.memory_service.upsert_wiki_page(
      page_name=target_page.page_name,
      title=target_page.title,
      content_md=content_md,
      facts_count=max(target_page.facts_count, source_page.facts_count, len(merged_sources)),
      reflections_count=max(target_page.reflections_count, source_page.reflections_count),
      metadata=self._merged_query_page_metadata(
        target_page=target_page,
        source_page=source_page,
        question=source_question,
        merge_count=len(merged_provenance),
      ),
      invalidated_at=None,
    )

  def _questions_are_near_duplicates(
    self,
    *,
    normalized_question: str,
    normalized_other_question: str,
    question_tokens: set[str],
    other_question_tokens: set[str],
    source_page_names: set[str],
    other_source_page_names: set[str],
  ) -> bool:
    if normalized_question == normalized_other_question:
      return True
    token_jaccard = self._jaccard_similarity(question_tokens, other_question_tokens)
    if token_jaccard >= self.settings.wiki_query_near_dedupe_min_token_jaccard:
      return True
    shared_tokens = question_tokens & other_question_tokens
    source_jaccard = self._jaccard_similarity(source_page_names, other_source_page_names)
    return len(shared_tokens) >= 2 and source_jaccard >= self.settings.wiki_query_near_dedupe_min_source_jaccard

  def _jaccard_similarity(self, left: set[str], right: set[str]) -> float:
    if not left or not right:
      return 0.0
    union = left | right
    if not union:
      return 0.0
    return len(left & right) / len(union)

  def _extract_domain_from_auto_page_name(self, page_name: str) -> str:
    prefix = f"{self.settings.wiki_query_auto_persist_prefix.strip('-_') or 'qa'}-"
    if not page_name.startswith(prefix):
      return "self"
    remainder = page_name[len(prefix):]
    domain, _, _ = remainder.partition("-")
    if domain in {"self", "project", "operational", "interaction"}:
      return domain
    return "self"

  def _merged_query_page_metadata(
    self,
    *,
    target_page,
    source_page,
    question: str,
    merge_count: int,
  ) -> dict[str, object]:
    target_metadata = dict(getattr(target_page, "metadata_json", None) or {})
    source_metadata = dict(getattr(source_page, "metadata_json", None) or {})
    domains = sorted(set(target_metadata.get("domains", [])) | set(source_metadata.get("domains", [])))
    if not domains:
      domains = [self._extract_domain_from_auto_page_name(target_page.page_name)]
    target_lifecycle = target_metadata.get("lifecycle_state", "fresh")
    lifecycle_state = "refreshable" if target_lifecycle in ("fresh", "refreshable") else target_lifecycle
    return {
      "page_kind": "query",
      "origin": "query_answer",
      "domains": domains,
      "themes": sorted(set(target_metadata.get("themes", [])) | set(source_metadata.get("themes", []))),
      "canonical_target": target_metadata.get("canonical_target"),
      "merge_count": merge_count,
      "superseded_by": target_metadata.get("superseded_by"),
      "query": target_metadata.get("query") or question,
      "lifecycle_state": lifecycle_state,
      "last_maintained_at": datetime.now(UTC).isoformat(),
    }

  def _extract_section(self, content_md: str, *, heading: str) -> str | None:
    pattern = re.compile(
      SECTION_PATTERN_TEMPLATE.format(heading=re.escape(heading)),
      re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content_md)
    if not match:
      return None
    return match.group(2).strip()

  def _upsert_section(self, content_md: str, *, heading: str, body: str) -> str:
    normalized_body = body.strip()
    replacement = f"## {heading}\n\n{normalized_body}\n"
    pattern = re.compile(
      SECTION_PATTERN_TEMPLATE.format(heading=re.escape(heading)),
      re.MULTILINE | re.DOTALL,
    )
    if pattern.search(content_md):
      updated = pattern.sub(replacement, content_md, count=1)
      return updated.rstrip() + "\n"
    return content_md.rstrip() + f"\n\n{replacement}"

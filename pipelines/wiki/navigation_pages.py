from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib

from db.models import MemoryItem, WikiPageCache
from pipelines.wiki.constants import NAVIGATION_PAGE_NAMES
from pipelines.wiki.wiki_schema import WikiPageDefinition

LOG_PAGE_LIMIT = 20


@dataclass(slots=True)
class NavigationPageContent:
  title: str
  content_md: str
  facts_count: int
  reflections_count: int = 0


def compute_content_fingerprint(content_md: str) -> str:
  return hashlib.sha256(content_md.encode("utf-8")).hexdigest()


def build_index_page(
  *,
  schema_pages: Sequence[WikiPageDefinition],
  cached_pages: Sequence[WikiPageCache],
) -> NavigationPageContent:
  cached_by_name = {page.page_name: page for page in cached_pages}
  schema_by_name = {page.name: page for page in schema_pages}
  page_names = sorted(
    (set(cached_by_name) | set(schema_by_name)) - NAVIGATION_PAGE_NAMES,
    key=lambda name: (
      (schema_by_name[name].title if name in schema_by_name else cached_by_name[name].title).lower()
      if name in cached_by_name or name in schema_by_name
      else name.lower(),
      name,
    ),
  )

  lines = [
    "# Wiki Index",
    "",
    "Automatically maintained overview of available wiki pages.",
    "",
  ]

  if not page_names:
    lines.append("No wiki pages are available yet.")
    return NavigationPageContent(
      title="Wiki Index",
      content_md="\n".join(lines).strip(),
      facts_count=0,
      reflections_count=0,
    )

  lines.extend(["## Pages", ""])
  stale_count = 0
  for page_name in page_names:
    cached_page = cached_by_name.get(page_name)
    schema_page = schema_by_name.get(page_name)
    title = schema_page.title if schema_page is not None else cached_page.title if cached_page is not None else page_name

    details: list[str] = []
    if cached_page is not None:
      details.append(f"updated {format_utc_datetime(cached_page.generated_at)}")
      details.append(f"{cached_page.facts_count} facts")
      details.append(f"{cached_page.reflections_count} reflections")
      if cached_page.invalidated_at is not None:
        details.append("stale")
        stale_count += 1
    else:
      details.append("not generated yet")

    lines.append(f"- `{title}` (`{page_name}`) — {', '.join(details)}")

  return NavigationPageContent(
    title="Wiki Index",
    content_md="\n".join(lines).strip(),
    facts_count=len(page_names),
    reflections_count=stale_count,
  )


def build_log_page(*, items: Sequence[MemoryItem]) -> NavigationPageContent:
  lines = [
    "# Activity Log",
    "",
    "Recent accepted items from the source of truth.",
    "",
  ]

  recent_items = list(items)[:LOG_PAGE_LIMIT]
  if not recent_items:
    lines.append("No recent accepted activity yet.")
    return NavigationPageContent(
      title="Activity Log",
      content_md="\n".join(lines).strip(),
      facts_count=0,
      reflections_count=0,
    )

  lines.extend(["## Recent Items", ""])
  for item in recent_items:
    lines.append(
      f"- {format_utc_datetime(item.created_at)} "
      f"`{item.domain}` / `{item.kind}`: {truncate_text(item.statement)}"
    )

  return NavigationPageContent(
    title="Activity Log",
    content_md="\n".join(lines).strip(),
    facts_count=len(recent_items),
    reflections_count=0,
  )


def format_utc_datetime(value: datetime) -> str:
  return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def truncate_text(text: str, limit: int = 160) -> str:
  normalized = " ".join(text.split())
  if len(normalized) <= limit:
    return normalized
  return f"{normalized[: limit - 1].rstrip()}…"

"""Helper functions for wiki page building and synthesis."""

import hashlib
import json
import re

from pipelines.wiki.wiki_schema import WikiPageDefinition


def compute_items_fingerprint(facts: list[str], reflections: list[str]) -> str:
    """Compute SHA256 fingerprint of facts and reflections.

    Args:
        facts: List of fact statements
        reflections: List of reflection statements

    Returns:
        SHA256 hash of concatenated items
    """
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "facts": facts,
                "reflections": reflections,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return fingerprint


def compute_page_fingerprint(
    page_def: WikiPageDefinition,
    facts: list[str],
    reflections: list[str],
    related_page_names: list[str] | None = None,
    source_refs: list[str] | None = None,
) -> str:
    """Compute fingerprint from page definition and source items."""
    return hashlib.sha256(
        json.dumps(
            {
                "page": {
                    "name": page_def.name,
                    "title": page_def.title,
                    "description": page_def.description,
                    "domains": page_def.domains,
                    "kinds": page_def.kinds,
                    "themes": page_def.themes,
                },
                "related_pages": related_page_names or [],
                "source_refs": source_refs or [],
                "items": {
                    "facts": facts,
                    "reflections": reflections,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def encode_cached_page_content(*, fingerprint: str, content_md: str) -> str:
  """Embed the source fingerprint in a markdown comment."""
  comment = f"<!-- wiki-source-fingerprint: {fingerprint} -->"
  return f"{comment}\n\n{content_md.lstrip()}"


def extract_cached_page_fingerprint(content_md: str) -> str | None:
  """Extract the embedded source fingerprint from cached markdown."""
  match = re.match(
    r"^<!-- wiki-source-fingerprint: ([0-9a-f]{64}) -->(?:\n\n|\n)?",
    content_md,
  )
  if not match:
    return None
  return match.group(1)


def strip_cached_page_metadata(content_md: str) -> str:
  """Remove the embedded fingerprint comment from cached markdown."""
  return re.sub(
    r"^<!-- wiki-source-fingerprint: [0-9a-f]{64} -->(?:\n\n|\n)?",
    "",
    content_md,
    count=1,
  )


def enrich_page_markdown(
  *,
  content_md: str,
  page_def: WikiPageDefinition,
  facts_count: int,
  reflections_count: int,
  related_pages: list[dict[str, str]],
  source_refs: list[str],
  source_highlights: list[dict[str, str]],
) -> str:
  """Append deterministic related/provenance sections to a generated page."""
  base_content = re.sub(
    r"\n## Related Pages\n.*$|\n## Source Highlights\n.*$|\n## Provenance\n.*$",
    "",
    content_md.strip(),
    flags=re.DOTALL,
  ).rstrip()

  sections = [base_content]

  if related_pages:
    sections.extend(
      [
        "",
        "## Related Pages",
        "",
        *[
          f"- [{page['title']}](wiki:{page['name']})"
          for page in related_pages
        ],
      ]
    )

  if source_highlights:
    sections.extend(
      [
        "",
        "## Source Highlights",
        "",
        *[
          f"- [{highlight['source_ref']}] {highlight['statement']}"
          for highlight in source_highlights
        ],
      ]
    )

  provenance_lines = [
    "",
    "## Provenance",
    "",
    f"- domains: {', '.join(page_def.domains)}",
    f"- kinds: {', '.join(page_def.kinds)}",
    f"- facts_count: {facts_count}",
    f"- reflections_count: {reflections_count}",
  ]
  if page_def.themes:
    provenance_lines.append(f"- themes: {', '.join(page_def.themes)}")
  for source_ref in source_refs:
    provenance_lines.append(f"- source_ref: {source_ref}")
  sections.extend(provenance_lines)

  return "\n".join(sections).strip()

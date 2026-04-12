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

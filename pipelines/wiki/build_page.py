"""Helper functions for wiki page building and synthesis."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipelines.wiki.wiki_schema import WikiPageDefinition


def compute_items_fingerprint(facts: list[str], reflections: list[str]) -> str:
    """Compute SHA256 fingerprint of facts and reflections.

    Args:
        facts: List of fact statements
        reflections: List of reflection statements

    Returns:
        SHA256 hash of concatenated items
    """
    # Concatenate all items in deterministic order
    items_text = "".join(facts) + "".join(reflections)
    fingerprint = hashlib.sha256(items_text.encode("utf-8")).hexdigest()
    return fingerprint


def read_existing_page(page_path: Path) -> tuple[str, str | None]:
    """Read existing wiki page and extract frontmatter fingerprint.

    Args:
        page_path: Path to wiki page file

    Returns:
        Tuple of (full_content, fingerprint) where fingerprint is None if not found
    """
    if not page_path.exists():
        return "", None

    content = page_path.read_text(encoding="utf-8")

    # Try to extract frontmatter
    if not content.startswith("---\n"):
        return content, None

    parts = content.split("---\n")
    if len(parts) < 3:
        return content, None

    try:
        frontmatter_text = parts[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        fingerprint = frontmatter.get("source_fingerprint") if frontmatter else None
        return content, fingerprint
    except Exception:
        return content, None


def write_wiki_page(page_path: Path, frontmatter: str, content: str) -> None:
    """Write wiki page with frontmatter to disk.

    Args:
        page_path: Path to wiki page file
        frontmatter: YAML frontmatter string
        content: Markdown content (without frontmatter)
    """
    page_path.parent.mkdir(parents=True, exist_ok=True)

    # Combine frontmatter and content
    full_content = f"---\n{frontmatter}---\n{content}"

    page_path.write_text(full_content, encoding="utf-8")


def generate_frontmatter(
    page_def: WikiPageDefinition,
    facts: list[str],
    reflections: list[str],
    fingerprint: str,
) -> str:
    """Generate YAML frontmatter for wiki page.

    Args:
        page_def: Page definition
        facts: List of facts used
        reflections: List of reflections used
        fingerprint: Source fingerprint

    Returns:
        YAML frontmatter string (without surrounding ---)
    """
    frontmatter = {
        "title": page_def.title,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_fingerprint": fingerprint,
        "facts_count": len(facts),
        "reflections_count": len(reflections),
    }

    # Generate YAML
    yaml_content = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

    # Remove trailing newline that yaml.dump adds
    return yaml_content.rstrip("\n") + "\n"

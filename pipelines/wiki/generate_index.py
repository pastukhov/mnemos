"""Wiki index generation module."""

from datetime import datetime
from pathlib import Path

import yaml

from core.logging import get_logger
from pipelines.wiki.wiki_schema import WikiSchema

logger = get_logger(__name__)


def generate_index(wiki_dir: str, schema: WikiSchema) -> str:
    """Generate index.md for wiki navigation.

    Scans the wiki directory for .md files (excluding index.md and log.md),
    extracts frontmatter, and generates a sorted index of all pages.

    Args:
        wiki_dir: Path to wiki output directory
        schema: WikiSchema with page definitions

    Returns:
        Markdown string with index content (not written to disk)
    """
    wiki_path = Path(wiki_dir)

    # Find all .md files (excluding index.md and log.md)
    md_files = list(wiki_path.glob("*.md"))
    md_files = [f for f in md_files if f.name not in ("index.md", "log.md")]

    # Parse frontmatter and extract metadata
    pages_data = []

    for page_file in md_files:
        try:
            content = page_file.read_text(encoding="utf-8")

            # Extract frontmatter
            if not content.startswith("---\n"):
                continue

            parts = content.split("---\n")
            if len(parts) < 3:
                continue

            try:
                frontmatter_text = parts[1]
                frontmatter = yaml.safe_load(frontmatter_text)
                if not frontmatter:
                    continue

                # Extract required fields
                title = frontmatter.get("title", page_file.stem)
                generated_at_str = frontmatter.get("generated_at")
                facts_count = frontmatter.get("facts_count", 0)
                reflections_count = frontmatter.get("reflections_count", 0)

                # Parse date
                if generated_at_str:
                    # Handle ISO format with Z suffix
                    if isinstance(generated_at_str, str):
                        generated_at_str = generated_at_str.replace("Z", "+00:00")
                        try:
                            generated_at = datetime.fromisoformat(generated_at_str)
                        except ValueError:
                            generated_at = None
                    else:
                        generated_at = generated_at_str
                else:
                    generated_at = None

                # Find page definition for description
                description = ""
                for page_def in schema.pages:
                    if page_def.name == page_file.stem:
                        description = page_def.description
                        break

                pages_data.append({
                    "name": page_file.stem,
                    "filename": page_file.name,
                    "title": title,
                    "description": description,
                    "facts_count": facts_count,
                    "reflections_count": reflections_count,
                    "generated_at": generated_at,
                })

            except yaml.YAMLError:
                # Log but continue on YAML parse errors
                logger.warning(
                    "failed to parse frontmatter",
                    extra={
                        "event": "wiki_index_frontmatter_parse_error",
                        "file": page_file.name,
                    },
                )
                continue

        except Exception as e:
            logger.warning(
                "failed to read wiki page",
                extra={
                    "event": "wiki_index_read_error",
                    "file": page_file.name,
                    "error": str(e),
                },
            )
            continue

    # Sort by generated_at (newest first), handle None values
    pages_data.sort(
        key=lambda x: x["generated_at"] if x["generated_at"] else datetime.min,
        reverse=True,
    )

    # Generate markdown
    lines = [
        "# Wiki Index",
        "",
        "Полная навигация по вики.",
        "",
    ]

    if pages_data:
        for page in pages_data:
            # Format date for display
            date_str = ""
            if page["generated_at"]:
                date_str = page["generated_at"].strftime("%Y-%m-%d")

            # Build entry
            entry = f"- [{page['title']}]({page['filename']})"
            if page["description"]:
                entry += f" — {page['description']}"

            # Add counts and date
            counts_parts = []
            if page["facts_count"] > 0:
                counts_parts.append(f"{page['facts_count']} facts")
            if page["reflections_count"] > 0:
                counts_parts.append(f"{page['reflections_count']} reflections")
            if date_str:
                counts_parts.append(f"updated {date_str}")

            if counts_parts:
                entry += f" ({', '.join(counts_parts)})"

            lines.append(entry)
    else:
        lines.append("*No pages yet*")

    lines.append("")

    logger.info(
        "wiki index generated",
        extra={
            "event": "wiki_index_generated",
            "pages_count": len(pages_data),
        },
    )

    return "\n".join(lines)

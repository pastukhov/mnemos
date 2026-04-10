"""Wiki log generation module."""

from collections import defaultdict
from datetime import datetime
from typing import Any

from core.config import ALLOWED_DOMAINS
from core.logging import get_logger
from services.memory_service import MemoryService

logger = get_logger(__name__)


def generate_log(memory_service: MemoryService, wiki_dir: str) -> str:
    """Generate log.md with chronological list of all source items.

    Loads all raw items from memory service, sorts by created_at (newest first),
    and generates a chronological log grouped by date.

    Args:
        memory_service: MemoryService instance for loading items
        wiki_dir: Path to wiki output directory (used for context)

    Returns:
        Markdown string with log content (not written to disk)
    """
    items: list[dict[str, Any]] = []

    # Load items from all allowed domains
    for domain in ALLOWED_DOMAINS:
        try:
            domain_items = memory_service.list_items_by_domain_kind(
                domain=domain,
                kind="raw",
            )
            for item in domain_items:
                items.append({
                    "created_at": item.created_at,
                    "source_type": item.metadata_json.get("source_type", "unknown") if item.metadata_json else "unknown",
                    "statement": item.statement,
                })
        except Exception as e:
            logger.warning(
                "Failed to load items for domain",
                extra={
                    "event": "wiki_log_load_error",
                    "domain": domain,
                    "error": str(e),
                },
            )
            # Continue with empty list for this domain

    # Sort by created_at (newest first)
    items_sorted = sorted(
        items,
        key=lambda x: x["created_at"] if x["created_at"] else datetime.min,
        reverse=True,
    )

    # Group by date
    items_by_date: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in items_sorted:
        try:
            # Truncate statement to 80 characters
            statement = item["statement"]
            if len(statement) > 80:
                statement = statement[:77] + "..."

            # Format date key (YYYY-MM-DD)
            if item["created_at"]:
                date_key = item["created_at"].strftime("%Y-%m-%d")
            else:
                date_key = "unknown"

            items_by_date[date_key].append({
                "source_type": item["source_type"],
                "statement": statement,
                "date": item["created_at"],
            })

        except Exception as e:
            logger.warning(
                "Failed to process item for log",
                extra={
                    "event": "wiki_log_process_error",
                    "error": str(e),
                },
            )
            continue

    # Generate markdown
    lines = [
        "# Wiki Log",
        "",
        "Хронологический лог всех добавленных источников.",
        "",
    ]

    if items_by_date:
        # Sort dates (newer first)
        sorted_dates = sorted(items_by_date.keys(), reverse=True)

        for date_key in sorted_dates:
            lines.append(f"## {date_key}")
            lines.append("")

            for item in items_by_date[date_key]:
                lines.append(
                    f'- **{item["source_type"]}**: "{item["statement"]}"'
                )

            lines.append("")
    else:
        lines.append("*No entries yet*")
        lines.append("")

    logger.info(
        "wiki log generated",
        extra={
            "event": "wiki_log_generated",
            "items_count": len(items_sorted),
            "dates_count": len(items_by_date),
        },
    )

    return "\n".join(lines)

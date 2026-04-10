"""Wiki build runner for generating wiki pages from facts and reflections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings
from core.logging import get_logger
from pipelines.wiki.build_page import (
    compute_items_fingerprint,
    generate_frontmatter,
    read_existing_page,
    write_wiki_page,
)
from pipelines.wiki.wiki_llm_client import WikiLLMClient
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema
from services.memory_service import MemoryService

logger = get_logger(__name__)


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
        """Initialize wiki build runner.

        Args:
            memory_service: Memory service for loading facts/reflections
            wiki_llm_client: LLM client for synthesizing pages
            settings: Application settings
        """
        self.memory_service = memory_service
        self.llm_client = wiki_llm_client
        self.settings = settings
        self.schema: WikiSchema | None = None

    def run(
        self,
        domain: str | None = None,
        page_name: str | None = None,
    ) -> WikiBuildReport:
        """Run wiki build pipeline.

        Args:
            domain: Optional domain filter (e.g., 'self', 'project')
            page_name: Optional specific page to build

        Returns:
            WikiBuildReport with results
        """
        report = WikiBuildReport()

        # Load schema if not already loaded
        if self.schema is None:
            try:
                self.schema = WikiSchema.load_from_yaml(self.settings.wiki_schema_path)
            except FileNotFoundError:
                logger.error(
                    "wiki schema file not found",
                    extra={
                        "event": "wiki_build_schema_not_found",
                        "path": self.settings.wiki_schema_path,
                    },
                )
                report.errors += 1
                return report

        logger.info(
            "wiki build starting",
            extra={
                "event": "wiki_build",
                "pages_total": len(self.schema.pages),
                "domain_filter": domain,
                "page_name_filter": page_name,
            },
        )

        # Create output directory
        output_dir = Path(self.settings.wiki_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Process each page definition
        for page_def in self.schema.pages:
            # Apply filters
            if page_name and page_def.name != page_name:
                report.pages_skipped += 1
                continue

            if domain and domain not in page_def.domains:
                report.pages_skipped += 1
                continue

            # Build the page
            self._build_page(page_def, output_dir, report, domain)

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
        output_dir: Path,
        report: WikiBuildReport,
        domain_filter: str | None = None,
    ) -> None:
        """Build a single wiki page from facts and reflections.

        This method:
        1. Loads facts and reflections for the page from memory service
        2. Checks if there are enough facts (>= wiki_min_facts_per_page)
        3. Computes fingerprint of input data
        4. Checks if page exists and if fingerprint has changed
        5. Synthesizes page content via LLM
        6. Generates frontmatter with metadata
        7. Writes page to disk
        8. Updates report with result

        Args:
            page_def: WikiPageDefinition with page configuration
            output_dir: Output directory path for wiki pages
            report: WikiBuildReport to update with results
            domain_filter: Optional domain filter to override page_def domains
        """
        page_path = output_dir / f"{page_def.name}.md"

        try:
            # Load facts and reflections for this page
            facts_list, reflections_list = self._load_items_for_page(
                page_def,
                domain_filter,
            )

            # Check if we have minimum facts
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

            # Compute fingerprint of input data
            fingerprint = compute_items_fingerprint(facts_list, reflections_list)

            # Check if page exists and if fingerprint changed
            existing_content, existing_fingerprint = read_existing_page(page_path)

            if existing_fingerprint == fingerprint:
                # Page hasn't changed
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

            # Determine if this is new or update
            is_new = not page_path.exists()

            # Synthesize page content with LLM
            markdown_content = self.llm_client.synthesize_page(
                page_def=page_def,
                facts=facts_list,
                reflections=reflections_list,
                existing_content=existing_content if not is_new else None,
            )

            # Generate frontmatter
            frontmatter = generate_frontmatter(
                page_def,
                facts_list,
                reflections_list,
                fingerprint,
            )

            # Write page to disk
            write_wiki_page(page_path, frontmatter, markdown_content)

            # Update report
            if is_new:
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
        """Load facts and reflections for a page definition.

        Loads items from memory service based on page definition filters:
        - Filters by domains specified in page_def or domain_filter
        - Filters by kinds specified in page_def
        - Optionally filters by themes if specified in page_def

        Args:
            page_def: WikiPageDefinition with domain, kind, and theme filters
            domain_filter: Optional domain filter to override page_def domains

        Returns:
            Tuple of (facts_list, reflections_list) where each is a list of statement strings
        """
        facts_list = []
        reflections_list = []

        # Determine which domains to load from
        domains_to_load = [domain_filter] if domain_filter else page_def.domains

        # Load each kind from each domain
        for domain in domains_to_load:
            for kind in page_def.kinds:
                items = self.memory_service.list_items_by_domain_kind(
                    domain=domain,
                    kind=kind,
                )

                # Filter by theme if specified
                if page_def.themes:
                    items = [
                        item
                        for item in items
                        if item.metadata_json.get("theme") in page_def.themes
                    ]

                # Collect items as strings
                item_statements = [item.statement for item in items]

                if kind in self.settings.wiki_facts_kinds:
                    facts_list.extend(item_statements)
                elif kind in self.settings.wiki_reflections_kinds:
                    reflections_list.extend(item_statements)

        return facts_list, reflections_list

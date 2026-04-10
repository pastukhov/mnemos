"""Tests for wiki index and log generation."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from pipelines.wiki.generate_index import generate_index
from pipelines.wiki.generate_log import generate_log
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


@pytest.fixture
def sample_wiki_dir(tmp_path):
    """Create a temporary wiki directory with sample pages."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


def test_generate_index_with_single_page(sample_wiki_dir):
    """Test index generation with a single wiki page."""
    # Create a sample page with frontmatter
    page_content = """---
title: Career and Skills
generated_at: 2026-04-10T10:00:00Z
source_fingerprint: abc123
facts_count: 5
reflections_count: 2
---

# Career and Skills

This is about career.
"""
    page_file = sample_wiki_dir / "career.md"
    page_file.write_text(page_content, encoding="utf-8")

    schema = WikiSchema(pages=[
        WikiPageDefinition(
            name="career",
            title="Career and Skills",
            description="Professional development and skills",
            domains=["self"],
            kinds=["fact", "reflection"],
        ),
    ])

    index_content = generate_index(str(sample_wiki_dir), schema)

    # Verify index contains the page
    assert "# Wiki Index" in index_content
    assert "career.md" in index_content
    assert "Career and Skills" in index_content
    assert "5 facts" in index_content
    assert "2 reflections" in index_content


def test_generate_index_with_multiple_pages(sample_wiki_dir):
    """Test index generation with multiple pages, sorted by date."""
    # Create pages with different dates
    pages_data = [
        {
            "name": "career",
            "title": "Career",
            "date": "2026-04-10T15:00:00Z",
            "facts": 5,
            "reflections": 2,
        },
        {
            "name": "learning",
            "title": "Learning",
            "date": "2026-04-09T10:00:00Z",
            "facts": 3,
            "reflections": 1,
        },
        {
            "name": "health",
            "title": "Health",
            "date": "2026-04-10T10:00:00Z",
            "facts": 4,
            "reflections": 3,
        },
    ]

    for page_data in pages_data:
        page_content = f"""---
title: {page_data['title']}
generated_at: {page_data['date']}
source_fingerprint: {page_data['name']}123
facts_count: {page_data['facts']}
reflections_count: {page_data['reflections']}
---

# {page_data['title']}

Content for {page_data['name']}.
"""
        page_file = sample_wiki_dir / f"{page_data['name']}.md"
        page_file.write_text(page_content, encoding="utf-8")

    schema = WikiSchema(pages=[
        WikiPageDefinition(
            name=p["name"],
            title=p["title"],
            description=f"Page for {p['name']}",
            domains=["self"],
            kinds=["fact", "reflection"],
        )
        for p in pages_data
    ])

    index_content = generate_index(str(sample_wiki_dir), schema)

    # Verify pages are present
    assert "career.md" in index_content
    assert "learning.md" in index_content
    assert "health.md" in index_content

    # Verify sorting by date (newer first)
    career_pos = index_content.find("career.md")
    health_pos = index_content.find("health.md")
    learning_pos = index_content.find("learning.md")

    # Career (2026-04-10 15:00) should come before Health (2026-04-10 10:00)
    # Both should come before Learning (2026-04-09)
    assert career_pos < health_pos < learning_pos


def test_generate_index_excludes_index_and_log(sample_wiki_dir):
    """Test that index.md and log.md are excluded from index generation."""
    # Create regular page
    page_content = """---
title: Career
generated_at: 2026-04-10T10:00:00Z
facts_count: 5
reflections_count: 2
---

# Career
"""
    (sample_wiki_dir / "career.md").write_text(page_content)

    # Create index.md and log.md (should be ignored)
    (sample_wiki_dir / "index.md").write_text("# Index")
    (sample_wiki_dir / "log.md").write_text("# Log")

    schema = WikiSchema(pages=[
        WikiPageDefinition(
            name="career",
            title="Career",
            description="Career page",
            domains=["self"],
            kinds=["fact"],
        ),
    ])

    index_content = generate_index(str(sample_wiki_dir), schema)

    # index.md and log.md should not appear in the generated index
    assert "index.md" not in index_content
    assert "log.md" not in index_content
    assert "career.md" in index_content


def test_generate_index_with_empty_directory(sample_wiki_dir):
    """Test index generation with empty wiki directory."""
    schema = WikiSchema(pages=[])

    index_content = generate_index(str(sample_wiki_dir), schema)

    # Should still have header
    assert "# Wiki Index" in index_content


def test_generate_index_with_missing_frontmatter(sample_wiki_dir):
    """Test index generation when page is missing frontmatter."""
    # Create a page without proper frontmatter
    page_content = "# Career\n\nNo frontmatter here."
    (sample_wiki_dir / "career.md").write_text(page_content)

    schema = WikiSchema(pages=[
        WikiPageDefinition(
            name="career",
            title="Career",
            description="Career page",
            domains=["self"],
            kinds=["fact"],
        ),
    ])

    # Should not raise an exception
    index_content = generate_index(str(sample_wiki_dir), schema)
    assert "# Wiki Index" in index_content


def test_generate_log_with_raw_items():
    """Test log generation with raw memory items."""
    # Create mock memory items
    now = datetime.now(timezone.utc)
    mock_item1 = Mock()
    mock_item1.created_at = now
    mock_item1.statement = "User likes working with modern tech stacks."
    mock_item1.metadata_json = {"source_type": "questionnaire"}
    mock_item1.id = "id1"

    mock_item2 = Mock()
    mock_item2.created_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=timezone.utc)
    mock_item2.statement = "Today I realized the importance of good documentation."
    mock_item2.metadata_json = {"source_type": "notes"}
    mock_item2.id = "id2"

    items = [mock_item1, mock_item2]

    # Create mock memory service
    memory_service = Mock()
    memory_service.list_items_by_domain_kind = Mock(return_value=items)

    wiki_dir = "/tmp/wiki"
    log_content = generate_log(memory_service, wiki_dir)

    # Verify log contains header
    assert "# Wiki Log" in log_content

    # Verify items are present
    assert "questionnaire" in log_content
    assert "User likes working with modern tech stacks." in log_content
    assert "notes" in log_content
    assert "Today I realized the importance of good documentation." in log_content

    # Verify date grouping
    assert "2026-04-" in log_content


def test_generate_log_sorts_by_date():
    """Test that log entries are sorted by created_at (newest first)."""
    # Create mock items with different dates
    mock_item1 = Mock()
    mock_item1.created_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=timezone.utc)
    mock_item1.statement = "Earlier entry."
    mock_item1.metadata_json = {"source_type": "notes"}
    mock_item1.id = "id1"

    mock_item2 = Mock()
    mock_item2.created_at = datetime(2026, 4, 10, 15, 0, 0, tzinfo=timezone.utc)
    mock_item2.statement = "Later entry."
    mock_item2.metadata_json = {"source_type": "questionnaire"}
    mock_item2.id = "id2"

    items = [mock_item1, mock_item2]

    memory_service = Mock()
    memory_service.list_items_by_domain_kind = Mock(return_value=items)

    log_content = generate_log(memory_service, "/tmp/wiki")

    # Verify newer entry appears before older entry
    later_pos = log_content.find("Later entry")
    earlier_pos = log_content.find("Earlier entry")
    assert later_pos < earlier_pos


def test_generate_log_truncates_long_statements():
    """Test that long statements are truncated to 80 characters."""
    long_statement = "This is a very long statement " * 10  # More than 80 chars

    mock_item = Mock()
    mock_item.created_at = datetime.now(timezone.utc)
    mock_item.statement = long_statement
    mock_item.metadata_json = {"source_type": "notes"}
    mock_item.id = "id1"

    items = [mock_item]

    memory_service = Mock()
    memory_service.list_items_by_domain_kind = Mock(return_value=items)

    log_content = generate_log(memory_service, "/tmp/wiki")

    # Verify statement is truncated
    assert "This is a very long statement" in log_content
    # The full long statement should not appear
    assert long_statement[:80] not in log_content or "..." in log_content


def test_generate_log_with_empty_items():
    """Test log generation with no items."""
    memory_service = Mock()
    memory_service.list_items_by_domain_kind = Mock(return_value=[])

    log_content = generate_log(memory_service, "/tmp/wiki")

    # Should still have header
    assert "# Wiki Log" in log_content


def test_generate_log_handles_missing_metadata():
    """Test log generation when metadata is missing."""
    mock_item = Mock()
    mock_item.created_at = datetime.now(timezone.utc)
    mock_item.statement = "Item without metadata."
    mock_item.metadata_json = None
    mock_item.id = "id1"

    items = [mock_item]

    memory_service = Mock()
    memory_service.list_items_by_domain_kind = Mock(return_value=items)

    # Should not raise an exception
    log_content = generate_log(memory_service, "/tmp/wiki")
    assert "# Wiki Log" in log_content


def test_wiki_build_runner_calls_index_and_log(client, tmp_path):
    """Test that WikiBuildRunner calls generate_index and generate_log after building pages."""
    from pipelines.wiki.wiki_runner import WikiBuildRunner
    from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema
    from tests.test_wiki_runner import FakeWikiLLMClient

    # Create test items
    def _create_item(domain: str, kind: str, statement: str):
        response = client.post(
            "/memory/items",
            json={
                "domain": domain,
                "kind": kind,
                "statement": statement,
                "confidence": 0.85,
                "metadata": {},
            },
        )
        return response.json()

    _create_item("self", "fact", "User builds automation systems.")
    _create_item("self", "fact", "User values observable delivery.")
    _create_item("self", "fact", "User enjoys reducing manual work.")
    _create_item("self", "reflection", "User is motivated by automation.")

    # Create wiki schema
    schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="career",
                title="Career",
                description="Professional journey",
                domains=["self"],
                kinds=["fact", "reflection"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    # Mock LLM client
    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = schema

    # Run build
    runner.run()

    # Verify index.md was created
    index_path = tmp_path / "index.md"
    assert index_path.exists()
    index_content = index_path.read_text()
    assert "# Wiki Index" in index_content

    # Verify log.md was created
    log_path = tmp_path / "log.md"
    assert log_path.exists()
    log_content = log_path.read_text()
    assert "# Wiki Log" in log_content

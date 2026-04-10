"""Tests for wiki build runner pipeline."""

from datetime import datetime

import yaml

from db.models import MemoryItem
from pipelines.wiki.wiki_runner import WikiBuildRunner, WikiBuildReport
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


class FakeWikiLLMClient:
    """Mock wiki LLM client for testing."""

    def __init__(self, fail_on_page_name: str | None = None):
        self.fail_on_page_name = fail_on_page_name
        self.synthesized_pages = []

    def synthesize_page(self, page_def, facts, reflections, existing_content=None):
        """Synthesize page or raise if configured to fail."""
        if self.fail_on_page_name and page_def.name == self.fail_on_page_name:
            raise RuntimeError(f"LLM failed to synthesize page: {page_def.name}")

        self.synthesized_pages.append({
            "page_name": page_def.name,
            "facts_count": len(facts),
            "reflections_count": len(reflections),
            "existing_content": existing_content,
        })

        content = f"# {page_def.title}\n\n{page_def.description}\n\n"
        if facts:
            content += "## Facts\n\n"
            for fact in facts:
                content += f"- {fact}\n"
            content += "\n"
        if reflections:
            content += "## Reflections\n\n"
            for reflection in reflections:
                content += f"- {reflection}\n"
        return content


def _create_item(client, *, domain: str, kind: str, statement: str, metadata: dict | None = None) -> MemoryItem:
    """Helper to create a memory item via client API."""
    raw_response = client.post(
        "/memory/items",
        json={
            "domain": domain,
            "kind": kind,
            "statement": statement,
            "confidence": 0.85,
            "metadata": metadata or {},
        },
    )
    return raw_response.json()


def test_wiki_build_creates_single_new_page(client, tmp_path):
    """Test building a single new wiki page."""
    # Create facts and reflections
    _create_item(client, domain="self", kind="fact", statement="User builds automation systems.")
    _create_item(client, domain="self", kind="fact", statement="User values observable delivery.")
    _create_item(client, domain="self", kind="fact", statement="User enjoys reducing manual work.")
    _create_item(client, domain="self", kind="reflection", statement="User is motivated by automation.")

    wiki_schema = WikiSchema(
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

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)

    # Override schema (normally loaded from file)
    runner.schema = wiki_schema

    report = runner.run()

    # Verify report
    assert report.pages_built == 1
    assert report.pages_updated == 0
    assert report.pages_skipped == 0
    assert report.errors == 0

    # Verify file was created with frontmatter
    page_path = tmp_path / "career.md"
    assert page_path.exists()

    content = page_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "title: Career" in content
    assert "generated_at:" in content
    assert "source_fingerprint:" in content
    assert "facts_count: 3" in content
    assert "reflections_count: 1" in content
    assert "---\n" in content
    assert "# Career" in content


def test_wiki_build_updates_existing_page_when_fingerprint_changes(client, tmp_path):
    """Test that existing page is updated when facts/reflections change."""
    # Create initial items
    _create_item(client, domain="self", kind="fact", statement="Initial fact")
    _create_item(client, domain="self", kind="fact", statement="Second fact")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="test",
                title="Test Page",
                description="Test",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 2

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    # First run - creates page
    report1 = runner.run(page_name="test")
    assert report1.pages_built == 1
    assert report1.pages_updated == 0

    # Get original fingerprint
    page_path = tmp_path / "test.md"
    original_content = page_path.read_text(encoding="utf-8")
    lines = original_content.split("\n")
    original_fingerprint = None
    for line in lines:
        if line.startswith("source_fingerprint:"):
            original_fingerprint = line.split(": ", 1)[1]
            break

    # Second run - should skip (fingerprint unchanged)
    report2 = runner.run(page_name="test")
    assert report2.pages_built == 0
    assert report2.pages_updated == 0
    assert report2.pages_skipped == 1

    # Add a new fact (changes fingerprint)
    _create_item(client, domain="self", kind="fact", statement="New fact")

    # Third run - should update
    report3 = runner.run(page_name="test")
    assert report3.pages_built == 0
    assert report3.pages_updated == 1
    assert report3.pages_skipped == 0

    # Verify new fingerprint is different
    updated_content = page_path.read_text(encoding="utf-8")
    updated_fingerprint = None
    for line in updated_content.split("\n"):
        if line.startswith("source_fingerprint:"):
            updated_fingerprint = line.split(": ", 1)[1]
            break

    assert updated_fingerprint != original_fingerprint


def test_wiki_build_skips_page_with_insufficient_facts(client, tmp_path):
    """Test that page is skipped if facts are below minimum."""
    # Create only 1 fact (less than default minimum of 3)
    _create_item(client, domain="self", kind="fact", statement="Only one fact")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="test",
                title="Test",
                description="Test",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 3

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    report = runner.run()

    assert report.pages_built == 0
    assert report.pages_skipped == 1
    assert report.errors == 0

    page_path = tmp_path / "test.md"
    assert not page_path.exists()


def test_wiki_build_filters_by_domain(client, tmp_path):
    """Test that pages respect domain filters."""
    # Create facts in different domains
    _create_item(client, domain="self", kind="fact", statement="Self fact 1")
    _create_item(client, domain="self", kind="fact", statement="Self fact 2")
    _create_item(client, domain="self", kind="fact", statement="Self fact 3")
    _create_item(client, domain="project", kind="fact", statement="Project fact 1")
    _create_item(client, domain="project", kind="fact", statement="Project fact 2")
    _create_item(client, domain="project", kind="fact", statement="Project fact 3")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="self_page",
                title="Self",
                description="Self facts",
                domains=["self"],
                kinds=["fact"],
            ),
            WikiPageDefinition(
                name="project_page",
                title="Project",
                description="Project facts",
                domains=["project"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    # Run for self domain only
    report = runner.run(domain="self")

    assert report.pages_built == 1
    assert report.pages_skipped == 1  # project_page skipped due to domain filter

    # Verify only self_page was created
    assert (tmp_path / "self_page.md").exists()
    assert not (tmp_path / "project_page.md").exists()


def test_wiki_build_filters_by_page_name(client, tmp_path):
    """Test that page_name parameter filters which pages to build."""
    _create_item(client, domain="self", kind="fact", statement="Fact 1")
    _create_item(client, domain="self", kind="fact", statement="Fact 2")
    _create_item(client, domain="self", kind="fact", statement="Fact 3")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="page_a",
                title="Page A",
                description="A",
                domains=["self"],
                kinds=["fact"],
            ),
            WikiPageDefinition(
                name="page_b",
                title="Page B",
                description="B",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    # Run for only page_a
    report = runner.run(page_name="page_a")

    assert report.pages_built == 1
    assert report.pages_skipped == 1  # page_b skipped due to name filter

    assert (tmp_path / "page_a.md").exists()
    assert not (tmp_path / "page_b.md").exists()


def test_wiki_build_handles_llm_error(client, tmp_path):
    """Test that LLM errors are caught and reported."""
    _create_item(client, domain="self", kind="fact", statement="Fact 1")
    _create_item(client, domain="self", kind="fact", statement="Fact 2")
    _create_item(client, domain="self", kind="fact", statement="Fact 3")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="fail_page",
                title="Fail",
                description="This will fail",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient(fail_on_page_name="fail_page")
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    report = runner.run()

    assert report.pages_built == 0
    assert report.errors == 1
    assert report.pages_skipped == 0

    page_path = tmp_path / "fail_page.md"
    assert not page_path.exists()


def test_wiki_build_report_render(client, tmp_path):
    """Test WikiBuildReport.render() output."""
    report = WikiBuildReport(pages_built=5, pages_updated=3, pages_skipped=2, errors=1)

    output = report.render()

    assert "Pages built: 5" in output
    assert "Pages updated: 3" in output
    assert "Pages skipped: 2" in output
    assert "Errors: 1" in output


def test_frontmatter_yaml_format(client, tmp_path):
    """Test that frontmatter is valid YAML at beginning of file."""
    _create_item(client, domain="self", kind="fact", statement="Fact 1")
    _create_item(client, domain="self", kind="fact", statement="Fact 2")
    _create_item(client, domain="self", kind="fact", statement="Fact 3")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="yaml_test",
                title="YAML Test",
                description="Test YAML frontmatter",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    runner.run()

    page_path = tmp_path / "yaml_test.md"
    content = page_path.read_text(encoding="utf-8")

    # Extract frontmatter
    parts = content.split("---\n")
    assert len(parts) >= 3
    assert parts[0] == ""

    frontmatter_text = parts[1]
    frontmatter = yaml.safe_load(frontmatter_text)

    # Verify frontmatter structure
    assert frontmatter["title"] == "YAML Test"
    assert "generated_at" in frontmatter
    assert "source_fingerprint" in frontmatter
    assert frontmatter["facts_count"] == 3
    assert frontmatter["reflections_count"] == 0

    # Verify generated_at is ISO format
    iso_str = frontmatter["generated_at"]
    datetime.fromisoformat(iso_str.replace("Z", "+00:00"))

    # Verify markdown content is after frontmatter
    markdown_content = "\n".join(parts[2:])
    assert "# YAML Test" in markdown_content


def test_wiki_build_combines_multiple_kinds(client, tmp_path):
    """Test building page with multiple kinds (facts and reflections)."""
    _create_item(client, domain="self", kind="fact", statement="Fact 1")
    _create_item(client, domain="self", kind="fact", statement="Fact 2")
    _create_item(client, domain="self", kind="reflection", statement="Reflection 1")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="multi",
                title="Multi",
                description="Multiple kinds",
                domains=["self"],
                kinds=["fact", "reflection"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    report = runner.run()

    assert report.pages_built == 1

    # Verify both kinds were passed to LLM
    assert llm_client.synthesized_pages[0]["facts_count"] == 2
    assert llm_client.synthesized_pages[0]["reflections_count"] == 1


def test_wiki_build_skipped_page_not_counted_toward_fingerprint_check(client, tmp_path):
    """Test that skipped pages don't affect future fingerprint checks."""
    # Create 1 fact (less than minimum of 3)
    _create_item(client, domain="self", kind="fact", statement="Fact 1")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="insufficient",
                title="Insufficient",
                description="Has insufficient facts",
                domains=["self"],
                kinds=["fact"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 3

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    # First run - skipped due to insufficient facts
    report1 = runner.run()
    assert report1.pages_skipped == 1
    assert not (tmp_path / "insufficient.md").exists()

    # Add more facts so we now have 3
    _create_item(client, domain="self", kind="fact", statement="Fact 2")
    _create_item(client, domain="self", kind="fact", statement="Fact 3")

    # Second run - should now build
    report2 = runner.run()
    assert report2.pages_built == 1
    assert (tmp_path / "insufficient.md").exists()


def test_wiki_build_respects_configurable_kind_mappings(client, tmp_path):
    """Test that kind mappings can be configured via settings."""
    # Create items with different kinds
    _create_item(client, domain="self", kind="fact", statement="Regular fact")
    _create_item(client, domain="self", kind="tension", statement="Tension item")
    _create_item(client, domain="self", kind="reflection", statement="Regular reflection")

    wiki_schema = WikiSchema(
        pages=[
            WikiPageDefinition(
                name="custom",
                title="Custom Kinds",
                description="Testing custom kind mappings",
                domains=["self"],
                kinds=["fact", "tension", "reflection"],
            ),
        ],
        output_dir=str(tmp_path),
    )

    llm_client = FakeWikiLLMClient()
    settings = client.app.state.settings
    settings.wiki_output_dir = str(tmp_path)
    settings.wiki_min_facts_per_page = 1
    # Configure tension as a facts kind (instead of default mapping)
    settings.wiki_facts_kinds = ["fact", "tension"]
    settings.wiki_reflections_kinds = ["reflection"]

    runner = WikiBuildRunner(client.app.state.memory_service, llm_client, settings)
    runner.schema = wiki_schema

    report = runner.run()

    assert report.pages_built == 1

    # Verify both fact and tension were treated as facts
    assert llm_client.synthesized_pages[0]["facts_count"] == 2
    assert llm_client.synthesized_pages[0]["reflections_count"] == 1

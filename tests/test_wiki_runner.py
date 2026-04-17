"""Tests for wiki cache and wiki build runner."""

from __future__ import annotations

import yaml
import pytest
from uuid import UUID

from pipelines.wiki.build_page import (
  extract_cached_page_fingerprint,
  strip_cached_page_metadata,
)
from pipelines.wiki.wiki_runner import WikiBuildRunner
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


class FakeWikiLLMClient:
  """Mock wiki LLM client for testing."""

  def __init__(self, fail_on_page_name: str | None = None) -> None:
    self.fail_on_page_name = fail_on_page_name
    self.synthesized_pages: list[dict[str, object]] = []

  def synthesize_page(self, page_def, facts, reflections, existing_content=None, related_pages=None):
    if self.fail_on_page_name and page_def.name == self.fail_on_page_name:
      raise RuntimeError(f"LLM failed to synthesize page: {page_def.name}")

    self.synthesized_pages.append(
      {
        "page_name": page_def.name,
        "facts_count": len(facts),
        "reflections_count": len(reflections),
        "existing_content": existing_content,
        "related_pages": related_pages,
      }
    )

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


def _create_item(
  client,
  *,
  domain: str,
  kind: str,
  statement: str,
  metadata: dict | None = None,
):
  response = client.post(
    "/memory/items",
    json={
      "domain": domain,
      "kind": kind,
      "statement": statement,
      "confidence": 0.85,
      "metadata": metadata or {},
    },
  )
  assert response.status_code == 201
  return response.json()


def _build_runner(client, *, wiki_schema: WikiSchema, llm_client: FakeWikiLLMClient) -> WikiBuildRunner:
  _install_wiki_schema(client, wiki_schema=wiki_schema)
  runner = WikiBuildRunner(client.app.state.memory_service, llm_client, client.app.state.settings)
  runner.schema = wiki_schema
  return runner


def _install_wiki_schema(client, *, wiki_schema: WikiSchema) -> None:
  schema_path = "/tmp/test_wiki_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(wiki_schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path


def test_wiki_build_creates_cached_page_record(client):
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
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  report = runner.run()

  assert report.pages_built == 3
  assert report.pages_updated == 0
  assert report.pages_skipped == 0
  assert report.errors == 0

  page = client.app.state.memory_service.get_wiki_page("career")
  assert page is not None
  assert page.title == "Career"
  assert page.facts_count == 3
  assert page.reflections_count == 1
  assert page.invalidated_at is None
  assert extract_cached_page_fingerprint(page.content_md) is not None
  assert strip_cached_page_metadata(page.content_md).startswith("# Career")
  page_content = strip_cached_page_metadata(page.content_md)
  assert "## Source Highlights" in page_content
  assert "## Provenance" in page_content
  assert "- facts_count: 3" in page_content
  assert "- reflections_count: 1" in page_content
  assert "- source_ref: memory:" in page_content


def test_wiki_build_maintains_index_and_log_pages(client):
  _create_item(client, domain="self", kind="fact", statement="User builds automation systems.")
  _create_item(client, domain="self", kind="fact", statement="User values observable delivery.")
  _create_item(client, domain="self", kind="fact", statement="User enjoys reducing manual work.")
  _create_item(client, domain="self", kind="reflection", statement="User is motivated by automation.")
  _create_item(client, domain="project", kind="decision", statement="Use PostgreSQL as source of truth.")

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
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  report = runner.run()

  assert report.pages_built == 3
  index_page = client.app.state.memory_service.get_wiki_page("index")
  log_page = client.app.state.memory_service.get_wiki_page("log")

  assert index_page is not None
  assert index_page.title == "Wiki Index"
  index_content = strip_cached_page_metadata(index_page.content_md)
  assert "# Wiki Index" in index_content
  assert "`career`" in index_content
  assert "`index`" not in index_content
  assert "`log`" not in index_content

  assert log_page is not None
  assert log_page.title == "Activity Log"
  log_content = strip_cached_page_metadata(log_page.content_md)
  assert "# Activity Log" in log_content
  assert "Use PostgreSQL as source of truth." in log_content


def test_wiki_build_adds_related_pages_section(client):
  _create_item(client, domain="self", kind="fact", statement="User builds automation systems.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User values observable delivery.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User prefers focused work blocks.", metadata={"theme": "work_style"})
  _create_item(client, domain="self", kind="fact", statement="User likes reusable systems.", metadata={"theme": "work_style"})

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="workstyle",
        title="Workstyle",
        description="How work gets done",
        domains=["self"],
        kinds=["fact"],
        themes=["work_style"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  report = runner.run(page_name="career")

  assert report.pages_built == 1
  page = client.app.state.memory_service.get_wiki_page("career")
  assert page is not None
  content = strip_cached_page_metadata(page.content_md)
  assert "## Related Pages" in content
  assert "[Workstyle](wiki:workstyle)" in content


def test_wiki_index_includes_cached_only_non_schema_pages(client):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="scratchpad",
    title="Scratchpad",
    content_md="# Scratchpad",
    facts_count=1,
    reflections_count=0,
  )

  report = runner.run(page_name="index")

  assert report.pages_built == 1
  index_page = client.app.state.memory_service.get_wiki_page("index")
  assert index_page is not None
  index_content = strip_cached_page_metadata(index_page.content_md)
  assert "`scratchpad`" in index_content


def test_navigation_pages_can_build_without_schema_file(client):
  client.app.state.settings.wiki_schema_path = "/tmp/missing_wiki_schema.yaml"
  client.app.state.wiki_runner.schema = None
  _create_item(client, domain="self", kind="summary", statement="Fresh summary without schema.")

  report = client.app.state.wiki_runner.run(page_name="log")

  assert report.errors == 0
  log_page = client.app.state.memory_service.get_wiki_page("log")
  assert log_page is not None
  assert "Fresh summary without schema." in strip_cached_page_metadata(log_page.content_md)


def test_wiki_runner_retries_schema_load_after_missing_file(client):
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")
  _create_item(client, domain="self", kind="fact", statement="User values observable delivery.")

  client.app.state.settings.wiki_schema_path = "/tmp/missing_wiki_schema_retry.yaml"
  client.app.state.wiki_runner.schema = None

  first_report = client.app.state.wiki_runner.run(page_name="log")
  assert first_report.errors == 0
  assert client.app.state.memory_service.get_wiki_page("career") is None

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  _install_wiki_schema(client, wiki_schema=wiki_schema)
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.wiki_runner.llm_client = FakeWikiLLMClient()
  client.app.state.wiki_runner.schema = None

  second_report = client.app.state.wiki_runner.run(page_name="career")

  assert second_report.pages_built == 1
  assert client.app.state.memory_service.get_wiki_page("career") is not None


def test_wiki_index_prefers_schema_title_over_cached_title(client):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career From Schema",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Old Cached Title",
    content_md="# Career",
    facts_count=1,
    reflections_count=0,
  )

  report = runner.run(page_name="index")

  assert report.pages_built == 1
  index_page = client.app.state.memory_service.get_wiki_page("index")
  assert index_page is not None
  index_content = strip_cached_page_metadata(index_page.content_md)
  assert "`Career From Schema` (`career`)" in index_content
  assert "Old Cached Title" not in index_content


def test_memory_service_invalidates_navigation_pages_for_non_schema_activity(client):
  _create_item(client, domain="self", kind="fact", statement="User builds automation systems.")
  _create_item(client, domain="self", kind="fact", statement="User values observable delivery.")

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)
  runner.run()

  index_before = client.app.state.memory_service.get_wiki_page("index")
  log_before = client.app.state.memory_service.get_wiki_page("log")
  assert index_before is not None
  assert log_before is not None
  assert index_before.invalidated_at is None
  assert log_before.invalidated_at is None

  _create_item(client, domain="self", kind="summary", statement="Fresh summary for the activity log.")

  index_after = client.app.state.memory_service.get_wiki_page("index")
  log_after = client.app.state.memory_service.get_wiki_page("log")
  assert index_after is not None
  assert log_after is not None
  assert index_after.invalidated_at is not None
  assert log_after.invalidated_at is not None


def test_wiki_build_skips_unchanged_cached_page(client):
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
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 2
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  report_first = runner.run(page_name="test")
  report_second = runner.run(page_name="test")

  assert report_first.pages_built == 1
  assert report_second.pages_built == 0
  assert report_second.pages_updated == 0
  assert report_second.pages_skipped == 1
  assert len(llm_client.synthesized_pages) == 1


def test_wiki_build_loads_schema_from_configured_yaml(client):
  _create_item(client, domain="self", kind="fact", statement="First fact")
  _create_item(client, domain="self", kind="fact", statement="Second fact")

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="from-file",
        title="From File",
        description="Loaded from yaml",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  _install_wiki_schema(client, wiki_schema=wiki_schema)

  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 2
  runner = WikiBuildRunner(client.app.state.memory_service, llm_client, client.app.state.settings)

  report = runner.run(page_name="from-file")

  assert report.pages_built == 1
  assert runner.schema is not None
  assert runner.schema.get_page("from-file") is not None


def test_wiki_build_updates_invalidated_page_and_passes_clean_existing_content(client):
  _create_item(client, domain="self", kind="fact", statement="First fact")
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
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 2
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  runner.run(page_name="test")
  _create_item(client, domain="self", kind="fact", statement="Third fact")

  page_before = client.app.state.memory_service.get_wiki_page("test")
  assert page_before is not None
  assert page_before.invalidated_at is not None

  report = runner.run(page_name="test")

  assert report.pages_built == 0
  assert report.pages_updated == 1
  assert report.pages_skipped == 0
  assert llm_client.synthesized_pages[-1]["existing_content"].startswith("# Test Page")
  assert "<!-- wiki-source-fingerprint:" not in llm_client.synthesized_pages[-1]["existing_content"]

  page_after = client.app.state.memory_service.get_wiki_page("test")
  assert page_after is not None
  assert page_after.invalidated_at is None
  assert page_after.facts_count == 3


def test_wiki_build_updates_when_page_definition_changes(client):
  _create_item(client, domain="self", kind="fact", statement="First fact")
  _create_item(client, domain="self", kind="fact", statement="Second fact")

  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 2

  first_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="test",
        title="Original Title",
        description="Original description",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  runner = _build_runner(client, wiki_schema=first_schema, llm_client=llm_client)
  runner.run(page_name="test")

  updated_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="test",
        title="Updated Title",
        description="Updated description",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  _install_wiki_schema(client, wiki_schema=updated_schema)

  report = runner.run(page_name="test")

  assert report.pages_updated == 1
  page = client.app.state.memory_service.get_wiki_page("test")
  assert page is not None
  assert page.title == "Updated Title"


def test_wiki_build_skips_page_with_insufficient_facts(client):
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
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 3
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  report = runner.run()

  assert report.pages_built == 2
  assert report.pages_skipped == 1
  assert report.errors == 0
  assert client.app.state.memory_service.get_wiki_page("test") is None
  assert client.app.state.memory_service.get_wiki_page("index") is not None
  assert client.app.state.memory_service.get_wiki_page("log") is not None


def test_memory_service_invalidates_only_matching_themed_pages(client):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="motivation",
        title="Motivation",
        description="Motivation patterns",
        domains=["self"],
        kinds=["reflection"],
        themes=["motivation"],
      ),
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career summary",
        domains=["self"],
        kinds=["fact", "reflection"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  _create_item(client, domain="self", kind="fact", statement="User values autonomy.")
  runner.run()
  client.app.state.memory_service.upsert_wiki_page(
    page_name="motivation",
    title="Motivation",
    content_md="# Motivation",
    facts_count=0,
    reflections_count=1,
  )

  _create_item(
    client,
    domain="self",
    kind="reflection",
    statement="Autonomy is a sustained motivator.",
    metadata={"theme": "motivation"},
  )

  motivation_page = client.app.state.memory_service.get_wiki_page("motivation")
  career_page = client.app.state.memory_service.get_wiki_page("career")

  assert motivation_page is not None
  assert motivation_page.invalidated_at is not None
  assert career_page is not None
  assert career_page.invalidated_at is not None


def test_memory_service_does_not_invalidate_for_unsupported_kind(client):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career summary",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  _create_item(client, domain="self", kind="fact", statement="User values autonomy.")
  runner.run()
  _create_item(client, domain="self", kind="tension", statement="User feels tradeoffs between speed and rigor.")

  page = client.app.state.memory_service.get_wiki_page("career")

  assert page is not None
  assert page.invalidated_at is None


@pytest.mark.parametrize("kind", ["decision", "summary", "note", "task"])
def test_memory_service_invalidates_supported_fact_like_kinds(client, kind):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="operations",
        title="Operations",
        description="Operational notes",
        domains=["self"],
        kinds=[kind],
      ),
    ],
  )
  _install_wiki_schema(client, wiki_schema=wiki_schema)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="operations",
    title="Operations",
    content_md="# Operations",
    facts_count=1,
    reflections_count=0,
  )

  _create_item(client, domain="self", kind=kind, statement=f"Example {kind} statement.")

  page = client.app.state.memory_service.get_wiki_page("operations")

  assert page is not None
  assert page.invalidated_at is not None


def test_wiki_build_related_pages_prefers_built_pages(client):
  # When two schema neighbors have the same base score, the one already built
  # in the DB gets a score bonus and should appear first in related pages.
  _create_item(client, domain="self", kind="fact", statement="User builds automation.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User values autonomy.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User has strong values.", metadata={"theme": "values"})
  _create_item(client, domain="self", kind="fact", statement="User prefers minimalism.", metadata={"theme": "values"})

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="values",
        title="Values",
        description="Personal values",
        domains=["self"],
        kinds=["fact"],
        themes=["values"],
      ),
      WikiPageDefinition(
        name="workstyle",
        title="Workstyle",
        description="Daily work habits",
        domains=["self"],
        kinds=["fact"],
        themes=["workstyle"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  # Build values first so it becomes a built page
  runner.run(page_name="values")

  # Now build career — values (already built) should rank above workstyle (not built)
  runner.run(page_name="career")

  career_page = client.app.state.memory_service.get_wiki_page("career")
  assert career_page is not None
  content = strip_cached_page_metadata(career_page.content_md)
  assert "## Related Pages" in content
  # values was built before career run — gets the built-page bonus; workstyle was not
  values_pos = content.find("[Values](wiki:values)")
  workstyle_pos = content.find("[Workstyle](wiki:workstyle)")
  assert values_pos != -1
  assert workstyle_pos != -1
  assert values_pos < workstyle_pos, "values (built) should appear before workstyle (unbuilt)"


def test_wiki_build_related_pages_uses_description_overlap(client):
  # Pages whose descriptions share keywords with the current page should score
  # higher than equally-structured pages with unrelated descriptions.
  _create_item(client, domain="self", kind="fact", statement="User builds career systems.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User pursues career growth.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User has strong ethics.", metadata={"theme": "ethics"})
  _create_item(client, domain="self", kind="fact", statement="User values integrity.", metadata={"theme": "ethics"})
  _create_item(client, domain="self", kind="fact", statement="User enjoys hobbies.", metadata={"theme": "leisure"})
  _create_item(client, domain="self", kind="fact", statement="User likes reading.", metadata={"theme": "leisure"})

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career development and professional growth",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="ethics",
        title="Ethics",
        # description shares "professional" with career description
        description="Professional ethics and integrity standards",
        domains=["self"],
        kinds=["fact"],
        themes=["ethics"],
      ),
      WikiPageDefinition(
        name="leisure",
        title="Leisure",
        # description shares nothing meaningful with career description
        description="Hobbies and free time activities",
        domains=["self"],
        kinds=["fact"],
        themes=["leisure"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  runner.run(page_name="career")

  career_page = client.app.state.memory_service.get_wiki_page("career")
  assert career_page is not None
  content = strip_cached_page_metadata(career_page.content_md)
  assert "## Related Pages" in content
  # ethics description shares "professional" with career — should rank above leisure
  ethics_pos = content.find("[Ethics](wiki:ethics)")
  leisure_pos = content.find("[Leisure](wiki:leisure)")
  assert ethics_pos != -1
  assert leisure_pos != -1
  assert ethics_pos < leisure_pos, "ethics (description overlap) should appear before leisure (no overlap)"


def test_wiki_build_passes_related_pages_to_llm_client(client):
  # The runner must forward the computed related_pages list to synthesize_page
  # so the LLM can generate inline cross-links.
  _create_item(client, domain="self", kind="fact", statement="User values systems thinking.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User pursues professional growth.", metadata={"theme": "career"})
  _create_item(client, domain="self", kind="fact", statement="User focuses daily on focused blocks.", metadata={"theme": "work_style"})
  _create_item(client, domain="self", kind="fact", statement="User minimises interruptions.", metadata={"theme": "work_style"})

  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="workstyle",
        title="Workstyle",
        description="Daily work habits",
        domains=["self"],
        kinds=["fact"],
        themes=["work_style"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  runner.run(page_name="career")

  career_call = next(c for c in llm_client.synthesized_pages if c["page_name"] == "career")
  assert career_call["related_pages"] is not None
  related_names = [p["name"] for p in career_call["related_pages"]]
  assert "workstyle" in related_names


def test_memory_service_ignores_invalid_wiki_schema_on_write(client, tmp_path):
  invalid_schema = tmp_path / "broken_wiki_schema.yaml"
  invalid_schema.write_text("pages: [broken", encoding="utf-8")
  client.app.state.settings.wiki_schema_path = str(invalid_schema)

  response = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "Schema failures must not break writes.",
      "confidence": 0.7,
    },
  )

  assert response.status_code == 201


def test_supersede_item_invalidates_wiki_cache(client):
  wiki_schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career summary",
        domains=["self"],
        kinds=["fact"],
      ),
    ],
  )
  llm_client = FakeWikiLLMClient()
  client.app.state.settings.wiki_min_facts_per_page = 1
  runner = _build_runner(client, wiki_schema=wiki_schema, llm_client=llm_client)

  original = _create_item(client, domain="self", kind="fact", statement="Original fact.")
  replacement = _create_item(client, domain="self", kind="fact", statement="Replacement fact.")
  runner.run(page_name="career")

  page_before = client.app.state.memory_service.get_wiki_page("career")
  assert page_before is not None
  assert page_before.invalidated_at is None

  client.app.state.memory_service.supersede_item(
    item_id=UUID(original["id"]),
    replacement_item_id=UUID(replacement["id"]),
  )

  page_after = client.app.state.memory_service.get_wiki_page("career")
  assert page_after is not None
  assert page_after.invalidated_at is not None

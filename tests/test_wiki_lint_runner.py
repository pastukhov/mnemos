from __future__ import annotations

from datetime import UTC, datetime, timedelta

import yaml

from pipelines.wiki.wiki_lint_runner import WikiLintRunner
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


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


def _install_schema(client, *, schema: WikiSchema) -> None:
  schema_path = "/tmp/test_wiki_lint_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path


def test_wiki_lint_reports_stale_empty_and_orphan_facts(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.settings.wiki_min_facts_per_page = 2

  page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career",
    facts_count=1,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career",
    facts_count=1,
    reflections_count=0,
    generated_at=page.generated_at,
    invalidated_at=page.generated_at,
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="Matched fact",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="Orphan fact",
    metadata={"theme": "other", "source_type": "manual", "source_id": "fact_2"},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.stale_pages == ["career"]
  assert report.empty_pages == ["career"]
  assert report.orphan_facts_count == 1
  assert report.contradictions == []
  assert report.missing_related_pages == []
  assert report.missing_provenance_pages == ["career"]
  assert report.missing_source_refs_pages == ["career"]
  assert report.missing_source_highlights_pages == ["career"]
  assert report.broken_wiki_links == []
  assert report.finding_codes(severity="action") == [
    "empty_pages",
    "missing_source_refs_pages",
    "canonical_drift_pages",
  ]
  assert report.finding_codes(severity="warn") == [
    "stale_pages",
    "orphan_facts",
    "missing_provenance_pages",
    "missing_source_highlights_pages",
  ]


def test_wiki_lint_fix_rebuilds_stale_pages(client):
  schema = WikiSchema(
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
  _install_schema(client, schema=schema)
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds reliable automation systems.",
    metadata={"source_type": "manual", "source_id": "fact_1"},
  )

  page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# stale",
    facts_count=0,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=page.content_md,
    facts_count=page.facts_count,
    reflections_count=page.reflections_count,
    generated_at=page.generated_at,
    invalidated_at=page.generated_at,
  )

  runner = WikiLintRunner(
    client.app.state.memory_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )
  report = runner.run(fix=True)

  assert report.stale_pages == ["career"]
  assert report.fixed_pages == ["career"]
  rebuilt = client.app.state.memory_service.get_wiki_page("career")
  assert rebuilt is not None
  assert rebuilt.invalidated_at is None
  assert "User builds reliable automation systems." in rebuilt.content_md


def test_wiki_lint_reports_missing_related_sections_and_broken_links(client):
  schema = WikiSchema(
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
        description="Core values",
        domains=["self"],
        kinds=["fact"],
        themes=["values"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career\n\nLinked to [Ghost](wiki:ghost-page)\n",
    facts_count=3,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="values",
    title="Values",
    content_md="# Values\n\n## Provenance\n\n- facts_count: 2\n",
    facts_count=2,
    reflections_count=0,
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.missing_related_pages == ["career", "values"]
  assert report.missing_provenance_pages == ["career"]
  assert report.missing_source_refs_pages == ["career", "values"]
  assert report.missing_source_highlights_pages == ["career", "values"]
  assert report.unresolved_source_refs == []
  assert report.broken_wiki_links == ["career -> ghost-page"]


def test_wiki_lint_reports_contradictory_facts_within_theme(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="workstyle",
        title="Workstyle",
        description="How work gets done",
        domains=["self"],
        kinds=["fact"],
        themes=["workstyle"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User likes remote work.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User does not like remote work.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_2"},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run(domain="self")

  assert report.contradictions == [
    "self/workstyle: 'User likes remote work.' <-> 'User does not like remote work.'"
  ]


def test_wiki_lint_reports_structured_contradictions(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="workstyle",
        title="Workstyle",
        description="How work gets done",
        domains=["self"],
        kinds=["fact"],
        themes=["workstyle"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User prefers small teams.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User rejects small teams.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_2"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User always documents decisions.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_3"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User never documents decisions.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_4"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User works remotely.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_5"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User works on-site.",
    metadata={"theme": "workstyle", "source_type": "manual", "source_id": "fact_6"},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run(domain="self")

  assert report.contradictions == [
    "self/workstyle: 'User always documents decisions.' <-> 'User never documents decisions.'",
    "self/workstyle: 'User prefers small teams.' <-> 'User rejects small teams.'",
    "self/workstyle: 'User works remotely.' <-> 'User works on-site.'",
  ]


def test_wiki_lint_reports_unresolved_source_refs(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=(
      "# Career\n\n"
      "## Provenance\n\n"
      "- facts_count: 1\n"
      "- reflections_count: 0\n"
      "- source_ref: manual:missing_fact\n"
    ),
    facts_count=1,
    reflections_count=0,
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.missing_source_highlights_pages == ["career"]
  assert report.unresolved_source_refs == ["career -> manual:missing_fact"]


def test_wiki_lint_reports_low_source_coverage(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=(
      "# Career\n\n"
      "## Source Highlights\n\n"
      "- [manual:fact_1] User builds durable systems.\n\n"
      "## Provenance\n\n"
      "- facts_count: 4\n"
      "- reflections_count: 0\n"
      "- source_ref: manual:fact_1\n"
    ),
    facts_count=4,
    reflections_count=0,
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.low_source_coverage_pages == ["career (1/3)"]


def test_wiki_lint_reports_overmerged_query_pages(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey and systems work",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="values",
        title="Values",
        description="Core values",
        domains=["self"],
        kinds=["fact"],
        themes=["values"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.settings.wiki_query_merge_provenance_max_entries = 2
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-kind-of-systems-does-the-user-build",
    title="Q&A: What kind of systems does the user build?",
    content_md=(
      "# Q&A: What kind of systems does the user build?\n\n"
      "## Query\n\n"
      "What kind of systems does the user build?\n\n"
      "## Answer\n\n"
      "Answer.\n\n"
      "## Sources\n\n"
      "- [career](wiki:career)\n"
      "- [values](wiki:values)\n\n"
      "## Merge Provenance\n\n"
      "- qa-self-a :: A?\n"
      "- qa-self-b :: B?\n"
      "- qa-self-c :: C?\n"
    ),
    facts_count=3,
    reflections_count=0,
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.overmerged_query_pages == [
    "qa-self-what-kind-of-systems-does-the-user-build (3/2)"
  ]
  assert report.canonicalization_candidates == [
    "qa-self-what-kind-of-systems-does-the-user-build -> career"
  ]


def test_wiki_lint_reports_canonical_drift_pages(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career\n\n## Query\n\nWhat?\n\n## Answer\n\nAnswer.\n",
    facts_count=3,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.canonical_drift_pages == ["career"]


def test_wiki_lint_reports_orphaned_query_pages(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-orphaned",
    title="Q&A: Orphaned",
    content_md=(
      "# Q&A: Orphaned\n\n"
      "## Query\n\n"
      "What is the orphaned answer?\n\n"
      "## Answer\n\n"
      "Unknown.\n"
    ),
    facts_count=1,
    reflections_count=0,
    metadata={"page_kind": "query", "origin": "query_answer", "domains": ["self"], "merge_count": 0},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.orphaned_query_pages == ["qa-self-orphaned"]


def test_wiki_lint_reports_stale_navigation_pages(client):
  old_generated_at = datetime.now(UTC) - timedelta(days=1)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="index",
    title="Wiki Index",
    content_md="# Wiki Index",
    facts_count=0,
    reflections_count=0,
    generated_at=old_generated_at,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="log",
    title="Activity Log",
    content_md="# Activity Log",
    facts_count=0,
    reflections_count=0,
    generated_at=old_generated_at,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career",
    facts_count=3,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )
  _create_item(
    client,
    domain="self",
    kind="note",
    statement="Recent item for log drift.",
    metadata={"source_type": "manual", "source_id": "note_1"},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.stale_navigation_pages == ["index", "log"]


def test_wiki_lint_reports_missing_page_candidates(client):
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User is studying distributed systems.",
    metadata={"theme": "learning", "source_type": "manual", "source_id": "fact_1"},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.missing_page_candidates == [
    "self/learning -> create canonical page (1 facts)"
  ]


def test_wiki_lint_reports_weakly_connected_pages(client):
  # canonical page with no inbound links from other pages is weakly connected
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career\n\n## Overview\n\nSome content.\n",
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.weakly_connected_pages == ["career"]
  assert "weakly_connected_pages" in report.finding_codes(severity="warn")


def test_wiki_lint_weakly_connected_not_reported_when_inbound_link_exists(client):
  # when another page links to career, it is no longer weakly connected
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career\n\n## Overview\n\nSome content.\n",
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="values",
    title="Values",
    content_md="# Values\n\nSee [Career](wiki:career).\n",
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["values"]},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  # career has inbound link from values, so it is not weakly connected
  assert "career" not in report.weakly_connected_pages
  # values has no inbound links and is weakly connected
  assert "values" in report.weakly_connected_pages


def test_wiki_lint_reports_editorial_structure_issues(client):
  # canonical page with facts but no content sections is an editorial issue
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=(
      "# Career\n\n"
      "## Provenance\n\n"
      "- facts_count: 2\n"
      "## Source Highlights\n\n"
      "- [manual:fact_1] Some fact.\n"
    ),
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.editorial_structure_issues == ["career (missing content section)"]
  assert "editorial_structure_issues" in report.finding_codes(severity="warn")


def test_wiki_lint_no_editorial_issue_when_content_section_present(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=(
      "# Career\n\n"
      "## Overview\n\n"
      "User is a software engineer.\n\n"
      "## Provenance\n\n"
      "- facts_count: 2\n"
    ),
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": ["career"]},
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  assert report.editorial_structure_issues == []


def test_wiki_lint_related_pages_incomplete_section_is_flagged(client):
  # When a canonical page has a Related Pages section that does NOT link to
  # the top expected schema neighbor, it should still be flagged.
  schema = WikiSchema(
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
        description="Core values",
        domains=["self"],
        kinds=["fact"],
        themes=["values"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=(
      "# Career\n\n"
      "## Overview\n\nCareer content.\n\n"
      "## Related Pages\n\n"
      # Deliberately links to a different page — not 'values' which is the expected neighbor
      "- [Some Other](wiki:some-other)\n"
    ),
    facts_count=2,
    reflections_count=0,
    metadata={
      "page_kind": "canonical",
      "origin": "schema",
      "domains": ["self"],
      "themes": ["career"],
    },
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="values",
    title="Values",
    content_md="# Values\n\n## Related Pages\n\n- [Career](wiki:career)\n",
    facts_count=2,
    reflections_count=0,
    metadata={
      "page_kind": "canonical",
      "origin": "schema",
      "domains": ["self"],
      "themes": ["values"],
    },
  )

  report = WikiLintRunner(client.app.state.memory_service, client.app.state.settings).run()

  # career has a Related Pages section but does not link to values (top expected)
  assert "career" in report.missing_related_pages
  # values correctly links to career — not flagged
  assert "values" not in report.missing_related_pages

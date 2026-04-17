from __future__ import annotations

import pytest
import yaml

from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema
from workers.pipeline_worker import PipelineWorker


@pytest.mark.asyncio
async def test_pipeline_worker_processes_raw_items_into_facts_reflections_and_wiki(client):
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What motivates you?\nAnswer: I prefer building automated systems; I enjoy reducing repetitive manual work.",
      "confidence": 0.95,
      "metadata": {"source_type": "questionnaire", "source_id": "q_1", "topic": "motivation"},
    },
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What do you value?\nAnswer: I value observable delivery; I prefer reusable systems.",
      "confidence": 0.95,
      "metadata": {"source_type": "questionnaire", "source_id": "q_2", "topic": "motivation"},
    },
  )

  worker = client.app.state.pipeline_worker

  report = await worker.run_once()

  assert report.errors == 0
  assert report.fact_domains == ["self"]
  assert report.reflection_domains == ["self"]
  assert report.wiki_domains == ["self"]
  assert report.wiki_pages == []
  assert report.lint_orphan_facts_count == 0

  facts = client.app.state.memory_service.list_items_by_domain_kind(domain="self", kind="fact")
  reflections = client.app.state.memory_service.list_items_by_domain_kind(domain="self", kind="reflection")

  assert len(facts) == 4
  assert len(reflections) == 1

  page = client.app.state.memory_service.get_wiki_page("career")

  assert page is not None
  assert page.invalidated_at is None
  assert page.facts_count == 4
  assert page.reflections_count == 1
  assert "stable motivation pattern" in page.content_md


@pytest.mark.asyncio
async def test_pipeline_worker_rebuilds_invalidated_wiki_pages(client):
  client.app.state.settings.wiki_min_facts_per_page = 1
  initial_page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Карьера и навыки",
    content_md="# stale",
    facts_count=0,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Карьера и навыки",
    content_md="# stale",
    facts_count=0,
    reflections_count=0,
    generated_at=initial_page.generated_at,
    invalidated_at=initial_page.generated_at,
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "topic": "career"},
    },
  )

  worker = PipelineWorker(
    memory_service=client.app.state.memory_service,
    fact_runner=client.app.state.fact_runner,
    reflection_runner=client.app.state.reflection_runner,
    wiki_runner=client.app.state.wiki_runner,
    interval_seconds=60.0,
  )

  report = await worker.run_once()

  assert report.errors == 0
  assert report.fact_domains == []
  assert report.reflection_domains == []
  assert report.wiki_domains == []
  assert report.wiki_pages == ["career"]

  page = client.app.state.memory_service.get_wiki_page("career")

  assert page is not None
  assert page.invalidated_at is None
  assert "User builds reliable automation systems." in page.content_md


@pytest.mark.asyncio
async def test_pipeline_worker_rebuilds_invalidated_navigation_pages(client):
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.memory_service.upsert_wiki_page(
    page_name="index",
    title="Wiki Index",
    content_md="# stale index",
    facts_count=0,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="log",
    title="Activity Log",
    content_md="# stale log",
    facts_count=0,
    reflections_count=0,
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "summary",
      "statement": "Fresh summary for synthetic page rebuilds.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "summary_1", "topic": "career"},
    },
  )

  worker = PipelineWorker(
    memory_service=client.app.state.memory_service,
    fact_runner=client.app.state.fact_runner,
    reflection_runner=client.app.state.reflection_runner,
    wiki_runner=client.app.state.wiki_runner,
    interval_seconds=60.0,
  )

  report = await worker.run_once()

  assert report.errors == 0
  assert sorted(report.wiki_pages) == ["index", "log"]

  index_page = client.app.state.memory_service.get_wiki_page("index")
  log_page = client.app.state.memory_service.get_wiki_page("log")
  assert index_page is not None
  assert log_page is not None
  assert index_page.invalidated_at is None
  assert log_page.invalidated_at is None
  assert "# Wiki Index" in index_page.content_md
  assert "Fresh summary for synthetic page rebuilds." in log_page.content_md


@pytest.mark.asyncio
async def test_pipeline_worker_reports_wiki_lint_state(client):
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
  schema_path = "/tmp/test_pipeline_worker_wiki_lint.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_min_facts_per_page = 2
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# stale",
    facts_count=1,
    reflections_count=0,
  )
  page = client.app.state.memory_service.get_wiki_page("career")
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md=page.content_md,
    facts_count=page.facts_count,
    reflections_count=page.reflections_count,
    generated_at=page.generated_at,
    invalidated_at=page.generated_at,
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "Orphan fact for lint report.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_orphan", "theme": "unknown"},
    },
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User likes remote work.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_like", "theme": "career"},
    },
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User does not like remote work.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_dislike", "theme": "career"},
    },
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert report.lint_stale_pages == []
  assert report.lint_empty_pages == []
  assert report.lint_orphan_facts_count >= 1
  assert report.lint_contradictions == [
    "self/career: 'User likes remote work.' <-> 'User does not like remote work.'"
  ]
  assert report.lint_unresolved_source_refs == []
  assert report.lint_canonical_drift_pages == []
  assert report.lint_orphaned_query_pages == []
  assert report.lint_stale_navigation_pages == []
  assert report.lint_missing_page_candidates == [
    "self/unknown -> create canonical page (1 facts)"
  ]


@pytest.mark.asyncio
async def test_pipeline_worker_refreshes_auto_query_pages(client):
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
  schema_path = "/tmp/test_pipeline_worker_query_maintenance.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_min_facts_per_page = 1

  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "theme": "career"},
    },
  )
  client.app.state.wiki_runner.run()
  result = client.app.state.wiki_query_runner.query(
    "What kind of systems does the user build?",
    domain="self",
    top_k=3,
    persist_page_name="qa-self-what-kind-of-systems-does-the-user-build",
  )
  assert result.persisted_page_name is not None

  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User eliminates repetitive manual work.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_2", "theme": "career"},
    },
  )
  client.app.state.wiki_runner.run(page_name="career")

  report = await client.app.state.pipeline_worker.run_once()

  assert result.persisted_page_name in report.refreshed_query_pages
  persisted = client.app.state.memory_service.get_wiki_page(result.persisted_page_name)
  assert persisted is not None
  assert "User eliminates repetitive manual" in persisted.content_md


@pytest.mark.asyncio
async def test_pipeline_worker_prunes_weak_auto_query_pages(client):
  client.app.state.settings.wiki_query_auto_persist_min_confidence = 0.75
  client.app.state.settings.wiki_query_auto_persist_min_sources = 2
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-unknown-question",
    title="Q&A: Unknown question",
    content_md="# Q&A: Unknown question\n\n## Query\n\nUnknown question\n",
    facts_count=0,
    reflections_count=0,
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert "qa-self-unknown-question" in report.pruned_query_pages
  assert client.app.state.memory_service.get_wiki_page("qa-self-unknown-question") is None


@pytest.mark.asyncio
async def test_pipeline_worker_reports_unresolved_wiki_source_refs(client):
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

  report = await client.app.state.pipeline_worker.run_once()

  assert report.lint_unresolved_source_refs == ["career -> manual:missing_fact"]


@pytest.mark.asyncio
async def test_pipeline_worker_reports_low_source_coverage(client):
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

  report = await client.app.state.pipeline_worker.run_once()

  assert report.lint_low_source_coverage_pages == ["career (1/3)"]


@pytest.mark.asyncio
async def test_pipeline_worker_reports_overmerged_query_pages(client):
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
    ],
  )
  schema_path = "/tmp/test_pipeline_worker_query_canonicalization.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_query_merge_provenance_max_entries = 2
  client.app.state.settings.wiki_query_maintenance_enabled = False
  client.app.state.pipeline_worker.wiki_canonicalization_runner = None
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
      "- [career](wiki:career)\n\n"
      "## Merge Provenance\n\n"
      "- qa-self-a :: A?\n"
      "- qa-self-b :: B?\n"
      "- qa-self-c :: C?\n"
    ),
    facts_count=3,
    reflections_count=0,
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert report.lint_overmerged_query_pages == [
    "qa-self-what-kind-of-systems-does-the-user-build (3/2)"
  ]
  assert report.lint_canonicalization_candidates == [
    "qa-self-what-kind-of-systems-does-the-user-build -> career"
  ]
  assert report.lint_canonical_drift_pages == []
  assert report.lint_orphaned_query_pages == []
  assert report.lint_stale_navigation_pages == []
  assert report.lint_missing_page_candidates == []
  assert report.lint_action_required_findings == [
    "missing_source_refs_pages",
    "canonicalization_candidates",
  ]
  assert report.lint_warning_findings == [
    "missing_provenance_pages",
    "missing_source_highlights_pages",
    "overmerged_query_pages",
  ]


@pytest.mark.asyncio
async def test_pipeline_worker_canonicalizes_overmerged_query_pages(client):
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
    ],
  )
  schema_path = "/tmp/test_pipeline_worker_query_canonicalize.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.settings.wiki_query_merge_provenance_max_entries = 2
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "theme": "career"},
    },
  )
  client.app.state.wiki_runner.run()
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
      "- [career](wiki:career)\n\n"
      "## Merge Provenance\n\n"
      "- qa-self-a :: A?\n"
      "- qa-self-b :: B?\n"
      "- qa-self-c :: C?\n"
    ),
    facts_count=3,
    reflections_count=0,
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert report.canonicalized_query_pages == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert report.canonicalized_targets == ["career"]
  assert report.lint_overmerged_query_pages == []
  assert report.lint_canonicalization_candidates == []
  assert report.lint_canonical_drift_pages == []
  assert report.lint_orphaned_query_pages == []
  assert report.lint_stale_navigation_pages == []
  assert report.lint_missing_page_candidates == []
  assert report.lint_action_required_findings == []
  # career is the only canonical page and has no inbound links from other pages —
  # weakly_connected_pages is expected here because the wiki has a single page with no peers.
  assert set(report.lint_warning_findings) <= {"weakly_connected_pages"}
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build") is None
  materialized = client.app.state.memory_service.get_item_by_source_ref(
    source_type="wiki_canonicalization",
    source_id="career:qa-self-what-kind-of-systems-does-the-user-build",
  )
  assert materialized is not None


@pytest.mark.asyncio
async def test_pipeline_worker_dedupes_duplicate_auto_query_pages(client):
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
  schema_path = "/tmp/test_pipeline_worker_query_dedupe.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "theme": "career"},
    },
  )
  client.app.state.wiki_runner.run()
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-kind-of-systems-does-the-user-build",
    title="Q&A: What kind of systems does the user build?",
    content_md=(
      "# Q&A: What kind of systems does the user build?\n\n"
      "## Query\n\n"
      "What kind of systems does the user build?\n\n"
      "## Answer\n\n"
      "Primary answer.\n"
    ),
    facts_count=3,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-kind-of-systems-does-the-user-build-copy",
    title="Q&A: What kind of systems does the user build?",
    content_md=(
      "# Q&A: What kind of systems does the user build?\n\n"
      "## Query\n\n"
      "What kind of systems does the user build?\n\n"
      "## Answer\n\n"
      "Duplicate answer.\n"
    ),
    facts_count=1,
    reflections_count=0,
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert report.refreshed_query_pages == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert report.pruned_query_pages == []
  assert report.deduped_query_pages == ["qa-self-what-kind-of-systems-does-the-user-build-copy"]
  kept_page = client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build")
  assert kept_page is not None
  assert "## Merge Provenance" in kept_page.content_md
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build-copy") is None


@pytest.mark.asyncio
async def test_pipeline_worker_dedupes_near_duplicate_auto_query_pages(client):
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
  schema_path = "/tmp/test_pipeline_worker_query_near_dedupe.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "theme": "career"},
    },
  )
  client.app.state.wiki_runner.run()
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-kind-of-systems-does-the-user-build",
    title="Q&A: What kind of systems does the user build?",
    content_md=(
      "# Q&A: What kind of systems does the user build?\n\n"
      "## Query\n\n"
      "What kind of systems does the user build?\n\n"
      "## Answer\n\n"
      "Primary answer.\n\n"
      "## Sources\n\n"
      "- [career](wiki:career)\n"
    ),
    facts_count=3,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-systems-does-the-user-like-to-build",
    title="Q&A: What systems does the user like to build?",
    content_md=(
      "# Q&A: What systems does the user like to build?\n\n"
      "## Query\n\n"
      "What systems does the user like to build?\n\n"
      "## Answer\n\n"
      "Near duplicate answer.\n\n"
      "## Sources\n\n"
      "- [career](wiki:career)\n"
      "- [values](wiki:values)\n"
    ),
    facts_count=1,
    reflections_count=0,
  )

  report = await client.app.state.pipeline_worker.run_once()

  assert report.refreshed_query_pages == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert report.pruned_query_pages == []
  assert report.deduped_query_pages == ["qa-self-what-systems-does-the-user-like-to-build"]
  kept_page = client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build")
  assert kept_page is not None
  assert "- [career](wiki:career)" in kept_page.content_md
  assert "- [values](wiki:values)" in kept_page.content_md
  assert "## Merge Provenance" in kept_page.content_md
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-systems-does-the-user-like-to-build") is None


@pytest.mark.asyncio
async def test_pipeline_worker_last_report_is_stored_after_run(client):
  # Before any run, _last_report should be None
  assert client.app.state.pipeline_worker._last_report is None

  await client.app.state.pipeline_worker.run_once()

  # After run, _last_report should be set
  assert client.app.state.pipeline_worker._last_report is not None
  report = client.app.state.pipeline_worker._last_report
  assert isinstance(report.errors, int)
  assert isinstance(report.fact_domains, list)


@pytest.mark.asyncio
async def test_wiki_maintenance_history_available_after_worker_run(client):
  await client.app.state.pipeline_worker.run_once()

  response = client.get("/api/wiki/maintenance/history")

  assert response.status_code == 200
  body = response.json()
  assert body["available"] is True
  assert "fact_domains" in body
  assert "lint_action_required_findings" in body
  assert "lint_warning_findings" in body

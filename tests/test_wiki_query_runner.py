from __future__ import annotations

import yaml

from pipelines.wiki.wiki_query_runner import (
  QUERY_OUTCOME_CANONICAL_PROMOTION,
  QUERY_OUTCOME_EPHEMERAL,
  QUERY_OUTCOME_QUERY_PAGE,
  WikiQueryRunner,
)
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
  schema_path = "/tmp/test_wiki_query_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None


def test_wiki_query_runner_returns_sources_and_answer(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query("What kind of systems does the user build?", domain="self", top_k=3)

  assert "Question: What kind of systems does the user build?" in result.answer
  assert "Wiki synthesis:" in result.answer
  assert "Index overview:" in result.answer
  assert "Recent activity:" in result.answer
  assert "career" in result.sources
  assert "index" in result.sources
  assert "log" in result.sources
  assert result.confidence > 0


def test_wiki_query_runner_handles_missing_sources(client):
  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
  ).query("Unknown question", domain="self", top_k=3)

  assert result.sources == []
  assert result.confidence == 0.0


def test_wiki_query_runner_can_persist_answer_as_cached_page(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )
  result = runner.query(
    "What kind of systems does the user build?",
    domain="self",
    top_k=3,
    persist_page_name="qa-systems",
    persist_title="Q&A: Systems",
  )

  assert "career" in result.sources
  persisted = client.app.state.memory_service.get_wiki_page("qa-systems")
  assert persisted is not None
  assert persisted.title == "Q&A: Systems"
  assert "## Query" in persisted.content_md
  assert "## Answer" in persisted.content_md
  assert "## Sources" in persisted.content_md
  assert "[career](wiki:career)" in persisted.content_md
  assert result.persisted_page_name == "qa-systems"


def test_wiki_query_runner_rebuilds_stale_pages_before_answering(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  page = client.app.state.memory_service.get_wiki_page("career")
  assert page is not None
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title=page.title,
    content_md=page.content_md,
    facts_count=page.facts_count,
    reflections_count=page.reflections_count,
    generated_at=page.generated_at,
    invalidated_at=page.generated_at,
  )

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query("What kind of systems does the user build?", domain="self", top_k=3)

  assert "career" in result.sources
  rebuilt = client.app.state.memory_service.get_wiki_page("career")
  assert rebuilt is not None
  assert rebuilt.invalidated_at is None


def test_wiki_query_runner_expands_to_related_pages(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User rejects killing under any circumstances.",
    metadata={"theme": "values", "source_type": "manual", "source_id": "fact_2"},
  )
  client.app.state.wiki_runner.run()
  values_page = client.app.state.memory_service.get_wiki_page("values")
  assert values_page is not None
  career_page = client.app.state.memory_service.get_wiki_page("career")
  assert career_page is not None
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title=career_page.title,
    content_md=f"{career_page.content_md}\n\n## Related Pages\n\n- [Values](wiki:values)\n",
    facts_count=career_page.facts_count,
    reflections_count=career_page.reflections_count,
    generated_at=career_page.generated_at,
    invalidated_at=None,
  )

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query("What kind of systems does the user build?", domain="self", top_k=1)

  assert "career" in result.sources
  assert "values" in result.sources
  assert "Related pages:" in result.answer


def test_wiki_query_runner_does_not_persist_low_confidence_answer(client):
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
  )

  result = runner.query(
    "Unknown question",
    domain="self",
    top_k=3,
    persist_page_name="qa-empty",
    persist_title="Q&A: Empty",
  )

  assert result.sources == []
  assert client.app.state.memory_service.get_wiki_page("qa-empty") is None


def test_wiki_query_runner_can_auto_persist_high_confidence_answer(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    "What is the user's career and professional journey?",
    domain="self",
    top_k=3,
    auto_persist=True,
  )

  assert result.persisted_page_name is None
  assert result.promoted_canonical_target == "career"
  promoted = client.app.state.memory_service.get_item_by_source_ref(
    source_type="wiki_query_promotion",
    source_id="career:what-is-the-user-s-career-and-professional-journey",
  )
  assert promoted is not None
  assert promoted.metadata_json["canonical_page"] == "career"
  rebuilt = client.app.state.memory_service.get_wiki_page("career")
  assert rebuilt is not None
  assert "Promoted wiki query for 'career'." in rebuilt.content_md


def test_wiki_query_runner_falls_back_to_qa_page_when_canonical_target_is_ambiguous(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User values principled decisions.",
    metadata={"theme": "values", "source_type": "manual", "source_id": "fact_2"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    "What matters most to the user?",
    domain="self",
    top_k=3,
    auto_persist=True,
  )

  assert result.promoted_canonical_target is None
  assert result.persisted_page_name == "qa-self-what-matters-most-to-the-user"
  persisted = client.app.state.memory_service.get_wiki_page(result.persisted_page_name)
  assert persisted is not None


def test_wiki_query_runner_can_refresh_auto_persisted_page(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )
  result = runner.query(
    "What kind of systems does the user build?",
    domain="self",
    top_k=3,
    persist_page_name="qa-self-what-kind-of-systems-does-the-user-build",
  )
  page_name = result.persisted_page_name
  assert page_name is not None

  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User also optimizes repetitive workflows.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_2"},
  )
  client.app.state.wiki_runner.run(page_name="career")

  refreshed = runner.refresh_auto_persisted_page(page_name)

  assert refreshed == "refreshed"
  persisted = client.app.state.memory_service.get_wiki_page(page_name)
  assert persisted is not None
  assert "optimizes repetitive workflows" in persisted.content_md


def test_wiki_query_refresh_promotes_recurring_query_to_canonical(client):
  # When a qa-* page's question clearly matches a canonical page descriptor,
  # refresh_auto_persisted_page should promote it to that canonical page and
  # mark the qa-* page as lifecycle_state="superseded".
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.settings.wiki_query_promote_to_canonical_enabled = True
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  # Create a qa-* page with a question that has token overlap with career descriptor
  # ("career" appears in both question and page descriptor)
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-career-trajectory",
    title="Q&A: Career trajectory",
    content_md=(
      "# Q&A: Career trajectory\n\n"
      "## Query\n\n"
      "What is the user's career professional trajectory?\n\n"
      "## Answer\n\n"
      "The user has a career focused on systems.\n"
    ),
    facts_count=3,
    reflections_count=0,
    metadata={
      "page_kind": "query",
      "origin": "query_answer",
      "domains": ["self"],
      "lifecycle_state": "refreshable",
    },
  )
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )

  outcome = runner.refresh_auto_persisted_page("qa-self-career-trajectory")

  assert outcome == "promoted"
  page = client.app.state.memory_service.get_wiki_page("qa-self-career-trajectory")
  assert page is not None
  page_metadata = page.metadata_json or {}
  assert page_metadata.get("lifecycle_state") == "superseded"
  assert page_metadata.get("superseded_by") == "career"


def test_wiki_query_runner_prunes_weak_auto_persisted_page(client):
  client.app.state.settings.wiki_query_auto_persist_min_confidence = 0.75
  client.app.state.settings.wiki_query_auto_persist_min_sources = 2
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-unknown-question",
    title="Q&A: Unknown question",
    content_md="# Q&A: Unknown question\n\n## Query\n\nUnknown question\n",
    facts_count=0,
    reflections_count=0,
  )
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )

  outcome = runner.refresh_auto_persisted_page("qa-self-unknown-question")

  assert outcome == "pruned"
  assert client.app.state.memory_service.get_wiki_page("qa-self-unknown-question") is None


def test_wiki_query_runner_dedupes_duplicate_auto_query_pages(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
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
      "First answer.\n"
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
      "Second answer.\n"
    ),
    facts_count=1,
    reflections_count=0,
  )
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )

  refreshed, pruned, deduped, promoted = runner.refresh_auto_persisted_pages()

  assert refreshed == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert pruned == []
  assert deduped == ["qa-self-what-kind-of-systems-does-the-user-build-copy"]
  kept_page = client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build")
  assert kept_page is not None
  assert "## Merge Provenance" in kept_page.content_md
  assert "- qa-self-what-kind-of-systems-does-the-user-build-copy :: What kind of systems does the user build?" in kept_page.content_md
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build-copy") is None


def test_wiki_query_runner_dedupes_near_duplicate_auto_query_pages(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
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
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )

  refreshed, pruned, deduped, promoted = runner.refresh_auto_persisted_pages()

  assert refreshed == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert pruned == []
  assert deduped == ["qa-self-what-systems-does-the-user-like-to-build"]
  kept_page = client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build")
  assert kept_page is not None
  assert "- [career](wiki:career)" in kept_page.content_md
  assert "- [values](wiki:values)" in kept_page.content_md
  assert "## Merge Provenance" in kept_page.content_md
  assert "- qa-self-what-systems-does-the-user-like-to-build :: What systems does the user like to build?" in kept_page.content_md
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-systems-does-the-user-like-to-build") is None


def test_wiki_query_outcome_is_ephemeral_when_not_persisted(client):
  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
  ).query("Unknown question", domain="self", top_k=3)

  assert result.outcome == QUERY_OUTCOME_EPHEMERAL


def test_wiki_query_outcome_is_query_page_when_persisted(client):
  schema = WikiPageDefinition(
    name="career",
    title="Career",
    description="Professional journey",
    domains=["self"],
    kinds=["fact"],
    themes=["career"],
  )
  from pipelines.wiki.wiki_schema import WikiSchema
  _install_schema(client, schema=WikiSchema(pages=[schema]))
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    "What systems does the user build?",
    domain="self",
    top_k=3,
    persist_page_name="qa-systems-test",
    persist_title="Q&A: Systems",
  )

  assert result.outcome == QUERY_OUTCOME_QUERY_PAGE
  assert result.persisted_page_name == "qa-systems-test"


def test_wiki_query_outcome_is_canonical_promotion_when_promoted(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    "What is the user's career and professional journey?",
    domain="self",
    top_k=3,
    auto_persist=True,
  )

  assert result.outcome == QUERY_OUTCOME_CANONICAL_PROMOTION
  assert result.promoted_canonical_target == "career"


def test_wiki_query_lifecycle_state_fresh_on_create(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    "What systems does the user prefer?",
    domain="self",
    top_k=3,
    persist_page_name="qa-lifecycle-test",
  )

  page = client.app.state.memory_service.get_wiki_page("qa-lifecycle-test")
  assert page is not None
  assert page.metadata_json["lifecycle_state"] == "fresh"


def test_wiki_query_lifecycle_state_refreshable_on_update(client):
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )
  # First persist creates a fresh page
  runner.query(
    "What systems does the user prefer?",
    domain="self",
    top_k=3,
    persist_page_name="qa-lifecycle-refresh-test",
  )
  page = client.app.state.memory_service.get_wiki_page("qa-lifecycle-refresh-test")
  assert page is not None
  assert page.metadata_json["lifecycle_state"] == "fresh"

  # Second persist to the same page should update lifecycle_state to refreshable
  runner.query(
    "What systems does the user prefer?",
    domain="self",
    top_k=3,
    persist_page_name="qa-lifecycle-refresh-test",
  )
  refreshed = client.app.state.memory_service.get_wiki_page("qa-lifecycle-refresh-test")
  assert refreshed is not None
  assert refreshed.metadata_json["lifecycle_state"] == "refreshable"


def test_wiki_query_refresh_includes_query_kind_pages(client):
  # Pages with page_kind="query" in metadata but non-standard names should be refreshed
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  # Create a query page with non-standard name prefix but correct page_kind metadata
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-lifecycle-query-kind",
    title="Q&A: lifecycle",
    content_md=(
      "# Q&A: lifecycle\n\n"
      "## Query\n\n"
      "What systems does the user build?\n"
    ),
    facts_count=1,
    reflections_count=0,
    metadata={
      "page_kind": "query",
      "origin": "query_answer",
      "domains": ["self"],
      "lifecycle_state": "fresh",
    },
  )
  runner = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  )

  refreshed, pruned, deduped, promoted = runner.refresh_auto_persisted_pages()

  assert "qa-self-lifecycle-query-kind" in refreshed or "qa-self-lifecycle-query-kind" in pruned


def test_wiki_query_single_candidate_no_overlap_falls_back_to_qa_page(client):
  # When the only canonical candidate's descriptor has no token overlap with
  # the question, the answer must not be promoted — falls back to a qa-* page.
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
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    # "systems" and "build" have zero overlap with career descriptor tokens
    # {"career", "professional", "journey"}, so no canonical promotion.
    "What kind of systems does the user build?",
    domain="self",
    top_k=3,
    auto_persist=True,
  )

  assert result.promoted_canonical_target is None
  assert result.persisted_page_name is not None
  assert result.outcome == QUERY_OUTCOME_QUERY_PAGE


def test_wiki_query_tied_candidates_fall_back_to_qa_page(client):
  # When two canonical candidates tie on token overlap, the question is
  # ambiguous and must not be promoted to either.
  schema = WikiSchema(
    pages=[
      WikiPageDefinition(
        name="career",
        title="Career",
        description="Career professional journey",
        domains=["self"],
        kinds=["fact"],
        themes=["career"],
      ),
      WikiPageDefinition(
        name="values",
        title="Values",
        description="Core values and ethics",
        domains=["self"],
        kinds=["fact"],
        themes=["values"],
      ),
    ],
  )
  _install_schema(client, schema=schema)
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User values good design principles.",
    metadata={"theme": "values", "source_type": "manual", "source_id": "fact_2"},
  )
  client.app.state.wiki_runner.run()

  result = WikiQueryRunner(
    client.app.state.memory_service,
    client.app.state.retrieval_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).query(
    # "career" overlaps career page (1), "values" overlaps values page (1) — tie.
    "What are the user's career values?",
    domain="self",
    top_k=5,
    auto_persist=True,
  )

  assert result.promoted_canonical_target is None
  assert result.outcome == QUERY_OUTCOME_QUERY_PAGE

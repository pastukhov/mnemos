"""Tests for wiki API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import yaml

from db.repositories.memory_items import MemoryItemRepository
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


class FakeWikiLLMClient:
  def __init__(self) -> None:
    self.calls: list[dict[str, object]] = []

  def synthesize_page(self, page_def, facts, reflections, existing_content=None, related_pages=None):
    self.calls.append(
      {
        "page_name": page_def.name,
        "facts": list(facts),
        "reflections": list(reflections),
        "existing_content": existing_content,
      }
    )
    body = [f"# {page_def.title}", "", page_def.description, ""]
    if facts:
      body.append("## Facts")
      body.append("")
      body.extend(f"- {fact}" for fact in facts)
      body.append("")
    if reflections:
      body.append("## Reflections")
      body.append("")
      body.extend(f"- {reflection}" for reflection in reflections)
      body.append("")
    return "\n".join(body).strip()


def _create_item(client, *, domain: str, kind: str, statement: str, metadata: dict | None = None):
  response = client.post(
    "/memory/items",
    json={
      "domain": domain,
      "kind": kind,
      "statement": statement,
      "confidence": 0.8,
      "metadata": metadata or {},
    },
  )
  assert response.status_code == 201
  return response.json()


def _install_wiki_setup(client, *, schema: WikiSchema, llm_client: FakeWikiLLMClient) -> None:
  schema_path = "/tmp/test_wiki_api_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.wiki_runner.schema = schema
  client.app.state.wiki_runner.llm_client = llm_client


def test_list_wiki_pages_returns_cache_summaries(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career",
    facts_count=3,
    reflections_count=1,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"]},
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="values",
    title="Values",
    content_md="# Values",
    facts_count=2,
    reflections_count=0,
    metadata={"page_kind": "query", "origin": "query_answer", "domains": ["self"], "merge_count": 2},
    invalidated_at=datetime.now(UTC),
  )

  response = client.get("/api/wiki/pages")
  body = response.json()

  assert response.status_code == 200
  assert [item["name"] for item in body["items"]] == ["career", "values"]
  assert body["items"][0]["is_stale"] is False
  assert body["items"][1]["is_stale"] is True
  assert body["items"][0]["governance"]["page_kind"] == "canonical"
  assert body["items"][1]["governance"]["merge_count"] == 2


def test_get_wiki_page_builds_missing_page_lazily(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")

  response = client.get("/api/wiki/pages/career")
  body = response.json()

  assert response.status_code == 200
  assert body["name"] == "career"
  assert body["title"] == "Career"
  assert body["is_stale"] is False
  assert body["content"].startswith("# Career")
  assert "<!-- wiki-source-fingerprint:" not in body["content"]
  assert body["governance"]["page_kind"] == "canonical"
  assert len(llm_client.calls) == 1


def test_get_wiki_page_regenerates_stale_page(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")
  client.get("/api/wiki/pages/career")
  _create_item(client, domain="self", kind="fact", statement="User prefers observable delivery.")

  response = client.get("/api/wiki/pages/career")
  body = response.json()

  assert response.status_code == 200
  assert body["facts_count"] == 2
  assert body["is_stale"] is False
  assert len(llm_client.calls) == 2
  assert llm_client.calls[-1]["existing_content"].startswith("# Career")


def test_regenerate_wiki_page_forces_rebuild(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")
  client.get("/api/wiki/pages/career")

  response = client.post("/api/wiki/pages/career/regenerate")
  body = response.json()

  assert response.status_code == 200
  assert body["name"] == "career"
  assert body["is_stale"] is False
  assert len(llm_client.calls) == 2


def test_get_navigation_wiki_pages_builds_index_and_log(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")
  _create_item(client, domain="project", kind="decision", statement="Use PostgreSQL as source of truth.")

  index_response = client.get("/api/wiki/pages/index")
  log_response = client.get("/api/wiki/pages/log")
  list_response = client.get("/api/wiki/pages")

  assert index_response.status_code == 200
  assert index_response.json()["name"] == "index"
  assert "# Wiki Index" in index_response.json()["content"]
  assert "`career`" in index_response.json()["content"]

  assert log_response.status_code == 200
  assert log_response.json()["name"] == "log"
  assert "Use PostgreSQL as source of truth." in log_response.json()["content"]

  listed_names = [item["name"] for item in list_response.json()["items"]]
  assert "index" in listed_names
  assert "log" in listed_names


def test_log_navigation_page_keeps_recent_accepted_items_in_desc_order(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)

  for index in range(22):
    _create_item(client, domain="self", kind="fact", statement=f"Accepted fact {index:02d}")

  with client.app.state.session_factory() as session:
    repository = MemoryItemRepository(session)
    repository.create(
      domain="self",
      kind="fact",
      statement="Pending fact should not appear in log.",
      confidence=0.8,
      metadata={"source_type": "manual", "source_id": "pending_fact"},
      status="pending",
    )
    repository.create(
      domain="self",
      kind="summary",
      statement="Accepted summary should appear in log.",
      confidence=0.8,
      metadata={"source_type": "manual", "source_id": "accepted_summary"},
      status="accepted",
    )
    session.commit()

  response = client.get("/api/wiki/pages/log")
  content = response.json()["content"]

  assert response.status_code == 200
  assert "Accepted fact 21" in content
  assert "Accepted fact 20" in content
  assert "Accepted summary should appear in log." in content
  assert "Accepted fact 03" in content
  assert "Accepted fact 02" not in content
  assert "Accepted fact 01" not in content
  assert "Accepted fact 00" not in content
  assert content.index("Accepted fact 21") < content.index("Accepted fact 20")
  assert "Pending fact should not appear in log." not in content


def test_navigation_pages_rebuild_after_new_writes(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="Initial fact")

  first_index = client.get("/api/wiki/pages/index")
  first_log = client.get("/api/wiki/pages/log")
  assert first_index.status_code == 200
  assert first_log.status_code == 200

  _create_item(client, domain="self", kind="raw", statement="Fresh raw note for rebuild.")

  second_index = client.get("/api/wiki/pages/index")
  second_log = client.get("/api/wiki/pages/log")

  assert second_index.status_code == 200
  assert second_index.json()["is_stale"] is False
  assert second_index.json()["updated_at"] >= first_index.json()["updated_at"]
  assert "`career`" in second_index.json()["content"]
  assert second_log.status_code == 200
  assert second_log.json()["is_stale"] is False
  assert second_log.json()["updated_at"] >= first_log.json()["updated_at"]
  assert "Fresh raw note for rebuild." in second_log.json()["content"]


def test_lint_wiki_endpoint_reports_and_fixes_stale_pages(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(client, domain="self", kind="fact", statement="User builds durable systems.")
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

  report = client.post("/api/wiki/lint").json()
  fixed = client.post("/api/wiki/lint?fix=true").json()

  assert report["stale_pages"] == ["career"]
  assert report["missing_provenance_pages"] == ["career"]
  assert report["missing_related_pages"] == []
  assert report["missing_source_refs_pages"] == []
  assert report["missing_source_highlights_pages"] == []
  assert report["low_source_coverage_pages"] == []
  assert report["unresolved_source_refs"] == []
  assert report["broken_wiki_links"] == []
  assert report["canonical_drift_pages"] == ["career"]
  assert report["orphaned_query_pages"] == []
  assert report["stale_navigation_pages"] == []
  assert report["overmerged_query_pages"] == []
  assert report["canonicalization_candidates"] == []
  assert report["missing_page_candidates"] == []
  assert report["findings"] == [
    {"code": "stale_pages", "severity": "warn", "count": 1, "items": ["career"]},
    {"code": "empty_pages", "severity": "action", "count": 1, "items": ["career"]},
    {"code": "missing_provenance_pages", "severity": "warn", "count": 1, "items": ["career"]},
    {"code": "canonical_drift_pages", "severity": "action", "count": 1, "items": ["career"]},
  ]
  assert fixed["stale_pages"] == ["career"]
  assert fixed["fixed_pages"] == ["career"]
  rebuilt = client.app.state.memory_service.get_wiki_page("career")
  assert rebuilt is not None
  assert rebuilt.invalidated_at is None


def test_query_wiki_endpoint_returns_answer_and_sources(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  response = client.post(
    "/api/wiki/query",
    json={"question": "What kind of systems does the user build?", "domain": "self", "top_k": 3},
  )
  body = response.json()

  assert response.status_code == 200
  assert "Question: What kind of systems does the user build?" in body["answer"]
  assert "career" in body["sources"]
  assert body["confidence"] > 0
  assert body["persisted_page_name"] is None
  assert body["promoted_canonical_target"] is None


def test_query_wiki_endpoint_can_persist_answer_page(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  response = client.post(
    "/api/wiki/query",
    json={
      "question": "What kind of systems does the user build?",
      "domain": "self",
      "top_k": 3,
      "persist_page_name": "qa-systems",
      "persist_title": "Q&A: Systems",
    },
  )

  assert response.status_code == 200
  assert response.json()["persisted_page_name"] == "qa-systems"
  assert response.json()["promoted_canonical_target"] is None
  persisted = client.app.state.memory_service.get_wiki_page("qa-systems")
  assert persisted is not None
  assert persisted.title == "Q&A: Systems"


def test_query_wiki_endpoint_can_auto_persist_answer_page(client):
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
  llm_client = FakeWikiLLMClient()
  _install_wiki_setup(client, schema=schema, llm_client=llm_client)
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()

  response = client.post(
    "/api/wiki/query",
    json={
      "question": "What is the user's career and professional journey?",
      "domain": "self",
      "top_k": 3,
      "auto_persist": True,
    },
  )

  assert response.status_code == 200
  assert response.json()["persisted_page_name"] is None
  assert response.json()["promoted_canonical_target"] == "career"
  promoted = client.app.state.memory_service.get_item_by_source_ref(
    source_type="wiki_query_promotion",
    source_id="career:what-is-the-user-s-career-and-professional-journey",
  )
  assert promoted is not None
  assert response.json()["outcome"] == "canonical_promotion"


def test_wiki_query_outcome_ephemeral_when_no_sources(client):
  response = client.post(
    "/api/wiki/query",
    json={"question": "Unknown question", "domain": "self", "top_k": 3},
  )

  assert response.status_code == 200
  assert response.json()["outcome"] == "ephemeral"
  assert response.json()["persisted_page_name"] is None


def test_wiki_maintenance_refresh_returns_results(client):
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
  _install_wiki_setup(client, schema=schema, llm_client=FakeWikiLLMClient())
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-systems",
    title="Q&A: What systems?",
    content_md=(
      "# Q&A: What systems?\n\n## Query\n\nWhat kind of systems does the user build?\n"
    ),
    facts_count=1,
    reflections_count=0,
  )

  response = client.post("/api/wiki/maintenance/refresh")

  assert response.status_code == 200
  body = response.json()
  assert body["action"] == "refresh"
  assert "refreshed" in body
  assert "pruned" in body
  assert "deduped" in body


def test_wiki_maintenance_canonicalize_returns_results(client):
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
  _install_wiki_setup(client, schema=schema, llm_client=FakeWikiLLMClient())
  client.app.state.settings.wiki_min_facts_per_page = 1
  _create_item(
    client,
    domain="self",
    kind="fact",
    statement="User builds durable systems.",
    metadata={"theme": "career", "source_type": "manual", "source_id": "fact_1"},
  )
  client.app.state.wiki_runner.run()
  # Create an overmerged query page that should be canonicalized
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-what-kind-of-systems-does-the-user-build",
    title="Q&A: What systems?",
    content_md=(
      "# Q&A: What systems?\n\n"
      "## Query\n\nWhat kind of systems does the user build career?\n\n"
      "## Answer\n\nUser builds durable systems.\n\n"
      "## Sources\n\n- [career](wiki:career)\n\n"
      "## Merge Provenance\n\n"
      "- qa-a :: A?\n- qa-b :: B?\n- qa-c :: C?\n- qa-d :: D?\n"
    ),
    facts_count=4,
    reflections_count=0,
    metadata={"page_kind": "query", "origin": "query_answer", "domains": ["self"]},
  )

  response = client.post("/api/wiki/maintenance/canonicalize")

  assert response.status_code == 200
  body = response.json()
  assert body["action"] == "canonicalize"
  assert "canonicalized" in body
  assert "canonical_targets" in body


def test_wiki_maintenance_rebuild_returns_results(client):
  # Create a stale page
  page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career\n\nOld content.",
    facts_count=1,
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

  response = client.post("/api/wiki/maintenance/rebuild")

  assert response.status_code == 200
  body = response.json()
  assert body["action"] == "rebuild"
  assert "rebuilt" in body


def test_wiki_maintenance_history_returns_unavailable_before_first_run(client):
  response = client.get("/api/wiki/maintenance/history")

  assert response.status_code == 200
  body = response.json()
  assert body["available"] is False

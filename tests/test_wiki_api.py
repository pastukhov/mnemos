"""Tests for wiki API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import yaml

from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


class FakeWikiLLMClient:
  def __init__(self) -> None:
    self.calls: list[dict[str, object]] = []

  def synthesize_page(self, page_def, facts, reflections, existing_content=None):
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
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="values",
    title="Values",
    content_md="# Values",
    facts_count=2,
    reflections_count=0,
    invalidated_at=datetime.now(UTC),
  )

  response = client.get("/api/wiki/pages")
  body = response.json()

  assert response.status_code == 200
  assert [item["name"] for item in body["items"]] == ["career", "values"]
  assert body["items"][0]["is_stale"] is False
  assert body["items"][1]["is_stale"] is True


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

from __future__ import annotations

import yaml

from pipelines.wiki.wiki_canonicalization_runner import WikiCanonicalizationRunner
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
  schema_path = "/tmp/test_wiki_canonicalization_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.wiki_runner.schema = None


def test_wiki_canonicalization_runner_materializes_summary_and_rebuilds_target_page(client):
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
      "The user builds durable systems and reusable automation.\n\n"
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

  report = WikiCanonicalizationRunner(
    client.app.state.memory_service,
    client.app.state.settings,
    wiki_runner=client.app.state.wiki_runner,
  ).run(candidates=["qa-self-what-kind-of-systems-does-the-user-build -> career"])

  assert report.canonicalized_pages == ["qa-self-what-kind-of-systems-does-the-user-build"]
  assert report.canonical_targets == ["career"]
  assert client.app.state.memory_service.get_wiki_page("qa-self-what-kind-of-systems-does-the-user-build") is None

  materialized = client.app.state.memory_service.get_item_by_source_ref(
    source_type="wiki_canonicalization",
    source_id="career:qa-self-what-kind-of-systems-does-the-user-build",
  )
  assert materialized is not None
  assert materialized.kind == "summary"
  assert materialized.metadata_json["canonical_page"] == "career"

  rebuilt = client.app.state.memory_service.get_wiki_page("career")
  assert rebuilt is not None
  assert "Canonicalized wiki Q&A for 'career'." in rebuilt.content_md

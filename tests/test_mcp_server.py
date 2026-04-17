import httpx
import pytest
import yaml

from core.config import Settings
from mcp_server.client import MnemosRestClient
from mcp_server.server import build_mcp_server
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


def build_rest_client(handler) -> MnemosRestClient:
  transport = httpx.MockTransport(handler)
  client = httpx.Client(base_url="http://mnemos.test", transport=transport)
  return MnemosRestClient(
    base_url="http://mnemos.test",
    timeout_seconds=5.0,
    client=client,
  )


class FakeWikiLLMClient:
  def synthesize_page(self, page_def, facts, reflections, existing_content=None, related_pages=None):
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


def _install_wiki_setup(client, *, schema: WikiSchema) -> None:
  schema_path = "/tmp/test_mcp_wiki_schema.yaml"
  with open(schema_path, "w", encoding="utf-8") as file:
    yaml.safe_dump(schema.model_dump(mode="python"), file, allow_unicode=True)
  client.app.state.settings.wiki_schema_path = schema_path
  client.app.state.settings.wiki_min_facts_per_page = 1
  client.app.state.wiki_runner.schema = schema
  client.app.state.wiki_runner.llm_client = FakeWikiLLMClient()


@pytest.mark.asyncio
async def test_mcp_search_memory_returns_items():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/query"
    return httpx.Response(
      200,
      json={
        "query": "automated systems",
        "domain": "self",
        "items": [
          {
            "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
            "domain": "self",
            "kind": "note",
            "statement": "User prefers building automated systems.",
            "confidence": 0.95,
            "status": "accepted",
            "metadata": {"source": "seed"},
            "created_at": "2026-03-10T10:00:00Z",
            "updated_at": "2026-03-10T10:00:00Z",
          }
        ],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "search_memory",
    {"query": "automated systems", "domain": "self", "top_k": 5},
  )

  assert result.structured_content["query"] == "automated systems"
  assert result.structured_content["domains"] == ["self"]
  assert result.structured_content["items"][0]["kind"] == "note"


@pytest.mark.asyncio
async def test_mcp_get_memory_item_handles_missing_item():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    return httpx.Response(404, json={"detail": "memory item not found"})

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "get_memory_item",
    {"item_id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4"},
  )

  assert result.structured_content == {
    "found": False,
    "item_id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
  }


@pytest.mark.asyncio
async def test_mcp_get_schema_info_returns_constraints():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/memory/schema"
    return httpx.Response(
      200,
      json={
        "schema": {
          "domains": ["self", "project", "operational", "interaction"],
          "kinds": ["raw", "fact", "reflection", "summary", "note", "decision", "task", "tension"],
          "memory_candidate": {
            "note_statement": {"min_length": 1, "max_length": 10000},
          },
        }
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("get_schema_info", {})

  assert "interaction" in result.structured_content["schema"]["domains"]
  assert result.structured_content["schema"]["memory_candidate"]["note_statement"]["max_length"] == 10000


@pytest.mark.asyncio
async def test_mcp_add_memory_note_posts_expected_payload():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidate"
    payload = request.read().decode("utf-8")
    assert '"domain":"interaction"' in payload
    assert '"kind":"note"' in payload
    assert '"statement":"Remember the user likes observability."' in payload
    return httpx.Response(
      201,
      json={
        "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
        "domain": "interaction",
        "kind": "note",
        "statement": "Remember the user likes observability.",
        "confidence": None,
        "agent_id": "mcp_server",
        "evidence": None,
        "status": "pending",
        "metadata": {"source_type": "mcp", "source_id": "add_memory_note"},
        "created_at": "2026-03-10T10:00:00Z",
        "reviewed_at": None,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "add_memory_note",
    {"text": "Remember the user likes observability."},
  )

  assert result.structured_content["domain"] == "interaction"
  assert result.structured_content["kind"] == "note"
  assert result.structured_content["status"] == "pending"


@pytest.mark.asyncio
async def test_mcp_propose_memory_item_posts_candidate_payload():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidate"
    payload = request.read().decode("utf-8")
    assert '"domain":"self"' in payload
    assert '"kind":"fact"' in payload
    assert '"statement":"User prefers observable architectures."' in payload
    return httpx.Response(
      201,
      json={
        "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
        "domain": "self",
        "kind": "fact",
        "statement": "User prefers observable architectures.",
        "confidence": 0.8,
        "agent_id": "mcp_server",
        "evidence": None,
        "status": "pending",
        "metadata": {"source_type": "mcp", "source_id": "propose_memory_item"},
        "created_at": "2026-03-10T10:00:00Z",
        "reviewed_at": None,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "propose_memory_item",
    {
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers observable architectures.",
      "confidence": 0.8,
    },
  )

  assert result.structured_content["kind"] == "fact"
  assert result.structured_content["status"] == "pending"


@pytest.mark.asyncio
async def test_mcp_validate_memory_item_uses_preview_endpoint():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidate/validate"
    return httpx.Response(
      200,
      json={
        "valid": False,
        "candidate": None,
        "errors": [{"loc": ["__root__"], "message": "statement must be at least 10 characters for kind=fact"}],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "validate_memory_item",
    {
      "domain": "self",
      "kind": "fact",
      "statement": "short",
      "confidence": 0.8,
    },
  )

  assert result.structured_content["valid"] is False
  assert result.structured_content["errors"][0]["loc"] == ["__root__"]


@pytest.mark.asyncio
async def test_mcp_propose_memory_items_posts_bulk_payload():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidates/bulk"
    payload = request.read().decode("utf-8")
    assert '"statement":"User prefers observable architectures."' in payload
    assert '"statement":"Remember deployment constraints."' in payload
    return httpx.Response(
      201,
      json={
        "created": 2,
        "items": [
          {
            "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
            "domain": "self",
            "kind": "fact",
            "statement": "User prefers observable architectures.",
            "confidence": 0.8,
            "agent_id": "mcp_server",
            "evidence": None,
            "status": "pending",
            "metadata": None,
            "created_at": "2026-03-10T10:00:00Z",
            "reviewed_at": None,
          },
          {
            "id": "70d8765e-fd5f-4ed9-ab06-d9de9f3e05c4",
            "domain": "interaction",
            "kind": "note",
            "statement": "Remember deployment constraints.",
            "confidence": None,
            "agent_id": "mcp_server",
            "evidence": None,
            "status": "pending",
            "metadata": None,
            "created_at": "2026-03-10T10:00:00Z",
            "reviewed_at": None,
          },
        ],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "propose_memory_items",
    {
      "items": [
        {
          "domain": "self",
          "kind": "fact",
          "statement": "User prefers observable architectures.",
          "confidence": 0.8,
        },
        {
          "domain": "interaction",
          "kind": "note",
          "statement": "Remember deployment constraints.",
        },
      ]
    },
  )

  assert result.structured_content["created"] == 2
  assert len(result.structured_content["items"]) == 2


@pytest.mark.asyncio
async def test_mcp_shortlist_memory_items_posts_shortlist_payload():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidates/shortlist"
    return httpx.Response(
      200,
      json={
        "review_session": {"id": "review-123", "label": "Interview 2026-03-13", "kind": "review"},
        "ready_count": 1,
        "invalid_count": 0,
        "items": [
          {
            "index": 1,
            "valid": True,
            "candidate": {
              "domain": "self",
              "kind": "fact",
              "statement": "User prefers observable architectures.",
              "confidence": 0.8,
              "write_mode": "create",
            },
            "errors": [],
            "preview": {
              "normalized_statement": "userprefersobservablearchitectures",
              "write_mode": "create",
              "will_create_status": "accepted",
              "preview_metadata": {},
              "review_session": {"id": "review-123", "label": "Interview 2026-03-13", "kind": "review"},
              "dedupe_hints": [],
              "suggested_action": None,
              "suggested_replacement_item_id": None,
            },
            "dedupe_hints": [],
          }
        ],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "shortlist_memory_items",
    {
      "items": [
        {
          "domain": "self",
          "kind": "fact",
          "statement": "User prefers observable architectures.",
          "confidence": 0.8,
        }
      ],
      "review_session_label": "Interview 2026-03-13",
    },
  )

  assert result.structured_content["review_session"]["id"] == "review-123"
  assert result.structured_content["ready_count"] == 1


@pytest.mark.asyncio
async def test_mcp_list_review_sessions_reads_grouped_sessions():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/memory/review-sessions"
    return httpx.Response(
      200,
      json={
        "items": [
          {
            "review_session": {
              "id": "interview-123",
              "label": "Interview 2026-03-13",
              "kind": "interview",
              "created_by": "mcp_server",
            },
            "candidate_count": 4,
            "pending_count": 3,
            "accepted_count": 1,
            "rejected_count": 0,
            "superseded_count": 0,
            "latest_created_at": "2026-03-13T08:00:00Z",
          }
        ]
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("list_review_sessions", {})

  assert result.structured_content["items"][0]["review_session"]["kind"] == "interview"
  assert result.structured_content["items"][0]["pending_count"] == 3


@pytest.mark.asyncio
async def test_mcp_add_memory_note_accepts_long_text():
  long_text = "Remember this long interview note. " * 400

  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/candidate"
    payload = request.read().decode("utf-8")
    assert long_text.strip() in payload
    return httpx.Response(
      201,
      json={
        "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
        "domain": "interaction",
        "kind": "note",
        "statement": long_text.strip(),
        "confidence": None,
        "agent_id": "mcp_server",
        "evidence": None,
        "status": "pending",
        "metadata": {"source_type": "mcp", "source_id": "add_memory_note"},
        "created_at": "2026-03-10T10:00:00Z",
        "reviewed_at": None,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "add_memory_note",
    {"text": long_text},
  )

  assert result.structured_content["statement"] == long_text.strip()


@pytest.mark.asyncio
async def test_mcp_get_context_returns_plain_text():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    return httpx.Response(
      200,
      json={
        "query": "observability",
        "domain": "operational",
        "items": [
          {
            "id": "48b76e6b-fd5f-4ed9-ab06-d9de9f3e05c4",
            "domain": "operational",
            "kind": "note",
            "statement": "User designs observable systems.",
            "confidence": 0.9,
            "status": "accepted",
            "metadata": {"source": "seed"},
            "created_at": "2026-03-10T10:00:00Z",
            "updated_at": "2026-03-10T10:00:00Z",
          }
        ],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "get_context",
    {"query": "observability", "domain": "operational", "top_k": 3},
  )

  context = result.structured_content["result"]
  assert "Mnemos context for query: observability" in context
  assert "[operational]" in context
  assert "User designs observable systems." in context


@pytest.mark.asyncio
async def test_mcp_list_wiki_pages_returns_cache_summaries():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages"
    return httpx.Response(
      200,
      json={
        "items": [
          {
            "name": "career",
            "title": "Career",
            "facts_count": 4,
            "reflections_count": 1,
            "updated_at": "2026-03-10T10:00:00Z",
            "is_stale": False,
          },
          {
            "name": "values",
            "title": "Values",
            "facts_count": 2,
            "reflections_count": 0,
            "updated_at": "2026-03-10T11:00:00Z",
            "is_stale": True,
          },
        ]
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("list_wiki_pages", {})

  assert result.structured_content["items"][0]["name"] == "career"
  assert result.structured_content["items"][1]["is_stale"] is True


@pytest.mark.asyncio
async def test_mcp_read_wiki_page_returns_page_content():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages/career"
    return httpx.Response(
      200,
      json={
        "name": "career",
        "title": "Career",
        "facts_count": 4,
        "reflections_count": 1,
        "updated_at": "2026-03-10T10:00:00Z",
        "is_stale": False,
        "content": "# Career\n\nUser builds reliable automation systems.",
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("read_wiki_page", {"name": "career"})

  assert result.structured_content["found"] is True
  assert result.structured_content["page"]["name"] == "career"
  assert "automation systems" in result.structured_content["page"]["content"]


@pytest.mark.asyncio
async def test_mcp_read_wiki_page_handles_missing_page():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages/missing"
    return httpx.Response(404, json={"detail": "wiki page not found"})

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("read_wiki_page", {"name": "missing"})

  assert result.structured_content == {
    "found": False,
    "name": "missing",
  }


@pytest.mark.asyncio
async def test_mcp_read_navigation_wiki_page():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages/index"
    return httpx.Response(
      200,
      json={
        "name": "index",
        "title": "Wiki Index",
        "facts_count": 3,
        "reflections_count": 0,
        "updated_at": "2026-03-10T10:00:00Z",
        "is_stale": False,
        "content": "# Wiki Index\n\n- `career` — updated 2026-03-10 10:00 UTC",
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("read_wiki_page", {"name": "index"})

  assert result.structured_content["found"] is True
  assert result.structured_content["page"]["name"] == "index"
  assert "Wiki Index" in result.structured_content["page"]["content"]


@pytest.mark.asyncio
async def test_mcp_read_log_navigation_page():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages/log"
    return httpx.Response(
      200,
      json={
        "name": "log",
        "title": "Activity Log",
        "facts_count": 2,
        "reflections_count": 0,
        "updated_at": "2026-03-10T10:05:00Z",
        "is_stale": False,
        "content": "# Activity Log\n\n- 2026-03-10 10:05 UTC `self` / `raw`: Fresh raw note",
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("read_wiki_page", {"name": "log"})

  assert result.structured_content["found"] is True
  assert result.structured_content["page"]["name"] == "log"
  assert "Fresh raw note" in result.structured_content["page"]["content"]


@pytest.mark.asyncio
async def test_mcp_read_log_navigation_page_surfaces_refreshed_content():
  calls = {"count": 0}

  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/api/wiki/pages/log"
    calls["count"] += 1
    if calls["count"] == 1:
      content = "# Activity Log\n\n- 2026-03-10 10:00 UTC `self` / `fact`: Initial fact"
    else:
      content = "# Activity Log\n\n- 2026-03-10 10:05 UTC `self` / `summary`: Fresh summary"
    return httpx.Response(
      200,
      json={
        "name": "log",
        "title": "Activity Log",
        "facts_count": 1,
        "reflections_count": 0,
        "updated_at": "2026-03-10T10:05:00Z",
        "is_stale": False,
        "content": content,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  first = await server.call_tool("read_wiki_page", {"name": "log"})
  second = await server.call_tool("read_wiki_page", {"name": "log"})

  assert "Initial fact" in first.structured_content["page"]["content"]
  assert "Fresh summary" in second.structured_content["page"]["content"]


@pytest.mark.asyncio
async def test_mcp_read_log_navigation_page_rebuilds_after_write(client):
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
  _install_wiki_setup(client, schema=schema)
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "Initial fact",
      "confidence": 0.8,
      "metadata": {"source_type": "manual", "source_id": "fact_1"},
    },
  )

  rest_client = MnemosRestClient(
    base_url="http://testserver",
    timeout_seconds=5.0,
    client=client,
  )
  server = build_mcp_server(
    settings=client.app.state.settings,
    client=rest_client,
  )

  first = await server.call_tool("read_wiki_page", {"name": "log"})
  assert "Initial fact" in first.structured_content["page"]["content"]

  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "summary",
      "statement": "Fresh summary after write",
      "confidence": 0.8,
      "metadata": {"source_type": "manual", "source_id": "summary_1"},
    },
  )

  second = await server.call_tool("read_wiki_page", {"name": "log"})
  assert "Fresh summary after write" in second.structured_content["page"]["content"]


@pytest.mark.asyncio
async def test_mcp_lint_wiki_returns_report():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/api/wiki/lint"
    assert request.url.params.get("domain") == "self"
    assert request.url.params.get("fix") == "true"
    return httpx.Response(
      200,
      json={
        "stale_pages": ["career"],
        "empty_pages": [],
        "orphan_facts_count": 1,
        "contradictions": [],
        "fixed_pages": ["career"],
        "missing_related_pages": [],
        "missing_provenance_pages": ["career"],
        "missing_source_refs_pages": ["career"],
        "missing_source_highlights_pages": ["career"],
        "low_source_coverage_pages": ["career (1/3)"],
        "unresolved_source_refs": [],
        "broken_wiki_links": [],
        "canonical_drift_pages": ["career"],
        "orphaned_query_pages": [],
        "stale_navigation_pages": ["index"],
        "overmerged_query_pages": ["qa-self-systems (4/3)"],
        "canonicalization_candidates": ["qa-self-systems -> career"],
        "missing_page_candidates": ["self/learning -> create canonical page (1 facts)"],
        "findings": [
          {"code": "stale_pages", "severity": "warn", "count": 1, "items": ["career"]},
          {"code": "canonical_drift_pages", "severity": "action", "count": 1, "items": ["career"]},
          {
            "code": "canonicalization_candidates",
            "severity": "action",
            "count": 1,
            "items": ["qa-self-systems -> career"],
          },
        ],
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool("lint_wiki", {"domain": "self", "fix": True})

  assert result.structured_content["stale_pages"] == ["career"]
  assert result.structured_content["orphan_facts_count"] == 1
  assert result.structured_content["fixed_pages"] == ["career"]
  assert result.structured_content["missing_provenance_pages"] == ["career"]
  assert result.structured_content["missing_source_refs_pages"] == ["career"]
  assert result.structured_content["missing_source_highlights_pages"] == ["career"]
  assert result.structured_content["low_source_coverage_pages"] == ["career (1/3)"]
  assert result.structured_content["unresolved_source_refs"] == []
  assert result.structured_content["canonical_drift_pages"] == ["career"]
  assert result.structured_content["orphaned_query_pages"] == []
  assert result.structured_content["stale_navigation_pages"] == ["index"]
  assert result.structured_content["overmerged_query_pages"] == ["qa-self-systems (4/3)"]
  assert result.structured_content["canonicalization_candidates"] == ["qa-self-systems -> career"]
  assert result.structured_content["missing_page_candidates"] == ["self/learning -> create canonical page (1 facts)"]
  assert result.structured_content["findings"] == [
    {"code": "stale_pages", "severity": "warn", "count": 1, "items": ["career"]},
    {"code": "canonical_drift_pages", "severity": "action", "count": 1, "items": ["career"]},
    {
      "code": "canonicalization_candidates",
      "severity": "action",
      "count": 1,
      "items": ["qa-self-systems -> career"],
    },
  ]


@pytest.mark.asyncio
async def test_mcp_query_wiki_returns_answer_and_sources():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/api/wiki/query"
    payload = request.read().decode("utf-8")
    assert '"question":"What kind of systems does the user build?"' in payload
    return httpx.Response(
      200,
      json={
        "answer": "Question: What kind of systems does the user build?\n\nRelevant wiki context:\n[career] # Career User builds durable systems.",
        "sources": ["career", "index"],
        "confidence": 0.65,
        "promoted_canonical_target": None,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "query_wiki",
    {"question": "What kind of systems does the user build?", "domain": "self", "top_k": 3},
  )

  assert "Question: What kind of systems does the user build?" in result.structured_content["answer"]
  assert result.structured_content["sources"] == ["career", "index"]
  assert result.structured_content["confidence"] == 0.65


@pytest.mark.asyncio
async def test_mcp_query_wiki_can_request_persisted_answer_page():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/api/wiki/query"
    payload = request.read().decode("utf-8")
    assert '"persist_page_name":"qa-systems"' in payload
    assert '"persist_title":"Q&A: Systems"' in payload
    return httpx.Response(
      200,
      json={
        "answer": "Question: What kind of systems does the user build?",
        "sources": ["career", "index"],
        "confidence": 0.65,
        "persisted_page_name": "qa-systems",
        "promoted_canonical_target": None,
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "query_wiki",
    {
      "question": "What kind of systems does the user build?",
      "domain": "self",
      "top_k": 3,
      "persist_page_name": "qa-systems",
      "persist_title": "Q&A: Systems",
    },
  )

  assert result.structured_content["sources"] == ["career", "index"]
  assert result.structured_content["persisted_page_name"] == "qa-systems"


@pytest.mark.asyncio
async def test_mcp_query_wiki_can_request_auto_persist():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/api/wiki/query"
    payload = request.read().decode("utf-8")
    assert '"auto_persist":true' in payload
    return httpx.Response(
      200,
      json={
        "answer": "Question: What kind of systems does the user build?",
        "sources": ["career", "index", "log"],
        "confidence": 0.95,
        "persisted_page_name": None,
        "promoted_canonical_target": "career",
      },
    )

  server = build_mcp_server(
    settings=Settings(),
    client=build_rest_client(handler),
  )
  result = await server.call_tool(
    "query_wiki",
    {
      "question": "What kind of systems does the user build?",
      "domain": "self",
      "top_k": 3,
      "auto_persist": True,
    },
  )

  assert result.structured_content["persisted_page_name"] is None
  assert result.structured_content["promoted_canonical_target"] == "career"

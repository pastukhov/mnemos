import httpx
import pytest

from core.config import Settings
from mcp_server.client import MnemosRestClient
from mcp_server.server import build_mcp_server


def build_rest_client(handler) -> MnemosRestClient:
  transport = httpx.MockTransport(handler)
  client = httpx.Client(base_url="http://mnemos.test", transport=transport)
  return MnemosRestClient(
    base_url="http://mnemos.test",
    timeout_seconds=5.0,
    client=client,
  )


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

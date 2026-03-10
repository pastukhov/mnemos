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
async def test_mcp_add_memory_note_posts_expected_payload():
  def handler(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/memory/items"
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
        "status": "accepted",
        "metadata": {"source_type": "mcp", "source_id": "add_memory_note"},
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-10T10:00:00Z",
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

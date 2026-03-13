from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="propose_memory_items",
    description="Propose multiple memory item candidates for later review and acceptance.",
  )
  def propose_memory_items(
    items: list[dict[str, object]],
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> dict[str, object]:
    created = client.propose_memory_items(
      items=items,
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    logger.info(
      "mcp tool propose_memory_items completed",
      extra={"event": "mcp_tool_propose_memory_items", "count": created.created},
    )
    return created.model_dump(mode="json", by_alias=True)

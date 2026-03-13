from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="shortlist_memory_items",
    description="Validate multiple memory item candidates without writing them, grouped into a review session.",
  )
  def shortlist_memory_items(
    items: list[dict[str, object]],
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> dict[str, object]:
    shortlist = client.shortlist_memory_items(
      items=items,
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    logger.info(
      "mcp tool shortlist_memory_items completed",
      extra={
        "event": "mcp_tool_shortlist_memory_items",
        "ready_count": shortlist.ready_count,
        "invalid_count": shortlist.invalid_count,
      },
    )
    return shortlist.model_dump(mode="json", by_alias=True)

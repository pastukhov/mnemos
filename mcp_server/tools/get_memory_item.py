from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="get_memory_item",
    description="Fetch a single Mnemos memory item by id.",
  )
  def get_memory_item(item_id: str) -> dict[str, object]:
    item = client.get_memory_item(item_id)
    found = item is not None
    logger.info(
      "mcp tool get_memory_item completed",
      extra={
        "event": "mcp_tool_get_memory_item",
        "item_id": item_id,
        "found": found,
      },
    )
    if item is None:
      return {"found": False, "item_id": item_id}
    return {"found": True, "item": item.model_dump(mode="json", by_alias=True)}

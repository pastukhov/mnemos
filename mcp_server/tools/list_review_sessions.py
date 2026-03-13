from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="list_review_sessions",
    description="List grouped Mnemos review sessions and their candidate counts.",
  )
  def list_review_sessions() -> dict[str, object]:
    response = client.list_review_sessions()
    logger.info(
      "mcp tool list_review_sessions completed",
      extra={"event": "mcp_tool_list_review_sessions", "count": len(response.items)},
    )
    return response.model_dump(mode="json")

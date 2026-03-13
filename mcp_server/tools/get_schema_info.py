from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="get_schema_info",
    description="Return Mnemos schema constraints, allowed values, and important field limits.",
  )
  def get_schema_info() -> dict[str, object]:
    schema = client.get_schema_info()
    logger.info(
      "mcp tool get_schema_info completed",
      extra={"event": "mcp_tool_get_schema_info"},
    )
    return schema.model_dump(mode="json", by_alias=True)

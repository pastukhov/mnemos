from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="list_wiki_pages",
    description="List cached Mnemos wiki pages with freshness and source counts.",
  )
  def list_wiki_pages() -> dict[str, object]:
    result = client.list_wiki_pages()
    items = [item.model_dump(mode="json", by_alias=True) for item in result.items]
    logger.info(
      "mcp tool list_wiki_pages completed",
      extra={
        "event": "mcp_tool_list_wiki_pages",
        "items_returned": len(items),
      },
    )
    return {"items": items}

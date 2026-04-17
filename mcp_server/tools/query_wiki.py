from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="query_wiki",
    description="Ask a question against the maintained wiki and return answer plus source pages.",
  )
  def query_wiki(
    question: str,
    domain: str = "self",
    top_k: int = 5,
    auto_persist: bool | None = None,
    persist_page_name: str | None = None,
    persist_title: str | None = None,
  ) -> dict[str, object]:
    result = client.query_wiki(
      question=question,
      domain=domain,
      top_k=top_k,
      auto_persist=auto_persist,
      persist_page_name=persist_page_name,
      persist_title=persist_title,
    )
    payload = result.model_dump(mode="json")
    logger.info(
      "mcp tool query_wiki completed",
      extra={
        "event": "mcp_tool_query_wiki",
        "domain": domain,
        "sources": len(result.sources),
      },
    )
    return payload

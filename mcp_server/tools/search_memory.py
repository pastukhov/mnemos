from fastmcp import FastMCP

from core.config import ALLOWED_DOMAINS
from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="search_memory",
    description="Search Mnemos memory items by semantic query.",
  )
  def search_memory(query: str, domain: str | None = None, top_k: int = 5) -> dict[str, object]:
    query_text = query.strip()
    if not query_text:
      raise ValueError("query must not be empty")
    if top_k < 1 or top_k > 50:
      raise ValueError("top_k must be between 1 and 50")
    if domain is not None and domain not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {domain}")

    domains = [domain] if domain else list(ALLOWED_DOMAINS)
    items: list[dict[str, object]] = []
    for current_domain in domains:
      result = client.query_memory(query=query_text, domain=current_domain, top_k=top_k)
      items.extend(item.model_dump(mode="json", by_alias=True) for item in result.items)

    logger.info(
      "mcp tool search_memory completed",
      extra={
        "event": "mcp_tool_search_memory",
        "domain": domain or "all",
        "top_k": top_k,
        "items_returned": len(items),
      },
    )
    return {
      "query": query_text,
      "domains": domains,
      "top_k": top_k,
      "mode": "single-domain" if domain else "per-domain",
      "items": items,
    }

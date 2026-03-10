from fastmcp import FastMCP

from core.config import ALLOWED_DOMAINS
from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="get_context",
    description="Build a plain-text context block from Mnemos search results.",
  )
  def get_context(query: str, domain: str | None = None, top_k: int = 3) -> str:
    query_text = query.strip()
    if not query_text:
      raise ValueError("query must not be empty")
    if top_k < 1 or top_k > 20:
      raise ValueError("top_k must be between 1 and 20")
    if domain is not None and domain not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {domain}")

    domains = [domain] if domain else list(ALLOWED_DOMAINS)
    lines = [f"Mnemos context for query: {query_text}", ""]
    found_any = False

    for current_domain in domains:
      result = client.query_memory(query=query_text, domain=current_domain, top_k=top_k)
      if not result.items:
        continue
      found_any = True
      lines.append(f"[{current_domain}]")
      for item in result.items:
        lines.append(f"- ({item.kind}) {item.statement}")
      lines.append("")

    if not found_any:
      return f"No relevant Mnemos context found for query: {query_text}"

    context = "\n".join(lines).strip()
    logger.info(
      "mcp tool get_context completed",
      extra={
        "event": "mcp_tool_get_context",
        "domain": domain or "all",
        "top_k": top_k,
      },
    )
    return context

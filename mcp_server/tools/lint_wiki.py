from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="lint_wiki",
    description="Run wiki health checks and optionally fix stale pages.",
  )
  def lint_wiki(domain: str | None = None, fix: bool = False) -> dict[str, object]:
    result = client.lint_wiki(domain=domain, fix=fix)
    payload = result.model_dump(mode="json")
    logger.info(
      "mcp tool lint_wiki completed",
      extra={
        "event": "mcp_tool_lint_wiki",
        "stale_pages": len(result.stale_pages),
        "fixed_pages": len(result.fixed_pages),
      },
    )
    return payload

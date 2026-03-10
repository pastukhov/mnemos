from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="propose_memory_item",
    description="Propose a memory item candidate for later review and acceptance.",
  )
  def propose_memory_item(
    domain: str,
    kind: str,
    statement: str,
    confidence: float | None = None,
  ) -> dict[str, object]:
    candidate = client.propose_memory_item(
      domain=domain,
      kind=kind,
      statement=statement.strip(),
      confidence=confidence,
      metadata={"source_type": "mcp", "source_id": "propose_memory_item"},
    )
    logger.info(
      "mcp tool propose_memory_item completed",
      extra={"event": "mcp_tool_propose_memory_item", "candidate_id": str(candidate.id)},
    )
    return candidate.model_dump(mode="json", by_alias=True)

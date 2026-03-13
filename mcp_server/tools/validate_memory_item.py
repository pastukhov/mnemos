from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="validate_memory_item",
    description="Validate a memory item candidate payload without writing it to Mnemos.",
  )
  def validate_memory_item(
    domain: str,
    kind: str,
    statement: str,
    confidence: float | str | None = None,
    write_mode: str = "create",
    source_note_id: str | None = None,
    evidence_ref: str | None = None,
    source_excerpt: str | None = None,
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> dict[str, object]:
    result = client.validate_memory_item(
      domain=domain,
      kind=kind,
      statement=statement.strip(),
      confidence=confidence,
      metadata={"source_type": "mcp", "source_id": "validate_memory_item"},
      write_mode=write_mode,
      source_note_id=source_note_id,
      evidence_ref=evidence_ref,
      source_excerpt=source_excerpt,
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    logger.info(
      "mcp tool validate_memory_item completed",
      extra={"event": "mcp_tool_validate_memory_item", "valid": result.valid},
    )
    return result.model_dump(mode="json", by_alias=True)

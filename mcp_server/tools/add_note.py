from fastmcp import FastMCP

from core.logging import get_logger
from mcp_server.client import MnemosRestClient

logger = get_logger(__name__)


def register(mcp: FastMCP, client: MnemosRestClient) -> None:
  @mcp.tool(
    name="add_memory_note",
    description="Propose a simple interaction note candidate in Mnemos.",
  )
  def add_memory_note(text: str) -> dict[str, object]:
    note_text = text.strip()
    if not note_text:
      raise ValueError("text must not be empty")
    item = client.add_memory_note(text=note_text)
    logger.info(
      "mcp tool add_memory_note completed",
      extra={"event": "mcp_tool_add_memory_note", "candidate_id": str(item.id)},
    )
    return item.model_dump(mode="json", by_alias=True)

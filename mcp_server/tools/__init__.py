from fastmcp import FastMCP

from mcp_server.client import MnemosRestClient
from mcp_server.tools.add_note import register as register_add_note
from mcp_server.tools.get_context import register as register_get_context
from mcp_server.tools.get_memory_item import register as register_get_memory_item
from mcp_server.tools.propose_memory_item import register as register_propose_memory_item
from mcp_server.tools.search_memory import register as register_search_memory


def register_tools(mcp: FastMCP, client: MnemosRestClient) -> None:
  register_search_memory(mcp, client)
  register_get_memory_item(mcp, client)
  register_add_note(mcp, client)
  register_propose_memory_item(mcp, client)
  register_get_context(mcp, client)

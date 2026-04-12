from fastmcp import FastMCP

from mcp_server.client import MnemosRestClient
from mcp_server.tools.add_note import register as register_add_note
from mcp_server.tools.get_context import register as register_get_context
from mcp_server.tools.get_memory_item import register as register_get_memory_item
from mcp_server.tools.get_schema_info import register as register_get_schema_info
from mcp_server.tools.list_review_sessions import register as register_list_review_sessions
from mcp_server.tools.list_wiki_pages import register as register_list_wiki_pages
from mcp_server.tools.propose_memory_item import register as register_propose_memory_item
from mcp_server.tools.propose_memory_items import register as register_propose_memory_items
from mcp_server.tools.read_wiki_page import register as register_read_wiki_page
from mcp_server.tools.search_memory import register as register_search_memory
from mcp_server.tools.shortlist_memory_items import register as register_shortlist_memory_items
from mcp_server.tools.validate_memory_item import register as register_validate_memory_item


def register_tools(mcp: FastMCP, client: MnemosRestClient) -> None:
  register_search_memory(mcp, client)
  register_get_memory_item(mcp, client)
  register_get_schema_info(mcp, client)
  register_list_review_sessions(mcp, client)
  register_add_note(mcp, client)
  register_propose_memory_item(mcp, client)
  register_propose_memory_items(mcp, client)
  register_shortlist_memory_items(mcp, client)
  register_validate_memory_item(mcp, client)
  register_get_context(mcp, client)
  register_list_wiki_pages(mcp, client)
  register_read_wiki_page(mcp, client)

# Mnemos - Phase 3: MCP Server Integration

## Objective

Expose Mnemos functionality to AI agents through the Model Context
Protocol (MCP).

Phase 3 introduces an MCP server that allows LLM agents to interact with
Mnemos as a set of tools.

The MCP server acts as an adapter between:

- Mnemos REST API
- LLM agents (Claude, Codex, etc.)

The MCP server must not replace the REST API.

REST remains the internal system interface.

## Architecture

Current architecture:

```text
Agent
  │
  ▼
Mnemos REST Gateway
  │
  ├── PostgreSQL
  └── Qdrant
```

After Phase 3:

```text
Agent
  │
  │ MCP
  ▼
Mnemos MCP Server
  │
  │ HTTP
  ▼
Mnemos Gateway (REST API)
  │
  ├── PostgreSQL
  └── Qdrant
```

The MCP server must be lightweight and stateless.

## Repository Changes

Add module:

```text
mnemos/mcp_server/
```

Structure:

```text
mnemos/
  mcp_server/
    __init__.py
    server.py
    tools/
      __init__.py
      search_memory.py
      get_memory_item.py
      add_note.py
      get_context.py
```

## Dependencies

Add MCP server dependency.

Preferred implementation:

FastMCP (Python MCP server library).

Example dependency:

```text
fastmcp
```

## MCP Server Initialization

File:

```text
mnemos/mcp_server/server.py
```

Responsibilities:

- initialize MCP server
- register tools
- start server

Example skeleton:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mnemos")

if __name__ == "__main__":
    mcp.run()
```

## Tool: `search_memory`

Primary tool used by agents.

Purpose:
semantic retrieval from Mnemos.

Parameters:

- `query`: string
- `domain`: string (optional)
- `top_k`: integer (optional)

Example schema:

```json
{
  "name": "search_memory",
  "description": "Search Mnemos memory system",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "domain": {"type": "string"},
      "top_k": {"type": "integer"}
    },
    "required": ["query"]
  }
}
```

Implementation:

- call REST endpoint `/memory/query`
- return retrieved items

## Tool: `get_memory_item`

Purpose:
fetch single memory item.

Parameters:

```text
item_id
```

Calls:

```text
GET /memory/item/{id}
```

## Tool: `add_memory_note`

Purpose:
allow agents to add simple notes.

Parameters:

```text
text
```

Implementation:

Call:

```text
POST /memory/items
```

Payload:

```json
{
  "domain": "interaction",
  "kind": "note",
  "statement": "<text>"
}
```

## Tool: `get_context`

Purpose:
return formatted context block for LLM prompts.

Parameters:

```text
query
```

Implementation:

1. call `/memory/query`
1. format items into readable context

Example output:

```text
User knowledge:

- User prefers building automated systems.
- User works as DevOps/SRE.
- User designs observable systems.
```

Return plain text.

## Error Handling

MCP tools must gracefully handle:

- REST API failure
- empty search results
- invalid parameters

Return meaningful error messages.

Do not crash MCP server.

## Configuration

MCP server must read configuration:

```text
MNEMOS_URL
```

Example:

```text
http://mnemos:8080
```

Default for local dev:

```text
http://localhost:8080
```

## CLI Start Command

Add CLI entrypoint:

```text
mnemos mcp-server
```

Example implementation:

```bash
python -m mnemos.mcp_server.server
```

## Docker Integration

Add new service to `docker-compose`:

```text
mnemos-mcp
```

Example:

```yaml
mnemos-mcp:
  build: .
  command: python -m mnemos.mcp_server.server
  environment:
    MNEMOS_URL: http://mnemos:8080
  depends_on:
    - mnemos
```

## Example Agent Configuration

Example Claude MCP config:

```json
{
  "mcpServers": {
    "mnemos": {
      "command": "python",
      "args": ["-m", "mnemos.mcp_server.server"]
    }
  }
}
```

## Logging

MCP server must log:

- tool calls
- REST calls
- errors

Log format must match Mnemos logging style.

## Testing

Add tests:

```text
tests/test_mcp_search_memory.py
tests/test_mcp_add_note.py
```

Test cases:

- search memory tool
- get memory item
- add note
- get context

Mock REST responses.

## Acceptance Criteria

Phase 3 is complete when:

- MCP server starts successfully
- agents can call tools
- `search_memory` returns semantic results
- `add_memory_note` stores notes in Mnemos
- `get_context` returns formatted memory context
- MCP server runs in Docker
- tools handle errors gracefully
- tests pass

## Non-Goals

Phase 3 must NOT implement:

- fact extraction
- reflection generation
- candidate memory pipeline
- agent role policies

These belong to later phases.

## Final Task

Implement the Mnemos MCP server so that AI agents can query and write
memory using MCP tools.

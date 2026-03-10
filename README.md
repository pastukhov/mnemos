# Mnemos

Mnemos is a production-oriented memory gateway service. PostgreSQL is the source of truth for memory items, Qdrant stores vectors for retrieval, and FastAPI exposes write/query/health/metrics endpoints. Phase 2 adds deterministic ingestion of questionnaire and notes sources into `memory_items`.
Phase 3 adds an MCP server that exposes Mnemos to AI agents through MCP
while continuing to use the REST API as the backend boundary.

## Architecture

- `api/`: FastAPI app, routes, schemas, dependency wiring
- `core/`: typed settings, JSON logging, Prometheus metrics
- `db/`: SQLAlchemy models, sessions, repositories
- `vector/`: Qdrant wrapper and indexing helpers
- `embeddings/`: mock and OpenAI-compatible embedding providers
- `mcp_server/`: FastMCP server, REST client, and MCP tools
- `services/`: write/query orchestration
- `migrations/`: Alembic migration history
- `scripts/`: bootstrap, collection init, seed data
- `pipelines/ingest/`: questionnaire and notes ingestion pipelines
- `data/raw/`: local raw inputs for ingestion, intentionally gitignored
- `docker/`: Dockerfile and Compose stack

Flow summary:

1. `POST /memory/items` validates input.
2. The service inserts the row into PostgreSQL inside a transaction.
3. The statement is embedded and upserted into the per-domain Qdrant collection.
4. `POST /memory/query` embeds the query, searches Qdrant, then hydrates ranked results from PostgreSQL.
5. MCP tools call the REST gateway and return agent-friendly tool results.

## Local Startup

1. Create env file:

```bash
cp .env.example .env
```

2. Create local virtualenv and install dependencies:

```bash
make venv
```

3. Start the stack:

```bash
make up
```

The API will be available at `http://localhost:8000`.

The checked-in `.env.example` is host-friendly: local CLI, Alembic, and tests use `localhost`, while Docker Compose overrides the `mnemos` container to talk to `postgres` and `qdrant` over the internal network.

4. Run a live smoke check against the running stack:

```bash
make smoke
```

## Configuration

Required environment variables:

- `MNEMOS_ENV`
- `MNEMOS_HOST`
- `MNEMOS_PORT`
- `MNEMOS_LOG_LEVEL`
- `MNEMOS_URL`
- `MNEMOS_TIMEOUT_SECONDS`
- `MCP_SERVER_HOST`
- `MCP_SERVER_PORT`
- `MCP_SERVER_TRANSPORT`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `QDRANT_URL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `QDRANT_VECTOR_SIZE`

Default local development uses `EMBEDDING_PROVIDER=mock`. For an OpenAI-compatible endpoint, set:

```bash
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://your-endpoint.example/v1
EMBEDDING_API_KEY=secret
EMBEDDING_MODEL=text-embedding-3-small
```

## Migrations

Run migrations locally:

```bash
.venv/bin/python -m alembic upgrade head
```

Inside Docker, migrations run automatically from `scripts/bootstrap.sh` on container startup.

## Ingestion

Phase 2 ingestion commands:

```bash
mnemos ingest questionnaire data/raw/questionnaire.md
mnemos ingest questionnaire data/raw/questionnaire.yaml
mnemos ingest notes data/raw/notes.jsonl
mnemos ingest all
```

Convenience Make targets:

```bash
make ingest-all
make ingest-questionnaire
make ingest-notes
```

Expected local dataset layout:

- `data/raw/questionnaire.md`: user-provided questionnaire source, intentionally not committed
- `data/raw/questionnaire.yaml`: optional user-provided YAML questionnaire source, intentionally not committed
- `data/raw/notes.jsonl`: optional local notes source, intentionally not committed

Ingestion is idempotent. Duplicate detection uses `metadata.source_type + metadata.source_id`, backed by PostgreSQL expression indexes and a unique index guard.

## Seed Example

Initialize collections and insert demo records from the Phase 1 seed script:

```bash
.venv/bin/python scripts/create_qdrant_collections.py
.venv/bin/python scripts/seed_memory.py
```

The seed script inserts 6 memory items across `self` and `project`.

## Query Examples

Create an item:

```bash
curl -X POST http://localhost:8000/memory/items \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "self",
    "kind": "note",
    "statement": "User prefers building automated systems.",
    "confidence": 0.95,
    "metadata": {"source": "manual_seed"}
  }'
```

Fetch a single item:

```bash
curl http://localhost:8000/memory/item/<uuid>
```

Run semantic retrieval:

```bash
curl -X POST http://localhost:8000/memory/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "automated systems",
    "domain": "self",
    "top_k": 5,
    "kinds": ["note", "fact", "reflection"]
  }'
```

Health and metrics:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
```

## MCP Server

Phase 3 adds a dedicated MCP server backed by the existing REST API.
For local agent integrations, use `stdio`; it avoids fixed-port conflicts
and allows many agent processes to run in parallel on the same machine.

Local stdio mode for agent integrations:

```bash
mnemos mcp-server
```

HTTP mode for local testing:

```bash
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
```

Optional Docker HTTP service:

```bash
docker compose -f docker/docker-compose.yml --env-file .env --profile mcp-http up -d mnemos-mcp
```

That service exposes `http://localhost:9000/mcp` only when the
`mcp-http` profile is enabled explicitly.

Example Claude Desktop style configuration:

```json
{
  "mcpServers": {
    "mnemos": {
      "command": "mnemos",
      "args": ["mcp-server"]
    }
  }
}
```

Exposed tools:

- `search_memory`
- `get_memory_item`
- `add_memory_note`
- `get_context`

When `domain` is omitted in `search_memory` and `get_context`, the MCP
server queries all Mnemos domains and aggregates results per domain.

## Testing

Run tests with:

```bash
.venv/bin/pytest -q
```

Live stack smoke verification:

```bash
make smoke
```

## Governance

This repository follows trunk-based development with a single long-lived
default branch: `main`.

Rules:

- create short-lived branches from the latest `origin/main`
- open a pull request back into `main`
- keep commit messages in Conventional Commits format
- merge only after required CI checks pass
- let the version workflow create SemVer tags from merged commit history
- delete task branches after merge

Local enforcement:

```bash
make install-hooks
```

Manual commit-message validation:

```bash
make validate-commit MSG="feat: add mcp governance workflow"
```

GitHub automation:

- CI workflow runs tests and governance checks on PRs to `main`
- version workflow computes the next SemVer tag on pushes to `main`
- release workflow builds and publishes the container image to GHCR on `v*` tags

Branch protection helper:

```bash
make governance
```

That script uses `gh` and repository admin permissions to enforce the
expected branch protection on GitHub.

Current coverage includes:

- liveness endpoint
- readiness endpoint
- memory creation
- memory query
- hydration from PostgreSQL after vector lookup
- questionnaire markdown ingestion
- questionnaire yaml ingestion
- notes ingestion
- duplicate skipping during ingestion

## Limitations

- No authentication yet
- Mock embeddings are intended for local dev and tests only
- Query filtering by kind happens after hydration from PostgreSQL
- No tracing, background jobs, or retry queue for failed indexing

## Roadmap Note

Phase 3 still remains out of scope here: fact extraction, reflections, agent roles, and candidate write pipelines.

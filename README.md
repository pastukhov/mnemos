# Mnemos

[Русская версия](README_ru.md)

Mnemos is a production-oriented memory gateway service. PostgreSQL is
the source of truth for memory items, Qdrant stores vectors for
retrieval, and FastAPI exposes write/query/health/metrics endpoints.
Phase 2 adds deterministic ingestion of questionnaire and notes sources
into `memory_items`.
Phase 3 adds an MCP server that exposes Mnemos to AI agents through MCP
while continuing to use the REST API as the backend boundary.
Phase 4 adds an LLM-backed fact extraction pipeline that derives `fact`
items from accepted `raw` items and stores `derived_from` relations.
Phase 5 adds a reflection generation pipeline that synthesizes accepted
`fact` items into evidence-backed `reflection` items linked through
`supported_by` relations.
Phase 6 adds candidate-based memory governance so agent-generated memory
is proposed, validated, and only then merged into accepted memory.

## Architecture

- `api/`: FastAPI app, routes, schemas, dependency wiring
- `core/`: typed settings, JSON logging, Prometheus metrics
- `db/`: SQLAlchemy models, sessions, repositories
- `vector/`: Qdrant wrapper and indexing helpers
- `embeddings/`: mock and OpenAI-compatible embedding providers
- `mcp_server/`: FastMCP server, REST client, and MCP tools
- `pipelines/extract/`: fact extraction schema, LLM client, and runner
- `pipelines/governance/`: candidate validation and merge pipeline
- `services/`: write/query orchestration
- `migrations/`: Alembic migration history
- `scripts/`: bootstrap, collection init, seed data
- `pipelines/ingest/`: questionnaire and notes ingestion pipelines
- `data/raw/`: local raw inputs for ingestion, intentionally gitignored
- `Dockerfile`, `docker-compose.yml`: container image and local stack

Flow summary:

1. `POST /memory/items` validates input.
1. The service inserts the row into PostgreSQL inside a transaction.
1. The statement is embedded and upserted into the per-domain Qdrant
   collection.
1. `POST /memory/query` embeds the query, searches Qdrant, then hydrates
   ranked results from PostgreSQL.
1. MCP tools call the REST gateway and return agent-friendly tool
   results.

## Local Startup

1. Create env file:

```bash
cp .env.example .env
```

1. Create local virtualenv and install dependencies:

```bash
make venv
```

Install local git hooks:

```bash
make install-hooks
```

1. Start the stack:

```bash
docker compose up -d --build
```

The API will be available at `http://localhost:8000`.

The checked-in `.env.example` intentionally omits Compose-internal
addresses. Service-to-service networking is defined directly in Compose.

1. Run a live smoke check against the running stack:

```bash
make smoke
```

## Configuration

Required environment variables:

- `MNEMOS_ENV`
- `MNEMOS_LOG_LEVEL`
- `MNEMOS_TIMEOUT_SECONDS`
- `MCP_SERVER_HOST`
- `MCP_SERVER_PORT`
- `MCP_SERVER_TRANSPORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `FACT_LLM_MODEL`
- `FACT_LLM_BASE_URL`
- `FACT_LLM_API_KEY`
- `FACT_LLM_TIMEOUT_SECONDS`
- `FACT_MAX_FACTS_PER_ITEM`
- `FACT_MIN_CHARS`
- `FACT_MAX_CHARS`
- `REFLECTION_LLM_MODEL`
- `REFLECTION_LLM_BASE_URL`
- `REFLECTION_LLM_API_KEY`
- `REFLECTION_LLM_TIMEOUT_SECONDS`
- `REFLECTION_MAX_PER_THEME`
- `REFLECTION_MIN_CHARS`
- `REFLECTION_MAX_CHARS`
- `QDRANT_VECTOR_SIZE`

Compose-internal addresses for PostgreSQL, Qdrant, Mnemos, and the
optional local mock OpenAI API are defined in Compose files, not in
`.env`.

Embedding, fact extraction, and reflection generation use explicit
OpenAI-compatible providers. Point them either at a real endpoint or at
the local mock service from `docker-compose.local-mock.yml`.

Example:

```bash
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_API_KEY=secret
EMBEDDING_MODEL=openai/text-embedding-3-small
FACT_LLM_BASE_URL=https://openrouter.ai/api/v1
FACT_LLM_API_KEY=secret
FACT_LLM_MODEL=openai/gpt-4.1-mini
REFLECTION_LLM_BASE_URL=https://openrouter.ai/api/v1
REFLECTION_LLM_API_KEY=secret
REFLECTION_LLM_MODEL=openai/gpt-4.1-mini
```

## Migrations

Inside Docker, migrations run automatically from `scripts/bootstrap.sh`
on container startup. The primary interface to the running system is the
HTTP API on `localhost:8000` and the MCP endpoint on `localhost:9000`.

## Ingestion

Phase 2 ingestion commands are available through the local CLI when you
need operational access:

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

- `data/raw/questionnaire.md`: user-provided questionnaire source,
  intentionally not committed
- `data/raw/questionnaire.yaml`: optional user-provided YAML
  questionnaire source, intentionally not committed
- `data/raw/notes.jsonl`: optional local notes source, intentionally not
  committed

Ingestion is idempotent. Duplicate detection uses
`metadata.source_type + metadata.source_id`, backed by PostgreSQL
expression indexes and a unique index guard.

## Fact Extraction

Phase 4 fact extraction command:

```bash
mnemos extract facts
mnemos extract facts --domain self
```

The runner:

- loads accepted `raw` items for the selected domain
- skips raw items that already have extracted facts
- calls the configured fact LLM client
- stores `fact` items plus `derived_from` relations
- indexes extracted facts in Qdrant

Local mock OpenAI-compatible stack:

```bash
cp .env.local-mock.example .env
docker compose -f docker-compose.yml -f docker-compose.local-mock.yml up -d --build
```

## Reflection Generation

Phase 5 reflection generation commands:

```bash
mnemos reflect build
mnemos reflect build --domain self
mnemos reflect build --theme motivation
```

The runner:

- loads accepted `fact` items for the selected domain
- groups facts by `metadata.theme` or upstream questionnaire
  `metadata.topic`
- computes a stable fingerprint per theme batch for idempotency
- calls the configured reflection LLM client
- stores `reflection` items plus `supported_by` relations
- indexes reflections in Qdrant

The local mock API is published on `http://localhost:18090/v1`.

For product deployment, use only `docker-compose.yml` plus real
OpenAI-compatible endpoint values in `.env`.

## Memory Governance

Phase 6 candidate governance endpoints:

```bash
curl -X POST http://localhost:8000/memory/candidate \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "self",
    "kind": "fact",
    "statement": "User prefers observable architectures.",
    "confidence": 0.78,
    "agent_id": "codex_cli",
    "evidence": {"source_fact_ids": ["<fact-uuid-1>", "<fact-uuid-2>"]}
  }'

curl "http://localhost:8000/memory/candidates?status=pending"
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/accept
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/reject \
  -H 'Content-Type: application/json' \
  -d '{"reason": "manual review"}'
```

CLI commands:

```bash
mnemos candidates list
mnemos candidates list --status pending
mnemos candidates accept <candidate-uuid>
mnemos candidates reject <candidate-uuid> --reason "manual review"
```

The governance runner:

- stores agent proposals in `memory_candidates`
- validates duplicate, evidence, and basic contradiction cases on accept
- merges valid candidates into `memory_items`
- creates `supported_by` relations from accepted items to evidence facts
- keeps rejected candidates for audit history

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

## Local Quality Gates

Local git hooks use `pre-commit` plus the existing Conventional Commit
`commit-msg` hook.

Installed checks:

- `ruff` for Python linting
- `mdl` for Markdown linting
- `pytest -q` for the test suite
- Conventional Commit validation on commit messages

Manual commands:

```bash
.venv/bin/pre-commit run --all-files
.venv/bin/ruff check .
.venv/bin/pytest -q
mdl docs/PHASE5_REFLECTION_LAYER.md
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

Default Docker MCP service:

```bash
docker compose up -d
```

That stack exposes `http://localhost:9000/mcp` by default.

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
- `propose_memory_item`
- `get_context`

When `domain` is omitted in `search_memory` and `get_context`, the MCP
server queries all Mnemos domains and aggregates results per domain.

Under Phase 6 governance, `add_memory_note` and `propose_memory_item`
create candidate memory through `/memory/candidate`; MCP tools no longer
write directly into accepted memory.

## Codex Skill

This repository contains an installable Codex skill at
`skills/mnemos-memory`.

Install it with:

```bash
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

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

If you are the only developer, keep the PR flow but configure branch
protection with `0` required approvals and mandatory CI checks.

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
- fact extraction from raw items
- duplicate extraction skipping
- derived_from relation creation
- reflection generation and `supported_by` relation creation
- candidate creation, validation, acceptance, and rejection flows
- fact indexing after extraction

## Limitations

- No authentication yet
- Mock embeddings are intended for local dev and tests only
- Query filtering by kind happens after hydration from PostgreSQL
- No tracing, background jobs, or retry queue for failed indexing

## Roadmap Note

Earlier roadmap notes from Phase 1 are now superseded by implemented
Phase 2 through Phase 6 functionality in this repository.

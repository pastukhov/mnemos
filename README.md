# Mnemos

[Русская версия](README_ru.md)

Mnemos is a memory gateway for storing, retrieving, and governing
machine-readable memory. It keeps PostgreSQL as the source of truth,
uses Qdrant for semantic retrieval, and exposes both a FastAPI service
and an MCP server for agent integrations.

The project is designed for a practical memory workflow: ingest raw
notes and questionnaires, extract evidence-backed facts, synthesize
reflections, and require governance before agent-generated memory
becomes accepted memory.

## Features

- Store structured memory items in PostgreSQL.
- Run semantic search through Qdrant while hydrating final results from
  PostgreSQL.
- Expose REST endpoints for memory writes, reads, queries, health, and
  metrics.
- Expose MCP tools for agent access through `mnemos mcp-server`.
- Ingest questionnaire and notes sources deterministically.
- Extract `fact` items from accepted `raw` items with an
  OpenAI-compatible LLM.
- Build `reflection` items from accepted facts with evidence links.
- Propose agent-generated memory as candidates and review it before
  merging.
- Run locally with Docker Compose, Alembic migrations, and a small test
  suite.

## Quick Start

### 1. Prepare the environment

```sh
cp .env.example .env
make venv
make install-hooks
```

### 2. Start the stack

```sh
docker compose up -d --build
```

The API is available at `http://localhost:8000`.
The MCP endpoint is available at `http://localhost:9000/mcp`.

### 3. Verify that it is running

```sh
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
```

### 4. Run the smoke test

```sh
make smoke
```

## Basic Usage

### Add a memory item

```sh
curl -X POST http://localhost:8000/memory/items \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "self",
    "kind": "note",
    "statement": "User prefers building automated systems.",
    "confidence": 0.95,
    "metadata": {"source": "manual_seed"}
  }'
```

### Fetch a single item

```sh
curl http://localhost:8000/memory/item/<uuid>
```

### Query memory

```sh
curl -X POST http://localhost:8000/memory/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "automated systems",
    "domain": "self",
    "top_k": 5,
    "kinds": ["note", "fact", "reflection"]
  }'
```

### Propose memory for review

```sh
curl -X POST http://localhost:8000/memory/candidate \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "self",
    "kind": "fact",
    "statement": "User prefers observable architectures.",
    "confidence": 0.78,
    "agent_id": "codex_cli",
    "evidence": {
      "source_fact_ids": ["<fact-uuid-1>", "<fact-uuid-2>"]
    }
  }'
```

### Review pending candidates

```sh
curl "http://localhost:8000/memory/candidates?status=pending"
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/accept
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual review"}'
```

## Architecture Overview

Mnemos has five main runtime parts:

- FastAPI API: write, read, query, health, readiness, and metrics
  endpoints
- PostgreSQL: source of truth for `memory_items`,
  `memory_candidates`, and relations
- Qdrant: vector index for retrieval and re-ranking candidates
- LLM pipelines: fact extraction and reflection generation via
  OpenAI-compatible APIs
- MCP server: agent-facing tool adapter over the REST API

Data flow for the common read path:

1. `POST /memory/query` embeds the query text.
1. Qdrant returns ranked IDs.
1. Mnemos hydrates the final items from PostgreSQL.
1. The API returns structured results to clients or the MCP server.

Data flow for agent writes under governance:

1. Agents call `/memory/candidate` directly or via MCP tools.
1. Candidates remain `pending`.
1. Acceptance validates duplicates, evidence, and contradiction checks.
1. Accepted candidates are merged into `memory_items` and indexed.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `api/` | FastAPI app, routes, schemas, dependency wiring |
| `services/` | Memory write, query, and governance orchestration |
| `db/` | SQLAlchemy models, repositories, sessions, Alembic support |
| `vector/` | Qdrant wrapper and indexing helpers |
| `embeddings/` | Mock and OpenAI-compatible embedding providers |
| `pipelines/ingest/` | Questionnaire and notes ingestion |
| `pipelines/extract/` | Fact extraction pipeline |
| `pipelines/reflect/` | Reflection generation pipeline |
| `pipelines/governance/` | Candidate validation and merge flow |
| `mcp_server/` | FastMCP server, REST client, MCP tools |
| `scripts/` | Bootstrap, collection init, hooks, versioning, seed data |
| `tests/` | API, ingestion, extraction, reflection, governance, and MCP tests |
| `docs/` | Phase specs and notes |

## Pipelines and Internal Processing

### Ingestion

Ingestion is deterministic and idempotent. It loads local source files
from `data/raw/` and maps them into `memory_items`.

Supported inputs:

- `data/raw/questionnaire.md`
- `data/raw/questionnaire.yaml`
- `data/raw/notes.jsonl`

Commands:

```sh
mnemos ingest questionnaire data/raw/questionnaire.md
mnemos ingest questionnaire data/raw/questionnaire.yaml
mnemos ingest notes data/raw/notes.jsonl
mnemos ingest all
```

Convenience targets:

```sh
make ingest-all
make ingest-questionnaire
make ingest-notes
```

Duplicate detection uses `metadata.source_type +
metadata.source_id`, backed by PostgreSQL indexes.

### Fact Extraction

Fact extraction turns accepted `raw` items into accepted `fact` items
and creates `derived_from` relations.

Commands:

```sh
mnemos extract facts
mnemos extract facts --domain self
make extract-facts
```

The runner:

- loads accepted `raw` items for the selected domain
- skips items that already have extracted facts
- calls the configured fact LLM client
- stores facts and evidence relations
- indexes new facts in Qdrant

### Reflection Generation

Reflection generation groups accepted facts by theme and creates
evidence-backed `reflection` items linked through `supported_by`
relations.

Commands:

```sh
mnemos reflect build
mnemos reflect build --domain self
mnemos reflect build --theme motivation
make reflect-build
```

The runner:

- loads accepted `fact` items
- groups them by `metadata.theme` or upstream topic
- computes a stable fingerprint for idempotency
- calls the configured reflection LLM client
- stores reflections and supporting relations
- indexes reflections in Qdrant

### Governance

Governance prevents agents from writing directly into accepted memory.
Instead, they create candidates that must be accepted or rejected.

Commands:

```sh
mnemos candidates list
mnemos candidates list --status pending
mnemos candidates accept <candidate-uuid>
mnemos candidates reject <candidate-uuid> --reason "manual review"
make candidates-list
```

The governance runner:

- stores agent proposals in `memory_candidates`
- validates duplicate, evidence, and basic contradiction cases
- merges valid candidates into `memory_items`
- creates `supported_by` relations from accepted items to evidence facts
- keeps rejected candidates for audit history

## MCP Server

For local agent integrations, `stdio` is the simplest transport:

```sh
mnemos mcp-server
```

For HTTP testing:

```sh
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
```

Available MCP tools:

- `search_memory`
- `get_memory_item`
- `add_memory_note`
- `propose_memory_item`
- `get_context`

Example Claude Desktop configuration:

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

When `domain` is omitted in `search_memory` or `get_context`, the MCP
server queries all Mnemos domains and aggregates the results.

Under governance mode, `add_memory_note` and `propose_memory_item`
create pending candidates instead of accepted memory.

## Configuration

Compose keeps service-to-service hostnames in the compose files, so
`.env` mainly contains application settings and external provider
configuration.

### Minimal required variables

These are the settings you will usually touch first:

| Variable | Purpose |
| --- | --- |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `QDRANT_VECTOR_SIZE` | Embedding vector size |
| `EMBEDDING_BASE_URL` | Embedding provider base URL |
| `EMBEDDING_API_KEY` | Embedding provider API key |
| `EMBEDDING_MODEL` | Embedding model name |
| `FACT_LLM_BASE_URL` | Fact extraction LLM endpoint |
| `FACT_LLM_API_KEY` | Fact extraction LLM API key |
| `FACT_LLM_MODEL` | Fact extraction model name |
| `REFLECTION_LLM_BASE_URL` | Reflection LLM endpoint |
| `REFLECTION_LLM_API_KEY` | Reflection LLM API key |
| `REFLECTION_LLM_MODEL` | Reflection model name |

Example:

```sh
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

### Advanced configuration

These tune runtime behavior and validation:

| Variable | Purpose |
| --- | --- |
| `MNEMOS_ENV` | Environment name |
| `MNEMOS_LOG_LEVEL` | Logging verbosity |
| `MNEMOS_TIMEOUT_SECONDS` | Default service timeout |
| `EMBEDDING_TIMEOUT_SECONDS` | Embedding client timeout |
| `FACT_LLM_TIMEOUT_SECONDS` | Fact extraction timeout |
| `FACT_MAX_FACTS_PER_ITEM` | Upper bound on extracted facts |
| `FACT_MIN_CHARS` | Minimum fact length |
| `FACT_MAX_CHARS` | Maximum fact length |
| `REFLECTION_LLM_TIMEOUT_SECONDS` | Reflection generation timeout |
| `REFLECTION_MAX_PER_THEME` | Max reflections per theme |
| `REFLECTION_MIN_CHARS` | Minimum reflection length |
| `REFLECTION_MAX_CHARS` | Maximum reflection length |

### Local mock provider

To run against the included mock OpenAI-compatible stack:

```sh
cp .env.local-mock.example .env
docker compose -f docker-compose.yml \
  -f docker-compose.local-mock.yml \
  up -d --build
```

The local mock API is exposed at `http://localhost:18090/v1`.

For production-like deployment, use `docker-compose.yml` with real
provider values in `.env`.

## Development

### Common commands

```sh
make venv
make up
make down
make logs
make migrate
make test
make smoke
```

### Seed demo data

```sh
.venv/bin/python scripts/create_qdrant_collections.py
.venv/bin/python scripts/seed_memory.py
```

The seed script inserts six demo items across the `self` and `project`
domains.

### Local quality gates

Installed checks:

- `ruff` for Python linting
- `mdl` for Markdown linting
- `pytest -q` for the test suite
- Conventional Commit validation on commit messages

Manual commands:

```sh
.venv/bin/pre-commit run --all-files
.venv/bin/ruff check .
.venv/bin/pytest -q
mdl README.md
```

### Testing coverage

Current tests cover:

- liveness and readiness endpoints
- memory creation and retrieval
- semantic query and hydration from PostgreSQL
- questionnaire Markdown and YAML ingestion
- notes ingestion and duplicate skipping
- fact extraction and `derived_from` relation creation
- reflection generation and `supported_by` relation creation
- candidate creation, validation, acceptance, and rejection
- MCP server tool behavior

## Codex Skill

This repository includes an installable skill at
`skills/mnemos-memory`.

Install it with:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

## Limitations

- No authentication yet.
- Mock providers are for local development and tests only.
- Query filtering by kind happens after hydration from PostgreSQL.
- There is no tracing, background job queue, or retry queue for failed
  indexing.

## Roadmap and Implemented Phases

The repository already contains the functionality from phases 1 through
6, and the list below keeps that roadmap in a user-oriented summary.

- Phase 1, implemented: core memory gateway with FastAPI, PostgreSQL,
  Qdrant, embeddings, health checks, metrics, Docker, and migrations
- Phase 2, implemented: deterministic ingestion of questionnaire and
  notes sources into memory
- Phase 3, implemented: MCP server that exposes Mnemos as tools for
  agents
- Phase 4, implemented: LLM-backed fact extraction from accepted raw
  memory with `derived_from` evidence
- Phase 5, implemented: reflection synthesis from accepted facts with
  `supported_by` evidence
- Phase 6, implemented: candidate-based governance for agent-generated
  memory

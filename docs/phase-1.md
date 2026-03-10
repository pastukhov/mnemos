Ниже Markdown, который можно скормить Codex.

# Mnemos Phase 1 Production Implementation Task

## Objective

Implement **Phase 1** of Mnemos as a production-ready MVP.

Phase 1 scope:

- structured memory storage
- vector index
- query API
- Dockerized deployment
- configuration management
- DB migrations
- health/readiness endpoints
- basic logging and metrics

This phase must be deployable and operable in a real environment.

Do NOT implement later phases yet:

- questionnaire ingestion
- fact extraction
- reflections
- agent roles
- candidate writes

---

## Product Goal

Mnemos Phase 1 is a **memory gateway service** that stores memory items in
structured storage, indexes them in Qdrant, and serves retrieval via API.

The system must:

- persist memory items in PostgreSQL
- index searchable text in Qdrant
- expose retrieval API via FastAPI
- support Docker Compose local/prod deployment
- be structured for later extension

Vector DB is **not** the source of truth. PostgreSQL is the source of truth.

---

## Deliverables

Implement a repository named `mnemos` with the following components:

1. FastAPI service
1. PostgreSQL models and migrations
1. Qdrant integration
1. Embedding abstraction layer
1. Query API
1. Health/readiness/metrics endpoints
1. Docker Compose stack
1. Bootstrap/init scripts
1. README with run/deploy instructions
1. Example seed script

---

## Repository Layout

Create this structure:

```text
mnemos/
  api/
    __init__.py
    main.py
    deps.py
    schemas.py
    routes/
      __init__.py
      health.py
      memory.py

  core/
    __init__.py
    config.py
    logging.py

  db/
    __init__.py
    base.py
    models.py
    session.py
    repositories/
      __init__.py
      memory_items.py

  migrations/
    env.py
    versions/

  vector/
    __init__.py
    qdrant_client.py
    indexer.py

  embeddings/
    __init__.py
    base.py
    mock.py
    openai_compatible.py

  services/
    __init__.py
    memory_service.py
    retrieval_service.py

  scripts/
    bootstrap.sh
    seed_memory.py
    create_qdrant_collections.py

  docker/
    docker-compose.yml
    Dockerfile

  tests/
    test_health.py
    test_memory_query.py
    test_memory_create.py

  .env.example
  alembic.ini
  Makefile
  README.md
  pyproject.toml
```

## Functional Requirements

### 1. Memory Model

Implement PostgreSQL as the source of truth.

Create table `memory_items` with at least these fields:

- `id` UUID primary key
- `domain` string, indexed
- `kind` string, indexed
- `statement` text, required
- `confidence` float nullable
- `status` string, indexed, default `accepted`
- `metadata` JSONB nullable
- `created_at` timestamp with timezone
- `updated_at` timestamp with timezone

Allowed initial domain values:

- `self`
- `project`
- `operational`
- `interaction`

Allowed initial kind values:

- `raw`
- `fact`
- `reflection`
- `summary`
- `note`
- `decision`
- `task`
- `tension`

For Phase 1, only `accepted` records are actively used.

### 2. Vector Index

Use Qdrant.

Create these collections:

- `mnemos_self`
- `mnemos_project`
- `mnemos_operational`
- `mnemos_interaction`

Each indexed point must contain:

- `vector`
- `payload.item_id`
- `payload.domain`
- `payload.kind`
- `payload.status`

Do not store source-of-truth text in Qdrant as the only copy. The retrieval
result must always hydrate from PostgreSQL.

### 3. Embedding Layer

Implement an embedding abstraction.

Interface requirements:

Create a base interface with method:

```python
embed_text(text: str) -> list[float]
```

Implement two providers:

1. Mock embedder
   For local testing without external dependencies.
1. OpenAI-compatible embedder
   Configurable with base URL, API key, and model name.

Use config-driven provider selection.

Default local dev provider may be mock. Do not hardcode external credentials.

### 4. API Endpoints

Implement FastAPI with the following endpoints.

#### `GET /health/live`

Returns process liveness.

Response example:

```json
{"status":"ok"}
```

#### `GET /health/ready`

Checks readiness of:

- PostgreSQL
- Qdrant

Response example:

```json
{
  "status": "ready",
  "checks": {
    "postgres": "ok",
    "qdrant": "ok"
  }
}
```

#### `GET /metrics`

Expose Prometheus-compatible metrics.

At minimum include:

- request count
- request latency
- query count
- query latency
- DB health metric
- Qdrant health metric

#### `POST /memory/items`

Create a memory item and index it.

Input:

```json
{
  "domain": "self",
  "kind": "note",
  "statement": "User prefers building automated systems.",
  "confidence": 0.95,
  "metadata": {
    "source": "manual_seed"
  }
}
```

Response:

Created item with id and timestamps.

#### `GET /memory/item/{id}`

Return a single memory item by id.

#### `POST /memory/query`

Perform semantic retrieval.

Input:

```json
{
  "query": "automation preferences",
  "domain": "self",
  "top_k": 5,
  "kinds": ["note", "fact", "reflection"]
}
```

Behavior:

- embed query
- search matching Qdrant collection
- fetch matching items from PostgreSQL
- return ordered hydrated results

Response example:

```json
{
  "query": "automation preferences",
  "domain": "self",
  "items": [
    {
      "id": "uuid",
      "domain": "self",
      "kind": "note",
      "statement": "User prefers building automated systems.",
      "confidence": 0.95,
      "metadata": {
        "source": "manual_seed"
      },
      "created_at": "2026-03-10T10:00:00Z",
      "updated_at": "2026-03-10T10:00:00Z"
    }
  ]
}
```

## Non-Functional Requirements

### 1. Production Readiness

The service must support:

- idempotent startup
- explicit configuration via environment variables
- DB migrations
- health endpoints for orchestration
- structured JSON logging
- graceful shutdown
- retry-safe dependency initialization

### 2. Configuration

Implement settings via environment variables and a typed config class.

Required settings:

- `MNEMOS_ENV`
- `MNEMOS_HOST`
- `MNEMOS_PORT`
- `MNEMOS_LOG_LEVEL`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `QDRANT_URL`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `QDRANT_VECTOR_SIZE`

Provide `.env.example`.

### 3. Observability

Implement:

#### Logging

Structured JSON logs for:

- startup
- shutdown
- request handling
- dependency failures
- indexing failures
- query requests

#### Metrics

Use Prometheus instrumentation.

At minimum:

- HTTP requests total
- HTTP request duration
- memory query total
- memory query duration
- memory item create total
- readiness failures

Do not add tracing yet.

### 4. Testing

Implement tests for:

- liveness endpoint
- readiness endpoint
- create memory item
- query memory item
- hydration from PostgreSQL after vector search

Tests should run with `pytest`.

## Database Implementation

Use SQLAlchemy 2.x and Alembic.

Create initial migration for `memory_items`.

Recommended schema:

```sql
CREATE TABLE memory_items (
  id UUID PRIMARY KEY,
  domain VARCHAR(64) NOT NULL,
  kind VARCHAR(64) NOT NULL,
  statement TEXT NOT NULL,
  confidence DOUBLE PRECISION NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'accepted',
  metadata JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memory_items_domain ON memory_items(domain);
CREATE INDEX idx_memory_items_kind ON memory_items(kind);
CREATE INDEX idx_memory_items_status ON memory_items(status);
CREATE INDEX idx_memory_items_domain_kind ON memory_items(domain, kind);
```

Use automatic `updated_at` refresh in application logic.

## Qdrant Implementation

For each domain, use one Qdrant collection.

Collection naming:

- `self -> mnemos_self`
- `project -> mnemos_project`
- `operational -> mnemos_operational`
- `interaction -> mnemos_interaction`

Implement collection creation script:

`scripts/create_qdrant_collections.py`

The script must be idempotent.

Use cosine distance unless a strong reason exists otherwise.

## Service Logic

### Create Memory Item Flow

When `POST /memory/items` is called:

- validate payload
- insert item into PostgreSQL
- embed statement
- upsert vector to domain collection in Qdrant
- return created item

If vector indexing fails after DB insert:

- keep DB row
- log indexing failure clearly
- return error or partial-failure response only if implemented consistently

Preferred MVP behavior:

- fail request
- roll back DB transaction before commit if indexing fails

Implement this cleanly.

### Query Flow

When `POST /memory/query` is called:

- validate request
- embed query text
- search Qdrant domain collection
- collect returned `item_id`s
- load matching items from PostgreSQL
- preserve ranking order from Qdrant
- optionally filter by kinds
- return hydrated items

Do not return orphaned vector results if PostgreSQL rows do not exist. Log orphan
count if detected.

## Security and Reliability Notes

For Phase 1:

- no auth required yet
- do not expose secrets in logs
- validate all input with Pydantic
- avoid raw SQL concatenation
- set reasonable HTTP timeouts for embedding calls
- handle dependency failures explicitly

## Docker Requirements

Implement `docker/docker-compose.yml` with services:

- `postgres`
- `qdrant`
- `mnemos`

Requirements:

### `postgres`

- persistent volume

### `qdrant`

- persistent volume

### `mnemos`

- build from local Dockerfile
- depends_on postgres and qdrant
- exposes API port
- loads config from env file

Also provide `Dockerfile` for app.

## Makefile Targets

Implement at least:

- `make up`
- `make down`
- `make logs`
- `make migrate`
- `make test`
- `make seed`

## Seed Data

Implement `scripts/seed_memory.py`.

Seed at least 6 memory items across 2 domains so retrieval can be tested.

Example sample data themes:

- self / automation preference
- self / work style
- project / architecture decision
- project / current constraint

## README Requirements

README must include:

- project purpose
- architecture overview
- local startup
- configuration
- migrations
- seed example
- query examples with `curl`
- limitations of Phase 1
- roadmap note for future phases

## Acceptance Criteria

Phase 1 is complete only if all of the following are true:

- FastAPI service starts successfully
- PostgreSQL migration applies successfully
- Qdrant collections can be initialized
- `POST /memory/items` stores item in PostgreSQL and indexes it in Qdrant
- `POST /memory/query` returns hydrated ranked items
- `GET /health/live` returns ok
- `GET /health/ready` validates PostgreSQL and Qdrant
- `/metrics` exposes Prometheus metrics
- Docker Compose starts the full stack
- tests pass
- README is usable by another engineer without external explanation

## Implementation Constraints

Use:

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Qdrant official client
- Pydantic v2

Keep code modular and ready for later phases.

Do not use:

- LangChain
- LlamaIndex
- heavy framework magic

## Suggested Execution Order

Implement in this order:

1. repository skeleton
1. config and logging
1. SQLAlchemy models and Alembic migration
1. DB session and repository layer
1. Qdrant client wrapper
1. embedding abstraction with mock provider
1. create-memory service
1. query service
1. FastAPI routes
1. health endpoints
1. metrics
1. Docker and Makefile
1. seed script
1. tests
1. README

## Final Instruction

Build Phase 1 completely and stop there.

Do not start questionnaire ingestion or any later-phase features until Phase 1
is working, tested, and documented.

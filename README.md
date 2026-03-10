# Mnemos Phase 1

Mnemos Phase 1 is a production-oriented memory gateway service. PostgreSQL is the source of truth for memory items, Qdrant stores vectors for retrieval, and FastAPI exposes write/query/health endpoints.

## Architecture

- `api/`: FastAPI app, routes, schemas, dependency wiring
- `core/`: typed settings, JSON logging, Prometheus metrics
- `db/`: SQLAlchemy models, sessions, repositories
- `vector/`: Qdrant wrapper and indexing helpers
- `embeddings/`: mock and OpenAI-compatible embedding providers
- `services/`: write/query orchestration
- `migrations/`: Alembic migration history
- `scripts/`: bootstrap, collection init, seed data
- `docker/`: Dockerfile and Compose stack

Flow summary:

1. `POST /memory/items` validates input.
2. The service inserts the row into PostgreSQL inside a transaction.
3. The statement is embedded and upserted into the per-domain Qdrant collection.
4. `POST /memory/query` embeds the query, searches Qdrant, then hydrates ranked results from PostgreSQL.

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

## Seed Example

Initialize collections and insert demo records:

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

## Testing

Run tests with:

```bash
.venv/bin/pytest -q
```

Live stack smoke verification:

```bash
make smoke
```

Current coverage includes:

- liveness endpoint
- readiness endpoint
- memory creation
- memory query
- hydration from PostgreSQL after vector lookup

## Limitations

- No authentication yet
- No ingestion pipeline beyond direct API writes
- Mock embeddings are intended for local dev and tests only
- Query filtering by kind happens after hydration from PostgreSQL
- No tracing, background jobs, or retry queue for failed indexing

## Roadmap Note

Phase 1 intentionally stops at storage, vector indexing, retrieval API, migrations, and operability. Later phases such as questionnaire ingestion, fact extraction, reflections, agent roles, and candidate writes are intentionally out of scope here.

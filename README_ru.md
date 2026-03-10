# Mnemos

[English version](README.md)

Mnemos - это production-oriented memory gateway service. PostgreSQL
выступает source of truth для `memory_items`, Qdrant хранит векторы для
retrieval, а FastAPI отдаёт write/query/health/metrics endpoints.
Phase 2 добавляет детерминированный ingestion опросника и заметок в
`memory_items`. Phase 3 добавляет MCP server для AI-агентов поверх
REST API. Phase 4 добавляет LLM-backed fact extraction pipeline, который
строит `fact` items из принятых `raw` items и создаёт `derived_from`
relations. Phase 5 добавляет reflection generation pipeline, который
синтезирует evidence-backed `reflection` items и связывает их через
`supported_by`. Phase 6 добавляет candidate-based memory governance:
агентские записи сначала предлагаются, валидируются и только потом
могут попасть в accepted memory.

## Архитектура

- `api/`: FastAPI app, routes, schemas и dependency wiring
- `core/`: typed settings, JSON logging и Prometheus metrics
- `db/`: SQLAlchemy models, sessions, repositories и Alembic migrations
- `vector/`: обёртка над Qdrant и indexing helpers
- `embeddings/`: mock и OpenAI-compatible embedding providers
- `mcp_server/`: FastMCP server, REST client и MCP tools
- `pipelines/extract/`: fact extraction schema, LLM client и runner
- `pipelines/reflect/`: reflection generation pipeline
- `pipelines/governance/`: candidate validation и merge pipeline
- `pipelines/ingest/`: ingestion pipelines для questionnaire и notes
- `services/`: orchestration для memory, retrieval и governance
- `scripts/`: bootstrap, init collections и seed scripts
- `docker/`: Dockerfile и Compose stack
- `data/raw/`: локальные raw inputs, каталог намеренно в `.gitignore`

Основной поток:

1. `POST /memory/items` валидирует вход.
1. Сервис сохраняет запись в PostgreSQL в рамках транзакции.
1. Statement эмбеддится и upsert'ится в per-domain коллекцию Qdrant.
1. `POST /memory/query` эмбеддит query, ищет в Qdrant и гидратирует
   результаты из PostgreSQL.
1. MCP tools работают через REST boundary.

## Локальный запуск

1. Создай env-файл:

```bash
cp .env.example .env
```

1. Создай virtualenv и установи зависимости:

```bash
make venv
```

Установи git hooks:

```bash
make install-hooks
```

1. Подними стек:

```bash
make up
```

API будет доступен на `http://localhost:8000`.

`.env.example` намеренно не содержит внутренних адресов Compose.
Сетевое взаимодействие между сервисами задаётся прямо в Compose.

1. Прогони live smoke check:

```bash
make smoke
```

## Конфигурация

Ключевые переменные окружения:

- `MNEMOS_ENV`, `MNEMOS_LOG_LEVEL`
- `MNEMOS_TIMEOUT_SECONDS`
- `MCP_SERVER_HOST`, `MCP_SERVER_PORT`, `MCP_SERVER_TRANSPORT`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `QDRANT_VECTOR_SIZE`
- `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`
- `FACT_LLM_MODEL`, `FACT_LLM_BASE_URL`, `FACT_LLM_API_KEY`,
  `FACT_LLM_TIMEOUT_SECONDS`
- `FACT_MAX_FACTS_PER_ITEM`, `FACT_MIN_CHARS`, `FACT_MAX_CHARS`
- `REFLECTION_LLM_MODEL`, `REFLECTION_LLM_BASE_URL`,
  `REFLECTION_LLM_API_KEY`,
  `REFLECTION_LLM_TIMEOUT_SECONDS`
- `REFLECTION_MAX_PER_THEME`, `REFLECTION_MIN_CHARS`,
  `REFLECTION_MAX_CHARS`

Embedding, fact extraction и reflection generation используют явные
`openai_compatible` providers. В `.env` можно указать либо реальный
endpoint, либо локальный mock-сервис из `docker-compose.local-mock.yml`.

Пример:

```bash
EMBEDDING_BASE_URL=https://your-endpoint.example/v1
EMBEDDING_API_KEY=secret
EMBEDDING_MODEL=text-embedding-3-small
FACT_LLM_BASE_URL=https://your-endpoint.example/v1
FACT_LLM_API_KEY=secret
FACT_LLM_MODEL=gpt-4.1-mini
REFLECTION_LLM_BASE_URL=https://your-endpoint.example/v1
REFLECTION_LLM_API_KEY=secret
REFLECTION_LLM_MODEL=gpt-4.1-mini
```

## Миграции

В Docker migrations запускаются автоматически из
`scripts/bootstrap.sh`. Основной интерфейс работающей системы - HTTP API
на `localhost:8000` и MCP endpoint на `localhost:9000`.

## Ingestion

Команды Phase 2 доступны через локальный CLI, если нужен
операционный доступ:

```bash
mnemos ingest questionnaire data/raw/questionnaire.md
mnemos ingest questionnaire data/raw/questionnaire.yaml
mnemos ingest notes data/raw/notes.jsonl
mnemos ingest all
```

Make targets:

```bash
make ingest-all
make ingest-questionnaire
make ingest-notes
```

Ожидаемые локальные файлы:

- `data/raw/questionnaire.md`
- `data/raw/questionnaire.yaml`
- `data/raw/notes.jsonl`

Ingestion идемпотентен. Дубликаты определяются по
`metadata.source_type + metadata.source_id`.

## Fact Extraction

Команды Phase 4:

```bash
mnemos extract facts
mnemos extract facts --domain self
```

Runner:

- загружает accepted `raw` items выбранного домена
- пропускает записи, у которых уже есть extracted facts
- вызывает настроенный fact LLM client
- сохраняет `fact` items и `derived_from` relations
- индексирует extracted facts в Qdrant

## Reflection Generation

Команды Phase 5:

```bash
mnemos reflect build
mnemos reflect build --domain self
mnemos reflect build --theme motivation
```

Для локального mock OpenAI-compatible стека:

```bash
cp .env.local-mock.example .env
docker compose -f docker-compose.yml -f docker-compose.local-mock.yml up -d --build
```

Runner:

- загружает accepted `fact` items выбранного домена
- группирует facts по `metadata.theme` или upstream `metadata.topic`
- считает stable fingerprint для идемпотентности
- вызывает reflection LLM client
- сохраняет `reflection` items и `supported_by` relations
- индексирует reflections в Qdrant

Локальный mock OpenAI-compatible API публикуется на
`http://localhost:18090/v1`.

Для product-эксплуатации используй только `docker-compose.yml` и
реальные значения OpenAI-compatible endpoint'ов в `.env`.

## Memory Governance

REST endpoints Phase 6:

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

CLI:

```bash
mnemos candidates list
mnemos candidates list --status pending
mnemos candidates accept <candidate-uuid>
mnemos candidates reject <candidate-uuid> --reason "manual review"
```

Governance runner:

- складывает предложения агентов в `memory_candidates`
- при accept валидирует duplicate, evidence и basic contradiction cases
- мерджит валидные candidates в `memory_items`
- создаёт `supported_by` relations к evidence facts
- сохраняет rejected candidates для аудита

## Seed и примеры запросов

Инициализация demo-данных:

```bash
.venv/bin/python scripts/create_qdrant_collections.py
.venv/bin/python scripts/seed_memory.py
```

Полезные вызовы:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics

curl -X POST http://localhost:8000/memory/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "automated systems",
    "domain": "self",
    "top_k": 5,
    "kinds": ["note", "fact", "reflection"]
  }'
```

## Local Quality Gates

Локальные hooks используют `pre-commit` и `commit-msg`.

Проверки:

- `ruff`
- `mdl`
- `pytest -q`
- Conventional Commit validation

Ручной запуск:

```bash
.venv/bin/pre-commit run --all-files
.venv/bin/ruff check .
.venv/bin/pytest -q
mdl docs/PHASE6_MEMORY_GOVERNANCE.md
```

## MCP Server

Для локальных agent integrations используй `stdio`, чтобы избежать
конфликтов портов.

```bash
mnemos mcp-server
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
docker compose -f docker/docker-compose.yml --env-file .env \
  --profile mcp-http up -d mnemos-mcp
```

MCP tools:

- `search_memory`
- `get_memory_item`
- `add_memory_note`
- `propose_memory_item`
- `get_context`

Под Phase 6 `add_memory_note` и `propose_memory_item` создают candidate
memory через `/memory/candidate`, а не пишут напрямую в accepted memory.

## Testing и Governance

Тесты:

```bash
.venv/bin/pytest -q
```

Репозиторий использует trunk-based development с единственной
long-lived веткой `main`.

Правила:

- создавай короткие ветки от свежего `origin/main`
- открывай PR обратно в `main`
- используй Conventional Commits
- мержи только после прохождения required checks
- удаляй task branches после merge

Полезные команды:

```bash
make install-hooks
make validate-commit MSG="feat: add mcp governance workflow"
make governance
```

## Ограничения

- Аутентификации пока нет
- Mock embeddings подходят только для local dev и tests
- Фильтрация по `kind` делается после hydration из PostgreSQL
- Нет tracing, background jobs и retry queue для failed indexing

## Примечание по roadmap

Старые roadmap notes из Phase 1 уже устарели: в этом репозитории
реализованы фазы со 2 по 6.

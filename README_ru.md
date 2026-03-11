# Mnemos

[English version](README.md)

Mnemos - это memory gateway для хранения, поиска и управления
машиночитаемой памятью. PostgreSQL остаётся source of truth, Qdrant
используется для семантического поиска, а наружу система отдаёт FastAPI
сервис и MCP server для интеграции с агентами.

Проект рассчитан на практический memory workflow: загрузить сырые
заметки и ответы опросника, извлечь из них evidence-backed facts,
синтезировать reflections и пропускать agent-generated memory через
governance, прежде чем она попадёт в accepted memory.

## Возможности

- Хранение структурированных memory items в PostgreSQL.
- Семантический поиск через Qdrant с финальной гидрацией результатов из
  PostgreSQL.
- REST endpoints для записи, чтения, поиска, health checks и metrics.
- MCP tools для агентского доступа через `mnemos mcp-server`.
- Детерминированный ingestion questionnaire и notes sources.
- Извлечение `fact` items из принятых `raw` items через
  OpenAI-compatible LLM.
- Построение `reflection` items из принятых facts со связями на
  evidence.
- Создание agent-generated memory как candidates с review перед merge.
- Локальный запуск через Docker Compose, Alembic migrations и небольшой
  test suite.

## Быстрый старт

### 1. Подготовь окружение

```sh
cp .env.example .env
make venv
make install-hooks
```

### 2. Подними стек

```sh
docker compose up -d --build
```

API будет доступен на `http://localhost:8000`.
MCP endpoint будет доступен на `http://localhost:9000/mcp`.

### 3. Проверь, что всё запустилось

```sh
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
```

### 4. Запусти smoke test

```sh
make smoke
```

## Базовое использование

### Добавить memory item

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

### Получить item по ID

```sh
curl http://localhost:8000/memory/item/<uuid>
```

### Выполнить запрос к памяти

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

### Предложить memory item на review

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

### Просмотреть pending candidates

```sh
curl "http://localhost:8000/memory/candidates?status=pending"
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/accept
curl -X POST http://localhost:8000/memory/candidate/<candidate-uuid>/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual review"}'
```

## Обзор архитектуры

У Mnemos есть пять основных runtime-компонентов:

- FastAPI API: endpoints для записи, чтения, query, health, readiness и
  metrics
- PostgreSQL: source of truth для `memory_items`,
  `memory_candidates` и relations
- Qdrant: vector index для retrieval и re-ranking candidates
- LLM pipelines: fact extraction и reflection generation через
  OpenAI-compatible APIs
- MCP server: agent-facing adapter поверх REST API

Поток данных для обычного read path:

1. `POST /memory/query` строит embedding для текста запроса.
1. Qdrant возвращает ранжированный список ID.
1. Mnemos гидратирует итоговые items из PostgreSQL.
1. API возвращает структурированный ответ клиенту или MCP server.

Поток данных для agent writes под governance:

1. Агенты вызывают `/memory/candidate` напрямую или через MCP tools.
1. Candidates остаются в статусе `pending`.
1. На accept выполняется валидация duplicate, evidence и contradiction
   checks.
1. Принятые candidates мерджатся в `memory_items` и индексируются.

## Структура репозитория

| Path | Назначение |
| --- | --- |
| `api/` | FastAPI app, routes, schemas, dependency wiring |
| `services/` | Оркестрация memory write, query и governance |
| `db/` | SQLAlchemy models, repositories, sessions и Alembic support |
| `vector/` | Обёртка над Qdrant и indexing helpers |
| `embeddings/` | Mock и OpenAI-compatible embedding providers |
| `pipelines/ingest/` | Ingestion questionnaire и notes |
| `pipelines/extract/` | Pipeline извлечения facts |
| `pipelines/reflect/` | Pipeline генерации reflections |
| `pipelines/governance/` | Валидация и merge candidates |
| `mcp_server/` | FastMCP server, REST client и MCP tools |
| `scripts/` | Bootstrap, init collections, hooks, versioning, seed data |
| `tests/` | Тесты API, ingestion, extraction, reflection, governance и MCP |
| `docs/` | Спецификации фаз и заметки |

## Пайплайны и внутренняя обработка

### Ingestion

Ingestion детерминирован и идемпотентен. Он загружает локальные source
files из `data/raw/` и превращает их в `memory_items`.

Поддерживаемые входные файлы:

- `data/raw/questionnaire.md`
- `data/raw/questionnaire.yaml`
- `data/raw/notes.jsonl`

Команды:

```sh
mnemos ingest questionnaire data/raw/questionnaire.md
mnemos ingest questionnaire data/raw/questionnaire.yaml
mnemos ingest notes data/raw/notes.jsonl
mnemos ingest all
```

Удобные make targets:

```sh
make ingest-all
make ingest-questionnaire
make ingest-notes
```

Поиск дубликатов использует `metadata.source_type +
metadata.source_id` и опирается на PostgreSQL indexes.

### Fact Extraction

Fact extraction превращает принятые `raw` items в принятые `fact`
items и создаёт relations `derived_from`.

Команды:

```sh
mnemos extract facts
mnemos extract facts --domain self
make extract-facts
```

Runner:

- загружает accepted `raw` items выбранного домена
- пропускает items, для которых facts уже извлечены
- вызывает настроенный fact LLM client
- сохраняет facts и evidence relations
- индексирует новые facts в Qdrant

### Reflection Generation

Reflection generation группирует принятые facts по теме и создаёт
evidence-backed `reflection` items, связанные через `supported_by`.

Команды:

```sh
mnemos reflect build
mnemos reflect build --domain self
mnemos reflect build --theme motivation
make reflect-build
```

Runner:

- загружает accepted `fact` items
- группирует их по `metadata.theme` или upstream topic
- вычисляет stable fingerprint для идемпотентности
- вызывает reflection LLM client
- сохраняет reflections и supporting relations
- индексирует reflections в Qdrant

### Governance

Governance не даёт агентам писать напрямую в accepted memory. Вместо
этого они создают candidates, которые нужно либо принять, либо
отклонить.

Команды:

```sh
mnemos candidates list
mnemos candidates list --status pending
mnemos candidates accept <candidate-uuid>
mnemos candidates reject <candidate-uuid> --reason "manual review"
make candidates-list
```

Governance runner:

- сохраняет предложения агентов в `memory_candidates`
- валидирует duplicate, evidence и базовые contradiction cases
- мерджит валидные candidates в `memory_items`
- создаёт `supported_by` relations от принятых items к evidence facts
- оставляет rejected candidates для audit history

## MCP Server

Для локальных agent integrations транспорт `stdio` проще всего:

```sh
mnemos mcp-server
```

Для HTTP-тестирования:

```sh
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
```

Доступные MCP tools:

- `search_memory`
- `get_memory_item`
- `add_memory_note`
- `propose_memory_item`
- `get_context`

Пример конфигурации для Claude Desktop:

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

Если `domain` не передан в `search_memory` или `get_context`, MCP
server делает запрос по всем доменам Mnemos и агрегирует результаты.

В режиме governance `add_memory_note` и `propose_memory_item` создают
pending candidates, а не accepted memory.

## Конфигурация

Compose хранит service-to-service hostnames в compose files, поэтому
`.env` в основном содержит application settings и конфигурацию внешних
providers.

### Минимально необходимые переменные

Обычно в первую очередь нужно настроить именно их:

| Variable | Назначение |
| --- | --- |
| `POSTGRES_DB` | Имя базы PostgreSQL |
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `QDRANT_VECTOR_SIZE` | Размер embedding vector |
| `EMBEDDING_BASE_URL` | Base URL embedding provider |
| `EMBEDDING_API_KEY` | API key embedding provider |
| `EMBEDDING_MODEL` | Имя embedding model |
| `FACT_LLM_BASE_URL` | Endpoint LLM для fact extraction |
| `FACT_LLM_API_KEY` | API key LLM для fact extraction |
| `FACT_LLM_MODEL` | Имя модели для fact extraction |
| `REFLECTION_LLM_BASE_URL` | Endpoint LLM для reflection generation |
| `REFLECTION_LLM_API_KEY` | API key LLM для reflections |
| `REFLECTION_LLM_MODEL` | Имя модели для reflections |

Пример:

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

### Расширенная конфигурация

Эти переменные настраивают runtime behavior и validation:

| Variable | Назначение |
| --- | --- |
| `MNEMOS_ENV` | Имя окружения |
| `MNEMOS_LOG_LEVEL` | Уровень логирования |
| `MNEMOS_TIMEOUT_SECONDS` | Базовый timeout сервиса |
| `EMBEDDING_TIMEOUT_SECONDS` | Timeout embedding client |
| `FACT_LLM_TIMEOUT_SECONDS` | Timeout fact extraction |
| `FACT_MAX_FACTS_PER_ITEM` | Верхняя граница числа facts |
| `FACT_MIN_CHARS` | Минимальная длина fact |
| `FACT_MAX_CHARS` | Максимальная длина fact |
| `REFLECTION_LLM_TIMEOUT_SECONDS` | Timeout reflection generation |
| `REFLECTION_MAX_PER_THEME` | Макс. число reflections на тему |
| `REFLECTION_MIN_CHARS` | Минимальная длина reflection |
| `REFLECTION_MAX_CHARS` | Максимальная длина reflection |

### Локальный mock provider

Чтобы работать через локальный OpenAI-compatible mock stack:

```sh
cp .env.local-mock.example .env
docker compose -f docker-compose.yml \
  -f docker-compose.local-mock.yml \
  up -d --build
```

Локальный mock API доступен на `http://localhost:18090/v1`.

Для более production-like сценария используй `docker-compose.yml` и
реальные значения providers в `.env`.

## Разработка

### Основные команды

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

Seed script добавляет шесть demo items в домены `self` и `project`.

### Локальные quality gates

Установленные проверки:

- `ruff` для Python linting
- `mdl` для Markdown linting
- `pytest -q` для test suite
- Conventional Commit validation для commit messages

Ручные команды:

```sh
.venv/bin/pre-commit run --all-files
.venv/bin/ruff check .
.venv/bin/pytest -q
mdl README_ru.md
```

### Покрытие тестами

Текущие тесты покрывают:

- liveness и readiness endpoints
- создание и получение memory items
- semantic query и гидрацию из PostgreSQL
- ingestion questionnaire в Markdown и YAML
- ingestion notes и пропуск дубликатов
- fact extraction и создание relations `derived_from`
- reflection generation и relations `supported_by`
- создание, валидацию, accept и reject candidates
- поведение MCP server tools

## Codex Skill

В репозитории есть устанавливаемый skill:
`skills/mnemos-memory`.

Установка:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

## Ограничения

- Аутентификации пока нет.
- Mock providers предназначены только для локальной разработки и
  тестов.
- Фильтрация query по kind происходит после гидрации из PostgreSQL.
- Нет tracing, background job queue и retry queue для ошибок
  индексации.

## Roadmap и реализованные фазы

Репозиторий уже содержит функциональность фаз 1-6, а список ниже
сохраняет исходный roadmap в более пользовательском виде.

- Phase 1, implemented: базовый memory gateway с FastAPI, PostgreSQL,
  Qdrant, embeddings, health checks, metrics, Docker и migrations
- Phase 2, implemented: детерминированный ingestion questionnaire и
  notes sources в memory
- Phase 3, implemented: MCP server, который открывает Mnemos агентам
  как набор tools
- Phase 4, implemented: LLM-backed fact extraction из accepted raw
  memory с evidence `derived_from`
- Phase 5, implemented: синтез reflections из accepted facts с evidence
  `supported_by`
- Phase 6, implemented: candidate-based governance для
  agent-generated memory

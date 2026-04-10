# Phase 7: LLM Wiki — персональная вики, управляемая LLM

> Референс: [llm-wiki.md](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (Andrej Karpathy)

## Мотивация

Сейчас mnemos хранит знания как дискретные записи: raw → fact → reflection.
Это хорошо для машинного поиска, но плохо для чтения человеком.

LLM Wiki добавляет **третий слой** — связные markdown-страницы, которые LLM
генерирует и обновляет из существующих фактов/рефлексий. Вики — это
«нарастающий артефакт» (compounding artifact), который обогащается с каждым
добавленным источником.

## Архитектура (три слоя)

```
┌──────────────────────────────────────────────────┐
│  Слой 1: Сырые источники (immutable)             │
│  memory_items kind=raw  ── уже реализовано        │
├──────────────────────────────────────────────────┤
│  Слой 2: Извлечённые знания                      │
│  facts + reflections     ── уже реализовано        │
├──────────────────────────────────────────────────┤
│  Слой 3: Вики (NEW)                              │
│  markdown-страницы, index.md, log.md             │
│  LLM генерирует и обновляет                       │
└──────────────────────────────────────────────────┘
```

## Три операции

| Операция  | Описание                                            |
|-----------|-----------------------------------------------------|
| **build** | LLM генерирует/обновляет wiki-страницы из facts+reflections |
| **query** | Пользователь задаёт вопрос → LLM читает wiki → отвечает     |
| **lint**  | Периодическая проверка на устаревшие/противоречивые записи    |

---

## Задачи

### Этап 7.1 — Wiki Schema Document

Конфигурационный файл, который определяет структуру вики: какие страницы
создавать, как группировать контент.

#### 7.1.1 Создать модель WikiSchema

- **Файл:** `pipelines/wiki/wiki_schema.py`
- Pydantic-модель `WikiPageDefinition`: name, title, description, domains[], kinds[], themes[]
- Pydantic-модель `WikiSchema`: pages list, output_dir, default_domain
- Загрузка из YAML-файла (`data/wiki_schema.yaml`)

#### 7.1.2 Создать дефолтный wiki_schema.yaml

- **Файл:** `data/wiki_schema.yaml`
- Определить стартовый набор страниц:
  - `career.md` — профессиональный опыт и навыки
  - `values.md` — ценности и мотивация
  - `workstyle.md` — рабочий стиль и предпочтения
  - `goals.md` — цели и планы
  - `decisions.md` — ключевые решения и контекст
- Каждая страница: name, title, description, фильтры по domain/kind/theme

#### 7.1.3 Добавить Settings для wiki

- **Файл:** `core/config.py`
- Новые настройки:
  - `WIKI_OUTPUT_DIR` (default: `data/wiki`)
  - `WIKI_SCHEMA_PATH` (default: `data/wiki_schema.yaml`)
  - `WIKI_LLM_MODEL` (default: то же, что reflection_llm_model)
  - `WIKI_LLM_BASE_URL`, `WIKI_LLM_API_KEY`, `WIKI_LLM_TIMEOUT_SECONDS`
  - `WIKI_MAX_PAGE_CHARS` (default: 5000)
  - `WIKI_MIN_FACTS_PER_PAGE` (default: 3)

---

### Этап 7.2 — Wiki LLM Client

LLM-клиент для синтеза wiki-страниц (по аналогии с FactLLMClient / ReflectionLLMClient).

#### 7.2.1 Создать WikiLLMClient (абстракция + OpenAI-совместимая реализация)

- **Файл:** `pipelines/wiki/wiki_llm_client.py`
- ABC `WikiLLMClient` с методом `synthesize_page(page_def, facts, reflections, existing_content?) → str`
- `OpenAICompatibleWikiLLMClient` — реализация через `/chat/completions`
- `MockWikiLLMClient` — для тестов (конкатенация фактов в markdown)

#### 7.2.2 Написать system prompt для wiki-синтеза

- **В том же файле:** `pipelines/wiki/wiki_llm_client.py`
- Промпт должен:
  - Получать page definition (title, description, scope)
  - Получать список фактов и рефлексий
  - Опционально получать текущее содержимое страницы (для обновления)
  - Генерировать связный markdown с заголовками, параграфами, списками
  - НЕ выдумывать информацию сверх того, что в фактах
  - При обновлении — интегрировать новую информацию, а не переписывать с нуля

#### 7.2.3 Добавить builder-функцию

- `build_wiki_llm_client(settings) → WikiLLMClient`
- По аналогии с `build_fact_llm_client` и `build_reflection_llm_client`

---

### Этап 7.3 — Wiki Build Pipeline

Основной пайплайн: читает facts/reflections → генерирует wiki-страницы.

#### 7.3.1 Создать WikiBuildRunner

- **Файл:** `pipelines/wiki/wiki_runner.py`
- Класс `WikiBuildRunner(memory_service, llm_client, settings)`
- Метод `run(domain?, page_name?) → WikiBuildReport`
- `WikiBuildReport`: pages_built, pages_updated, pages_skipped, errors

#### 7.3.2 Логика построения страницы

- **В том же файле или** `pipelines/wiki/build_page.py`
- Для каждой page definition из schema:
  1. Загрузить facts + reflections по фильтрам (domain, kind, theme)
  2. Если фактов < `WIKI_MIN_FACTS_PER_PAGE` → skip
  3. Проверить, существует ли текущая страница на диске
  4. Вычислить fingerprint входных данных (как в reflection_runner)
  5. Если fingerprint не изменился → skip
  6. Вызвать LLM: передать page_def + facts + reflections + existing_content
  7. Записать результат в `{WIKI_OUTPUT_DIR}/{page_name}.md`
  8. Сохранить fingerprint в metadata-файл

#### 7.3.3 Генерация frontmatter для каждой страницы

- Каждая wiki-страница начинается с YAML frontmatter:
  ```yaml
  ---
  title: Карьера и навыки
  generated_at: 2026-04-10T12:00:00Z
  source_fingerprint: abc123
  facts_count: 12
  reflections_count: 3
  ---
  ```

---

### Этап 7.4 — Index и Log

Автоматическая генерация навигационных файлов.

#### 7.4.1 Генерация index.md

- **Файл:** `pipelines/wiki/generate_index.py`
- Функция `generate_index(wiki_dir, schema) → str`
- Сканирует `WIKI_OUTPUT_DIR`, для каждой страницы:
  - Читает frontmatter (title, generated_at, facts_count)
  - Генерирует строку `- [Title](page.md) — description (N facts, updated DATE)`
- Записывает `{WIKI_OUTPUT_DIR}/index.md`

#### 7.4.2 Генерация log.md

- **Файл:** `pipelines/wiki/generate_log.py`
- Функция `generate_log(memory_service, wiki_dir) → str`
- Для каждого raw-элемента (из БД): дата, source_type, краткое описание
- Записывает `{WIKI_OUTPUT_DIR}/log.md`
- Формат: хронологический (новые сверху)

#### 7.4.3 Вызов index/log из WikiBuildRunner

- После генерации всех страниц вызвать `generate_index()` и `generate_log()`
- Оба файла перегенерируются при каждом build

---

### Этап 7.5 — CLI команды

#### 7.5.1 `mnemos wiki build`

- **Файл:** `cli.py` — добавить `wiki` subparser
- Аргументы: `--domain` (опционально), `--page` (опционально)
- Вызывает `WikiBuildRunner.run()`
- Печатает отчёт

#### 7.5.2 `mnemos wiki lint`

- Аргументы: `--domain` (опционально), `--fix` (флаг, default false)
- Запускает lint-проверку (реализация в этапе 7.6)
- Печатает найденные проблемы

#### 7.5.3 `mnemos wiki query "вопрос"`

- Аргументы: позиционный `question`
- Запускает wiki-query (реализация в этапе 7.7)
- Печатает ответ

---

### Этап 7.6 — Wiki Lint Pipeline

Проверка вики на целостность и актуальность.

#### 7.6.1 Создать WikiLintRunner

- **Файл:** `pipelines/wiki/wiki_lint_runner.py`
- Класс `WikiLintRunner(memory_service, llm_client, settings)`
- Метод `run(domain?) → WikiLintReport`

#### 7.6.2 Проверки lint

- **Stale pages**: страница, чей fingerprint устарел (новые факты добавлены)
- **Empty pages**: страница с < N фактов (порог из настроек)
- **Orphan facts**: факты, не попавшие ни в одну wiki-страницу
- **Contradictions**: LLM проверяет каждую страницу на внутренние противоречия
  (отправляет содержимое страницы + свежие факты → LLM возвращает список issues)

#### 7.6.3 WikiLintReport

- `WikiLintReport`: stale_pages[], empty_pages[], orphan_facts_count, contradictions[]
- Метод `render()` — человекочитаемый вывод
- Опциональный `--fix`: для stale_pages запускает rebuild

---

### Этап 7.7 — Wiki Query

Запрос к вики с помощью LLM.

#### 7.7.1 Создать WikiQueryRunner

- **Файл:** `pipelines/wiki/wiki_query_runner.py`
- Класс `WikiQueryRunner(memory_service, retrieval_service, llm_client, settings)`
- Метод `query(question, domain?) → WikiQueryResult`

#### 7.7.2 Логика query

1. Семантический поиск по Qdrant → топ-K релевантных фактов
2. Определить, какие wiki-страницы содержат эти факты (по theme/domain)
3. Прочитать содержимое этих wiki-страниц с диска
4. Отправить LLM: question + содержимое релевантных страниц + index.md
5. LLM отвечает, ссылаясь на конкретные страницы

#### 7.7.3 WikiQueryResult

- `answer: str` — ответ LLM
- `sources: list[str]` — список использованных wiki-страниц
- `confidence: float`

---

### Этап 7.8 — MCP Tools для Wiki

Доступ к вики через MCP-сервер для AI-агентов.

#### 7.8.1 `build_wiki` tool

- **Файл:** `mcp_server/tools/build_wiki.py`
- Запускает WikiBuildRunner
- Возвращает отчёт

#### 7.8.2 `query_wiki` tool

- **Файл:** `mcp_server/tools/query_wiki.py`
- Принимает question + domain
- Возвращает ответ со ссылками на страницы

#### 7.8.3 `read_wiki_page` tool

- **Файл:** `mcp_server/tools/read_wiki_page.py`
- Принимает page_name
- Возвращает содержимое страницы

#### 7.8.4 `list_wiki_pages` tool

- **Файл:** `mcp_server/tools/list_wiki_pages.py`
- Возвращает список страниц (из index.md или сканированием директории)

#### 7.8.5 Зарегистрировать tools в MCP сервере

- **Файл:** `mcp_server/server.py`
- Добавить 4 новых инструмента в регистрацию

---

### Этап 7.9 — Wiki Ingest (обновление страниц при поступлении данных)

Ключевая идея Карпати: при добавлении нового источника LLM обновляет
существующие wiki-страницы инкрементально.

#### 7.9.1 Определить, какие страницы затронуты

- **Файл:** `pipelines/wiki/wiki_ingest.py`
- Функция `affected_pages(new_items, schema) → list[WikiPageDefinition]`
- По domain/kind/theme нового элемента определяет, какие страницы обновить

#### 7.9.2 Инкрементальное обновление страницы

- Загрузить текущее содержимое страницы
- Отправить LLM: current_content + new_facts → updated_content
- LLM промпт: «Интегрируй новую информацию в существующую страницу.
  Не удаляй корректное содержимое. Добавляй, уточняй, дополняй.»
- Записать обновлённую страницу, обновить fingerprint

#### 7.9.3 Хук в IngestRunner

- После успешного ingest raw-элементов → вызвать wiki_ingest
  для обновления затронутых страниц
- Флаг `WIKI_AUTO_UPDATE` в Settings (default: false) —
  включает автоматическое обновление wiki при ingest

---

### Этап 7.10 — Web UI для Wiki

Просмотр вики в веб-интерфейсе.

#### 7.10.1 API endpoint для списка страниц

- **Файл:** `api/routes/web.py`
- `GET /ui/api/wiki/pages` — список страниц (из index.md)

#### 7.10.2 API endpoint для чтения страницы

- `GET /ui/api/wiki/pages/{page_name}` — содержимое страницы (markdown → HTML)

#### 7.10.3 API endpoint для wiki query

- `POST /ui/api/wiki/query` — вопрос к вики, возвращает ответ

#### 7.10.4 API endpoint для build/lint

- `POST /ui/api/wiki/build` — запуск генерации
- `POST /ui/api/wiki/lint` — запуск проверки

#### 7.10.5 Фронтенд: таб Wiki

- **Файл:** `api/static/app.js`
- Новый таб «Wiki» в навигации
- Список страниц (кликабельный) → просмотр страницы (рендер markdown)
- Кнопка «Rebuild Wiki»
- Поле для wiki-query

---

### Этап 7.11 — Тесты

#### 7.11.1 Unit-тесты для WikiSchema

- Загрузка из YAML, валидация, дефолтные значения

#### 7.11.2 Unit-тесты для MockWikiLLMClient

- Генерация страницы из фактов

#### 7.11.3 Unit-тесты для WikiBuildRunner

- Build с mock LLM, проверка создания файлов, fingerprint, skip

#### 7.11.4 Unit-тесты для index/log генерации

- Корректный markdown, frontmatter parsing

#### 7.11.5 Unit-тесты для WikiLintRunner

- Обнаружение stale pages, orphan facts

#### 7.11.6 Unit-тесты для WikiQueryRunner

- Ответ на вопрос с mock LLM

#### 7.11.7 Integration-тесты для API endpoints

- Wiki pages list, read page, query, build

#### 7.11.8 Integration-тесты для CLI

- `mnemos wiki build`, `mnemos wiki lint`, `mnemos wiki query`

---

## Порядок реализации

```
7.1 Schema Document          ← минимальная база
 ↓
7.2 Wiki LLM Client          ← основной инструмент
 ↓
7.3 Wiki Build Pipeline       ← MVP: можно сгенерировать вики
 ↓
7.4 Index + Log               ← навигация
 ↓
7.5 CLI команды               ← пользователь может запускать
 ↓
7.11.1–7.11.4 Тесты          ← покрыть MVP
 ↓
7.6 Wiki Lint                 ← качество контента
 ↓
7.7 Wiki Query                ← интерактивный запрос
 ↓
7.8 MCP Tools                 ← доступ для агентов
 ↓
7.9 Wiki Ingest               ← инкрементальные обновления
 ↓
7.10 Web UI                   ← визуальный интерфейс
 ↓
7.11.5–7.11.8 Тесты          ← покрыть всё остальное
```

## Оценка новых файлов

| Этап | Новые файлы                                    |
|------|------------------------------------------------|
| 7.1  | `pipelines/wiki/wiki_schema.py`, `data/wiki_schema.yaml` |
| 7.2  | `pipelines/wiki/wiki_llm_client.py`           |
| 7.3  | `pipelines/wiki/wiki_runner.py`, `pipelines/wiki/build_page.py` |
| 7.4  | `pipelines/wiki/generate_index.py`, `pipelines/wiki/generate_log.py` |
| 7.5  | изменения в `cli.py`                           |
| 7.6  | `pipelines/wiki/wiki_lint_runner.py`           |
| 7.7  | `pipelines/wiki/wiki_query_runner.py`          |
| 7.8  | `mcp_server/tools/build_wiki.py`, `query_wiki.py`, `read_wiki_page.py`, `list_wiki_pages.py` |
| 7.9  | `pipelines/wiki/wiki_ingest.py`, изменения в `ingest_runner.py` |
| 7.10 | изменения в `web.py`, `app.js`, `app.css`     |
| 7.11 | `tests/test_wiki_*.py`                         |

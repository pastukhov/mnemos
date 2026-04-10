---
layout: default
title: CLI Reference
permalink: /cli/
lang: ru
alternate_url: /en/cli/
lead: Справочник по командам `mnemos` с примерами запуска и основными
  флагами.
---

# CLI Reference

Этот справочник описывает команды `mnemos` из `cli.py`. Примеры ниже
показывают реальное дерево команд и ключевые флаги.

## Быстрый обзор

| Команда | Назначение |
| --- | --- |
| `ingest` | Импортировать источники в память |
| `extract` | Извлечь `fact` из длинных `raw`-материалов |
| `reflect` | Собрать `reflection` на основе фактов |
| `candidates` | Просмотреть и модерировать кандидатов |
| `wiki` | Построить, проверить или запросить wiki |
| `mcp-server` | Запустить MCP server |

## `ingest`

Импортирует данные в память.

Синтаксис:

```sh
mnemos ingest questionnaire <path>
mnemos ingest notes <path>
mnemos ingest all
```

Подкоманды:

- `questionnaire <path>` - загрузить ответы опросника из файла
- `notes <path>` - загрузить заметки из файла
- `all` - запустить полный ingest pipeline

Примеры:

```sh
mnemos ingest questionnaire data/survey.md
mnemos ingest notes data/notes.md
mnemos ingest all
```

## `extract`

Извлекает факты из сохранённых `raw`-элементов.

Синтаксис:

```sh
mnemos extract facts [--domain DOMAIN]
```

Флаги:

- `--domain DOMAIN` - ограничить извлечение одной областью памяти
  (`self` по умолчанию)

Пример:

```sh
mnemos extract facts --domain self
```

## `reflect`

Строит более общие выводы на основе извлечённых фактов.

Синтаксис:

```sh
mnemos reflect build [--domain DOMAIN] [--theme THEME]
```

Флаги:

- `--domain DOMAIN` - ограничить сбор reflections одной областью
  памяти (`self` по умолчанию)
- `--theme THEME` - опционально сузить сборку по теме

Пример:

```sh
mnemos reflect build --domain self --theme workstyle
```

## `candidates`

Показывает, принимает и отклоняет кандидатов до записи в основную
память.

Синтаксис:

```sh
mnemos candidates list [--status STATUS] [--domain DOMAIN] [--kind KIND]
mnemos candidates accept <candidate_id>
mnemos candidates reject <candidate_id> --reason REASON
```

Подкоманды:

- `list` - вывести список кандидатов
- `accept <candidate_id>` - принять кандидата и попытаться слить его в
  memory
- `reject <candidate_id>` - отклонить кандидата с причиной

Флаги:

- `--status STATUS` - фильтр по статусу
- `--domain DOMAIN` - фильтр по области памяти
- `--kind KIND` - фильтр по типу записи
- `--reason REASON` - обязательная причина отклонения

Примеры:

```sh
mnemos candidates list --status pending
mnemos candidates accept 123
mnemos candidates reject 123 --reason "too vague"
```

## `wiki`

Строит и проверяет wiki-страницы.

Синтаксис:

```sh
mnemos wiki build [--domain DOMAIN] [--page PAGE]
mnemos wiki lint [--domain DOMAIN] [--fix]
mnemos wiki query <question> [--domain DOMAIN]
```

Подкоманды:

- `build` - сгенерировать wiki-страницы из facts и reflections
- `lint` - проверить wiki на целостность и актуальность
- `query` - задать вопрос к уже собранной wiki

Флаги:

- `--domain DOMAIN` - ограничить операцию одной областью памяти
- `--page PAGE` - сгенерировать только одну wiki-страницу
- `--fix` - попытаться исправить найденные проблемы при lint

Примеры:

```sh
mnemos wiki build
mnemos wiki build --domain self --page career
mnemos wiki lint --fix
mnemos wiki query "What are my workstyle preferences?"
```

Примечание:

`mnemos wiki lint` и `mnemos wiki query` пока выводят заглушку:
реализация запланирована на более поздний этап.

## `mcp-server`

Запускает MCP server для подключения агентов.

Синтаксис:

```sh
mnemos mcp-server [--transport TRANSPORT] [--host HOST] [--port PORT]
```

Флаги:

- `--transport TRANSPORT` - `stdio`, `streamable-http`, `http` или `sse`
- `--host HOST` - host для сетевого транспорта
- `--port PORT` - port для сетевого транспорта

Пример:

```sh
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
```

## Порядок запуска

- Сначала загрузите данные через `ingest`.
- Затем извлеките `fact` через `extract`.
- После этого соберите `reflection` через `reflect`.
- Для проверки новых знаний используйте `candidates`.
- Когда нужны читаемые страницы, запускайте `wiki build`.
- Для интеграции с агентами поднимайте `mcp-server`.

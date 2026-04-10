---
layout: default
title: Конфигурация Mnemos
permalink: /config/
lang: ru
alternate_url: /en/config/
lead: Справочник по переменным окружения Mnemos, сгруппированный по
  подсистемам.
---

# Конфигурация

Эта страница описывает основные переменные окружения Mnemos. Источник
истины для значений по умолчанию находится в `.env.example` и
`core/config.py`.

## Общие настройки

- `MNEMOS_ENV` - режим запуска. По умолчанию `development`.
- `MNEMOS_HOST` - адрес HTTP-сервера. По умолчанию `0.0.0.0`.
- `MNEMOS_PORT` - порт HTTP-сервера. По умолчанию `8000`.
- `MNEMOS_LOG_LEVEL` - уровень логирования. По умолчанию `INFO`.
- `MNEMOS_TIMEOUT_SECONDS` - общий таймаут для запросов. По умолчанию
  `10`.
- `MCP_SERVER_HOST` - адрес MCP-сервера. По умолчанию `0.0.0.0`.
- `MCP_SERVER_PORT` - порт MCP-сервера. По умолчанию `9000`.
- `MCP_SERVER_TRANSPORT` - транспорт MCP-сервера. По умолчанию `stdio`.

## База данных

- `POSTGRES_HOST` - хост PostgreSQL. По умолчанию `localhost`.
- `POSTGRES_PORT` - порт PostgreSQL. По умолчанию `5432`.
- `POSTGRES_DB` - имя базы данных. По умолчанию `mnemos`.
- `POSTGRES_USER` - пользователь базы данных. По умолчанию `postgres`.
- `POSTGRES_PASSWORD` - пароль базы данных. По умолчанию `postgres`.
- `DATABASE_URL` - полный URL базы данных. Если задан, он имеет
  приоритет над отдельными `POSTGRES_*` значениями.

## Qdrant

- `QDRANT_URL` - адрес Qdrant. По умолчанию `http://localhost:6333`.
- `QDRANT_VECTOR_SIZE` - размер вектора. По умолчанию `1536`.
- `QDRANT_TIMEOUT_SECONDS` - таймаут для Qdrant. По умолчанию `5`.

## Embeddings

- `EMBEDDING_MODEL` - модель эмбеддингов. По умолчанию
  `openai/text-embedding-3-small`.
- `EMBEDDING_BASE_URL` - OpenAI-compatible endpoint для эмбеддингов. По
  умолчанию `https://openrouter.ai/api/v1`.
- `EMBEDDING_API_KEY` - API key для embedding-провайдера.
- `EMBEDDING_TIMEOUT_SECONDS` - таймаут для embedding-запросов. По
  умолчанию `10`.

## Facts и reflections

- `FACT_LLM_MODEL` - модель для извлечения facts. По умолчанию
  `openai/gpt-4.1-mini`.
- `FACT_LLM_BASE_URL` - endpoint для fact LLM. По умолчанию
  `https://openrouter.ai/api/v1`.
- `FACT_LLM_API_KEY` - API key для fact LLM.
- `FACT_LLM_TIMEOUT_SECONDS` - таймаут для fact LLM. По умолчанию `20`.
- `FACT_MAX_FACTS_PER_ITEM` - максимум facts из одного исходника. По
  умолчанию `5`.
- `FACT_MIN_CHARS` - минимальная длина исходного текста для fact
  extraction. По умолчанию `10`.
- `FACT_MAX_CHARS` - максимальная длина текста для fact extraction. По
  умолчанию `300`.
- `REFLECTION_LLM_MODEL` - модель для reflections. По умолчанию
  `openai/gpt-4.1-mini`.
- `REFLECTION_LLM_BASE_URL` - endpoint для reflection LLM. По
  умолчанию `https://openrouter.ai/api/v1`.
- `REFLECTION_LLM_API_KEY` - API key для reflection LLM.
- `REFLECTION_LLM_TIMEOUT_SECONDS` - таймаут для reflection LLM. По
  умолчанию `20`.
- `REFLECTION_MAX_PER_THEME` - максимум reflections на одну тему. По
  умолчанию `5`.
- `REFLECTION_MIN_CHARS` - минимальная длина текста для reflection
  extraction. По умолчанию `20`.
- `REFLECTION_MAX_CHARS` - максимальная длина текста для reflection
  extraction. По умолчанию `300`.

## Wiki

- `WIKI_OUTPUT_DIR` - директория для сгенерированных wiki-страниц. По
  умолчанию `data/wiki`.
- `WIKI_SCHEMA_PATH` - путь к YAML-схеме wiki. По умолчанию
  `data/wiki_schema.yaml`.
- `WIKI_LLM_TIMEOUT_SECONDS` - таймаут для wiki LLM. По умолчанию `20`.
- `WIKI_MAX_PAGE_CHARS` - максимальная длина одной wiki-страницы. По
  умолчанию `5000`.
- `WIKI_MIN_FACTS_PER_PAGE` - минимальное число facts для генерации
  страницы. По умолчанию `3`.
- `WIKI_FACTS_KINDS` - kinds, которые wiki может использовать как facts.
- `WIKI_REFLECTIONS_KINDS` - kinds, которые wiki может использовать как
  reflections.

### Как работает wiki LLM

Wiki использует те же настройки, что и reflections, если отдельные
значения не заданы. Это значит, что по умолчанию:

- `WIKI_LLM_MODEL` берётся из `REFLECTION_LLM_MODEL`
- `WIKI_LLM_BASE_URL` берётся из `REFLECTION_LLM_BASE_URL`
- `WIKI_LLM_API_KEY` берётся из `REFLECTION_LLM_API_KEY`

Практически это удобно, когда reflections и wiki должны работать через
один и тот же OpenAI-compatible провайдер.

### Mock mode и real LLM mode

В локальной разработке можно использовать mock-режим, если вы не хотите
подключать внешний LLM-провайдер. В таком режиме генерация остаётся
детерминированной или упрощённой, чтобы можно было проверять pipeline и
тесты без API-ключей.

Реальный LLM-режим нужен, когда вы хотите фактически генерировать facts,
reflections или wiki-страницы через внешний модельный endpoint. Для
него обычно нужны:

- `*_BASE_URL`
- `*_API_KEY`
- подходящая модель

## Практический набор

Если вам нужен минимальный локальный запуск, обычно достаточно:

- `POSTGRES_*`
- `QDRANT_URL`
- `EMBEDDING_*`
- `FACT_LLM_*`
- `REFLECTION_LLM_*`

Если вы хотите включить wiki, добавьте:

- `WIKI_OUTPUT_DIR`
- `WIKI_SCHEMA_PATH`
- при необходимости `WIKI_LLM_TIMEOUT_SECONDS`
- при необходимости `WIKI_MAX_PAGE_CHARS`
- при необходимости `WIKI_MIN_FACTS_PER_PAGE`

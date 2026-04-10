---
layout: default
title: Mnemos Configuration
permalink: /en/config/
lang: en
alternate_url: /config/
lead: Reference for Mnemos environment variables, grouped by subsystem.
---

# Configuration

This page documents the main Mnemos environment variables. The source of
truth for defaults is `.env.example` and `core/config.py`.

## General settings

- `MNEMOS_ENV` - runtime mode. Default: `development`.
- `MNEMOS_HOST` - HTTP server address. Default: `0.0.0.0`.
- `MNEMOS_PORT` - HTTP server port. Default: `8000`.
- `MNEMOS_LOG_LEVEL` - log level. Default: `INFO`.
- `MNEMOS_TIMEOUT_SECONDS` - global request timeout. Default: `10`.
- `MCP_SERVER_HOST` - MCP server address. Default: `0.0.0.0`.
- `MCP_SERVER_PORT` - MCP server port. Default: `9000`.
- `MCP_SERVER_TRANSPORT` - MCP transport. Default: `stdio`.

## Database

- `POSTGRES_HOST` - PostgreSQL host. Default: `localhost`.
- `POSTGRES_PORT` - PostgreSQL port. Default: `5432`.
- `POSTGRES_DB` - database name. Default: `mnemos`.
- `POSTGRES_USER` - database user. Default: `postgres`.
- `POSTGRES_PASSWORD` - database password. Default: `postgres`.
- `DATABASE_URL` - full database URL. If set, it overrides the separate
  `POSTGRES_*` values.

## Qdrant

- `QDRANT_URL` - Qdrant endpoint. Default: `http://localhost:6333`.
- `QDRANT_VECTOR_SIZE` - vector size. Default: `1536`.
- `QDRANT_TIMEOUT_SECONDS` - Qdrant timeout. Default: `5`.

## Embeddings

- `EMBEDDING_MODEL` - embedding model. Default:
  `openai/text-embedding-3-small`.
- `EMBEDDING_BASE_URL` - OpenAI-compatible embedding endpoint. Default:
  `https://openrouter.ai/api/v1`.
- `EMBEDDING_API_KEY` - API key for the embedding provider.
- `EMBEDDING_TIMEOUT_SECONDS` - embedding request timeout. Default: `10`.

## Facts and reflections

- `FACT_LLM_MODEL` - model for fact extraction. Default:
  `openai/gpt-4.1-mini`.
- `FACT_LLM_BASE_URL` - endpoint for the fact LLM. Default:
  `https://openrouter.ai/api/v1`.
- `FACT_LLM_API_KEY` - API key for the fact LLM.
- `FACT_LLM_TIMEOUT_SECONDS` - fact LLM timeout. Default: `20`.
- `FACT_MAX_FACTS_PER_ITEM` - maximum facts per source item. Default:
  `5`.
- `FACT_MIN_CHARS` - minimum input length for fact extraction. Default:
  `10`.
- `FACT_MAX_CHARS` - maximum input length for fact extraction. Default:
  `300`.
- `REFLECTION_LLM_MODEL` - model for reflections. Default:
  `openai/gpt-4.1-mini`.
- `REFLECTION_LLM_BASE_URL` - endpoint for the reflection LLM.
  Default: `https://openrouter.ai/api/v1`.
- `REFLECTION_LLM_API_KEY` - API key for the reflection LLM.
- `REFLECTION_LLM_TIMEOUT_SECONDS` - reflection LLM timeout. Default:
  `20`.
- `REFLECTION_MAX_PER_THEME` - maximum reflections per theme. Default:
  `5`.
- `REFLECTION_MIN_CHARS` - minimum input length for reflection
  extraction. Default: `20`.
- `REFLECTION_MAX_CHARS` - maximum input length for reflection
  extraction. Default: `300`.

## Wiki

- `WIKI_OUTPUT_DIR` - directory for generated wiki pages. Default:
  `data/wiki`.
- `WIKI_SCHEMA_PATH` - path to the wiki YAML schema. Default:
  `data/wiki_schema.yaml`.
- `WIKI_LLM_TIMEOUT_SECONDS` - wiki LLM timeout. Default: `20`.
- `WIKI_MAX_PAGE_CHARS` - maximum size of one wiki page. Default:
  `5000`.
- `WIKI_MIN_FACTS_PER_PAGE` - minimum facts required to generate a
  page. Default: `3`.
- `WIKI_FACTS_KINDS` - kinds that wiki can use as facts.
- `WIKI_REFLECTIONS_KINDS` - kinds that wiki can use as reflections.

### How the wiki LLM works

Wiki uses the same settings as reflections when separate values are not
provided. By default:

- `WIKI_LLM_MODEL` is taken from `REFLECTION_LLM_MODEL`
- `WIKI_LLM_BASE_URL` is taken from `REFLECTION_LLM_BASE_URL`
- `WIKI_LLM_API_KEY` is taken from `REFLECTION_LLM_API_KEY`

This is useful when reflections and wiki should run through the same
OpenAI-compatible provider.

### Mock mode and real LLM mode

In local development you can use a mock mode if you do not want to
connect to an external LLM provider. In that mode, generation stays
deterministic or simplified so you can verify the pipeline and tests
without API keys.

Real LLM mode is what you use when you want actual fact extraction,
reflections, or wiki page generation through an external model
endpoint. In practice, it usually needs:

- `*_BASE_URL`
- `*_API_KEY`
- a suitable model

## Practical baseline

For a minimal local setup, you usually need:

- `POSTGRES_*`
- `QDRANT_URL`
- `EMBEDDING_*`
- `FACT_LLM_*`
- `REFLECTION_LLM_*`

If you want wiki enabled, add:

- `WIKI_OUTPUT_DIR`
- `WIKI_SCHEMA_PATH`
- optionally `WIKI_LLM_TIMEOUT_SECONDS`
- optionally `WIKI_MAX_PAGE_CHARS`
- optionally `WIKI_MIN_FACTS_PER_PAGE`

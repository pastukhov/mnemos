# Rewrite README Brief

## Goal

Rewrite the existing `README.md` to make it clear, concise, and oriented
toward users rather than internal development history.

The current README is confusing because:

- It starts with development phases instead of explaining the project.
- It exposes architecture and repository structure before explaining usage.
- It lacks quickstart instructions.
- It lacks concrete API examples.
- It overloads readers with environment variables.

Your task is to rewrite the README while preserving all important technical
information but reorganizing it into a clearer structure.

## Important Rules

- Keep the document concise.
- Prefer examples over abstract descriptions.
- Make the first 2 minutes of reading enough for someone to run the system.
- Move development history (phases) to the end as a roadmap.
- Preserve all existing functionality descriptions.

## Target Structure of the New README

1. Project Title
1. Short Description

   2-3 sentences explaining what the system is and what problem it solves.

1. Features

   Bullet list describing key capabilities (memory ingestion, semantic search,
   MCP support, etc.).

1. Quick Start

   Minimal steps required to run the system locally.

   Example:

   ```sh
   docker compose up -d
   curl http://localhost:8000/health
   ```

1. Basic Usage

   Example: Add memory

   ```sh
   curl -X POST http://localhost:8000/memory/items \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "personal",
       "statement": "Example memory"
     }'
   ```

   Example: Query memory

   ```sh
   curl -X POST http://localhost:8000/memory/query \
     -H "Content-Type: application/json" \
     -d '{
       "query": "example"
     }'
   ```

1. Architecture Overview

   Short explanation of system components:

   - API service
   - PostgreSQL
   - Vector database
   - LLM extraction
   - MCP integration

1. Repository Structure

   Short explanation of key directories.

1. Pipelines / Internal Processing

   Explain ingestion, extraction, reflection, governance.

1. Configuration

   Split configuration into:

   - Minimal required variables
   - Advanced configuration

1. Development

    How to run locally, tests, etc.

1. Roadmap

    Move the Phase 1-6 descriptions here.

## Style Guidelines

- Use short sections.
- Avoid long paragraphs.
- Use code blocks for examples.
- Use tables where helpful.

## Output

Produce a fully rewritten `README.md` that replaces the existing file.
Do not summarize; produce the full document.

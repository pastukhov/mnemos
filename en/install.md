---
layout: default
title: Install
permalink: /en/install/
lang: en
alternate_url: /install/
lead: Step-by-step setup that works on any platform with Docker.
---

# Install

## What you get at the end

After following this guide, Mnemos will be running locally with:

- API at `http://localhost:8000`
- MCP endpoint at `http://localhost:9000/mcp`
- web UI at `http://localhost:8000/`
- review queue, shortlist workflow, and grouped review sessions in the UI

## Before you start

- a Linux or Windows computer
- Docker Desktop or Docker Engine with Compose
- access to Terminal, PowerShell, or another shell
- a local copy of the `mnemos` project folder

If Docker is not installed yet:

- Docker Desktop is convenient on Windows and macOS
- Docker Engine + Docker Compose works well on Linux

## Step 1. Start Docker

If you use Docker Desktop, launch it and wait until it is ready.

> **Important**: Mnemos will not start while Docker is unavailable.

## Step 2. Open a shell

Any of these works:

- Terminal or another shell
- Linux terminal
- PowerShell or Windows Terminal on Windows

## Step 3. Move into the project directory

If the project is already downloaded:

```sh
cd /path/to/mnemos
```

Example:

```sh
cd /Users/yourname/Downloads/mnemos
```

## Step 4. Prepare the environment file

Copy the example configuration:

```sh
cp .env.example .env
```

That creates the working `.env` file used by Mnemos at startup.

## Step 5. Python local environment

You do **not** need this step for end-user Docker installation.

`make venv` is for development work, local CLI usage, and tests outside Docker.

## Step 6. Start Mnemos

Run:

```sh
docker compose up -d --build
```

This will:

- build the project containers
- start PostgreSQL, Qdrant, and Mnemos itself
- make the service available locally

The first startup is usually slower than the next ones.

## Step 7. Verify that it works

Open these in the browser:

- `http://localhost:8000/`
- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`

You can also run:

```sh
make smoke
```

## If you need facts and reflections

These features usually require an external LLM provider.

Fill in these `.env` variables:

- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `FACT_LLM_BASE_URL`
- `FACT_LLM_API_KEY`
- `FACT_LLM_MODEL`
- `REFLECTION_LLM_BASE_URL`
- `REFLECTION_LLM_API_KEY`
- `REFLECTION_LLM_MODEL`

If you want local mock mode:

```sh
cp .env.local-mock.example .env
docker compose -f docker-compose.yml \
  -f docker-compose.local-mock.yml \
  up -d --build
```

## What to check next

- [Open the user guide](/mnemos/en/guide/)
- [Read the FAQ](/mnemos/en/faq/)
- [Open the Russian README](/mnemos/README_ru.md)

After startup it is useful to check:

- `GET /memory/schema` to see allowed values and limits
- the review tab in the web UI
- the MCP flow with `get_schema_info` and
  `shortlist_memory_items` if you connect an agent

## If you want to connect an agent

After startup, you can use this MCP endpoint:

```text
http://localhost:9000/mcp
```

Or install the repository skill:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

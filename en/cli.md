---
layout: default
title: CLI Reference
permalink: /en/cli/
lang: en
alternate_url: /cli/
lead: Reference for `mnemos` commands with usage examples and key
  flags.
---

# CLI Reference

This reference describes the `mnemos` commands in `cli.py`. The examples
below reflect the actual command tree and the key flags.

## Quick Overview

| Command | Purpose |
| --- | --- |
| `ingest` | Import source material into memory |
| `extract` | Extract `fact` items from long `raw` material |
| `reflect` | Build `reflection` items from facts |
| `candidates` | List and moderate candidates |
| `mcp-server` | Start the MCP server |

## `ingest`

Imports data into memory.

Syntax:

```sh
mnemos ingest questionnaire <path>
mnemos ingest notes <path>
mnemos ingest all
```

Subcommands:

- `questionnaire <path>` - load questionnaire answers from a file
- `notes <path>` - load notes from a file
- `all` - run the full ingest pipeline

Examples:

```sh
mnemos ingest questionnaire data/survey.md
mnemos ingest notes data/notes.md
mnemos ingest all
```

## `extract`

Extracts facts from stored `raw` items.

Syntax:

```sh
mnemos extract facts [--domain DOMAIN]
```

Flags:

- `--domain DOMAIN` - limit extraction to one memory domain
  (`self` by default)

Example:

```sh
mnemos extract facts --domain self
```

## `reflect`

Builds broader conclusions from extracted facts.

Syntax:

```sh
mnemos reflect build [--domain DOMAIN] [--theme THEME]
```

Flags:

- `--domain DOMAIN` - limit reflection building to one memory domain
  (`self` by default)
- `--theme THEME` - optionally narrow the build to one theme

Example:

```sh
mnemos reflect build --domain self --theme workstyle
```

## `candidates`

Lists, accepts, and rejects candidates before they enter accepted memory.

Syntax:

```sh
mnemos candidates list [--status STATUS] [--domain DOMAIN] [--kind KIND]
mnemos candidates accept <candidate_id>
mnemos candidates reject <candidate_id> --reason REASON
```

Subcommands:

- `list` - print candidate records
- `accept <candidate_id>` - accept a candidate and try to merge it into
  memory
- `reject <candidate_id>` - reject a candidate with a reason

Flags:

- `--status STATUS` - filter by status
- `--domain DOMAIN` - filter by memory domain
- `--kind KIND` - filter by record kind
- `--reason REASON` - required rejection reason

Examples:

```sh
mnemos candidates list --status pending
mnemos candidates accept 123
mnemos candidates reject 123 --reason "too vague"
```

## Wiki pages

Wiki pages are no longer exposed as a CLI command. Use the web UI or
API instead:

- `GET /api/wiki/pages` - list pages
- `GET /api/wiki/pages/{name}` - read a page
- `POST /api/wiki/pages/{name}/regenerate` - regenerate a page

## `mcp-server`

Starts the MCP server for agent connections.

Syntax:

```sh
mnemos mcp-server [--transport TRANSPORT] [--host HOST] [--port PORT]
```

Flags:

- `--transport TRANSPORT` - `stdio`, `streamable-http`, `http`, or `sse`
- `--host HOST` - host for network transports
- `--port PORT` - port for network transports

Example:

```sh
mnemos mcp-server --transport streamable-http --host 0.0.0.0 --port 9000
```

## Recommended Order

- Load data with `ingest`.
- Extract facts with `extract`.
- Build reflections with `reflect`.
- Review new knowledge with `candidates`.
- Access readable wiki pages through the web UI and API.
- Expose memory to agents with `mcp-server`.

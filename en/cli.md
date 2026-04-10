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
| `wiki` | Build, lint, or query the wiki |
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

## `wiki`

Builds and checks wiki pages.

Syntax:

```sh
mnemos wiki build [--domain DOMAIN] [--page PAGE]
mnemos wiki lint [--domain DOMAIN] [--fix]
mnemos wiki query <question> [--domain DOMAIN]
```

Subcommands:

- `build` - generate wiki pages from facts and reflections
- `lint` - check the wiki for integrity and freshness issues
- `query` - ask a question against the generated wiki

Flags:

- `--domain DOMAIN` - limit the operation to one memory domain
- `--page PAGE` - build only one wiki page
- `--fix` - try to fix issues found by lint

Examples:

```sh
mnemos wiki build
mnemos wiki build --domain self --page career
mnemos wiki lint --fix
mnemos wiki query "What are my workstyle preferences?"
```

Note:

`mnemos wiki lint` and `mnemos wiki query` currently print placeholders.
The full implementation is scheduled for a later phase.

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
- Generate readable pages with `wiki build`.
- Expose memory to agents with `mcp-server`.

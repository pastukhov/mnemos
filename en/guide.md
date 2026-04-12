---
layout: default
title: User Guide
permalink: /en/guide/
lang: en
alternate_url: /guide/
lead: A practical explanation of what Mnemos is, who it is for, and how
  to use it without diving into internal implementation details.
---

# User Guide

Mnemos helps you collect knowledge about a person or project in one
place, find it semantically, and gradually turn raw notes into more
useful conclusions. In short, it is memory for both humans and AI.

## What Mnemos is for

Mnemos becomes useful when you accumulate a lot of scattered information:

- interview answers and questionnaires
- working notes
- observations about habits, preferences, and decisions
- conclusions derived from those materials

Instead of a chaotic set of files, Mnemos lets you:

- keep information in one system
- search by meaning, not only by exact wording
- separate raw material from reviewed facts
- control new records before they reach long-term memory

## What Mnemos can do

### Store records

You can add notes, raw records, facts, decisions, and other items.

### Search semantically

If you search for automation or observability, Mnemos can find related
records even if they use different words.

### Import questionnaires and notes

Mnemos can ingest prepared files and turn them into memory records.

### Extract facts

From longer texts, the system can derive short factual statements.

### Build reflections

From several facts, the system can assemble a broader pattern.

### Build wiki pages

Mnemos can synthesize human-readable wiki pages from facts and
reflections. The generated pages are cached in the database and exposed
through the web UI and API as connected documentation that is easy to
read and refresh.

### Review new knowledge

If an agent proposes a new record, it can first enter a review queue and
be accepted or rejected later.

### Build a shortlist before writing

Mnemos can validate a batch of candidate facts before writing them.
This is useful for interviews and long sessions where one answer
produces multiple claims.

Shortlist helps you see:

- whether candidates are valid
- which schema constraints apply
- whether dedupe hints exist
- what the resulting review session will look like

## Information lifecycle

1. You add a note or load questionnaire answers.
1. The source text is stored as `note` or `raw`.
1. Candidate facts can be derived from the source note.
1. Those facts can be checked through shortlist before writing.
1. Candidates then enter a review session.
1. After acceptance they become long-term memory.
1. Facts and reflections can then be assembled into wiki pages that are
   cached in the database and available through the web UI and API.
1. If a new fact refines an older one, `upsert` can mark the old record as `superseded`.

This matters because Mnemos does not mix raw data, conclusions, and
agent proposals into one undifferentiated pile.

## Core concepts

### Note

A note is raw material: a long answer, quote, draft, or work note.

### Fact

A fact is a short verifiable statement that can go through review and
become durable memory.

### Review session

A review session is a group of candidate items created within one work
session, for example one interview.

### Superseded

Superseded means an older record was replaced by a newer or more precise fact.

### Governance

Governance means an agent does not write everything directly into
accepted memory. New knowledge can first be inspected.

## Before you start

For local setup you need:

- a Linux or Windows machine
- Docker Desktop or Docker Engine with Compose
- access to Terminal, PowerShell, or another shell
- 15 to 20 minutes for the first startup

If you want fact extraction and reflections, you also need an
OpenAI-compatible provider key.

Next:

- [Install with Docker](/mnemos/en/install/)
- [FAQ](/mnemos/en/faq/)

## Connect Mnemos to an agent

Mnemos can act as memory for agentic systems.

After starting the stack, use this MCP endpoint:

```text
http://localhost:9000/mcp
```

An agent can then:

- search records in memory
- fetch context on a topic
- save new notes
- retrieve schema info before writing
- build a shortlist before propose
- inspect review sessions
- propose facts and reflections as candidates

This matters because an agent should not write every claim directly into
accepted memory.

## Practical interview workflow

If you are building a user profile or processing a long interview, a
good workflow is:

1. save long answers as `note`
1. extract candidate facts from the note
1. run shortlist before writing
1. inspect duplicates and provenance
1. send confirmed candidates into a review session
1. open the wiki in the web UI or use the API to read or regenerate the
   resulting cached page
1. use `upsert` when a new fact should replace an older profile fact

## Which skill to use

The repository provides the installable skill:

```text
skills/mnemos-memory
```

It guides an agent on when to:

- search memory
- save a note
- propose a structured fact
- use memory context instead of blind raw search

Install it with:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

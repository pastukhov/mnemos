---
layout: default
title: FAQ
permalink: /en/faq/
lang: en
alternate_url: /faq/
lead: Short answers to the most common questions about Mnemos, setup,
  and daily use.
---

# FAQ

## What is Mnemos in simple terms

It is a memory system for AI. It helps store important knowledge and
return it to AI when needed.

## Is it a chatbot

No. It is not the chat itself, but a memory layer that can be connected
to chats, agents, and applications.

## Why is it better than ordinary notes

Notes are useful for humans. Mnemos also makes knowledge usable for AI:
it can be searched semantically, structured, and accessed programmatically.

## Do I need technical experience

For the first setup, yes, you still need a terminal and Docker Desktop.
After startup, a web UI is available, but the fully non-technical path
is still evolving.

## Do I need Python and `make venv` to use it

No, not for the end-user Docker setup.

`make venv` is for development: local CLI usage, tests, and working on
the code outside Docker.

## Can I keep the data on my own infrastructure

Yes. The project is designed for local deployment and control over your
own environment.

## Can I validate new knowledge before adding it

Yes. That is what candidates, preview/validate, shortlist, and review
workflow are for.

## What is Wiki in Mnemos

It is a layer of readable markdown pages that Mnemos assembles from
facts and reflections. It lets you read memory as documentation, not
just search it.

## Where are wiki pages stored

By default, they are written to `data/wiki`. You can change that with
`WIKI_OUTPUT_DIR`, and `WIKI_SCHEMA_PATH` defines the page structure.

## Do I need an LLM for Wiki

Yes, for generating and updating wiki pages. No, for reading pages that
have already been generated.

## What is the difference between a note and a fact

`note` is raw material: a long answer, draft, quote, or working note.

`fact` is a short verifiable statement suitable for durable memory and review.

## What should I do with long interviews

Save them as `note`, then build a shortlist of candidate facts, and only
after that send them into a review session.

## What is a review session

It is a batch of candidates linked to one session, for example one interview.
That makes it easier to review 10 to 20 facts together.

## What does superseded mean

It is the status of an older record that was replaced by a newer fact
through `upsert`. It remains in history but is no longer the primary memory.

## Do I need to install PostgreSQL separately

No. In local mode PostgreSQL runs inside Docker.

## Do I need to install Qdrant separately

No. It also starts through Docker Compose.

## Can I run it on other operating systems

Yes. If Docker Compose is available, Mnemos can run on Windows and Linux.

## What should I open after startup

Main user address:

- `http://localhost:8000/`

Health checks:

- `http://localhost:8000/health/live`
- `http://localhost:8000/health/ready`

## Can I do everything with the mouse

Not yet. Initial setup and some administrative actions still require a terminal.

## What if Docker Desktop is not running

1. Open Docker Desktop.
1. Wait for it to finish starting.
1. Retry the start command.

## How do I connect Mnemos to an agent

Use the MCP endpoint:

```text
http://localhost:9000/mcp
```

Or install the repository skill:

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

The agent also gets dedicated tools such as `get_schema_info`,
`validate_memory_item`, `shortlist_memory_items`, and
`list_review_sessions`.

## Where should I go next

- [Home](/mnemos/en/)
- [About](/mnemos/en/about/)
- [User guide](/mnemos/en/guide/)
- [Install](/mnemos/en/install/)

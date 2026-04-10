---
layout: default
title: Wiki
permalink: /en/wiki/
lang: en
alternate_url: /wiki/
lead: An automatically generated wiki that turns facts and reflections
  into readable markdown pages.
---

# Wiki

## What LLM Wiki is

LLM Wiki is a documentation layer that Mnemos generates from extracted
facts and reflections. It makes memory useful not only for search and
agents, but also for human reading.

Instead of a scattered set of records, you get a connected library of
pages that can grow together with memory.

## How it works

1. You add raw material: notes, answers, texts, or other source records.
1. Mnemos extracts facts and builds reflections.
1. The `mnemos wiki build` command reads the schema and decides which
   pages to generate.
1. The LLM synthesizes markdown from facts, reflections, and, when
   available, the current page content.
1. The result is written as regular `.md` files.

This keeps the source of truth separate from the human-readable form.

## How to run it

Basic command:

```text
mnemos wiki build
```

You can also build pages selectively when you only need part of the
wiki refreshed. Exact filters depend on the CLI implementation, but the
main workflow always starts with `wiki build`.

## How the schema works

The `wiki_schema.yaml` file defines which pages should be generated and
which filters should be used to gather content.

A schema usually defines:

- page name
- page title
- scope and description
- domain filters
- kinds and themes that fit the page

The default schema can produce pages such as career, values, workstyle,
goals, and key decisions.

## Example output

```markdown
---
title: Career and skills
generated_at: 2026-04-10T12:00:00Z
source_fingerprint: abc123
facts_count: 12
reflections_count: 3
---

# Career and skills

## Summary

This page gathers facts about professional experience, skills, and work
preferences.

## Main themes

- experience in specific roles
- strengths and skills
- work preferences
```

## What comes next

Wiki can serve as a layer for reading, navigation, and further knowledge
growth. It does not replace facts and reflections; it makes them easier
for people to consume.

---
layout: default
title: About Mnemos
permalink: /en/about/
lang: en
alternate_url: /about/
lead: A complete description of the project, its goals, use cases, and
  operating principles.
---

# About Mnemos

## What Mnemos is

Mnemos is a memory system for AI. It helps you store important knowledge
and return it to AI when it matters.

It is not a chatbot and not a standalone LLM. It is a memory layer that
can be connected to chats, agents, and applications so they do not start
from zero on every request.

---

## Who it is for

Mnemos fits people, teams, and products that need durable context for AI work.

### For individuals

Store important facts about yourself, your goals, habits, plans, and
preferences so AI does not need the same explanation every time.

### For teams

Give AI durable context about team processes, vocabulary, rules, and
accumulated knowledge.

### For products

Add memory to AI features so responses are more personalized, precise,
and useful.

---

## What problem it solves

Most AI tools respond well inside one dialog but lose context quickly.
Important details remain in notes, chats, documents, and the user's head.

That leads to repetition, correction cycles, and wasted time rebuilding context.

- AI forgets agreements and preferences
- knowledge drifts across many sources
- answer provenance is often unclear
- adding new facts safely is hard

---

## How Mnemos addresses it

Mnemos stores facts, notes, and reflections in a structured form,
indexes them for search, and gives AI access through API and MCP.

As a result, AI gets more than word matching. It gets memory that can be
updated, searched, reviewed, and improved over time.

### Structured storage

Memory is stored in PostgreSQL as explicit records rather than as a pile
of conversations.

### Semantic search

Qdrant helps retrieve relevant context by meaning, not only by exact words.

### Governed memory updates

New facts can go to review instead of entering memory immediately.

### Preview and shortlist before write

Before writing, you can inspect a candidate fact, schema constraints,
dedupe hints, and a preview without creating a record.

### Review sessions and provenance

Candidates can be grouped by interview or work session, and review cards
show which note and source excerpt a fact came from.

### Fact extraction and reflections

The system can derive more durable knowledge from raw notes.

### Integration with AI agents

Mnemos connects to agents and applications through REST API and MCP.

---

## How it works

1. **Load your source material**  
   That can be notes, questionnaires, text files, or manual entries.

1. **Mnemos turns it into memory**  
   The system stores notes, extracts facts, and builds links across notes,
   facts, and reflections.

1. **AI reads memory during work**  
   When an agent needs context, Mnemos returns relevant records in a
   structured form.

1. **You keep quality under control**  
   New knowledge can go through shortlist, review sessions, dedupe hints,
   and only then be accepted.

---

## What you can store

- personal preferences and habits
- project information and goals
- important decisions and agreements
- verified facts derived from notes
- reflections built from multiple facts
- pending candidates waiting for review
- superseded records replaced by a newer fact

---

## Why it is more reliable than a chat

In a normal chat, context disappears quickly and the source of an answer
is often opaque. In Mnemos, memory is stored separately from any one conversation.

That means it can be updated, searched, reviewed, exported, and reused
across multiple AI tools.

- memory is separate from a single session
- data stays in your infrastructure
- semantic search is built in
- review protects new knowledge
- the architecture is explicit and open source

---

## How to connect Mnemos to an agent

Mnemos can be connected to agents through the MCP server.

After you start the stack with Docker Compose, you get:

- API: `http://localhost:8000`
- MCP endpoint: `http://localhost:9000/mcp`

Typical flow:

1. start Mnemos locally
1. connect the agent to the MCP endpoint
1. let the agent search memory, fetch context, and save notes
1. send stronger claims through governance as candidates

The repository also provides the installable `mnemos-memory` skill so an
agent uses the endpoint through the correct workflow.

```sh
npx skills add https://github.com/pastukhov/mnemos --skill mnemos-memory
```

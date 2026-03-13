---
layout: default
title: Mnemos
permalink: /en/
lang: en
alternate_url: /
lead: Memory for your AI assistants, presented in the same visual language
  as the application UI.
---

# Mnemos

## Memory for your AI assistants

Mnemos helps you store important facts, notes, and reflections so AI can
work from accumulated knowledge instead of guesses. It is a memory layer
between your data and your AI tools.

- [What it is](/mnemos/en/about/)
- [User guide](/mnemos/en/guide/)
- [Install with Docker](/mnemos/en/install/)

> Open source. FastAPI + PostgreSQL + Qdrant + MCP.

---

## What Mnemos solves

Most AI tools answer well inside a single conversation, but they lose
context quickly. Important details remain scattered across notes,
documents, chats, and the user's head.

Mnemos exists so that:

- AI does not forget important facts and preferences
- knowledge does not fragment across many sources
- you can find relevant context semantically
- new knowledge goes through review instead of chaotic writes
- long interviews can be preserved as notes without fragile limits
- similar facts can be checked through shortlist before writing
- memory can be connected to agents, not just read manually

---

## How it works

1. You bring notes, questionnaires, text, or manual entries into the system.
1. Mnemos stores long notes as source material.
1. The system can build a shortlist of candidate facts without writing them.
1. Review sessions let you inspect candidates as a batch.
1. AI receives the needed context through API or MCP.

[More about how Mnemos works](/mnemos/en/about/#how-it-works)

---

## Where it is useful

### Personal AI assistant

So an assistant can remember your goals, habits, work style, and preferences.

### Team knowledge base

So AI can work with team processes, terminology, and accumulated experience.

### AI inside a product

So answers can be personalized with known user context.

### AI agents and workflows

So an agent can search memory, save notes, and propose facts through governance.

---

## Why it is better than an ordinary chat

- memory is separate from a single chat session
- data stays in your own infrastructure
- semantic search is built in
- new knowledge goes through review
- review sessions support interview-style batch checks
- upsert mode can update durable profile facts
- the architecture is open and the code is open source
- an MCP server is available for agent integration

---

## Connect it to an agent

Mnemos is not only a local UI. It can also serve as memory for agentic systems.

Typical setup:

- start Mnemos with Docker Compose
- use the MCP endpoint `http://localhost:9000/mcp`
- connect that endpoint in your agent or MCP client

If you use Codex CLI, the repository also provides the installable
`mnemos-memory` skill for correct memory workflows.

- [More about agent integration](/mnemos/en/guide/#connect-mnemos-to-an-agent)

## Next step

If you want AI to stop starting from zero on every request, Mnemos gives
you a practical base: storage, search, fact extraction, and governed
memory updates.

- [Open the full overview](/mnemos/en/about/)
- [Open the guide](/mnemos/en/guide/)
- [See installation](/mnemos/en/install/)

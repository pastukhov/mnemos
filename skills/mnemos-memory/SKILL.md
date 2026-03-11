---
name: mnemos-memory
description: >
  Use this skill when working with the Mnemos memory MCP server for
  memory search, memory-aware answering, interviewing a user to capture
  knowledge, saving notes, proposing new memory items through
  governance, or retrieving context before responding. Triggers:
  mnemos, memory server, search memory, get context, save note, propose
  memory, interview into memory, capture knowledge, memory candidate,
  memory recall, user profile memory.
---

# Mnemos Memory

Use this skill when the task should read from or write to the Mnemos MCP server.

Mnemos tools available through MCP:

- `search_memory(query, domain?, top_k?)`
- `get_memory_item(item_id)`
- `get_context(query, domain?, top_k?)`
- `add_memory_note(text)`
- `propose_memory_item(statement, domain, kind, confidence?)`

## Default Workflow

For memory-aware answers:

1. If the user asks about prior preferences, prior facts, goals, work
   style, or project context, call `get_context` or `search_memory`
   first.
1. Use returned memory as supporting context, not as unquestionable
   truth.
1. If memory conflicts with the current user message, prefer the current
   message and mention the conflict briefly.

For saving new information:

1. Use `add_memory_note` for lightweight observations, quotes, or
   interview answers that should be preserved as notes.
1. Use `propose_memory_item` for more structured facts, decisions,
   tensions, tasks, or reflections that should go through governance.
1. Do not claim a proposed item is accepted memory unless the system
   explicitly confirms acceptance elsewhere.

## Interview Workflow

Use this when the user wants the agent to ask questions and capture answers in Mnemos.

1. Ask one focused question at a time.
1. After each answer, save the answer with `add_memory_note`.
1. If the answer is stable and specific enough to be a reusable fact,
   also call `propose_memory_item`.
1. Keep proposed facts atomic. Prefer one fact per proposal.
1. At the end, summarize:
   - what was saved as notes
   - what was proposed as structured memory
   - any open questions worth asking next

When turning an answer into a proposed fact:

- Keep the statement short and explicit.
- Avoid speculation, diagnosis, or personality claims that are not
  directly supported.
- Prefer statements like `User prefers direct communication.` over long
  narrative text.

## Tool Selection

Use `get_context` when:

- you want a short text block to ground your reply
- the user asked for advice or a summary that should consider prior
  memory

Use `search_memory` when:

- you want item-level results
- you expect to inspect ids, metadata, or individual entries

Use `get_memory_item` when:

- you already have an item id
- you need the full stored record for one item

Use `add_memory_note` when:

- saving raw interview answers
- saving temporary but useful observations
- preserving phrasing close to the user's own words

Use `propose_memory_item` when:

- the information is reusable as a stable fact, decision, tension, task,
  or reflection
- the item should go through governance before being treated as accepted
  memory

## Domain Heuristics

If the user does not specify a domain:

- use `self` for personal preferences, biography, goals, habits, values,
  relationships, work style
- use `project` for repo, product, architecture, backlog, design, roadmap
- use `operational` for runtime issues, incidents, infra, monitoring,
  deployment procedures
- use `interaction` for preferences about how the agent should
  collaborate in the current working relationship

## Good Patterns

Good note:

- `User said they want to spend one day per week on a startup.`

Good proposed fact:

- `User is willing to spend one day per week on a startup.`

Bad proposed fact:

- `User is finally ready to become a successful founder.`

## Safety Rules

- Do not store secrets, tokens, passwords, private keys, or credentials
  in Mnemos.
- Do not silently convert a vague answer into a strong factual claim.
- Do not use `propose_memory_item` for high-risk inferences unless the
  user clearly confirmed them.
- If uncertain, save a note instead of proposing a fact.

## Response Pattern

When you used Mnemos in a meaningful way, tell the user briefly what happened:

- searched memory
- saved a note
- proposed one or more items

Keep that status line short. The main reply should still focus on the user's task.

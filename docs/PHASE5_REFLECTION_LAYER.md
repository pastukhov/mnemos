# Mnemos - Phase 5: Reflection Layer

## Objective

Implement a reflection generation pipeline that derives higher-level
patterns from facts.

Phase 5 introduces the first synthesis layer in Mnemos.

The goal is to transform multiple atomic facts into structured
reflections.

Reflections are not raw facts.
They are higher-level, evidence-backed summaries of recurring patterns.

Each reflection must be linked to supporting facts.

## Architecture

Pipeline flow:

```text
raw memory
   │
   ▼
facts
   │
   ▼
reflection generation pipeline
   │
   ▼
reflections
   │
   ▼
vector index
```

Reflections must remain linked to the fact items that support them.

## Reflection Definition

A reflection is a higher-level statement derived from multiple facts.

Examples:

Good reflection:

- User prefers building automated systems instead of repetitive manual
  operations.
- User is energized by tasks that combine systems design and
  experimentation.
- User prefers decomposable, observable architectures.

Bad reflection:

- User is definitely an innovator.
- User has a unique personality.
- User is afraid of chaos.

Reflections must be grounded in evidence.
No diagnosis.
No moral judgment.
No speculative psychology.

## Pipeline Location

Create module:

```text
pipelines/reflect/
```

Files:

```text
build_reflections.py
reflection_schema.py
reflection_llm_client.py
reflection_runner.py
```

Optional future extension:

```text
detect_tensions.py
build_summaries.py
```

Do not implement optional files yet unless they are needed for clean
structure.

## Input Data

The pipeline must process `memory_items` where:

```text
domain = self
kind = fact
status = accepted
```

The reflection generator must work over groups of related facts.

## Fact Grouping

Before generating reflections, group facts into themes.

Initial themes may include:

- identity
- work_style
- motivation
- decision_style
- goals
- learning_style
- values

Grouping strategy for MVP:

1. first use fact metadata if available
1. if metadata topic is absent, group all facts into a single batch
1. keep implementation simple and deterministic

If topic metadata exists in source chain, preserve it.

## Reflection Requirements

Each reflection must:

- be supported by at least 2 facts
- be concise
- describe a stable pattern
- include confidence
- include evidence fact ids

Each reflection must NOT:

- be derived from a single fact
- contain direct diagnosis
- overstate confidence
- claim unsupported personal attributes

Good example:

```text
statement:
User prefers systems that reduce repetitive manual work and increase
automation.

evidence:
[fact_001, fact_007, fact_010]

confidence:
0.84
```

Bad example:

```text
statement:
User will definitely be happier in AI platform engineering.
```

This is advice or prediction, not reflection.

## Output Format

Each reflection becomes a new `memory_item`.

Example:

```text
domain: self
kind: reflection
statement: User prefers decomposable and observable systems.
confidence: 0.82
```

```text
metadata:
```

```json
{
  "source_type": "reflection_generation",
  "theme": "decision_style",
  "source_fact_ids": ["fact_001", "fact_004", "fact_009"]
}
```

```text
status:
accepted
```

## Reflection Schema

Create schema in:

```text
pipelines/reflect/reflection_schema.py
```

Expected LLM output format:

```json
{
  "reflections": [
    {
      "statement": "User prefers decomposable and observable systems.",
      "confidence": 0.82,
      "evidence_fact_ids": ["fact_001", "fact_004"]
    }
  ]
}
```

Schema fields:

- statement
- confidence
- evidence_fact_ids

Validation rules:

- evidence_fact_ids length >= 2
- confidence between 0 and 1
- statement length between 20 and 300 chars

## LLM Prompt

Prompt template:

```text
You are deriving evidence-backed reflections from a set of facts about a user.

Rules:

- Reflections must be supported by at least 2 facts
- Focus on stable patterns in behavior, work style, motivation, goals,
  learning style, and values
- Do not diagnose
- Do not speculate beyond evidence
- Do not produce advice
- Output JSON only

Input facts:
<list of facts with ids>

Return JSON with reflections.
```

## LLM Client

Create abstraction:

```text
reflection_llm_client.py
```

Interface:

```text
generate_reflections(facts: list[Fact]) -> list[Reflection]
```

The implementation must support OpenAI-compatible APIs.

Configuration variables:

```text
REFLECTION_LLM_MODEL
REFLECTION_LLM_BASE_URL
REFLECTION_LLM_API_KEY
```

The reflection model may be the same as the fact extraction model, but
must be configurable independently.

## Idempotency

Reflections must not be regenerated endlessly.

For MVP:

- generate reflections per theme
- if accepted reflections already exist for the same theme and same
  input fact set fingerprint, skip generation

Suggested strategy:

1. compute stable fingerprint from sorted fact ids
1. store it in reflection metadata:

```text
source_fact_fingerprint
```

1. skip if reflection set for this fingerprint already exists

This must make the pipeline safe to rerun.

## Storage

Each reflection becomes a new row in `memory_items`.

Fields:

```text
domain: self
kind: reflection
statement: <reflection text>
confidence: <llm confidence>
```

Metadata example:

```json
{
  "source_type": "reflection_generation",
  "theme": "motivation",
  "source_fact_ids": ["fact_001", "fact_007"],
  "source_fact_fingerprint": "..."
}
```

## Relations

Create relations between reflection and supporting facts.

Relation type:

```text
supported_by
```

Example:

```text
reflection_item -> supported_by -> fact_item
```

There must be one relation per supporting fact.

## Embedding

Reflections must be embedded and indexed.

Embedding input:

```text
reflection statement text
```

Store vectors in:

```text
mnemos_self
```

Reflections should become retrievable alongside facts and raw items.

## Retrieval Impact

After this phase, semantic retrieval should be able to return:

- raw memory
- facts
- reflections

Reflections should improve answers to high-level questions such as:

- What kind of work suits the user?
- What motivates the user?
- What architectural style does the user prefer?

## CLI Commands

Add commands:

```text
mnemos reflect build
mnemos reflect build --theme motivation
mnemos reflect build --domain self
```

The command must:

1. load accepted facts
1. group them
1. call reflection LLM
1. validate reflections
1. store reflections
1. create relations
1. index embeddings

## Logging

Log reflection generation progress.

Example logs:

```text
INFO reflection_generation facts_loaded=120
INFO reflection_generation themes_processed=6
INFO reflection_generation reflections_created=18
INFO reflection_generation skipped=3
```

Errors must include theme and batch fingerprint.

## Metrics

Expose Prometheus metrics:

```text
mnemos_reflection_runs_total
mnemos_reflections_created_total
mnemos_reflection_errors_total
mnemos_reflection_skipped_total
```

## Validation and Safety Rules

To prevent memory pollution:

- minimum 2 evidence facts per reflection
- maximum 5 reflections per theme batch
- reject empty output
- reject reflections shorter than 20 chars
- reject reflections longer than 300 chars
- reject duplicate reflection statements
- reject reflections with evidence ids not present in input set

Optional but recommended:

- deduplicate near-identical reflections by normalized statement

## Testing

Create tests:

```text
tests/test_reflection_pipeline.py
```

Test cases:

- generate reflection from multiple facts
- reject reflection with only one evidence fact
- create supported_by relations
- skip duplicate reflection generation
- vector indexing works
- reflection validation rejects malformed output

LLM calls must be mockable.

## Acceptance Criteria

Phase 5 is complete when:

- accepted facts can be processed into reflections
- reflections are generated using LLM
- reflections stored in PostgreSQL
- supported_by relations created between reflections and facts
- reflections indexed in Qdrant
- reflection pipeline is idempotent
- CLI command works
- metrics exposed
- tests pass

## Non-Goals

Phase 5 must NOT implement:

- summaries
- tensions / contradiction detection
- candidate write pipeline
- agent role-based retrieval policies

These belong to later phases.

## Final Task

Implement a reflection generation pipeline that derives evidence-backed
higher-level reflections from facts and stores them safely in Mnemos.

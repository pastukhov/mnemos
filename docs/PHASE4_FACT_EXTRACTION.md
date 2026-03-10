# Mnemos - Phase 4: Fact Extraction Pipeline

## Objective

Implement a pipeline that converts raw memory items into structured
facts.

Phase 4 introduces the first LLM-powered transformation layer in
Mnemos.

The goal is to extract atomic facts from raw knowledge sources.

Raw knowledge sources include:

- questionnaire answers
- notes
- interaction logs

The output of this phase must be structured memory items with:

```text
kind = fact
```

Facts must always reference their source evidence.

## Architecture

Pipeline flow:

```text
raw memory_items
      │
      ▼
fact extraction pipeline
      │
      ▼
fact memory_items
      │
      ▼
vector index
```

Facts remain linked to the raw items that generated them.

## Pipeline Location

Create module:

```text
pipelines/extract/
```

Files:

```text
extract_facts.py
fact_schema.py
fact_llm_client.py
fact_runner.py
```

## Input Data

The pipeline must process `memory_items` where:

```text
domain = self
kind = raw
```

These are typically questionnaire answers.

Example raw memory item:

```text
statement:

Question: What motivates you most in work?
Answer: Designing systems that reduce repetitive manual operations.
```

## Output Format

Each extracted fact must become a new `memory_item`.

Example fact:

```text
domain: self
kind: fact
```

```text
statement:

User prefers designing automated systems over performing repetitive
manual operations.
```

```text
metadata:
```

```json
{
  "source_type": "fact_extraction",
  "source_item_id": "<raw memory id>"
}
```

```text
confidence:

0.85
```

## Fact Requirements

Facts must follow strict rules.

Each fact must be:

- atomic
- concise
- supported by source text
- non-speculative

Facts must NOT:

- contain interpretation beyond the text
- contain multiple claims
- contain reasoning

Good example:

```text
User prefers designing automated systems.
```

Bad example:

```text
User is an innovative engineer who loves automation.
```

## Fact Schema

Create schema definition in:

```text
pipelines/extract/fact_schema.py
```

Fields:

```text
fact_statement
confidence
evidence_reference
```

Example JSON output from LLM:

```json
{
  "facts": [
    {
      "statement": "User prefers designing automated systems.",
      "confidence": 0.9
    }
  ]
}
```

## LLM Prompt

Prompt template:

```text
You are extracting factual statements from a knowledge source.

Rules:

- Extract only explicit facts
- Each fact must be atomic
- Do not interpret or speculate
- Output JSON only

Source text:

<Question and Answer text>

Return JSON with list of facts.
```

## LLM Client

Create abstraction:

```text
fact_llm_client.py
```

Interface:

```text
extract_facts(text: str) -> list[Fact]
```

The implementation must support OpenAI-compatible APIs.

Configuration variables:

```text
FACT_LLM_MODEL
FACT_LLM_BASE_URL
FACT_LLM_API_KEY
```

## Idempotency

Facts must not be generated twice.

Before inserting a fact:

Check `metadata.source_item_id`.

If facts already exist for that raw item:

Skip extraction.

## Storage

Each extracted fact becomes a new row in `memory_items`.

Fields:

```text
domain: self
kind: fact
statement: <fact text>
confidence: <llm confidence>
```

Metadata example:

```json
{
  "source_type": "fact_extraction",
  "source_item_id": "<raw memory id>"
}
```

## Relations

Create relation between fact and source item.

Relation type:

```text
derived_from
```

Example:

```text
fact_item -> derived_from -> raw_item
```

Use `memory_relations` table.

## Embedding

Facts must also be embedded and indexed.

Embedding input:

```text
fact statement text
```

Vector stored in Qdrant.

Collection:

```text
mnemos_self
```

## CLI Commands

Add commands:

```text
mnemos extract facts
mnemos extract facts --domain self
```

The command must:

1. fetch raw items
1. run extraction
1. store facts
1. index embeddings

## Logging

Log extraction progress.

Example logs:

```text
INFO fact_extraction items_processed=50
INFO fact_extraction facts_created=82
INFO fact_extraction skipped=10
```

Errors must be logged with raw item id.

## Metrics

Expose metrics:

```text
mnemos_fact_extraction_runs_total
mnemos_facts_created_total
mnemos_fact_extraction_errors_total
```

## Testing

Create tests:

```text
tests/test_fact_extraction_pipeline.py
```

Test cases:

- extract fact from questionnaire
- skip duplicate extraction
- create relation to source item
- vector indexing works

LLM calls must be mockable.

## Safety Rules

To prevent memory pollution:

- limit maximum facts per raw item (for example 5)
- reject empty fact lists
- reject facts shorter than 10 characters
- reject facts longer than 300 characters

## Acceptance Criteria

Phase 4 is complete when:

- raw memory items can be processed
- facts are generated using LLM
- facts stored in PostgreSQL
- relations created between fact and raw items
- facts indexed in Qdrant
- extraction pipeline is idempotent
- CLI command works
- metrics exposed
- tests pass

## Non-Goals

Phase 4 must NOT implement:

- reflections
- summaries
- candidate write pipeline
- agent role policies

Those belong to Phase 5 and Phase 6.

## Final Task

Implement a fact extraction pipeline that converts raw memory into
structured facts using an LLM and stores them safely in Mnemos.

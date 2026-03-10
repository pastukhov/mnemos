# Mnemos — Phase 2: Self Knowledge Ingestion

## Goal

Implement ingestion of self-knowledge sources into Mnemos memory.

This phase enables Mnemos to load human-written knowledge sources
(questionnaire and notes) and convert them into memory_items that are
stored in PostgreSQL and indexed in Qdrant.

This phase must be deterministic and reproducible.

No LLM processing yet.

---

## Scope

Phase 2 adds ingestion pipelines for:

- questionnaire (Markdown or YAML)
- notes (JSONL)

The pipeline must integrate with Phase 1 infrastructure.

Do NOT implement yet:

- fact extraction
- reflections
- agent roles
- candidate write pipeline

---

## Data Sources

Create directory:

data/raw/

Supported files:

- questionnaire.md
- questionnaire.yaml
- notes.jsonl

---

## Questionnaire Markdown Format

Primary supported format is Markdown.

Example:

## q01

Topic: identity

Question: What do you do professionally?

Answer:
I work as a DevOps/SRE engineer building automation
and observability systems.

---

## q02

Topic: motivation

Question: What motivates you most in work?

Answer:
Designing systems that reduce repetitive manual operations.

---

## Questionnaire YAML Format

YAML must also be supported.

Example:

- id: q01
  topic: identity
  question: What do you do professionally?
  answer: I work as a DevOps/SRE engineer building automation systems.
  created_at: 2026-03-10

---

## Notes Format

File: `data/raw/notes.jsonl`

Example:

```json
{"id":"note_1","text":"Idea: build AI agent orchestration layer","created_at":"2026-03-10T10:00:00Z"}
{"id":"note_2","text":"Prefer systems that can be decomposed into observable components","created_at":"2026-03-10T10:10:00Z"}
```

---

## Memory Mapping

Questionnaire answers must be stored as:

```text
domain: self
kind: raw
```

Statement format:

```text
Question: [question]
Answer: [answer]
```

Example statement:

```text
Question: What motivates you most in work?
Answer: Designing systems that reduce repetitive manual operations.
```

Metadata example:

```json
{
  "source_type": "questionnaire",
  "source_id": "q02",
  "topic": "motivation"
}
```

---

## Notes Mapping

Notes must be stored as:

```text
domain: self
kind: note
```

Statement:

```text
[note text]
```

Metadata example:

```json
{
  "source_type": "note",
  "source_id": "note_1"
}
```

---

## Ingestion Pipelines

Create module: `pipelines/ingest/`

Files:

- `load_questionnaire_md.py`
- `load_questionnaire_yaml.py`
- `load_notes.py`
- `ingest_runner.py`

---

## Markdown Loader Responsibilities

load_questionnaire_md.py must:

1. read markdown file
1. split sections by "## qXX"
1. extract:
   - id
   - topic
   - question
   - answer
1. generate memory_items
1. call memory service to persist
1. index embeddings

---

## YAML Loader Responsibilities

load_questionnaire_yaml.py must:

1. read YAML
1. validate schema
1. generate memory_items
1. persist and index

---

## Notes Loader Responsibilities

load_notes.py must:

1. read JSONL
1. validate schema
1. generate memory_items
1. persist and index

---

## Idempotency Requirements

Ingestion must be safe to run repeatedly.

Duplicate detection must use metadata:

- `metadata.source_type`
- `metadata.source_id`

Items with same source_type + source_id must not be inserted twice.

Use index:

```sql
CREATE INDEX idx_memory_source_ref
ON memory_items((metadata->>'source_id'));
```

---

## Embedding Behavior

Embeddings must be generated from:

`Question + Answer` for questionnaire items.

Example input:

```text
Question: What motivates you most in work?
Answer: Designing systems that reduce repetitive manual operations.
```

Notes use note text as embedding input.

---

## CLI Interface

Add CLI commands:

```bash
mnemos ingest questionnaire data/raw/questionnaire.md
mnemos ingest questionnaire data/raw/questionnaire.yaml
mnemos ingest notes data/raw/notes.jsonl
mnemos ingest all
```

---

## Ingestion Runner

`pipelines/ingest/ingest_runner.py` must:

- run questionnaire loader
- run notes loader
- produce ingestion summary

Example output:

```text
Questionnaire answers ingested: 50
Notes ingested: 12
Duplicates skipped: 3
```

---

## Logging

Ingestion must produce structured logs.

Example:

```text
INFO ingestion.questionnaire loaded=50 skipped=2
INFO ingestion.notes loaded=12
```

---

## Metrics

Expose Prometheus metrics:

- `mnemos_ingest_items_total`
- `mnemos_ingest_duplicates_total`
- `mnemos_ingest_errors_total`

---

## Testing

Create tests:

- `tests/test_ingestion_questionnaire_md.py`
- `tests/test_ingestion_questionnaire_yaml.py`
- `tests/test_ingestion_notes.py`

Test cases must include:

- questionnaire load
- duplicate skipping
- note ingestion
- vector indexing

---

## Seed Dataset

Add example dataset:

- `data/raw/questionnaire.md`
- `data/raw/notes.jsonl`

Minimum:

- 10 questionnaire entries
- 5 notes

Dataset must support semantic retrieval testing.

---

## Acceptance Criteria

Phase 2 is complete when:

- questionnaire.md loads successfully
- questionnaire.yaml loads successfully
- notes.jsonl loads successfully
- ingestion is idempotent
- items stored in PostgreSQL
- vectors indexed in Qdrant
- semantic retrieval returns ingested data
- CLI commands work
- ingestion metrics exposed
- structured logs generated

---

## Non-Goals

This phase must NOT implement:

- LLM fact extraction
- reflections
- agent memory writes
- candidate pipeline

These belong to Phase 3.

---

## Final Task

Implement Phase 2 ingestion so that Mnemos can load a human-written
questionnaire and notes dataset and immediately support semantic retrieval
across that knowledge.

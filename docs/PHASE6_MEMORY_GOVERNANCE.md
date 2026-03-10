# Mnemos - Phase 6: Memory Governance and Candidate Pipeline

## Objective

Introduce a governance layer for Mnemos memory updates.

Phase 6 prevents agents from directly mutating accepted memory.

Instead, agents propose candidate memory items, which are validated and
then optionally merged into the main memory store.

This phase ensures:

- memory integrity
- prevention of hallucinated facts
- controlled evolution of memory
- traceability of agent actions

## Architecture

Before Phase 6:

```text
raw -> facts -> reflections
```

After Phase 6:

```text
agent output
   |
   v
candidate memory
   |
   v
validation pipeline
   |
   v
accepted memory
   |
   v
vector index
```

Agents never write directly to accepted memory.

## New Data Model

Create table:

```text
memory_candidates
```

Suggested schema:

```sql
CREATE TABLE memory_candidates (
  id UUID PRIMARY KEY,
  domain VARCHAR(64) NOT NULL,
  kind VARCHAR(64) NOT NULL,
  statement TEXT NOT NULL,
  confidence DOUBLE PRECISION,
  agent_id VARCHAR(64),
  evidence JSONB,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  reviewed_at TIMESTAMPTZ
);
```

## Candidate Status Lifecycle

Candidate items must move through states:

```text
pending
accepted
rejected
```

Transitions:

```text
pending -> accepted
pending -> rejected
```

Accepted candidates become `memory_items`.

Rejected candidates remain for audit.

## Candidate Creation

Agents create candidate memory via API.

Endpoint:

```text
POST /memory/candidate
```

Example payload:

```json
{
  "domain": "self",
  "kind": "fact",
  "statement": "User prefers observable architectures.",
  "confidence": 0.78,
  "agent_id": "codex_cli",
  "evidence": {
    "source_fact_ids": ["fact_001", "fact_004"]
  }
}
```

The server must:

1. validate schema
1. insert into `memory_candidates`
1. return candidate id

## Validation Pipeline

Create module:

```text
pipelines/governance/
```

Files:

```text
validate_candidate.py
merge_candidate.py
candidate_runner.py
```

## Validation Rules

Candidates must pass the following checks.

### Schema Validation

Ensure:

- domain is valid
- kind is valid
- statement length between 10 and 500 chars

### Duplicate Detection

Reject if a near-identical statement already exists.

Strategy:

- normalize statement
- compare against `memory_items`
- similarity threshold

### Evidence Validation

If a candidate references facts:

- ensure referenced facts exist
- ensure domain consistency

Candidates with invalid evidence must be rejected.

### Contradiction Detection

Check if a candidate contradicts an existing accepted fact.

Example:

```text
existing fact:
User prefers Kubernetes.

candidate:
User dislikes Kubernetes.
```

Initial implementation may simply flag potential contradictions for
manual review.

## Candidate Merge

Merge operation converts a candidate into an accepted memory item.

Steps:

1. load candidate
1. verify `status = pending`
1. insert new row in `memory_items`
1. create relations if evidence exists
1. generate embedding
1. index vector in Qdrant
1. mark candidate status = accepted

## Relations

If a candidate includes evidence facts, create relations:

```text
fact -> supported_by -> candidate_fact
```

or:

```text
candidate_fact -> derived_from -> fact
```

Use the `memory_relations` table.

## API Endpoints

Add endpoints:

### Create Candidate

```text
POST /memory/candidate
```

### List Candidates

```text
GET /memory/candidates
```

Query parameters:

```text
status
domain
kind
```

### Accept Candidate

```text
POST /memory/candidate/{id}/accept
```

### Reject Candidate

```text
POST /memory/candidate/{id}/reject
```

## CLI Commands

Add CLI commands:

```text
mnemos candidates list
mnemos candidates accept <id>
mnemos candidates reject <id>
```

Example:

```text
mnemos candidates list --status pending
```

## MCP Integration

Agents using MCP should call:

```text
add_memory_note
```

or:

```text
propose_memory_item
```

These tools must internally call:

```text
POST /memory/candidate
```

Agents must never call direct memory write endpoints.

## Logging

Log candidate activity.

Examples:

```text
INFO candidate_created agent=codex_cli id=abc123
INFO candidate_accepted id=abc123
INFO candidate_rejected id=xyz789 reason=duplicate
```

## Metrics

Expose Prometheus metrics:

```text
mnemos_candidates_created_total
mnemos_candidates_accepted_total
mnemos_candidates_rejected_total
mnemos_candidate_validation_failures_total
```

## Testing

Create tests:

```text
tests/test_candidate_creation.py
tests/test_candidate_validation.py
tests/test_candidate_merge.py
```

Test cases:

- candidate creation
- duplicate rejection
- evidence validation
- merge into `memory_items`
- vector indexing after merge

LLM calls must remain mockable.

## Acceptance Criteria

Phase 6 is complete when:

- agents can create candidate memory items
- candidates are stored separately from `memory_items`
- validation rules prevent invalid candidates
- accepted candidates become `memory_items`
- relations are created when evidence exists
- vectors are indexed correctly
- CLI commands operate correctly
- metrics and logs are produced
- tests pass

## Non-Goals

Phase 6 must NOT implement:

- automatic candidate approval
- reputation systems
- conflict resolution beyond basic detection
- automatic reflection updates

These features belong to future phases.

## Final Task

Implement a governance layer that ensures all agent-generated memory
enters Mnemos as candidates and is validated before becoming accepted
memory.

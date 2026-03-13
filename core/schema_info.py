from __future__ import annotations

from core.config import (
  ALLOWED_DOMAINS,
  ALLOWED_KINDS,
  ALLOWED_CANDIDATE_WRITE_MODES,
  CANDIDATE_AGENT_ID_MAX_LENGTH,
  CANDIDATE_STATEMENT_MAX_LENGTH,
  CANDIDATE_STATEMENT_MIN_LENGTH,
  CANDIDATE_STATUSES,
  CONFIDENCE_ALIASES,
  EVIDENCE_REF_MAX_LENGTH,
  MEMORY_ITEM_STATUSES,
  MEMORY_CONFIDENCE_MAX,
  MEMORY_CONFIDENCE_MIN,
  MEMORY_STATEMENT_MIN_LENGTH,
  NOTE_STATEMENT_MAX_LENGTH,
  QUERY_MIN_LENGTH,
  QUERY_TOP_K_MAX,
  QUERY_TOP_K_MIN,
  REVIEW_SESSION_ID_MAX_LENGTH,
  REVIEW_SESSION_LABEL_MAX_LENGTH,
  SOURCE_EXCERPT_MAX_LENGTH,
)


def build_schema_info() -> dict[str, object]:
  return {
    "domains": list(ALLOWED_DOMAINS),
    "kinds": list(ALLOWED_KINDS),
    "candidate_statuses": list(CANDIDATE_STATUSES),
    "memory_item_statuses": list(MEMORY_ITEM_STATUSES),
    "confidence": {
      "type": "float_or_alias",
      "min": MEMORY_CONFIDENCE_MIN,
      "max": MEMORY_CONFIDENCE_MAX,
      "example": 0.85,
      "aliases": dict(CONFIDENCE_ALIASES),
      "description": "Use a numeric value from 0.0 to 1.0 inclusive, or low/medium/high.",
    },
    "memory_item": {
      "statement": {
        "min_length": MEMORY_STATEMENT_MIN_LENGTH,
      },
      "status_lifecycle": [
        {"status": "accepted", "meaning": "Visible in retrieval and active memory."},
        {"status": "superseded", "meaning": "Kept for audit/history, but replaced by a newer item."},
      ],
    },
    "memory_query": {
      "query": {
        "min_length": QUERY_MIN_LENGTH,
      },
      "top_k": {
        "min": QUERY_TOP_K_MIN,
        "max": QUERY_TOP_K_MAX,
        "default": 5,
      },
      "kinds": {
        "allowed_values": list(ALLOWED_KINDS),
      },
    },
    "memory_candidate": {
      "write_modes": {
        "allowed_values": list(ALLOWED_CANDIDATE_WRITE_MODES),
        "default": "create",
      },
      "default_statement": {
        "min_length": CANDIDATE_STATEMENT_MIN_LENGTH,
        "max_length": CANDIDATE_STATEMENT_MAX_LENGTH,
      },
      "note_statement": {
        "min_length": 1,
        "max_length": NOTE_STATEMENT_MAX_LENGTH,
      },
      "agent_id": {
        "max_length": CANDIDATE_AGENT_ID_MAX_LENGTH,
      },
      "review_session": {
        "id_max_length": REVIEW_SESSION_ID_MAX_LENGTH,
        "label_max_length": REVIEW_SESSION_LABEL_MAX_LENGTH,
      },
      "provenance": {
        "source_note_id": {"type": "uuid_string"},
        "evidence_ref": {"max_length": EVIDENCE_REF_MAX_LENGTH},
        "source_excerpt": {"max_length": SOURCE_EXCERPT_MAX_LENGTH},
      },
      "rules": {
        "note_uses_interaction_domain": True,
        "note_definition": "Raw interview material, working notes, or unstructured observations.",
        "fact_definition": "A concise, reviewable claim suitable for long-term memory.",
        "reflection_definition": "A higher-level pattern derived from multiple facts.",
      },
    },
    "workflows": {
      "shortlist_then_propose": [
        "validate or shortlist items without writing",
        "review dedupe hints and provenance",
        "submit items in bulk with a review session id",
      ],
      "interview_session": [
        "capture raw note candidates",
        "shortlist candidate facts with review session metadata",
        "review grouped candidates and accept or reject them",
      ],
    },
  }

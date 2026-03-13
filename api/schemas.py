from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from api.validation import (
  ensure_agent_id,
  ensure_allowed_domain,
  ensure_allowed_kind,
  ensure_candidate_write_mode,
  ensure_candidate_statement,
  ensure_candidate_status,
  ensure_confidence_range,
  ensure_evidence_ref,
  ensure_memory_item_status,
  ensure_memory_statement,
  ensure_non_empty_text,
  ensure_review_session_id,
  ensure_review_session_label,
  ensure_source_excerpt,
  ensure_top_k,
)
from core.config import ALLOWED_KINDS
from core.schema_info import build_schema_info


class LivenessResponse(BaseModel):
  status: str


class ReadinessCheckResponse(BaseModel):
  postgres: str
  qdrant: str


class ReadinessResponse(BaseModel):
  status: str
  checks: ReadinessCheckResponse


class MemoryCreateRequest(BaseModel):
  domain: str
  kind: str
  statement: str
  confidence: float | None = None
  metadata: dict[str, object] | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    return ensure_allowed_domain(value)

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    return ensure_allowed_kind(value)

  @field_validator("statement")
  @classmethod
  def validate_statement(cls, value: str) -> str:
    return ensure_memory_statement(value)

  @field_validator("confidence")
  @classmethod
  def validate_confidence(cls, value: float | None) -> float | None:
    return ensure_confidence_range(value)


class MemoryItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True, populate_by_name=True)

  id: UUID
  domain: str
  kind: str
  statement: str
  confidence: float | None
  status: str
  metadata: dict[str, object] | None = Field(alias="metadata_json", serialization_alias="metadata")
  created_at: datetime
  updated_at: datetime

  @model_validator(mode="before")
  @classmethod
  def enrich_from_metadata(cls, value: Any) -> Any:
    if isinstance(value, dict):
      return value
    metadata = getattr(value, "metadata_json", None) or {}
    payload = {
      "id": getattr(value, "id"),
      "domain": getattr(value, "domain"),
      "kind": getattr(value, "kind"),
      "statement": getattr(value, "statement"),
      "confidence": getattr(value, "confidence"),
      "status": getattr(value, "status"),
      "metadata_json": metadata,
      "created_at": getattr(value, "created_at"),
      "updated_at": getattr(value, "updated_at"),
    }
    return payload


class MemoryQueryRequest(BaseModel):
  query: str
  domain: str
  top_k: int = 5
  kinds: list[str] | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    return ensure_allowed_domain(value)

  @field_validator("query")
  @classmethod
  def validate_query(cls, value: str) -> str:
    return ensure_non_empty_text(value, field_name="query")

  @field_validator("top_k")
  @classmethod
  def validate_top_k(cls, value: int) -> int:
    return ensure_top_k(value)

  @field_validator("kinds")
  @classmethod
  def validate_kinds(cls, value: list[str] | None) -> list[str] | None:
    if value is None:
      return value
    invalid = [kind for kind in value if kind not in ALLOWED_KINDS]
    if invalid:
      raise ValueError(
        f"unsupported kinds: {', '.join(invalid)}. Allowed values: {', '.join(ALLOWED_KINDS)}. "
        "Remove or replace unsupported kinds."
      )
    return value


class MemoryQueryResponse(BaseModel):
  query: str
  domain: str
  items: list[MemoryItemResponse]


class MemoryCandidateCreateRequest(BaseModel):
  domain: str
  kind: str
  statement: str
  confidence: float | str | None = None
  agent_id: str | None = None
  evidence: dict[str, object] | None = None
  metadata: dict[str, object] | None = None
  write_mode: str = "create"
  source_note_id: str | None = None
  evidence_ref: str | None = None
  source_excerpt: str | None = None
  review_session_id: str | None = None
  review_session_label: str | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    return ensure_allowed_domain(value)

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    return ensure_allowed_kind(value)

  @field_validator("confidence")
  @classmethod
  def validate_confidence(cls, value: float | str | None) -> float | None:
    return ensure_confidence_range(value)

  @field_validator("agent_id")
  @classmethod
  def validate_agent_id(cls, value: str | None) -> str | None:
    return ensure_agent_id(value)

  @field_validator("write_mode")
  @classmethod
  def validate_write_mode(cls, value: str) -> str:
    validated = ensure_candidate_write_mode(value)
    assert validated is not None
    return validated

  @field_validator("source_note_id")
  @classmethod
  def validate_source_note_id(cls, value: str | None) -> str | None:
    return ensure_review_session_id(value)

  @field_validator("review_session_id")
  @classmethod
  def validate_review_session_id(cls, value: str | None) -> str | None:
    return ensure_review_session_id(value)

  @field_validator("review_session_label")
  @classmethod
  def validate_review_session_label(cls, value: str | None) -> str | None:
    return ensure_review_session_label(value)

  @field_validator("evidence_ref")
  @classmethod
  def validate_evidence_ref(cls, value: str | None) -> str | None:
    return ensure_evidence_ref(value)

  @field_validator("source_excerpt")
  @classmethod
  def validate_source_excerpt(cls, value: str | None) -> str | None:
    return ensure_source_excerpt(value)

  @model_validator(mode="after")
  def validate_statement_length(self) -> "MemoryCandidateCreateRequest":
    self.statement = ensure_candidate_statement(self.statement, kind=self.kind)
    return self


class CandidateDedupeHint(BaseModel):
  existing_item_id: str
  similarity: float
  statement: str
  status: str
  action: str


class ReviewSessionInfo(BaseModel):
  id: str
  label: str | None = None
  kind: str = "review"
  created_by: str | None = None


class MemoryCandidateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True, populate_by_name=True)

  id: UUID
  domain: str
  kind: str
  statement: str
  confidence: float | None
  agent_id: str | None
  evidence: dict[str, object] | None = Field(
    alias="evidence_json",
    serialization_alias="evidence",
  )
  status: str
  metadata: dict[str, object] | None = Field(alias="metadata_json", serialization_alias="metadata")
  created_at: datetime
  reviewed_at: datetime | None
  write_mode: str | None = None
  source_note_id: str | None = None
  evidence_ref: str | None = None
  source_excerpt: str | None = None
  review_session: ReviewSessionInfo | None = None

  @model_validator(mode="before")
  @classmethod
  def enrich_from_provenance(cls, value: Any) -> Any:
    if isinstance(value, dict):
      return value
    metadata = getattr(value, "metadata_json", None) or {}
    evidence = getattr(value, "evidence_json", None) or {}
    review_session_id = metadata.get("review_session_id")
    review_session = None
    if isinstance(review_session_id, str) and review_session_id:
      review_session = {
        "id": review_session_id,
        "label": metadata.get("review_session_label"),
        "kind": metadata.get("review_session_kind", "review"),
        "created_by": metadata.get("review_session_created_by"),
      }
    return {
      "id": getattr(value, "id"),
      "domain": getattr(value, "domain"),
      "kind": getattr(value, "kind"),
      "statement": getattr(value, "statement"),
      "confidence": getattr(value, "confidence"),
      "agent_id": getattr(value, "agent_id"),
      "evidence_json": evidence,
      "status": getattr(value, "status"),
      "metadata_json": metadata,
      "created_at": getattr(value, "created_at"),
      "reviewed_at": getattr(value, "reviewed_at"),
      "write_mode": metadata.get("write_mode"),
      "source_note_id": evidence.get("source_note_id"),
      "evidence_ref": evidence.get("evidence_ref"),
      "source_excerpt": evidence.get("source_excerpt"),
      "review_session": review_session,
    }


class MemoryCandidateListResponse(BaseModel):
  items: list[MemoryCandidateResponse]


class MemoryItemListResponse(BaseModel):
  items: list[MemoryItemResponse]


class MemoryCandidateBulkCreateRequest(BaseModel):
  items: list[MemoryCandidateCreateRequest] = Field(min_length=1, max_length=50)
  review_session_id: str | None = None
  review_session_label: str | None = None

  @field_validator("review_session_id")
  @classmethod
  def validate_review_session_id(cls, value: str | None) -> str | None:
    return ensure_review_session_id(value)

  @field_validator("review_session_label")
  @classmethod
  def validate_review_session_label(cls, value: str | None) -> str | None:
    return ensure_review_session_label(value)


class MemoryCandidateBulkCreateResponse(BaseModel):
  created: int
  items: list[MemoryCandidateResponse]
  review_session: ReviewSessionInfo | None = None


class MemoryCandidateValidationIssue(BaseModel):
  loc: list[str]
  message: str


class MemoryCandidatePreview(BaseModel):
  normalized_statement: str
  write_mode: str
  will_create_status: str
  preview_metadata: dict[str, object]
  review_session: ReviewSessionInfo | None = None
  dedupe_hints: list[CandidateDedupeHint] = Field(default_factory=list)
  suggested_action: str | None = None
  suggested_replacement_item_id: str | None = None


class MemoryCandidateValidateResponse(BaseModel):
  valid: bool
  candidate: MemoryCandidateCreateRequest | None = None
  errors: list[MemoryCandidateValidationIssue] = Field(default_factory=list)
  preview: MemoryCandidatePreview | None = None
  dedupe_hints: list[CandidateDedupeHint] = Field(default_factory=list)


class MemoryCandidateShortlistItem(BaseModel):
  index: int
  valid: bool
  candidate: MemoryCandidateCreateRequest | None = None
  errors: list[MemoryCandidateValidationIssue] = Field(default_factory=list)
  preview: MemoryCandidatePreview | None = None
  dedupe_hints: list[CandidateDedupeHint] = Field(default_factory=list)


class MemoryCandidateShortlistRequest(BaseModel):
  items: list[MemoryCandidateCreateRequest] = Field(min_length=1, max_length=50)
  review_session_id: str | None = None
  review_session_label: str | None = None

  @field_validator("review_session_id")
  @classmethod
  def validate_review_session_id(cls, value: str | None) -> str | None:
    return ensure_review_session_id(value)

  @field_validator("review_session_label")
  @classmethod
  def validate_review_session_label(cls, value: str | None) -> str | None:
    return ensure_review_session_label(value)


class MemoryCandidateShortlistResponse(BaseModel):
  review_session: ReviewSessionInfo
  ready_count: int
  invalid_count: int
  items: list[MemoryCandidateShortlistItem]


class MemorySchemaInfoResponse(BaseModel):
  schema_info: dict[str, Any] = Field(
    default_factory=build_schema_info,
    validation_alias="schema",
    serialization_alias="schema",
  )


class CandidateRejectRequest(BaseModel):
  reason: str = Field(min_length=1, max_length=200)


class CandidateDecisionResponse(BaseModel):
  candidate: MemoryCandidateResponse
  merged_item: MemoryItemResponse | None = None
  validation_errors: list[str] = Field(default_factory=list)
  dedupe_hints: list[CandidateDedupeHint] = Field(default_factory=list)


class CandidateListQuery(BaseModel):
  status: str | None = None
  domain: str | None = None
  kind: str | None = None
  review_session_id: str | None = None

  @field_validator("status")
  @classmethod
  def validate_status(cls, value: str | None) -> str | None:
    return ensure_candidate_status(value)

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str | None) -> str | None:
    if value is None:
      return value
    return ensure_allowed_domain(value)

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str | None) -> str | None:
    if value is None:
      return value
    return ensure_allowed_kind(value)

  @field_validator("review_session_id")
  @classmethod
  def validate_review_session_id(cls, value: str | None) -> str | None:
    return ensure_review_session_id(value)


class MemoryItemListQuery(BaseModel):
  domain: str
  kind: str | None = None
  status: str | None = "accepted"

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    return ensure_allowed_domain(value)

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str | None) -> str | None:
    if value is None:
      return value
    return ensure_allowed_kind(value)

  @field_validator("status")
  @classmethod
  def validate_status(cls, value: str | None) -> str | None:
    return ensure_memory_item_status(value)


class ReviewSessionSummary(BaseModel):
  review_session: ReviewSessionInfo
  candidate_count: int
  pending_count: int
  accepted_count: int
  rejected_count: int
  superseded_count: int
  latest_created_at: datetime


class ReviewSessionListResponse(BaseModel):
  items: list[ReviewSessionSummary]


class WebDomainSummary(BaseModel):
  domain: str
  items_total: int


class WebOverviewResponse(BaseModel):
  status: str
  checks: ReadinessCheckResponse
  domains: list[WebDomainSummary]
  pending_candidates: int
  features: list[str]


class WebListItemsResponse(BaseModel):
  items: list[MemoryItemResponse]


class ImportPreviewRequest(BaseModel):
  content: str
  filename: str | None = None
  domain: str = "self"
  kind: str = "note"

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    return ensure_allowed_domain(value)

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    return ensure_allowed_kind(value)

  @field_validator("content")
  @classmethod
  def validate_content(cls, value: str) -> str:
    return ensure_non_empty_text(value, field_name="content")


class ImportPreviewItem(BaseModel):
  statement: str
  metadata: dict[str, Any] | None = None


class ImportPreviewResponse(BaseModel):
  detected_format: str
  items: list[ImportPreviewItem]
  warnings: list[str] = Field(default_factory=list)
  truncated: bool = False


class ImportApplyResponse(BaseModel):
  detected_format: str
  created: int
  skipped: int
  items: list[MemoryItemResponse]

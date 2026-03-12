from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from api.validation import (
  ensure_agent_id,
  ensure_allowed_domain,
  ensure_allowed_kind,
  ensure_candidate_statement,
  ensure_candidate_status,
  ensure_confidence_range,
  ensure_memory_statement,
  ensure_non_empty_text,
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
  confidence: float | None = None
  agent_id: str | None = None
  evidence: dict[str, object] | None = None
  metadata: dict[str, object] | None = None

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
  def validate_confidence(cls, value: float | None) -> float | None:
    return ensure_confidence_range(value)

  @field_validator("agent_id")
  @classmethod
  def validate_agent_id(cls, value: str | None) -> str | None:
    return ensure_agent_id(value)

  @model_validator(mode="after")
  def validate_statement_length(self) -> "MemoryCandidateCreateRequest":
    self.statement = ensure_candidate_statement(self.statement, kind=self.kind)
    return self


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


class MemoryCandidateListResponse(BaseModel):
  items: list[MemoryCandidateResponse]


class MemoryCandidateBulkCreateRequest(BaseModel):
  items: list[MemoryCandidateCreateRequest] = Field(min_length=1, max_length=50)


class MemoryCandidateBulkCreateResponse(BaseModel):
  created: int
  items: list[MemoryCandidateResponse]


class MemoryCandidateValidationIssue(BaseModel):
  loc: list[str]
  message: str


class MemoryCandidateValidateResponse(BaseModel):
  valid: bool
  candidate: MemoryCandidateCreateRequest | None = None
  errors: list[MemoryCandidateValidationIssue] = Field(default_factory=list)


class MemorySchemaInfoResponse(BaseModel):
  schema: dict[str, Any] = Field(default_factory=build_schema_info)


class CandidateRejectRequest(BaseModel):
  reason: str = Field(min_length=1, max_length=200)


class CandidateDecisionResponse(BaseModel):
  candidate: MemoryCandidateResponse
  merged_item: MemoryItemResponse | None = None
  validation_errors: list[str] = Field(default_factory=list)


class CandidateListQuery(BaseModel):
  status: str | None = None
  domain: str | None = None
  kind: str | None = None

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

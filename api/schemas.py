from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.config import ALLOWED_DOMAINS, ALLOWED_KINDS

CANDIDATE_STATUSES = ("pending", "accepted", "rejected")


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
  statement: str = Field(min_length=1)
  confidence: float | None = None
  metadata: dict[str, object] | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    if value not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {value}")
    return value

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    if value not in ALLOWED_KINDS:
      raise ValueError(f"unsupported kind: {value}")
    return value


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
  query: str = Field(min_length=1)
  domain: str
  top_k: int = Field(default=5, ge=1, le=50)
  kinds: list[str] | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    if value not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {value}")
    return value

  @field_validator("kinds")
  @classmethod
  def validate_kinds(cls, value: list[str] | None) -> list[str] | None:
    if value is None:
      return value
    invalid = [kind for kind in value if kind not in ALLOWED_KINDS]
    if invalid:
      raise ValueError(f"unsupported kinds: {', '.join(invalid)}")
    return value


class MemoryQueryResponse(BaseModel):
  query: str
  domain: str
  items: list[MemoryItemResponse]


class MemoryCandidateCreateRequest(BaseModel):
  domain: str
  kind: str
  statement: str = Field(min_length=10, max_length=500)
  confidence: float | None = None
  agent_id: str | None = Field(default=None, min_length=1, max_length=64)
  evidence: dict[str, object] | None = None
  metadata: dict[str, object] | None = None

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    if value not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {value}")
    return value

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    if value not in ALLOWED_KINDS:
      raise ValueError(f"unsupported kind: {value}")
    return value


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
    if value is None:
      return value
    if value not in CANDIDATE_STATUSES:
      raise ValueError(f"unsupported candidate status: {value}")
    return value

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str | None) -> str | None:
    if value is None:
      return value
    if value not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {value}")
    return value

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str | None) -> str | None:
    if value is None:
      return value
    if value not in ALLOWED_KINDS:
      raise ValueError(f"unsupported kind: {value}")
    return value


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
  content: str = Field(min_length=1)
  filename: str | None = None
  domain: str = "self"
  kind: str = "note"

  @field_validator("domain")
  @classmethod
  def validate_domain(cls, value: str) -> str:
    if value not in ALLOWED_DOMAINS:
      raise ValueError(f"unsupported domain: {value}")
    return value

  @field_validator("kind")
  @classmethod
  def validate_kind(cls, value: str) -> str:
    if value not in ALLOWED_KINDS:
      raise ValueError(f"unsupported kind: {value}")
    return value


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

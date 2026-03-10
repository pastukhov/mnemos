from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.config import ALLOWED_DOMAINS, ALLOWED_KINDS


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

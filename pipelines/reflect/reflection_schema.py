from pydantic import BaseModel, Field, field_validator


class ReflectionFactInput(BaseModel):
  id: str = Field(min_length=1)
  statement: str = Field(min_length=1)


class GeneratedReflection(BaseModel):
  statement: str
  confidence: float
  evidence_fact_ids: list[str]

  @field_validator("statement")
  @classmethod
  def validate_statement(cls, value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
      raise ValueError("statement must not be empty")
    return normalized


class GeneratedReflectionsPayload(BaseModel):
  reflections: list[GeneratedReflection]

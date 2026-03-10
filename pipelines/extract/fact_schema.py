from pydantic import BaseModel, Field


class ExtractedFact(BaseModel):
  statement: str = Field(min_length=1)
  confidence: float = Field(ge=0.0, le=1.0)
  evidence_reference: str | None = None


class ExtractedFactsPayload(BaseModel):
  facts: list[ExtractedFact]

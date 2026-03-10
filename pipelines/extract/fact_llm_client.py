from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import httpx

from core.config import Settings
from pipelines.extract.fact_schema import ExtractedFact, ExtractedFactsPayload

SYSTEM_PROMPT = """You are extracting factual statements from a knowledge source.

Rules:
- Extract only explicit facts
- Each fact must be atomic
- Do not interpret or speculate
- Output JSON only

Return JSON with top-level key "facts"."""


class FactLLMClient(ABC):
  @abstractmethod
  def extract_facts(self, text: str) -> list[ExtractedFact]:
    raise NotImplementedError


class MockFactLLMClient(FactLLMClient):
  ANSWER_RE = re.compile(r"(?:^|\n)(?:Answer|Ответ):\s*(.+)", re.IGNORECASE | re.DOTALL)

  def extract_facts(self, text: str) -> list[ExtractedFact]:
    answer = self._extract_answer(text)
    candidates = [part.strip() for part in re.split(r"[;\n]+", answer) if part.strip()]
    facts: list[ExtractedFact] = []
    for candidate in candidates:
      statement = self._normalize_statement(candidate)
      if not statement:
        continue
      facts.append(
        ExtractedFact(
          statement=statement,
          confidence=0.8,
          evidence_reference=answer,
        )
      )
    return facts

  def _extract_answer(self, text: str) -> str:
    match = self.ANSWER_RE.search(text)
    if match:
      return " ".join(match.group(1).split())
    return " ".join(text.split())

  def _normalize_statement(self, text: str) -> str:
    normalized = text.strip().rstrip(".")
    replacements = (
      (r"^I am\b", "User is"),
      (r"^I'm\b", "User is"),
      (r"^I work\b", "User works"),
      (r"^I prefer\b", "User prefers"),
      (r"^I enjoy\b", "User enjoys"),
      (r"^I like\b", "User likes"),
      (r"^I build\b", "User builds"),
      (r"^I design\b", "User designs"),
      (r"^I use\b", "User uses"),
      (r"^I want\b", "User wants"),
    )
    for pattern, replacement in replacements:
      normalized = re.sub(pattern, replacement, normalized, count=1, flags=re.IGNORECASE)
    if normalized == text.strip().rstrip(".") and not normalized.lower().startswith("user "):
      normalized = f"User values {normalized[:1].lower()}{normalized[1:]}"
    return normalized.strip() + "."


class OpenAICompatibleFactLLMClient(FactLLMClient):
  def __init__(
    self,
    *,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
  ) -> None:
    self.model = model
    self.base_url = base_url.rstrip("/")
    self.api_key = api_key
    self.timeout_seconds = timeout_seconds

  def extract_facts(self, text: str) -> list[ExtractedFact]:
    headers = {"Content-Type": "application/json"}
    if self.api_key:
      headers["Authorization"] = f"Bearer {self.api_key}"

    response = httpx.post(
      f"{self.base_url}/chat/completions",
      headers=headers,
      timeout=self.timeout_seconds,
      json={
        "model": self.model,
        "response_format": {"type": "json_object"},
        "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {"role": "user", "content": f"Source text:\n\n{text}"},
        ],
      },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return ExtractedFactsPayload.model_validate(parsed).facts


def build_fact_llm_client(settings: Settings) -> FactLLMClient:
  if settings.fact_llm_provider != "openai_compatible":
    raise ValueError("FACT_LLM_PROVIDER must be 'openai_compatible'")
  if not settings.fact_llm_base_url:
    raise ValueError("FACT_LLM_BASE_URL is required for FACT_LLM_PROVIDER=openai_compatible")
  return OpenAICompatibleFactLLMClient(
    model=settings.fact_llm_model,
    base_url=settings.fact_llm_base_url,
    api_key=settings.fact_llm_api_key,
    timeout_seconds=settings.fact_llm_timeout_seconds,
  )

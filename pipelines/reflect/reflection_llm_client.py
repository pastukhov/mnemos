from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections import Counter

import httpx

from core.config import Settings
from pipelines.reflect.reflection_schema import (
  GeneratedReflection,
  GeneratedReflectionsPayload,
  ReflectionFactInput,
)

SYSTEM_PROMPT = """You are deriving evidence-backed reflections from a set of facts about a user.

Rules:
- Reflections must be supported by at least 2 facts
- Focus on stable patterns in behavior, work style, motivation, goals, learning style, and values
- Do not diagnose
- Do not speculate beyond evidence
- Do not produce advice
- Output JSON only

Return JSON with top-level key "reflections"."""

STOP_WORDS = {
  "user",
  "the",
  "and",
  "that",
  "with",
  "from",
  "into",
  "their",
  "they",
  "this",
  "these",
  "those",
  "prefers",
  "likes",
  "enjoys",
  "values",
  "works",
  "builds",
  "uses",
  "around",
  "stable",
  "pattern",
  "systems",
}


class ReflectionLLMClient(ABC):
  @abstractmethod
  def generate_reflections(self, *, theme: str, facts: list[ReflectionFactInput]) -> list[GeneratedReflection]:
    raise NotImplementedError


class MockReflectionLLMClient(ReflectionLLMClient):
  WORD_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)

  def generate_reflections(self, *, theme: str, facts: list[ReflectionFactInput]) -> list[GeneratedReflection]:
    if len(facts) < 2:
      return []
    evidence = facts[: min(len(facts), 3)]
    keywords = self._top_keywords(facts)
    if keywords:
      subject = ", ".join(keywords[:3])
      statement = f"User shows a stable {theme} pattern centered on {subject}."
    else:
      statement = f"User shows a stable {theme} pattern across multiple accepted facts."
    confidence = min(0.95, 0.65 + 0.05 * len(evidence))
    return [
      GeneratedReflection(
        statement=statement,
        confidence=confidence,
        evidence_fact_ids=[fact.id for fact in evidence],
      )
    ]

  def _top_keywords(self, facts: list[ReflectionFactInput]) -> list[str]:
    counter: Counter[str] = Counter()
    for fact in facts:
      words = {word.lower() for word in self.WORD_RE.findall(fact.statement)}
      for word in words:
        if word not in STOP_WORDS:
          counter[word] += 1
    return [word for word, _ in counter.most_common(3)]


class OpenAICompatibleReflectionLLMClient(ReflectionLLMClient):
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

  def generate_reflections(self, *, theme: str, facts: list[ReflectionFactInput]) -> list[GeneratedReflection]:
    headers = {"Content-Type": "application/json"}
    if self.api_key:
      headers["Authorization"] = f"Bearer {self.api_key}"

    fact_lines = "\n".join(f"- {fact.id}: {fact.statement}" for fact in facts)
    response = httpx.post(
      f"{self.base_url}/chat/completions",
      headers=headers,
      timeout=self.timeout_seconds,
      json={
        "model": self.model,
        "response_format": {"type": "json_object"},
        "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {
            "role": "user",
            "content": f"Theme: {theme}\nInput facts:\n{fact_lines}",
          },
        ],
      },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return GeneratedReflectionsPayload.model_validate(parsed).reflections


def build_reflection_llm_client(settings: Settings) -> ReflectionLLMClient:
  if settings.reflection_llm_provider != "openai_compatible":
    raise ValueError("REFLECTION_LLM_PROVIDER must be 'openai_compatible'")
  if not settings.reflection_llm_base_url:
    raise ValueError(
      "REFLECTION_LLM_BASE_URL is required for REFLECTION_LLM_PROVIDER=openai_compatible"
    )
  return OpenAICompatibleReflectionLLMClient(
    model=settings.reflection_llm_model,
    base_url=settings.reflection_llm_base_url,
    api_key=settings.reflection_llm_api_key,
    timeout_seconds=settings.reflection_llm_timeout_seconds,
  )

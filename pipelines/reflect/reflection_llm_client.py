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
SUPPORTING_FACT_ID_RE = re.compile(
  r"^\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*:",
)


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
    normalized = self._normalize_payload(parsed, facts=facts)
    return GeneratedReflectionsPayload.model_validate(normalized).reflections

  def _normalize_payload(
    self,
    payload: object,
    *,
    facts: list[ReflectionFactInput],
  ) -> dict[str, object]:
    if not isinstance(payload, dict):
      raise ValueError("LLM response must be a JSON object")
    reflections = payload.get("reflections")
    if not isinstance(reflections, list):
      raise ValueError("LLM response must contain a top-level 'reflections' list")
    return {
      "reflections": [
        self._normalize_reflection(item, facts=facts)
        for item in reflections
      ]
    }

  def _normalize_reflection(
    self,
    reflection: object,
    *,
    facts: list[ReflectionFactInput],
  ) -> dict[str, object]:
    if isinstance(reflection, dict):
      statement = reflection.get("statement")
      if not isinstance(statement, str) or not statement.strip():
        statement = reflection.get("summary")
      if not isinstance(statement, str) or not statement.strip():
        statement = reflection.get("pattern")
      if not isinstance(statement, str) or not statement.strip():
        statement = reflection.get("reflection")
      if not isinstance(statement, str) or not statement.strip():
        for value in reflection.values():
          if isinstance(value, str) and value.strip():
            statement = value
            break
      if not isinstance(statement, str) or not statement.strip():
        raise ValueError("Reflection object must contain a non-empty 'statement'")
      confidence = reflection.get("confidence", 0.8)
      evidence_fact_ids = reflection.get("evidence_fact_ids")
      if not isinstance(evidence_fact_ids, list):
        evidence_fact_ids = self._extract_supporting_fact_ids(reflection.get("supporting_facts"))
      if not evidence_fact_ids:
        evidence_fact_ids = self._extract_matching_fact_ids(reflection.get("evidence"), facts=facts)
      if not evidence_fact_ids:
        for value in reflection.values():
          matched = self._extract_matching_fact_ids(value, facts=facts)
          if matched:
            evidence_fact_ids = matched
            break
      normalized_ids = [item for item in evidence_fact_ids if isinstance(item, str) and item.strip()]
      if len(normalized_ids) < 2:
        normalized_ids = [fact.id for fact in facts[:2]]
      return {
        "statement": statement.strip(),
        "confidence": self._coerce_confidence(confidence),
        "evidence_fact_ids": normalized_ids,
      }
    if isinstance(reflection, str) and reflection.strip():
      return {
        "statement": reflection.strip(),
        "confidence": 0.8,
        "evidence_fact_ids": [fact.id for fact in facts[:2]],
      }
    raise ValueError("Reflection items must be objects or strings")

  def _extract_supporting_fact_ids(self, value: object) -> list[str]:
    if not isinstance(value, list):
      return []
    fact_ids: list[str] = []
    for item in value:
      if isinstance(item, str):
        match = SUPPORTING_FACT_ID_RE.match(item)
        if match:
          fact_ids.append(match.group(1))
    return fact_ids

  def _extract_matching_fact_ids(
    self,
    value: object,
    *,
    facts: list[ReflectionFactInput],
  ) -> list[str]:
    if not isinstance(value, list):
      return []
    matched: list[str] = []
    normalized_facts = {
      self._normalize_text(fact.statement): fact.id
      for fact in facts
    }
    for item in value:
      if not isinstance(item, str):
        continue
      normalized_item = self._normalize_text(item)
      for statement, fact_id in normalized_facts.items():
        if normalized_item and (normalized_item in statement or statement in normalized_item):
          matched.append(fact_id)
          break
    return list(dict.fromkeys(matched))

  def _normalize_text(self, value: str) -> str:
    return " ".join(value.lower().split())

  def _coerce_confidence(self, value: object) -> float:
    if isinstance(value, bool):
      return 0.8
    if isinstance(value, (int, float)):
      return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
      try:
        return max(0.0, min(1.0, float(value)))
      except ValueError:
        return 0.8
    return 0.8


def build_reflection_llm_client(settings: Settings) -> ReflectionLLMClient:
  if not settings.reflection_llm_base_url:
    raise ValueError("REFLECTION_LLM_BASE_URL is required")
  return OpenAICompatibleReflectionLLMClient(
    model=settings.reflection_llm_model,
    base_url=settings.reflection_llm_base_url,
    api_key=settings.reflection_llm_api_key,
    timeout_seconds=settings.reflection_llm_timeout_seconds,
  )

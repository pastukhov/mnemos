from __future__ import annotations

import hashlib
import json
import re
from collections import Counter

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mnemos-mock-openai")

WORD_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
ANSWER_RE = re.compile(r"(?:^|\n)(?:Answer|Ответ):\s*(.+)", re.IGNORECASE | re.DOTALL)
FACT_LINE_RE = re.compile(r"^- ([^:]+): (.+)$", re.MULTILINE)
THEME_RE = re.compile(r"^Theme:\s*(.+)$", re.MULTILINE)
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
VECTOR_SIZE = 64


class EmbeddingsRequest(BaseModel):
  model: str
  input: str | list[str]


class ChatMessage(BaseModel):
  role: str
  content: str


class ChatCompletionsRequest(BaseModel):
  model: str
  messages: list[ChatMessage]


def _embedding_for_text(text: str) -> list[float]:
  digest = hashlib.sha256(text.encode("utf-8")).digest()
  vector: list[float] = []
  while len(vector) < VECTOR_SIZE:
    for byte in digest:
      vector.append((byte / 255.0) * 2.0 - 1.0)
      if len(vector) == VECTOR_SIZE:
        break
  return vector


def _extract_answer(text: str) -> str:
  match = ANSWER_RE.search(text)
  if match:
    return " ".join(match.group(1).split())
  return " ".join(text.split())


def _normalize_fact(text: str) -> str:
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


def _facts_payload(text: str) -> dict[str, object]:
  answer = _extract_answer(text)
  candidates = [part.strip() for part in re.split(r"[;\n]+", answer) if part.strip()]
  facts = [
    {
      "statement": _normalize_fact(candidate),
      "confidence": 0.8,
      "evidence_reference": answer,
    }
    for candidate in candidates
  ]
  return {"facts": facts[:5]}


def _top_keywords(statements: list[str]) -> list[str]:
  counter: Counter[str] = Counter()
  for statement in statements:
    words = {word.lower() for word in WORD_RE.findall(statement)}
    for word in words:
      if word not in STOP_WORDS:
        counter[word] += 1
  return [word for word, _ in counter.most_common(3)]


def _reflections_payload(content: str) -> dict[str, object]:
  theme_match = THEME_RE.search(content)
  theme = theme_match.group(1).strip() if theme_match else "general"
  facts = FACT_LINE_RE.findall(content)
  if len(facts) < 2:
    return {"reflections": []}
  evidence_ids = [fact_id for fact_id, _ in facts[:3]]
  keywords = _top_keywords([statement for _, statement in facts])
  if keywords:
    subject = ", ".join(keywords)
    statement = f"User shows a stable {theme} pattern centered on {subject}."
  else:
    statement = f"User shows a stable {theme} pattern across multiple accepted facts."
  return {
    "reflections": [
      {
        "statement": statement,
        "confidence": 0.8,
        "evidence_fact_ids": evidence_ids,
      }
    ]
  }


@app.get("/health")
async def health() -> dict[str, str]:
  return {"status": "ok"}


@app.post("/v1/embeddings")
async def embeddings(request: EmbeddingsRequest) -> dict[str, object]:
  text = request.input if isinstance(request.input, str) else request.input[0]
  return {
    "object": "list",
    "data": [
      {
        "object": "embedding",
        "index": 0,
        "embedding": _embedding_for_text(text),
      }
    ],
    "model": request.model,
  }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionsRequest) -> dict[str, object]:
  system_prompt = request.messages[0].content if request.messages else ""
  user_content = request.messages[-1].content if request.messages else ""
  if "extracting factual statements" in system_prompt:
    payload = _facts_payload(user_content)
  elif "deriving evidence-backed reflections" in system_prompt:
    payload = _reflections_payload(user_content)
  else:
    payload = {"message": "mock-openai-api"}
  return {
    "id": "chatcmpl-mock",
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "message": {"role": "assistant", "content": json.dumps(payload)},
        "finish_reason": "stop",
      }
    ],
    "model": request.model,
  }

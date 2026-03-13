from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.config import (
  ALLOWED_DOMAINS,
  ALLOWED_KINDS,
  ALLOWED_CANDIDATE_WRITE_MODES,
  CANDIDATE_AGENT_ID_MAX_LENGTH,
  CANDIDATE_STATEMENT_MAX_LENGTH,
  CANDIDATE_STATEMENT_MIN_LENGTH,
  CANDIDATE_STATUSES,
  CONFIDENCE_ALIASES,
  EVIDENCE_REF_MAX_LENGTH,
  MEMORY_CONFIDENCE_MAX,
  MEMORY_CONFIDENCE_MIN,
  MEMORY_ITEM_STATUSES,
  MEMORY_STATEMENT_MIN_LENGTH,
  NOTE_STATEMENT_MAX_LENGTH,
  QUERY_TOP_K_MAX,
  QUERY_TOP_K_MIN,
  REVIEW_SESSION_ID_MAX_LENGTH,
  REVIEW_SESSION_LABEL_MAX_LENGTH,
  SOURCE_EXCERPT_MAX_LENGTH,
)


def register_validation_exception_handler(app: FastAPI) -> None:
  @app.exception_handler(RequestValidationError)
  async def handle_validation_error(  # type: ignore[misc]
    request: Request,
    exc: RequestValidationError,
  ) -> JSONResponse:
    errors = [_format_validation_error(error) for error in exc.errors()]
    return JSONResponse(
      status_code=422,
      content={
        "detail": {
          "message": "Request validation failed.",
          "errors": errors,
        }
      },
    )


def ensure_allowed_domain(value: str) -> str:
  if value not in ALLOWED_DOMAINS:
    raise ValueError(
      f"unsupported domain '{value}'. Allowed values: {', '.join(ALLOWED_DOMAINS)}. "
      "Choose one of the supported domains."
    )
  return value


def ensure_allowed_kind(value: str) -> str:
  if value not in ALLOWED_KINDS:
    raise ValueError(
      f"unsupported kind '{value}'. Allowed values: {', '.join(ALLOWED_KINDS)}. "
      "Replace it with one of the supported kinds."
    )
  return value


def ensure_candidate_status(value: str | None) -> str | None:
  if value is None:
    return value
  if value not in CANDIDATE_STATUSES:
    raise ValueError(
      f"unsupported candidate status '{value}'. Allowed values: {', '.join(CANDIDATE_STATUSES)}. "
      "Use one of the documented lifecycle statuses."
    )
  return value


def ensure_memory_item_status(value: str | None) -> str | None:
  if value is None:
    return value
  if value not in MEMORY_ITEM_STATUSES:
    raise ValueError(
      f"unsupported memory item status '{value}'. Allowed values: {', '.join(MEMORY_ITEM_STATUSES)}. "
      "Use one of the supported lifecycle states."
    )
  return value


def normalize_confidence_value(value: float | str | None) -> float | None:
  if value is None:
    return value
  if isinstance(value, str):
    normalized = value.strip().lower()
    if normalized in CONFIDENCE_ALIASES:
      return CONFIDENCE_ALIASES[normalized]
    raise ValueError(
      f"unsupported confidence alias '{value}'. Allowed aliases: {', '.join(CONFIDENCE_ALIASES)}. "
      f"Or use a numeric value between {MEMORY_CONFIDENCE_MIN} and {MEMORY_CONFIDENCE_MAX}. "
      "Use a numeric value such as 0.85."
    )
  return float(value)


def ensure_confidence_range(value: float | str | None) -> float | None:
  value = normalize_confidence_value(value)
  if value is None:
    return value
  if value < MEMORY_CONFIDENCE_MIN or value > MEMORY_CONFIDENCE_MAX:
    raise ValueError(
      f"confidence must be between {MEMORY_CONFIDENCE_MIN} and {MEMORY_CONFIDENCE_MAX} inclusive. "
      "Use a numeric value such as 0.85."
    )
  return value


def ensure_non_empty_text(value: str, *, field_name: str) -> str:
  if len(value) < MEMORY_STATEMENT_MIN_LENGTH:
    raise ValueError(f"{field_name} must not be empty. Provide at least one character.")
  return value


def ensure_top_k(value: int) -> int:
  if value < QUERY_TOP_K_MIN or value > QUERY_TOP_K_MAX:
    raise ValueError(
      f"top_k must be between {QUERY_TOP_K_MIN} and {QUERY_TOP_K_MAX} inclusive. "
      "Pick a value within that range."
    )
  return value


def ensure_agent_id(value: str | None) -> str | None:
  if value is None:
    return value
  if not value:
    raise ValueError("agent_id must not be empty when provided.")
  if len(value) > CANDIDATE_AGENT_ID_MAX_LENGTH:
    raise ValueError(
      f"agent_id is too long: got {len(value)} characters, maximum is {CANDIDATE_AGENT_ID_MAX_LENGTH}. "
      "Shorten the identifier and try again."
    )
  return value


def ensure_candidate_write_mode(value: str | None) -> str | None:
  if value is None:
    return value
  if value not in ALLOWED_CANDIDATE_WRITE_MODES:
    raise ValueError(
      f"unsupported write_mode '{value}'. Allowed values: {', '.join(ALLOWED_CANDIDATE_WRITE_MODES)}. "
      "Use 'create' for a new memory item or 'upsert' to replace a close existing one."
    )
  return value


def ensure_review_session_id(value: str | None) -> str | None:
  if value is None:
    return value
  normalized = value.strip()
  if not normalized:
    raise ValueError("review_session_id must not be empty when provided.")
  if len(normalized) > REVIEW_SESSION_ID_MAX_LENGTH:
    raise ValueError(
      f"review_session_id is too long: got {len(normalized)} characters, maximum is {REVIEW_SESSION_ID_MAX_LENGTH}. "
      "Shorten the identifier and try again."
    )
  return normalized


def ensure_review_session_label(value: str | None) -> str | None:
  if value is None:
    return value
  normalized = value.strip()
  if not normalized:
    raise ValueError("review_session_label must not be empty when provided.")
  if len(normalized) > REVIEW_SESSION_LABEL_MAX_LENGTH:
    raise ValueError(
      f"review_session_label is too long: got {len(normalized)} characters, maximum is {REVIEW_SESSION_LABEL_MAX_LENGTH}. "
      "Shorten the label and try again."
    )
  return normalized


def ensure_evidence_ref(value: str | None) -> str | None:
  if value is None:
    return value
  normalized = value.strip()
  if not normalized:
    raise ValueError("evidence_ref must not be empty when provided.")
  if len(normalized) > EVIDENCE_REF_MAX_LENGTH:
    raise ValueError(
      f"evidence_ref is too long: got {len(normalized)} characters, maximum is {EVIDENCE_REF_MAX_LENGTH}. "
      "Shorten the reference and try again."
    )
  return normalized


def ensure_source_excerpt(value: str | None) -> str | None:
  if value is None:
    return value
  normalized = value.strip()
  if not normalized:
    raise ValueError("source_excerpt must not be empty when provided.")
  if len(normalized) > SOURCE_EXCERPT_MAX_LENGTH:
    raise ValueError(
      f"source_excerpt is too long: got {len(normalized)} characters, maximum is {SOURCE_EXCERPT_MAX_LENGTH}. "
      "Trim the excerpt and try again."
    )
  return normalized


def ensure_memory_statement(value: str) -> str:
  if len(value) < MEMORY_STATEMENT_MIN_LENGTH:
    raise ValueError(
      f"statement is too short: got {len(value)} characters, minimum is {MEMORY_STATEMENT_MIN_LENGTH}. "
      "Expand the text and try again."
    )
  return value


def ensure_candidate_statement(value: str, *, kind: str) -> str:
  statement = value.strip()
  if kind == "note":
    if not statement:
      raise ValueError("note statement must not be empty. Provide at least one character.")
    if len(statement) > NOTE_STATEMENT_MAX_LENGTH:
      raise ValueError(
        f"note statement is too long: got {len(statement)} characters, maximum is {NOTE_STATEMENT_MAX_LENGTH}. "
        "Shorten the note or split it into multiple entries."
      )
    return statement
  if len(statement) < CANDIDATE_STATEMENT_MIN_LENGTH:
    raise ValueError(
      f"statement is too short: got {len(statement)} characters, allowed range is "
      f"{CANDIDATE_STATEMENT_MIN_LENGTH}-{CANDIDATE_STATEMENT_MAX_LENGTH}. Expand the text and try again."
    )
  if len(statement) > CANDIDATE_STATEMENT_MAX_LENGTH:
    raise ValueError(
      f"statement is too long: got {len(statement)} characters, maximum is {CANDIDATE_STATEMENT_MAX_LENGTH}. "
      "Shorten the text or split it into multiple entries."
    )
  return statement


def _format_validation_error(error: dict[str, Any]) -> dict[str, Any]:
  loc = [str(part) for part in error.get("loc", []) if part != "body"]
  entry = {
    "loc": loc or ["__root__"],
    "field": ".".join(loc) if loc else "request",
    "message": error.get("msg", "validation error"),
  }
  if "input" in error:
    entry["input"] = error["input"]
  return entry

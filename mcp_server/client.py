from __future__ import annotations

import httpx

from api.schemas import (
  CandidateDecisionResponse,
  MemoryCandidateBulkCreateRequest,
  MemoryCandidateBulkCreateResponse,
  MemoryCandidateCreateRequest,
  MemoryCandidateShortlistRequest,
  MemoryCandidateShortlistResponse,
  MemoryCandidateResponse,
  MemoryCandidateValidateResponse,
  MemoryItemResponse,
  MemoryQueryRequest,
  MemoryQueryResponse,
  MemorySchemaInfoResponse,
  ReviewSessionListResponse,
)
from core.logging import get_logger

logger = get_logger(__name__)


class MnemosApiError(RuntimeError):
  pass


class MnemosRestClient:
  def __init__(
    self,
    *,
    base_url: str,
    timeout_seconds: float,
    client: httpx.Client | None = None,
  ) -> None:
    self.base_url = base_url.rstrip("/")
    self.timeout_seconds = timeout_seconds
    self._client = client or httpx.Client(
      base_url=self.base_url,
      timeout=self.timeout_seconds,
      headers={"User-Agent": "mnemos-mcp-server/0.1.0"},
    )
    self._owns_client = client is None

  def close(self) -> None:
    if self._owns_client:
      self._client.close()

  def query_memory(
    self,
    *,
    query: str,
    domain: str,
    top_k: int,
    kinds: list[str] | None = None,
  ) -> MemoryQueryResponse:
    payload = MemoryQueryRequest(query=query, domain=domain, top_k=top_k, kinds=kinds)
    response = self._request("POST", "/memory/query", json=payload.model_dump())
    return MemoryQueryResponse.model_validate(response.json())

  def get_memory_item(self, item_id: str) -> MemoryItemResponse | None:
    response = self._request("GET", f"/memory/item/{item_id}", allow_404=True)
    if response.status_code == 404:
      return None
    return MemoryItemResponse.model_validate(response.json())

  def get_schema_info(self) -> MemorySchemaInfoResponse:
    response = self._request("GET", "/memory/schema")
    return MemorySchemaInfoResponse.model_validate(response.json())

  def list_review_sessions(self) -> ReviewSessionListResponse:
    response = self._request("GET", "/memory/review-sessions")
    return ReviewSessionListResponse.model_validate(response.json())

  def add_memory_note(
    self,
    *,
    text: str,
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> MemoryCandidateResponse:
    payload = MemoryCandidateCreateRequest(
      domain="interaction",
      kind="note",
      statement=text,
      agent_id="mcp_server",
      metadata={"source_type": "mcp", "source_id": "add_memory_note"},
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    response = self._request("POST", "/memory/candidate", json=payload.model_dump())
    return MemoryCandidateResponse.model_validate(response.json())

  def validate_memory_item(
    self,
    *,
    domain: str,
    kind: str,
    statement: str,
    confidence: float | None = None,
    evidence: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    agent_id: str = "mcp_server",
    write_mode: str = "create",
    source_note_id: str | None = None,
    evidence_ref: str | None = None,
    source_excerpt: str | None = None,
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> MemoryCandidateValidateResponse:
    response = self._request(
      "POST",
      "/memory/candidate/validate",
      json={
        "domain": domain,
        "kind": kind,
        "statement": statement,
        "confidence": confidence,
        "evidence": evidence,
        "metadata": metadata,
        "agent_id": agent_id,
        "write_mode": write_mode,
        "source_note_id": source_note_id,
        "evidence_ref": evidence_ref,
        "source_excerpt": source_excerpt,
        "review_session_id": review_session_id,
        "review_session_label": review_session_label,
      },
    )
    return MemoryCandidateValidateResponse.model_validate(response.json())

  def propose_memory_item(
    self,
    *,
    domain: str,
    kind: str,
    statement: str,
    confidence: float | None = None,
    evidence: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    agent_id: str = "mcp_server",
    write_mode: str = "create",
    source_note_id: str | None = None,
    evidence_ref: str | None = None,
    source_excerpt: str | None = None,
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> MemoryCandidateResponse:
    payload = MemoryCandidateCreateRequest(
      domain=domain,
      kind=kind,
      statement=statement,
      confidence=confidence,
      agent_id=agent_id,
      evidence=evidence,
      metadata=metadata,
      write_mode=write_mode,
      source_note_id=source_note_id,
      evidence_ref=evidence_ref,
      source_excerpt=source_excerpt,
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    response = self._request("POST", "/memory/candidate", json=payload.model_dump())
    return MemoryCandidateResponse.model_validate(response.json())

  def propose_memory_items(
    self,
    *,
    items: list[dict[str, object]],
    agent_id: str = "mcp_server",
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> MemoryCandidateBulkCreateResponse:
    payload = MemoryCandidateBulkCreateRequest(
      items=[
        MemoryCandidateCreateRequest(
          domain=str(item["domain"]),
          kind=str(item["kind"]),
          statement=str(item["statement"]),
          confidence=item.get("confidence"),
          evidence=item.get("evidence"),
          metadata=item.get("metadata"),
          agent_id=str(item.get("agent_id") or agent_id),
          write_mode=str(item.get("write_mode") or "create"),
          source_note_id=item.get("source_note_id"),
          evidence_ref=item.get("evidence_ref"),
          source_excerpt=item.get("source_excerpt"),
          review_session_id=item.get("review_session_id"),
          review_session_label=item.get("review_session_label"),
        )
        for item in items
      ],
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    response = self._request("POST", "/memory/candidates/bulk", json=payload.model_dump())
    return MemoryCandidateBulkCreateResponse.model_validate(response.json())

  def shortlist_memory_items(
    self,
    *,
    items: list[dict[str, object]],
    agent_id: str = "mcp_server",
    review_session_id: str | None = None,
    review_session_label: str | None = None,
  ) -> MemoryCandidateShortlistResponse:
    payload = MemoryCandidateShortlistRequest(
      items=[
        MemoryCandidateCreateRequest(
          domain=str(item["domain"]),
          kind=str(item["kind"]),
          statement=str(item["statement"]),
          confidence=item.get("confidence"),
          evidence=item.get("evidence"),
          metadata=item.get("metadata"),
          agent_id=str(item.get("agent_id") or agent_id),
          write_mode=str(item.get("write_mode") or "create"),
          source_note_id=item.get("source_note_id"),
          evidence_ref=item.get("evidence_ref"),
          source_excerpt=item.get("source_excerpt"),
          review_session_id=item.get("review_session_id"),
          review_session_label=item.get("review_session_label"),
        )
        for item in items
      ],
      review_session_id=review_session_id,
      review_session_label=review_session_label,
    )
    response = self._request("POST", "/memory/candidates/shortlist", json=payload.model_dump())
    return MemoryCandidateShortlistResponse.model_validate(response.json())

  def accept_candidate(self, candidate_id: str) -> CandidateDecisionResponse:
    response = self._request("POST", f"/memory/candidate/{candidate_id}/accept")
    return CandidateDecisionResponse.model_validate(response.json())

  def reject_candidate(self, candidate_id: str, *, reason: str) -> CandidateDecisionResponse:
    response = self._request(
      "POST",
      f"/memory/candidate/{candidate_id}/reject",
      json={"reason": reason},
    )
    return CandidateDecisionResponse.model_validate(response.json())

  def _request(
    self,
    method: str,
    path: str,
    *,
    allow_404: bool = False,
    **kwargs,
  ) -> httpx.Response:
    try:
      response = self._client.request(method, path, **kwargs)
      logger.info(
        "mcp rest call completed",
        extra={
          "event": "mcp_rest_call",
          "method": method,
          "path": path,
          "status_code": response.status_code,
        },
      )
    except httpx.RequestError as exc:
      raise MnemosApiError("mnemos REST API is unavailable") from exc

    if allow_404 and response.status_code == 404:
      return response

    try:
      response.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = _extract_error_detail(response)
      raise MnemosApiError(
        f"mnemos REST API returned {response.status_code}: {detail}"
      ) from exc
    return response


def _extract_error_detail(response: httpx.Response) -> str:
  try:
    payload = response.json()
  except ValueError:
    return response.text or "unexpected response"

  if isinstance(payload, dict) and "detail" in payload:
    detail = payload["detail"]
    if isinstance(detail, str):
      return detail
    if isinstance(detail, dict):
      message = detail.get("message")
      errors = detail.get("errors")
      if isinstance(errors, list) and errors:
        formatted_errors = []
        for error in errors:
          if not isinstance(error, dict):
            continue
          field = error.get("field", "request")
          error_message = error.get("message", "validation error")
          formatted_errors.append(f"{field}: {error_message}")
        if formatted_errors:
          if isinstance(message, str) and message:
            return f"{message} {'; '.join(formatted_errors)}"
          return "; ".join(formatted_errors)
      if isinstance(message, str) and message:
        return message
  return response.text or "unexpected response"

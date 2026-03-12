from __future__ import annotations

import httpx

from api.schemas import (
  CandidateDecisionResponse,
  MemoryCandidateBulkCreateRequest,
  MemoryCandidateBulkCreateResponse,
  MemoryCandidateCreateRequest,
  MemoryCandidateResponse,
  MemoryCandidateValidateResponse,
  MemoryItemResponse,
  MemoryQueryRequest,
  MemoryQueryResponse,
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

  def add_memory_note(self, *, text: str) -> MemoryCandidateResponse:
    payload = MemoryCandidateCreateRequest(
      domain="interaction",
      kind="note",
      statement=text,
      agent_id="mcp_server",
      metadata={"source_type": "mcp", "source_id": "add_memory_note"},
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
  ) -> MemoryCandidateResponse:
    payload = MemoryCandidateCreateRequest(
      domain=domain,
      kind=kind,
      statement=statement,
      confidence=confidence,
      agent_id=agent_id,
      evidence=evidence,
      metadata=metadata,
    )
    response = self._request("POST", "/memory/candidate", json=payload.model_dump())
    return MemoryCandidateResponse.model_validate(response.json())

  def propose_memory_items(
    self,
    *,
    items: list[dict[str, object]],
    agent_id: str = "mcp_server",
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
        )
        for item in items
      ]
    )
    response = self._request("POST", "/memory/candidates/bulk", json=payload.model_dump())
    return MemoryCandidateBulkCreateResponse.model_validate(response.json())

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
  return response.text or "unexpected response"

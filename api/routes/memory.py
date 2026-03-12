from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import (
  get_checked_governance_service,
  get_checked_memory_service,
  get_checked_retrieval_service,
)
from api.schemas import (
  CandidateDecisionResponse,
  CandidateListQuery,
  CandidateRejectRequest,
  MemoryCandidateBulkCreateRequest,
  MemoryCandidateBulkCreateResponse,
  MemoryCandidateCreateRequest,
  MemoryCandidateListResponse,
  MemoryCandidateResponse,
  MemoryCandidateValidateResponse,
  MemoryCreateRequest,
  MemoryItemResponse,
  MemoryQueryRequest,
  MemoryQueryResponse,
)
from pipelines.governance.candidate_runner import CandidateRunner
from services.memory_governance_service import MemoryGovernanceService
from services.memory_service import MemoryService
from services.retrieval_service import RetrievalService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/items", response_model=MemoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_memory_item(
  payload: MemoryCreateRequest,
  service: MemoryService = Depends(get_checked_memory_service),
) -> MemoryItemResponse:
  return MemoryItemResponse.model_validate(service.create_item(payload))


@router.get("/item/{item_id}", response_model=MemoryItemResponse)
def get_memory_item(
  item_id: str,
  service: MemoryService = Depends(get_checked_memory_service),
) -> MemoryItemResponse:
  item = service.get_item(item_id)
  if item is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory item not found")
  return MemoryItemResponse.model_validate(item)


@router.post("/query", response_model=MemoryQueryResponse)
def query_memory(
  payload: MemoryQueryRequest,
  service: RetrievalService = Depends(get_checked_retrieval_service),
) -> MemoryQueryResponse:
  return service.query(payload)


@router.post("/candidate", response_model=MemoryCandidateResponse, status_code=status.HTTP_201_CREATED)
def create_memory_candidate(
  payload: MemoryCandidateCreateRequest,
  service: MemoryGovernanceService = Depends(get_checked_governance_service),
) -> MemoryCandidateResponse:
  return MemoryCandidateResponse.model_validate(service.create_candidate(payload))


@router.post("/candidate/validate", response_model=MemoryCandidateValidateResponse)
def validate_memory_candidate(
  payload: dict[str, object],
  service: MemoryGovernanceService = Depends(get_checked_governance_service),
) -> MemoryCandidateValidateResponse:
  return service.validate_candidate_payload(payload)


@router.post(
  "/candidates/bulk",
  response_model=MemoryCandidateBulkCreateResponse,
  status_code=status.HTTP_201_CREATED,
)
def create_memory_candidates_bulk(
  payload: MemoryCandidateBulkCreateRequest,
  service: MemoryGovernanceService = Depends(get_checked_governance_service),
) -> MemoryCandidateBulkCreateResponse:
  items = service.create_candidates(payload.items)
  return MemoryCandidateBulkCreateResponse(
    created=len(items),
    items=[MemoryCandidateResponse.model_validate(item) for item in items],
  )


@router.get("/candidates", response_model=MemoryCandidateListResponse)
def list_memory_candidates(
  status_value: str | None = Query(default=None, alias="status"),
  domain: str | None = Query(default=None),
  kind: str | None = Query(default=None),
  service: MemoryGovernanceService = Depends(get_checked_governance_service),
) -> MemoryCandidateListResponse:
  query = CandidateListQuery(status=status_value, domain=domain, kind=kind)
  items = service.list_candidates(status=query.status, domain=query.domain, kind=query.kind)
  return MemoryCandidateListResponse(
    items=[MemoryCandidateResponse.model_validate(item) for item in items]
  )


@router.post("/candidate/{candidate_id}/accept", response_model=CandidateDecisionResponse)
def accept_memory_candidate(
  candidate_id: str,
  governance_service: MemoryGovernanceService = Depends(get_checked_governance_service),
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> CandidateDecisionResponse:
  decision = CandidateRunner(governance_service, memory_service).accept(candidate_id)
  return CandidateDecisionResponse(
    candidate=MemoryCandidateResponse.model_validate(decision.candidate),
    merged_item=MemoryItemResponse.model_validate(decision.merged_item) if decision.merged_item else None,
    validation_errors=decision.validation_errors,
  )


@router.post("/candidate/{candidate_id}/reject", response_model=CandidateDecisionResponse)
def reject_memory_candidate(
  candidate_id: str,
  payload: CandidateRejectRequest,
  service: MemoryGovernanceService = Depends(get_checked_governance_service),
) -> CandidateDecisionResponse:
  candidate = service.reject_candidate(candidate_id, reason=payload.reason)
  return CandidateDecisionResponse(
    candidate=MemoryCandidateResponse.model_validate(candidate),
    merged_item=None,
    validation_errors=[],
  )

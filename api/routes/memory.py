from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_checked_memory_service, get_checked_retrieval_service
from api.schemas import (
  MemoryCreateRequest,
  MemoryItemResponse,
  MemoryQueryRequest,
  MemoryQueryResponse,
)
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

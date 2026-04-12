from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from services.memory_governance_service import MemoryGovernanceService
from services.memory_service import MemoryService
from services.retrieval_service import RetrievalService
from pipelines.wiki.wiki_runner import WikiBuildRunner


def get_session(request: Request) -> Generator[Session, None, None]:
  session_factory = request.app.state.session_factory
  session = session_factory()
  try:
    yield session
  finally:
    session.close()


def get_memory_service(request: Request) -> MemoryService:
  return request.app.state.memory_service


def get_retrieval_service(request: Request) -> RetrievalService:
  return request.app.state.retrieval_service


def get_governance_service(request: Request) -> MemoryGovernanceService:
  return request.app.state.governance_service


def get_wiki_runner(request: Request) -> WikiBuildRunner:
  return getattr(request.app.state, "wiki_runner", None)


def get_checked_memory_service(
  service: MemoryService = Depends(get_memory_service),
) -> MemoryService:
  if service is None:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="memory service unavailable",
    )
  return service


def get_checked_retrieval_service(
  service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalService:
  if service is None:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="retrieval service unavailable",
    )
  return service


def get_checked_governance_service(
  service: MemoryGovernanceService = Depends(get_governance_service),
) -> MemoryGovernanceService:
  if service is None:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="governance service unavailable",
    )
  return service


def get_checked_wiki_runner(
  runner: WikiBuildRunner = Depends(get_wiki_runner),
) -> WikiBuildRunner:
  if runner is None:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="wiki runner unavailable",
    )
  return runner

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_checked_memory_service, get_checked_wiki_runner
from api.schemas import WikiPageListResponse, WikiPageResponse, WikiPageSummaryResponse
from pipelines.wiki.wiki_runner import WikiBuildRunner
from services.memory_service import MemoryService

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


def _load_wiki_page(
  *,
  page_name: str,
  memory_service: MemoryService,
  runner: WikiBuildRunner,
):
  page = memory_service.get_wiki_page(page_name)
  if page is None or page.invalidated_at is not None:
    runner.run(page_name=page_name)
    page = memory_service.get_wiki_page(page_name)
  return page


@router.get("/pages", response_model=WikiPageListResponse)
def list_wiki_pages(
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> WikiPageListResponse:
  return WikiPageListResponse(
    items=[WikiPageSummaryResponse.model_validate(page) for page in memory_service.list_wiki_pages()],
  )


@router.get("/pages/{name}", response_model=WikiPageResponse)
def get_wiki_page(
  name: str,
  memory_service: MemoryService = Depends(get_checked_memory_service),
  runner: WikiBuildRunner = Depends(get_checked_wiki_runner),
) -> WikiPageResponse:
  page = _load_wiki_page(page_name=name, memory_service=memory_service, runner=runner)
  if page is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wiki page not found")
  return WikiPageResponse.model_validate(page)


@router.post("/pages/{name}/regenerate", response_model=WikiPageResponse)
def regenerate_wiki_page(
  name: str,
  memory_service: MemoryService = Depends(get_checked_memory_service),
  runner: WikiBuildRunner = Depends(get_checked_wiki_runner),
) -> WikiPageResponse:
  page = memory_service.get_wiki_page(name)
  if page is not None:
    memory_service.upsert_wiki_page(
      page_name=page.page_name,
      title=page.title,
      content_md=page.content_md,
      facts_count=page.facts_count,
      reflections_count=page.reflections_count,
      generated_at=page.generated_at,
      invalidated_at=datetime.now(UTC),
    )
  page = _load_wiki_page(page_name=name, memory_service=memory_service, runner=runner)
  if page is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wiki page not found")
  return WikiPageResponse.model_validate(page)

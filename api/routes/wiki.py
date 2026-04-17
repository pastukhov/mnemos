from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.deps import (
  get_checked_memory_service,
  get_checked_wiki_canonicalization_runner,
  get_checked_wiki_lint_runner,
  get_checked_wiki_query_runner,
  get_checked_wiki_runner,
)
from api.schemas import (
  WikiLintFindingResponse,
  WikiLintResponse,
  WikiMaintenanceActionResponse,
  WikiMaintenanceHistoryResponse,
  WikiQueryRequest,
  WikiQueryResponse,
  WikiPageListResponse,
  WikiPageResponse,
  WikiPageSummaryResponse,
)
from pipelines.wiki.wiki_canonicalization_runner import WikiCanonicalizationRunner
from pipelines.wiki.wiki_lint_runner import WikiLintRunner
from pipelines.wiki.wiki_query_runner import WikiQueryRunner
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


@router.post("/lint", response_model=WikiLintResponse)
def lint_wiki(
  domain: str | None = Query(default=None),
  fix: bool = Query(default=False),
  runner: WikiLintRunner = Depends(get_checked_wiki_lint_runner),
) -> WikiLintResponse:
  report = runner.run(domain=domain, fix=fix)
  findings = [
    WikiLintFindingResponse(
      code=finding.code,
      severity=finding.severity,
      count=finding.count,
      items=finding.items,
    )
    for finding in report.findings()
  ]
  return WikiLintResponse(
    stale_pages=report.stale_pages,
    empty_pages=report.empty_pages,
    orphan_facts_count=report.orphan_facts_count,
    contradictions=report.contradictions,
    fixed_pages=report.fixed_pages,
    missing_related_pages=report.missing_related_pages,
    missing_provenance_pages=report.missing_provenance_pages,
    missing_source_refs_pages=report.missing_source_refs_pages,
    missing_source_highlights_pages=report.missing_source_highlights_pages,
    low_source_coverage_pages=report.low_source_coverage_pages,
    unresolved_source_refs=report.unresolved_source_refs,
    broken_wiki_links=report.broken_wiki_links,
    canonical_drift_pages=report.canonical_drift_pages,
    orphaned_query_pages=report.orphaned_query_pages,
    stale_navigation_pages=report.stale_navigation_pages,
    overmerged_query_pages=report.overmerged_query_pages,
    canonicalization_candidates=report.canonicalization_candidates,
    missing_page_candidates=report.missing_page_candidates,
    weakly_connected_pages=report.weakly_connected_pages,
    editorial_structure_issues=report.editorial_structure_issues,
    findings=findings,
  )


@router.post("/query", response_model=WikiQueryResponse)
def query_wiki(
  payload: WikiQueryRequest,
  runner: WikiQueryRunner = Depends(get_checked_wiki_query_runner),
) -> WikiQueryResponse:
  result = runner.query(
    payload.question,
    domain=payload.domain,
    top_k=payload.top_k,
    auto_persist=payload.auto_persist,
    persist_page_name=payload.persist_page_name,
    persist_title=payload.persist_title,
  )
  return WikiQueryResponse(
    answer=result.answer,
    sources=result.sources,
    confidence=result.confidence,
    persisted_page_name=result.persisted_page_name,
    promoted_canonical_target=result.promoted_canonical_target,
    outcome=result.outcome,
  )


@router.post("/maintenance/refresh", response_model=WikiMaintenanceActionResponse)
def maintenance_refresh(
  runner: WikiQueryRunner = Depends(get_checked_wiki_query_runner),
) -> WikiMaintenanceActionResponse:
  refreshed, pruned, deduped, promoted = runner.refresh_auto_persisted_pages()
  return WikiMaintenanceActionResponse(
    action="refresh",
    refreshed=refreshed,
    pruned=pruned,
    deduped=deduped,
    promoted=promoted,
  )


@router.post("/maintenance/canonicalize", response_model=WikiMaintenanceActionResponse)
def maintenance_canonicalize(
  lint_runner: WikiLintRunner = Depends(get_checked_wiki_lint_runner),
  canonicalization_runner: WikiCanonicalizationRunner = Depends(get_checked_wiki_canonicalization_runner),
) -> WikiMaintenanceActionResponse:
  lint_report = lint_runner.run()
  if not lint_report.canonicalization_candidates:
    return WikiMaintenanceActionResponse(action="canonicalize")
  canon_report = canonicalization_runner.run(candidates=lint_report.canonicalization_candidates)
  return WikiMaintenanceActionResponse(
    action="canonicalize",
    canonicalized=canon_report.canonicalized_pages,
    canonical_targets=canon_report.canonical_targets,
  )


@router.post("/maintenance/rebuild", response_model=WikiMaintenanceActionResponse)
def maintenance_rebuild(
  memory_service: MemoryService = Depends(get_checked_memory_service),
  runner: WikiBuildRunner = Depends(get_checked_wiki_runner),
) -> WikiMaintenanceActionResponse:
  stale_pages = memory_service.list_invalidated_wiki_pages()
  rebuilt: list[str] = []
  for page in stale_pages:
    runner.run(page_name=page.page_name)
    rebuilt.append(page.page_name)
  return WikiMaintenanceActionResponse(action="rebuild", rebuilt=rebuilt)


@router.get("/maintenance/history", response_model=WikiMaintenanceHistoryResponse)
def maintenance_history(request: Request) -> WikiMaintenanceHistoryResponse:
  worker = getattr(request.app.state, "pipeline_worker", None)
  if worker is None:
    return WikiMaintenanceHistoryResponse(available=False)
  last_report = getattr(worker, "_last_report", None)
  if last_report is None:
    return WikiMaintenanceHistoryResponse(available=False)
  return WikiMaintenanceHistoryResponse(
    available=True,
    fact_domains=last_report.fact_domains,
    reflection_domains=last_report.reflection_domains,
    wiki_pages=last_report.wiki_pages,
    refreshed_query_pages=last_report.refreshed_query_pages,
    pruned_query_pages=last_report.pruned_query_pages,
    deduped_query_pages=last_report.deduped_query_pages,
    promoted_query_pages=last_report.promoted_query_pages,
    canonicalized_query_pages=last_report.canonicalized_query_pages,
    canonicalized_targets=last_report.canonicalized_targets,
    lint_action_required_findings=last_report.lint_action_required_findings,
    lint_warning_findings=last_report.lint_warning_findings,
    lint_canonical_drift_pages=last_report.lint_canonical_drift_pages,
    lint_orphaned_query_pages=last_report.lint_orphaned_query_pages,
    errors=last_report.errors,
  )

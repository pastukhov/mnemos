from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import WikiPageCache


class WikiPageCacheRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def get(self, page_name: str) -> WikiPageCache | None:
    query = select(WikiPageCache).where(WikiPageCache.page_name == page_name)
    return self.session.execute(query).scalar_one_or_none()

  def list_pages(self) -> list[WikiPageCache]:
    query = select(WikiPageCache).order_by(WikiPageCache.page_name.asc())
    return list(self.session.execute(query).scalars())

  def list_invalidated_pages(self) -> list[WikiPageCache]:
    query = (
      select(WikiPageCache)
      .where(WikiPageCache.invalidated_at.is_not(None))
      .order_by(WikiPageCache.invalidated_at.asc(), WikiPageCache.page_name.asc())
    )
    return list(self.session.execute(query).scalars())

  def upsert_page(
    self,
    *,
    page_name: str,
    title: str,
    content_md: str,
    facts_count: int,
    reflections_count: int,
    metadata: dict[str, object] | None = None,
    generated_at: datetime | None = None,
    invalidated_at: datetime | None = None,
  ) -> WikiPageCache:
    page = self.get(page_name)
    if page is not None:
      return self._update_page(
        page,
        title=title,
        content_md=content_md,
        facts_count=facts_count,
        reflections_count=reflections_count,
        metadata=metadata,
        generated_at=generated_at,
        invalidated_at=invalidated_at,
      )

    page = WikiPageCache(
      page_name=page_name,
      title=title,
      content_md=content_md,
      facts_count=facts_count,
      reflections_count=reflections_count,
      metadata_json=metadata,
      generated_at=generated_at or datetime.now(UTC),
      invalidated_at=invalidated_at,
    )
    self.session.add(page)
    try:
      self.session.flush()
      return page
    except IntegrityError:
      self.session.rollback()
      page = self.get(page_name)
      if page is None:
        raise
      return self._update_page(
        page,
        title=title,
        content_md=content_md,
        facts_count=facts_count,
        reflections_count=reflections_count,
        metadata=metadata,
        generated_at=generated_at,
        invalidated_at=invalidated_at,
      )

  def mark_invalidated(self, page_name: str, *, invalidated_at: datetime | None = None) -> WikiPageCache | None:
    page = self.get(page_name)
    if page is None:
      return None
    page.invalidated_at = page.invalidated_at or invalidated_at or datetime.now(UTC)
    self.session.add(page)
    self.session.flush()
    return page

  def clear_invalidated(self, page_name: str) -> WikiPageCache | None:
    page = self.get(page_name)
    if page is None:
      return None
    page.invalidated_at = None
    self.session.add(page)
    self.session.flush()
    return page

  def delete_page(self, page_name: str) -> bool:
    page = self.get(page_name)
    if page is None:
      return False
    self.session.delete(page)
    self.session.flush()
    return True

  def _update_page(
    self,
    page: WikiPageCache,
    *,
    title: str,
    content_md: str,
    facts_count: int,
    reflections_count: int,
    metadata: dict[str, object] | None,
    generated_at: datetime | None,
    invalidated_at: datetime | None,
  ) -> WikiPageCache:
    page.title = title
    page.content_md = content_md
    page.facts_count = facts_count
    page.reflections_count = reflections_count
    page.metadata_json = metadata
    page.generated_at = generated_at or datetime.now(UTC)
    page.invalidated_at = invalidated_at
    self.session.add(page)
    self.session.flush()
    return page

"""Tests for wiki page cache storage helpers."""

from datetime import UTC, datetime

from db.repositories.wiki_page_cache import WikiPageCacheRepository


def test_wiki_page_cache_repository_upsert_and_list(client):
  with client.app.state.session_factory() as session:
    repository = WikiPageCacheRepository(session)
    repository.upsert_page(
      page_name="career",
      title="Career",
      content_md="# Career",
      facts_count=3,
      reflections_count=1,
      generated_at=datetime.now(UTC),
    )
    session.commit()

  pages = client.app.state.memory_service.list_wiki_pages()

  assert len(pages) == 1
  assert pages[0].page_name == "career"
  assert pages[0].title == "Career"


def test_wiki_page_cache_repository_lists_invalidated_pages(client):
  page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Career",
    content_md="# Career",
    facts_count=3,
    reflections_count=1,
  )
  assert page.invalidated_at is None

  with client.app.state.session_factory() as session:
    repository = WikiPageCacheRepository(session)
    repository.mark_invalidated("career")
    session.commit()

  invalidated = client.app.state.memory_service.list_invalidated_wiki_pages()

  assert len(invalidated) == 1
  assert invalidated[0].page_name == "career"
  assert invalidated[0].invalidated_at is not None

from __future__ import annotations

import pytest

from workers.pipeline_worker import PipelineWorker


@pytest.mark.asyncio
async def test_pipeline_worker_processes_raw_items_into_facts_reflections_and_wiki(client):
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What motivates you?\nAnswer: I prefer building automated systems; I enjoy reducing repetitive manual work.",
      "confidence": 0.95,
      "metadata": {"source_type": "questionnaire", "source_id": "q_1", "topic": "motivation"},
    },
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What do you value?\nAnswer: I value observable delivery; I prefer reusable systems.",
      "confidence": 0.95,
      "metadata": {"source_type": "questionnaire", "source_id": "q_2", "topic": "motivation"},
    },
  )

  worker = client.app.state.pipeline_worker

  report = await worker.run_once()

  assert report.errors == 0
  assert report.fact_domains == ["self"]
  assert report.reflection_domains == ["self"]
  assert report.wiki_domains == ["self"]
  assert report.wiki_pages == []

  facts = client.app.state.memory_service.list_items_by_domain_kind(domain="self", kind="fact")
  reflections = client.app.state.memory_service.list_items_by_domain_kind(domain="self", kind="reflection")

  assert len(facts) == 4
  assert len(reflections) == 1

  page = client.app.state.memory_service.get_wiki_page("career")

  assert page is not None
  assert page.invalidated_at is None
  assert page.facts_count == 4
  assert page.reflections_count == 1
  assert "stable motivation pattern" in page.content_md


@pytest.mark.asyncio
async def test_pipeline_worker_rebuilds_invalidated_wiki_pages(client):
  client.app.state.settings.wiki_min_facts_per_page = 1
  initial_page = client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Карьера и навыки",
    content_md="# stale",
    facts_count=0,
    reflections_count=0,
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Карьера и навыки",
    content_md="# stale",
    facts_count=0,
    reflections_count=0,
    generated_at=initial_page.generated_at,
    invalidated_at=initial_page.generated_at,
  )
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User builds reliable automation systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "manual", "source_id": "fact_1", "topic": "career"},
    },
  )

  worker = PipelineWorker(
    memory_service=client.app.state.memory_service,
    fact_runner=client.app.state.fact_runner,
    reflection_runner=client.app.state.reflection_runner,
    wiki_runner=client.app.state.wiki_runner,
    interval_seconds=60.0,
  )

  report = await worker.run_once()

  assert report.errors == 0
  assert report.fact_domains == []
  assert report.reflection_domains == []
  assert report.wiki_domains == []
  assert report.wiki_pages == ["career"]

  page = client.app.state.memory_service.get_wiki_page("career")

  assert page is not None
  assert page.invalidated_at is None
  assert "User builds reliable automation systems." in page.content_md

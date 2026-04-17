def test_web_shell_renders_homepage(client):
  response = client.get("/")

  assert response.status_code == 200
  assert "Mnemos" in response.text
  assert "Добавить первую запись" in response.text
  assert 'data-nav-target="wiki"' in response.text
  assert 'data-panel="wiki"' in response.text
  assert 'id="wiki-pages"' in response.text
  assert 'id="wiki-page-content"' in response.text
  assert 'data-lang-switch="ru"' in response.text
  assert 'data-lang-switch="en"' in response.text
  assert "/ui/static/app.js" in response.text


def test_web_shell_accepts_initial_language_override(client):
  response = client.get("/ui", params={"lang": "en"})

  assert response.status_code == 200
  assert 'data-initial-lang="en"' in response.text


def test_web_overview_reports_counts(client):
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "note",
      "statement": "User prefers clear interfaces.",
    },
  )
  client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers clear interfaces in tools.",
      "agent_id": "web_ui",
    },
  )

  response = client.get("/ui/api/overview")
  body = response.json()

  assert response.status_code == 200
  assert body["status"] == "ready"
  assert body["pending_candidates"] == 1
  assert "wiki_pages:0" in body["features"]
  assert body["wiki"]["total_pages"] == 0
  assert body["wiki"]["canonical_pages"] == 0
  self_domain = next(item for item in body["domains"] if item["domain"] == "self")
  assert self_domain["items_total"] == 1


def test_web_wiki_health_reports_page_kinds_and_candidates(client):
  client.app.state.memory_service.upsert_wiki_page(
    page_name="career",
    title="Карьера и навыки",
    content_md="# Career",
    facts_count=3,
    reflections_count=1,
    metadata={"page_kind": "canonical", "origin": "schema", "domains": ["self"], "themes": []},
  )
  client.app.state.memory_service.upsert_wiki_page(
    page_name="qa-self-systems",
    title="Q&A: Systems",
    content_md=(
      "# Q&A: Systems\n\n"
      "## Query\n\n"
      "What kind of systems does the user build?\n\n"
      "## Answer\n\n"
      "Answer.\n\n"
      "## Sources\n\n"
      "- [career](wiki:career)\n\n"
      "## Merge Provenance\n\n"
      "- qa-self-a :: A?\n"
      "- qa-self-b :: B?\n"
      "- qa-self-c :: C?\n"
      "- qa-self-d :: D?\n"
    ),
    facts_count=4,
    reflections_count=0,
    metadata={"page_kind": "query", "origin": "query_answer", "domains": ["self"], "merge_count": 4},
  )

  response = client.get("/ui/api/wiki/health")
  body = response.json()

  assert response.status_code == 200
  assert body["total_pages"] == 2
  assert body["canonical_pages"] == 1
  assert body["query_pages"] == 1
  assert body["canonical_drift_pages"] == []
  assert body["orphaned_query_pages"] == []
  assert body["stale_navigation_pages"] == []
  assert body["action_required_findings"] == [
    "missing_source_refs_pages",
    "canonicalization_candidates",
  ]
  assert body["warning_findings"] == [
    "missing_provenance_pages",
    "missing_source_highlights_pages",
    "overmerged_query_pages",
    "editorial_structure_issues",
  ]
  assert body["overmerged_query_pages"] == ["qa-self-systems (4/3)"]
  assert body["canonicalization_candidates"] == ["qa-self-systems -> career"]
  assert body["missing_page_candidates"] == []


def test_web_import_preview_and_apply_are_idempotent(client):
  payload = {
    "filename": "notes.txt",
    "domain": "self",
    "kind": "note",
    "content": "First note about observability.\n\nSecond note about YAML configs.",
  }

  preview_response = client.post("/ui/api/import/preview", json=payload)
  preview_body = preview_response.json()

  assert preview_response.status_code == 200
  assert preview_body["detected_format"] == "text"
  assert len(preview_body["items"]) == 2

  first_apply = client.post("/ui/api/import/apply", json=payload)
  second_apply = client.post("/ui/api/import/apply", json=payload)

  assert first_apply.status_code == 200
  assert first_apply.json()["created"] == 2
  assert first_apply.json()["skipped"] == 0
  assert second_apply.status_code == 200
  assert second_apply.json()["created"] == 0
  assert second_apply.json()["skipped"] == 2


def test_web_items_endpoint_lists_recent_items(client):
  client.post(
    "/memory/items",
    json={
      "domain": "project",
      "kind": "decision",
      "statement": "Use PostgreSQL as the source of truth.",
    },
  )
  client.post(
    "/memory/items",
    json={
      "domain": "project",
      "kind": "task",
      "statement": "Prepare onboarding copy for the web UI.",
    },
  )

  response = client.get("/ui/api/items", params={"domain": "project", "limit": 10})
  body = response.json()

  assert response.status_code == 200
  assert len(body["items"]) == 2
  assert body["items"][0]["statement"] == "Prepare onboarding copy for the web UI."

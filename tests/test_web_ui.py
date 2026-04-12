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
  self_domain = next(item for item in body["domains"] if item["domain"] == "self")
  assert self_domain["items_total"] == 1


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

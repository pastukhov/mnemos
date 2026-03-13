from uuid import UUID

from db.models import CandidateMetric, MemoryCandidate, MemoryItem, MemoryRelation


def test_candidate_creation_and_listing(client):
  create_response = client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers observable architectures.",
      "confidence": 0.78,
      "agent_id": "codex_cli",
      "evidence": {"source_fact_ids": []},
      "metadata": {"source_type": "mcp", "source_id": "candidate_test"},
    },
  )

  assert create_response.status_code == 201
  assert create_response.json()["status"] == "pending"

  list_response = client.get("/memory/candidates", params={"status": "pending"})
  items = list_response.json()["items"]

  assert list_response.status_code == 200
  assert len(items) == 1
  assert items[0]["agent_id"] == "codex_cli"


def test_schema_endpoint_exposes_constraints(client):
  response = client.get("/memory/schema")

  assert response.status_code == 200
  body = response.json()["schema"]
  assert "self" in body["domains"]
  assert "fact" in body["kinds"]
  assert body["memory_candidate"]["note_statement"]["max_length"] == 50_000
  assert body["confidence"]["aliases"]["high"] == 0.9
  assert "upsert" in body["memory_candidate"]["write_modes"]["allowed_values"]


def test_candidate_accept_merges_into_memory_and_creates_relations(client):
  raw_one = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What do you prefer?\nAnswer: I prefer observable architectures.",
      "confidence": 0.9,
      "metadata": {"source_type": "questionnaire", "source_id": "q1", "topic": "work_style"},
    },
  ).json()
  raw_two = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": "Question: What do you value?\nAnswer: I value decomposable systems.",
      "confidence": 0.9,
      "metadata": {"source_type": "questionnaire", "source_id": "q2", "topic": "work_style"},
    },
  ).json()
  fact_one = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers observable architectures.",
      "confidence": 0.8,
      "metadata": {"source_type": "fact_extraction", "source_id": "f1", "source_item_id": raw_one["id"]},
    },
  ).json()
  fact_two = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User values decomposable systems.",
      "confidence": 0.8,
      "metadata": {"source_type": "fact_extraction", "source_id": "f2", "source_item_id": raw_two["id"]},
    },
  ).json()
  candidate = client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "reflection",
      "statement": "User consistently prefers observable and decomposable architectures.",
      "confidence": 0.83,
      "agent_id": "codex_cli",
      "evidence": {"source_fact_ids": [fact_one["id"], fact_two["id"]]},
    },
  ).json()

  accept_response = client.post(f"/memory/candidate/{candidate['id']}/accept")
  body = accept_response.json()

  assert accept_response.status_code == 200
  assert body["candidate"]["status"] == "accepted"
  assert body["merged_item"]["kind"] == "reflection"
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 5

  with client.app.state.session_factory() as session:
    candidates = session.query(MemoryCandidate).all()
    merged_items = session.query(MemoryItem).filter(MemoryItem.kind == "reflection").all()
    relations = session.query(MemoryRelation).filter(MemoryRelation.relation_type == "supported_by").all()
    metrics = session.query(CandidateMetric).all()

  assert len(candidates) == 1
  assert len(merged_items) == 1
  assert len(relations) == 2
  assert metrics[0].created_total == 1
  assert metrics[0].accepted_total == 1


def test_candidate_accept_rejects_duplicate_statement(client):
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers Kubernetes.",
      "confidence": 0.9,
      "metadata": {"source_type": "seed", "source_id": "fact_existing"},
    },
  )
  candidate = client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers Kubernetes.",
      "confidence": 0.7,
      "agent_id": "codex_cli",
    },
  ).json()

  accept_response = client.post(f"/memory/candidate/{candidate['id']}/accept")
  body = accept_response.json()

  assert accept_response.status_code == 200
  assert body["candidate"]["status"] == "rejected"
  assert body["merged_item"] is None
  assert "duplicates existing accepted memory" in body["validation_errors"][0]

  with client.app.state.session_factory() as session:
    metrics = session.query(CandidateMetric).all()
  assert metrics[0].validation_failures_total == 1


def test_candidate_reject_endpoint_marks_candidate_rejected(client):
  candidate = client.post(
    "/memory/candidate",
    json={
      "domain": "interaction",
      "kind": "note",
      "statement": "Remember to ask the user about deployment preferences.",
      "agent_id": "codex_cli",
    },
  ).json()

  reject_response = client.post(
    f"/memory/candidate/{candidate['id']}/reject",
    json={"reason": "manual review rejected it"},
  )

  assert reject_response.status_code == 200
  assert reject_response.json()["candidate"]["status"] == "rejected"


def test_candidate_validate_endpoint_returns_errors_without_writing(client):
  response = client.post(
    "/memory/candidate/validate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "short",
      "confidence": 0.8,
    },
  )

  assert response.status_code == 200
  assert response.json()["valid"] is False
  assert response.json()["errors"][0]["loc"] == ["__root__"]

  list_response = client.get("/memory/candidates", params={"status": "pending"})
  assert list_response.json()["items"] == []


def test_candidate_bulk_create_creates_multiple_candidates(client):
  response = client.post(
    "/memory/candidates/bulk",
    json={
      "items": [
        {
          "domain": "self",
          "kind": "fact",
          "statement": "User prefers observable architectures.",
          "confidence": 0.8,
          "agent_id": "codex_cli",
        },
        {
          "domain": "interaction",
          "kind": "note",
          "statement": "Remember to ask follow-up questions about deployment constraints.",
          "agent_id": "codex_cli",
        },
      ]
    },
  )

  assert response.status_code == 201
  body = response.json()
  assert body["created"] == 2
  assert [item["kind"] for item in body["items"]] == ["fact", "note"]
  assert body["review_session"] is not None


def test_long_note_candidate_is_accepted(client):
  statement = "Long note. " * 800

  response = client.post(
    "/memory/candidate",
    json={
      "domain": "interaction",
      "kind": "note",
      "statement": statement,
      "agent_id": "codex_cli",
    },
  )

  assert response.status_code == 201
  body = response.json()
  assert body["kind"] == "note"
  assert body["statement"] == statement.strip()


def test_candidate_create_returns_structured_validation_errors(client):
  response = client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "goal",
      "statement": "User wants a better workflow.",
      "confidence": "certain",
    },
  )

  assert response.status_code == 422
  body = response.json()["detail"]
  assert body["message"] == "Request validation failed."
  messages = [item["message"] for item in body["errors"]]
  assert any("Allowed values" in message for message in messages)
  assert any("Use a numeric value such as 0.85" in message for message in messages)


def test_candidate_validate_supports_confidence_alias_and_dedupe_hints(client):
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers structured review workflows.",
      "confidence": 0.82,
    },
  )

  response = client.post(
    "/memory/candidate/validate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers structured review workflows for memory updates.",
      "confidence": "high",
      "write_mode": "upsert",
    },
  )

  assert response.status_code == 200
  body = response.json()
  assert body["candidate"]["confidence"] == 0.9
  assert body["preview"]["write_mode"] == "upsert"
  assert body["dedupe_hints"]
  assert body["preview"]["suggested_action"] in {"consider_upsert_existing_memory", "upsert_existing_memory"}


def test_candidate_shortlist_groups_items_into_review_session(client):
  response = client.post(
    "/memory/candidates/shortlist",
    json={
      "review_session_label": "Interview 2026-03-13",
      "items": [
        {
          "domain": "self",
          "kind": "fact",
          "statement": "User prefers explicit API contracts.",
          "confidence": "medium",
        },
        {
          "domain": "interaction",
          "kind": "note",
          "statement": "Interview raw note. " * 50,
        },
      ],
    },
  )

  assert response.status_code == 200
  body = response.json()
  assert body["ready_count"] == 2
  assert body["review_session"]["id"].startswith("review-")
  assert body["items"][0]["preview"]["review_session"]["label"] == "Interview 2026-03-13"


def test_interview_propose_creates_review_session_and_source_provenance(client):
  note = client.post(
    "/memory/items",
    json={
      "domain": "interaction",
      "kind": "note",
      "statement": "Interview answer about observability and explicit contracts.",
    },
  ).json()

  response = client.post(
    "/memory/interview/propose",
    json={
      "review_session_label": "Interview 2026-03-13",
      "items": [
        {
          "domain": "self",
          "kind": "fact",
          "statement": "User prefers explicit contracts and observability.",
          "source_note_id": note["id"],
          "evidence_ref": "answer-1",
          "source_excerpt": "observability and explicit contracts",
          "write_mode": "create",
        }
      ],
    },
  )

  assert response.status_code == 201
  body = response.json()
  assert body["review_session"]["kind"] == "interview"
  assert body["items"][0]["source_note_id"] == note["id"]
  assert body["items"][0]["evidence_ref"] == "answer-1"


def test_candidate_upsert_supersedes_existing_memory(client):
  existing = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers observable architectures with strong telemetry.",
      "confidence": 0.75,
    },
  ).json()
  candidate = client.post(
    "/memory/candidate",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": "User prefers observable architectures with strong telemetry and explicit contracts.",
      "confidence": "high",
      "write_mode": "upsert",
    },
  ).json()

  accept_response = client.post(f"/memory/candidate/{candidate['id']}/accept")

  assert accept_response.status_code == 200
  with client.app.state.session_factory() as session:
    superseded = session.get(MemoryItem, UUID(existing["id"]))
  assert superseded.status == "superseded"
  assert superseded.metadata_json["superseded_by_item_id"] == accept_response.json()["merged_item"]["id"]

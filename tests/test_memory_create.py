def test_create_memory_item(client):
  payload = {
    "domain": "self",
    "kind": "note",
    "statement": "User prefers automated systems.",
    "confidence": 0.95,
    "metadata": {"source": "test"},
  }
  response = client.post("/memory/items", json=payload)
  body = response.json()

  assert response.status_code == 201
  assert body["domain"] == "self"
  assert body["kind"] == "note"
  assert body["metadata"] == {"source": "test"}
  assert body["status"] == "accepted"

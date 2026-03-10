def test_query_memory_item(client):
  first = {
    "domain": "self",
    "kind": "note",
    "statement": "User prefers building automated systems.",
    "confidence": 0.95,
    "metadata": {"source": "seed"},
  }
  second = {
    "domain": "self",
    "kind": "fact",
    "statement": "User enjoys deliberate architecture discussions.",
    "confidence": 0.75,
    "metadata": {"source": "seed"},
  }
  first_response = client.post("/memory/items", json=first)
  second_response = client.post("/memory/items", json=second)
  first_id = first_response.json()["id"]

  response = client.post(
      "/memory/query",
      json={
        "query": "automated systems",
        "domain": "self",
        "top_k": 5,
        "kinds": ["note", "fact"],
      },
    )
  body = response.json()

  assert response.status_code == 200
  assert body["query"] == "automated systems"
  assert body["items"]
  assert body["items"][0]["id"] == first_id


def test_query_hydrates_from_postgres(client):
  payload = {
    "domain": "project",
    "kind": "decision",
    "statement": "PostgreSQL is the source of truth.",
    "confidence": 0.99,
    "metadata": {"source": "seed"},
  }
  create_response = client.post("/memory/items", json=payload)
  item_id = create_response.json()["id"]

  response = client.post(
    "/memory/query",
    json={"query": "source of truth", "domain": "project", "top_k": 1},
  )
  item = response.json()["items"][0]

  assert response.status_code == 200
  assert item["id"] == item_id
  assert item["statement"] == "PostgreSQL is the source of truth."

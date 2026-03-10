from db.models import MemoryItem, MemoryRelation
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.extract.fact_schema import ExtractedFact


class FakeFactLLMClient:
  def __init__(self, facts_by_text: dict[str, list[ExtractedFact]]) -> None:
    self.facts_by_text = facts_by_text

  def extract_facts(self, text: str) -> list[ExtractedFact]:
    return self.facts_by_text[text]


def test_fact_extraction_creates_fact_and_relation(client):
  raw_payload = {
    "domain": "self",
    "kind": "raw",
    "statement": "Question: What motivates you most in work?\nAnswer: I prefer building automated systems.",
    "confidence": 0.99,
    "metadata": {"source_type": "questionnaire", "source_id": "q_1"},
  }
  create_response = client.post("/memory/items", json=raw_payload)
  raw_item_id = create_response.json()["id"]
  raw_statement = create_response.json()["statement"]

  llm_client = FakeFactLLMClient(
    {
      raw_statement: [
        ExtractedFact(
          statement="User prefers building automated systems.",
          confidence=0.9,
          evidence_reference="Answer: I prefer building automated systems.",
        )
      ]
    }
  )
  runner = FactExtractionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)
  report = runner.run(domain="self")

  assert report.items_processed == 1
  assert report.facts_created == 1
  assert report.skipped == 0
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 2

  with client.app.state.session_factory() as session:
    facts = session.query(MemoryItem).filter(MemoryItem.kind == "fact").all()
    relations = session.query(MemoryRelation).all()

  assert len(facts) == 1
  assert facts[0].metadata_json["source_type"] == "fact_extraction"
  assert facts[0].metadata_json["source_item_id"] == raw_item_id
  assert len(relations) == 1
  assert str(relations[0].target_item_id) == raw_item_id
  assert relations[0].relation_type == "derived_from"


def test_fact_extraction_is_idempotent(client):
  raw_payload = {
    "domain": "self",
    "kind": "raw",
    "statement": "Question: What do you enjoy?\nAnswer: I enjoy infrastructure automation.",
    "confidence": 0.95,
    "metadata": {"source_type": "questionnaire", "source_id": "q_2"},
  }
  response = client.post("/memory/items", json=raw_payload)
  raw_statement = response.json()["statement"]

  llm_client = FakeFactLLMClient(
    {
      raw_statement: [
        ExtractedFact(
          statement="User enjoys infrastructure automation.",
          confidence=0.85,
          evidence_reference="Answer: I enjoy infrastructure automation.",
        )
      ]
    }
  )
  runner = FactExtractionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)

  first = runner.run(domain="self")
  second = runner.run(domain="self")

  assert first.facts_created == 1
  assert second.facts_created == 0
  assert second.skipped == 1

  with client.app.state.session_factory() as session:
    facts = session.query(MemoryItem).filter(MemoryItem.kind == "fact").all()

  assert len(facts) == 1


def test_fact_extraction_results_are_retrievable(client):
  raw_payload = {
    "domain": "self",
    "kind": "raw",
    "statement": "Question: What do you prefer?\nAnswer: I prefer observable systems.",
    "confidence": 0.95,
    "metadata": {"source_type": "questionnaire", "source_id": "q_3"},
  }
  response = client.post("/memory/items", json=raw_payload)
  raw_statement = response.json()["statement"]

  llm_client = FakeFactLLMClient(
    {
      raw_statement: [
        ExtractedFact(
          statement="User prefers observable systems.",
          confidence=0.88,
          evidence_reference="Answer: I prefer observable systems.",
        )
      ]
    }
  )
  runner = FactExtractionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)
  runner.run(domain="self")

  query_response = client.post(
    "/memory/query",
    json={"query": "observable systems", "domain": "self", "top_k": 5, "kinds": ["fact"]},
  )
  items = query_response.json()["items"]

  assert query_response.status_code == 200
  assert len(items) == 1
  assert items[0]["kind"] == "fact"
  assert items[0]["statement"] == "User prefers observable systems."

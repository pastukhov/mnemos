from db.models import MemoryItem, MemoryRelation, ReflectionMetric
from pipelines.reflect.build_reflections import validate_generated_reflections
from pipelines.reflect.reflection_runner import ReflectionRunner
from pipelines.reflect.reflection_schema import GeneratedReflection


class FakeReflectionLLMClient:
  def __init__(self, reflections_by_theme: dict[str, list[GeneratedReflection]]) -> None:
    self.reflections_by_theme = reflections_by_theme

  def generate_reflections(self, *, theme: str, facts):
    return self.reflections_by_theme[theme]


def _create_fact(client, *, source_id: str, topic: str, statement: str) -> None:
  raw_response = client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "raw",
      "statement": f"Question: {topic}?\nAnswer: {statement}",
      "confidence": 0.95,
      "metadata": {"source_type": "questionnaire", "source_id": source_id, "topic": topic},
    },
  )
  raw_item = raw_response.json()
  client.post(
    "/memory/items",
    json={
      "domain": "self",
      "kind": "fact",
      "statement": statement,
      "confidence": 0.88,
      "metadata": {
        "source_type": "fact_extraction",
        "source_id": f"fact:{source_id}",
        "source_item_id": raw_item["id"],
      },
    },
  )


def test_reflection_generation_creates_reflections_and_relations(client):
  _create_fact(
    client,
    source_id="q_1",
    topic="motivation",
    statement="User prefers building automated systems.",
  )
  _create_fact(
    client,
    source_id="q_2",
    topic="motivation",
    statement="User enjoys reducing repetitive manual work.",
  )
  _create_fact(
    client,
    source_id="q_3",
    topic="motivation",
    statement="User values observable delivery pipelines.",
  )

  with client.app.state.session_factory() as session:
    facts = session.query(MemoryItem).filter(MemoryItem.kind == "fact").order_by(MemoryItem.created_at.asc()).all()
  llm_client = FakeReflectionLLMClient(
    {
      "motivation": [
        GeneratedReflection(
          statement="User shows a stable motivation pattern around automation and observable delivery.",
          confidence=0.84,
          evidence_fact_ids=[str(facts[0].id), str(facts[1].id), str(facts[2].id)],
        )
      ]
    }
  )
  runner = ReflectionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)

  report = runner.run(domain="self")

  assert report.facts_loaded == 3
  assert report.themes_processed == 1
  assert report.reflections_created == 1
  assert report.skipped == 0
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 7

  with client.app.state.session_factory() as session:
    reflections = session.query(MemoryItem).filter(MemoryItem.kind == "reflection").all()
    relations = session.query(MemoryRelation).filter(MemoryRelation.relation_type == "supported_by").all()
    metrics = session.query(ReflectionMetric).all()

  assert len(reflections) == 1
  assert reflections[0].metadata_json["source_type"] == "reflection_generation"
  assert reflections[0].metadata_json["theme"] == "motivation"
  assert len(relations) == 3
  assert {str(relation.target_item_id) for relation in relations} == {str(fact.id) for fact in facts}
  assert len(metrics) == 1
  assert metrics[0].reflections_created_total == 1
  assert metrics[0].runs_total == 1


def test_reflection_generation_is_idempotent(client):
  _create_fact(
    client,
    source_id="q_4",
    topic="work_style",
    statement="User prefers decomposable systems.",
  )
  _create_fact(
    client,
    source_id="q_5",
    topic="work_style",
    statement="User values observable architectures.",
  )

  with client.app.state.session_factory() as session:
    facts = session.query(MemoryItem).filter(MemoryItem.kind == "fact").order_by(MemoryItem.created_at.asc()).all()
  llm_client = FakeReflectionLLMClient(
    {
      "work_style": [
        GeneratedReflection(
          statement="User shows a stable work_style pattern around decomposable and observable systems.",
          confidence=0.82,
          evidence_fact_ids=[str(facts[0].id), str(facts[1].id)],
        )
      ]
    }
  )
  runner = ReflectionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)

  first = runner.run(domain="self")
  second = runner.run(domain="self")

  assert first.reflections_created == 1
  assert second.reflections_created == 0
  assert second.skipped == 1

  with client.app.state.session_factory() as session:
    reflections = session.query(MemoryItem).filter(MemoryItem.kind == "reflection").all()

  assert len(reflections) == 1


def test_reflection_results_are_retrievable(client):
  _create_fact(
    client,
    source_id="q_6",
    topic="goals",
    statement="User wants long-term leverage through automation.",
  )
  _create_fact(
    client,
    source_id="q_7",
    topic="goals",
    statement="User prefers work that compounds through reusable systems.",
  )

  with client.app.state.session_factory() as session:
    facts = session.query(MemoryItem).filter(MemoryItem.kind == "fact").order_by(MemoryItem.created_at.asc()).all()
  llm_client = FakeReflectionLLMClient(
    {
      "goals": [
        GeneratedReflection(
          statement="User shows a stable goals pattern focused on reusable automation and leverage.",
          confidence=0.86,
          evidence_fact_ids=[str(facts[0].id), str(facts[1].id)],
        )
      ]
    }
  )
  runner = ReflectionRunner(client.app.state.memory_service, llm_client, client.app.state.settings)
  runner.run(domain="self")

  query_response = client.post(
    "/memory/query",
    json={"query": "reusable automation leverage", "domain": "self", "top_k": 5, "kinds": ["reflection"]},
  )
  items = query_response.json()["items"]

  assert query_response.status_code == 200
  assert len(items) == 1
  assert items[0]["kind"] == "reflection"
  assert "reusable automation and leverage" in items[0]["statement"]


def test_reflection_validation_rejects_single_evidence_fact():
  valid = validate_generated_reflections(
    [
      GeneratedReflection(
        statement="User shows a stable motivation pattern around automation.",
        confidence=0.8,
        evidence_fact_ids=["fact-1"],
      )
    ],
    input_fact_ids={"fact-1"},
    max_reflections_per_batch=5,
    min_chars=20,
    max_chars=300,
  )

  assert valid == []

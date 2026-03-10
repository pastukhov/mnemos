from db.models import MemoryItem
from pipelines.ingest.load_questionnaire_yaml import load_questionnaire_yaml


def test_questionnaire_yaml_ingestion_indexes_vectors(client, tmp_path):
  source = tmp_path / "questionnaire.yaml"
  source.write_text(
    "\n".join(
      [
        '- id: "q01"',
        '  topic: "identity"',
        '  question: "What do you do professionally?"',
        "  answer: |",
        "    I build SRE automation and observability tooling.",
        '  created_at: "2026-03-10"',
        "",
        '- id: "q02"',
        '  topic: "motivation"',
        '  question: "What motivates you most in work?"',
        "  answer: |",
        "    Reducing repetitive manual operations.",
        '  created_at: "2026-03-10"',
        "",
      ]
    ),
    encoding="utf-8",
  )

  service = client.app.state.memory_service
  report = load_questionnaire_yaml(source, service)

  assert report.loaded == 2
  assert report.skipped == 0
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 2

  with client.app.state.session_factory() as session:
    items = session.query(MemoryItem).all()

  assert {item.metadata_json["source_id"] for item in items} == {"q01", "q02"}

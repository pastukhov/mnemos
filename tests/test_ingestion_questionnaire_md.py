from db.models import MemoryItem
from pipelines.ingest.load_questionnaire_md import load_questionnaire_markdown


def test_questionnaire_markdown_ingestion_is_idempotent(client, tmp_path):
  source = tmp_path / "questionnaire.md"
  source.write_text(
    "\n".join(
      [
        "## 1. Identity",
        "",
        "- **1.1.** What do you do professionally?",
        "  **Ответ:** I work on SRE systems and infrastructure automation.",
        "",
        "- **1.2.** What motivates you most in work?",
        "  **Ответ:** Designing observable systems that reduce manual toil.",
        "",
      ]
    ),
    encoding="utf-8",
  )

  service = client.app.state.memory_service
  first = load_questionnaire_markdown(source, service)
  second = load_questionnaire_markdown(source, service)

  assert first.loaded == 2
  assert first.skipped == 0
  assert second.loaded == 0
  assert second.skipped == 2

  with client.app.state.session_factory() as session:
    items = session.query(MemoryItem).all()

  assert len(items) == 2
  assert items[0].kind == "raw"
  assert items[0].metadata_json["source_type"] == "questionnaire"
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 2

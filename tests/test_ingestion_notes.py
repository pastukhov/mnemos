from db.models import MemoryItem
from pipelines.ingest.load_notes import load_notes


def test_notes_ingestion_skips_duplicates(client, tmp_path):
  source = tmp_path / "notes.jsonl"
  source.write_text(
    "\n".join(
      [
        '{"id":"note_1","text":"Prefer observable systems with strong alerts.","created_at":"2026-03-10T10:00:00Z"}',
        '{"id":"note_2","text":"AI can accelerate infrastructure automation.","created_at":"2026-03-10T10:05:00Z"}',
        "",
      ]
    ),
    encoding="utf-8",
  )

  service = client.app.state.memory_service
  first = load_notes(source, service)
  second = load_notes(source, service)

  assert first.loaded == 2
  assert second.loaded == 0
  assert second.skipped == 2
  assert len(client.app.state.qdrant.collections["mnemos_self"]) == 2

  with client.app.state.session_factory() as session:
    items = session.query(MemoryItem).order_by(MemoryItem.kind.asc()).all()

  assert [item.kind for item in items] == ["note", "note"]
  assert items[0].metadata_json["source_type"] == "note"

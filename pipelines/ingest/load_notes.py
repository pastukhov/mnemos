import json
from pathlib import Path

from core.logging import get_logger
from pipelines.ingest.common import IngestItem, IngestReport, ingest_items
from services.memory_service import MemoryService

logger = get_logger(__name__)


def load_notes(path: str | Path, memory_service: MemoryService) -> IngestReport:
  source_path = Path(path)
  items: list[IngestItem] = []
  for line_number, raw_line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
    line = raw_line.strip()
    if not line:
      continue
    try:
      payload = json.loads(line)
    except json.JSONDecodeError as exc:
      raise ValueError(f"invalid notes jsonl at line {line_number}") from exc
    items.append(build_item(payload))

  report = ingest_items(
    memory_service=memory_service,
    source_type="note",
    items=items,
    source_path=source_path,
  )
  logger.info(
    "ingestion.notes",
    extra={
      "event": "ingestion_notes",
      "source_type": "note",
      "source_path": str(source_path),
      "loaded": report.loaded,
      "skipped": report.skipped,
    },
  )
  return report


def build_item(entry: object) -> IngestItem:
  if not isinstance(entry, dict):
    raise ValueError("note item must be an object")

  note_id = _require_str(entry, "id")
  text = _require_str(entry, "text")
  metadata: dict[str, object] = {
    "source_type": "note",
    "source_id": note_id,
  }
  if "created_at" in entry:
    metadata["created_at"] = _require_str(entry, "created_at")

  return IngestItem(
    source_type="note",
    source_id=note_id,
    domain="self",
    kind="note",
    statement=text,
    metadata=metadata,
  )


def _require_str(entry: dict[str, object], key: str) -> str:
  value = entry.get(key)
  if not isinstance(value, str) or not value.strip():
    raise ValueError(f"note field '{key}' must be a non-empty string")
  return value.strip()

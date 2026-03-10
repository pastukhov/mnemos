from pathlib import Path

import yaml

from core.logging import get_logger
from pipelines.ingest.common import (
  IngestItem,
  IngestReport,
  build_questionnaire_statement,
  ingest_items,
)
from services.memory_service import MemoryService

logger = get_logger(__name__)


def load_questionnaire_yaml(path: str | Path, memory_service: MemoryService) -> IngestReport:
  source_path = Path(path)
  payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
  if not isinstance(payload, list):
    raise ValueError("questionnaire yaml must contain a list of items")

  items = [build_item(entry) for entry in payload]
  report = ingest_items(
    memory_service=memory_service,
    source_type="questionnaire",
    items=items,
    source_path=source_path,
  )
  logger.info(
    "ingestion.questionnaire",
    extra={
      "event": "ingestion_questionnaire",
      "source_type": "questionnaire",
      "source_path": str(source_path),
      "loaded": report.loaded,
      "skipped": report.skipped,
    },
  )
  return report


def build_item(entry: object) -> IngestItem:
  if not isinstance(entry, dict):
    raise ValueError("questionnaire yaml item must be an object")

  item_id = _require_str(entry, "id")
  topic = _require_str(entry, "topic")
  question = _require_str(entry, "question")
  answer = _require_str(entry, "answer")
  metadata: dict[str, object] = {
    "source_type": "questionnaire",
    "source_id": item_id,
    "topic": topic,
  }
  if "created_at" in entry:
    metadata["created_at"] = _require_str(entry, "created_at")

  return IngestItem(
    source_type="questionnaire",
    source_id=item_id,
    domain="self",
    kind="raw",
    statement=build_questionnaire_statement(question, answer),
    metadata=metadata,
  )


def _require_str(entry: dict[str, object], key: str) -> str:
  value = entry.get(key)
  if not isinstance(value, str) or not value.strip():
    raise ValueError(f"questionnaire yaml field '{key}' must be a non-empty string")
  return value.strip()

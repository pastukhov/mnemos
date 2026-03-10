from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from api.schemas import MemoryCreateRequest
from core.logging import get_logger
from services.memory_service import MemoryService

logger = get_logger(__name__)


@dataclass(slots=True)
class IngestItem:
  source_type: str
  source_id: str
  domain: str
  kind: str
  statement: str
  metadata: dict[str, object]
  confidence: float | None = None


@dataclass(slots=True)
class IngestReport:
  loaded: int = 0
  skipped: int = 0
  errors: int = 0

  def merge(self, other: "IngestReport") -> "IngestReport":
    self.loaded += other.loaded
    self.skipped += other.skipped
    self.errors += other.errors
    return self


def build_questionnaire_statement(question: str, answer: str) -> str:
  return f"Question: {question.strip()}\nAnswer: {answer.strip()}"


def ingest_items(
  *,
  memory_service: MemoryService,
  source_type: str,
  items: list[IngestItem],
  source_path: Path,
) -> IngestReport:
  report = IngestReport()
  for item in items:
    existing = memory_service.get_item_by_source_ref(
      source_type=item.source_type,
      source_id=item.source_id,
    )
    if existing is not None:
      report.skipped += 1
      continue

    payload = MemoryCreateRequest(
      domain=item.domain,
      kind=item.kind,
      statement=item.statement,
      confidence=item.confidence,
      metadata=item.metadata,
    )
    try:
      memory_service.create_item_record(payload)
      report.loaded += 1
    except IntegrityError as exc:
      if "uq_memory_source_ref" in str(exc):
        report.skipped += 1
        continue
      report.errors += 1
      memory_service.record_ingestion_metrics(
        source_type=source_type,
        loaded=report.loaded,
        duplicates=report.skipped,
        errors=report.errors,
      )
      logger.exception(
        "ingestion item failed",
        extra={
          "event": "ingestion_item_failed",
          "source_type": source_type,
          "source_id": item.source_id,
          "source_path": str(source_path),
        },
      )
      raise
    except Exception:
      report.errors += 1
      memory_service.record_ingestion_metrics(
        source_type=source_type,
        loaded=report.loaded,
        duplicates=report.skipped,
        errors=report.errors,
      )
      logger.exception(
        "ingestion item failed",
        extra={
          "event": "ingestion_item_failed",
          "source_type": source_type,
          "source_id": item.source_id,
          "source_path": str(source_path),
        },
      )
      raise
  memory_service.record_ingestion_metrics(
    source_type=source_type,
    loaded=report.loaded,
    duplicates=report.skipped,
    errors=report.errors,
  )
  return report

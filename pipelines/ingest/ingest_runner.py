from dataclasses import dataclass
from pathlib import Path

from pipelines.ingest.common import IngestReport
from pipelines.ingest.load_notes import load_notes
from pipelines.ingest.load_questionnaire_md import load_questionnaire_markdown
from pipelines.ingest.load_questionnaire_yaml import load_questionnaire_yaml
from services.memory_service import MemoryService


@dataclass(slots=True)
class IngestionSummary:
  questionnaire_answers_ingested: int = 0
  notes_ingested: int = 0
  duplicates_skipped: int = 0
  errors: int = 0

  def add_questionnaire(self, report: IngestReport) -> None:
    self.questionnaire_answers_ingested += report.loaded
    self.duplicates_skipped += report.skipped
    self.errors += report.errors

  def add_notes(self, report: IngestReport) -> None:
    self.notes_ingested += report.loaded
    self.duplicates_skipped += report.skipped
    self.errors += report.errors

  def render(self) -> str:
    lines = [
      f"Questionnaire answers ingested: {self.questionnaire_answers_ingested}",
      f"Notes ingested: {self.notes_ingested}",
      f"Duplicates skipped: {self.duplicates_skipped}",
    ]
    if self.errors:
      lines.append(f"Errors: {self.errors}")
    return "\n".join(lines)


class IngestRunner:
  def __init__(self, memory_service: MemoryService) -> None:
    self.memory_service = memory_service

  def run_questionnaire(self, path: str | Path) -> IngestReport:
    source_path = Path(path)
    if source_path.suffix.lower() == ".md":
      return load_questionnaire_markdown(source_path, self.memory_service)
    if source_path.suffix.lower() in {".yaml", ".yml"}:
      return load_questionnaire_yaml(source_path, self.memory_service)
    raise ValueError("questionnaire ingestion supports only .md, .yaml and .yml files")

  def run_notes(self, path: str | Path) -> IngestReport:
    return load_notes(path, self.memory_service)

  def run_all(
    self,
    *,
    questionnaire_md_path: str | Path = "data/raw/questionnaire.md",
    questionnaire_yaml_path: str | Path = "data/raw/questionnaire.yaml",
    notes_path: str | Path = "data/raw/notes.jsonl",
  ) -> IngestionSummary:
    summary = IngestionSummary()

    questionnaire_md = Path(questionnaire_md_path)
    questionnaire_yaml = Path(questionnaire_yaml_path)
    if questionnaire_md.exists():
      summary.add_questionnaire(self.run_questionnaire(questionnaire_md))
    elif questionnaire_yaml.exists():
      summary.add_questionnaire(self.run_questionnaire(questionnaire_yaml))
    else:
      raise FileNotFoundError("questionnaire source file not found")

    notes_file = Path(notes_path)
    if notes_file.exists():
      summary.add_notes(self.run_notes(notes_file))

    return summary

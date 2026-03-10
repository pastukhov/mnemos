import re
from pathlib import Path

from core.logging import get_logger
from pipelines.ingest.common import (
  IngestItem,
  IngestReport,
  build_questionnaire_statement,
  ingest_items,
)
from services.memory_service import MemoryService

logger = get_logger(__name__)

CANONICAL_SECTION_RE = re.compile(r"^##\s+(q[\w-]+)\s*$", re.MULTILINE)
TOPIC_HEADING_RE = re.compile(r"^##\s+(.*)$")
BULLET_QUESTION_RE = re.compile(r"^- \*\*(\d+)\.(\d+)\.\*\*\s*(.*)$")
ANSWER_RE = re.compile(r"^\s*\*\*Ответ:\*\*\s*(.*)$")


def load_questionnaire_markdown(path: str | Path, memory_service: MemoryService) -> IngestReport:
  source_path = Path(path)
  content = source_path.read_text(encoding="utf-8")
  items = parse_questionnaire_markdown(content)
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


def parse_questionnaire_markdown(content: str) -> list[IngestItem]:
  if CANONICAL_SECTION_RE.search(content):
    return _parse_canonical_markdown(content)
  return _parse_bulleted_markdown(content)


def _parse_canonical_markdown(content: str) -> list[IngestItem]:
  matches = list(CANONICAL_SECTION_RE.finditer(content))
  items: list[IngestItem] = []
  for index, match in enumerate(matches):
    section_id = match.group(1).strip()
    start = match.end()
    end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
    block = content[start:end].strip()
    topic_match = re.search(r"^Topic:\s*(.+)$", block, re.MULTILINE)
    question_match = re.search(r"^Question:\s*(.+)$", block, re.MULTILINE)
    answer_match = re.search(r"^Answer:\s*(.*)$", block, re.MULTILINE)
    if topic_match is None or question_match is None or answer_match is None:
      raise ValueError(f"invalid questionnaire markdown section: {section_id}")
    answer_start = answer_match.end()
    answer_text = block[answer_start:].strip()
    items.append(
      _build_questionnaire_item(
        item_id=section_id,
        topic=topic_match.group(1).strip(),
        question=question_match.group(1).strip(),
        answer=answer_text,
      )
    )
  return items


def _parse_bulleted_markdown(content: str) -> list[IngestItem]:
  items: list[IngestItem] = []
  current_topic: str | None = None
  current_id: str | None = None
  question_lines: list[str] = []
  answer_lines: list[str] = []
  in_answer = False

  def flush_current() -> None:
    nonlocal current_id, question_lines, answer_lines, in_answer
    if current_id is None:
      return
    question = " ".join(line.strip() for line in question_lines if line.strip())
    answer = _join_answer_lines(answer_lines)
    if not question or not answer:
      raise ValueError(f"invalid questionnaire markdown item: {current_id}")
    items.append(
      _build_questionnaire_item(
        item_id=current_id,
        topic=current_topic or "unknown",
        question=question,
        answer=answer,
      )
    )
    current_id = None
    question_lines = []
    answer_lines = []
    in_answer = False

  for raw_line in content.splitlines():
    heading_match = TOPIC_HEADING_RE.match(raw_line)
    if heading_match:
      flush_current()
      current_topic = re.sub(r"^\d+\.\s*", "", heading_match.group(1).strip())
      continue

    question_match = BULLET_QUESTION_RE.match(raw_line)
    if question_match:
      flush_current()
      major = int(question_match.group(1))
      minor = int(question_match.group(2))
      current_id = f"q{major:02d}_{minor:02d}"
      question_lines = [question_match.group(3).strip()]
      answer_lines = []
      in_answer = False
      continue

    answer_match = ANSWER_RE.match(raw_line)
    if answer_match and current_id is not None:
      in_answer = True
      initial_answer = answer_match.group(1).strip()
      if initial_answer:
        answer_lines.append(initial_answer)
      continue

    if current_id is None:
      continue

    stripped = raw_line.strip()
    if not stripped:
      if in_answer and answer_lines and answer_lines[-1] != "":
        answer_lines.append("")
      continue

    if in_answer:
      answer_lines.append(stripped)
    else:
      question_lines.append(stripped)

  flush_current()
  return items


def _build_questionnaire_item(*, item_id: str, topic: str, question: str, answer: str) -> IngestItem:
  return IngestItem(
    source_type="questionnaire",
    source_id=item_id,
    domain="self",
    kind="raw",
    statement=build_questionnaire_statement(question, answer),
    metadata={
      "source_type": "questionnaire",
      "source_id": item_id,
      "topic": topic,
    },
  )


def _join_answer_lines(lines: list[str]) -> str:
  answer = "\n".join(lines).strip()
  answer = re.sub(r"\n{3,}", "\n\n", answer)
  return answer

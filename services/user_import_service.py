from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any

from api.schemas import ImportPreviewItem, MemoryCreateRequest
from services.memory_service import MemoryService

MAX_PREVIEW_ITEMS = 50


@dataclass
class ParsedImport:
  detected_format: str
  items: list[ImportPreviewItem]
  warnings: list[str]
  truncated: bool


@dataclass
class AppliedImport:
  detected_format: str
  created: int
  skipped: int
  items: list


class UserImportService:
  def __init__(self, memory_service: MemoryService) -> None:
    self.memory_service = memory_service

  def preview(self, *, content: str, filename: str | None, domain: str, kind: str) -> ParsedImport:
    detected_format = detect_format(content=content, filename=filename)
    statements, warnings = parse_import_content(content=content, detected_format=detected_format)
    truncated = len(statements) > MAX_PREVIEW_ITEMS
    preview_items = [
      ImportPreviewItem(
        statement=statement,
        metadata=build_import_metadata(
          statement=statement,
          detected_format=detected_format,
          filename=filename,
          index=index,
        ),
      )
      for index, statement in enumerate(statements[:MAX_PREVIEW_ITEMS], start=1)
    ]
    if not preview_items:
      warnings.append("Не удалось выделить записи для импорта. Проверьте формат содержимого.")
    return ParsedImport(
      detected_format=detected_format,
      items=preview_items,
      warnings=warnings,
      truncated=truncated,
    )

  def apply(self, *, content: str, filename: str | None, domain: str, kind: str) -> AppliedImport:
    preview = self.preview(content=content, filename=filename, domain=domain, kind=kind)
    created_items = []
    skipped = 0
    for item in preview.items:
      metadata = dict(item.metadata or {})
      source_type = str(metadata["source_type"])
      source_id = str(metadata["source_id"])
      existing = self.memory_service.get_item_by_source_ref(source_type=source_type, source_id=source_id)
      if existing is not None:
        skipped += 1
        continue
      created = self.memory_service.create_item_record(
        MemoryCreateRequest(
          domain=domain,
          kind=kind,
          statement=item.statement,
          metadata=metadata,
        )
      )
      created_items.append(created)
    return AppliedImport(
      detected_format=preview.detected_format,
      created=len(created_items),
      skipped=skipped,
      items=created_items,
    )


def detect_format(*, content: str, filename: str | None) -> str:
  lower_name = (filename or "").lower()
  stripped = content.strip()
  if lower_name.endswith(".csv"):
    return "csv"
  if lower_name.endswith(".md") or lower_name.endswith(".markdown"):
    return "markdown"
  if lower_name.endswith(".txt"):
    return "text"
  if lower_name.endswith(".json"):
    if "mapping" in stripped or '"conversations"' in stripped:
      return "chatgpt_export"
    return "json"
  if stripped.startswith("{") or stripped.startswith("["):
    if '"mapping"' in stripped or '"conversations"' in stripped:
      return "chatgpt_export"
    return "json"
  if "," in stripped and "\n" in stripped:
    first_line = stripped.splitlines()[0]
    if first_line.count(",") >= 1:
      return "csv"
  if "#" in stripped or stripped.startswith("- ") or stripped.startswith("##"):
    return "markdown"
  return "text"


def parse_import_content(*, content: str, detected_format: str) -> tuple[list[str], list[str]]:
  if detected_format == "csv":
    return parse_csv(content), []
  if detected_format == "chatgpt_export":
    return parse_chatgpt_export(content)
  if detected_format == "json":
    try:
      payload = json.loads(content)
    except json.JSONDecodeError:
      return parse_text_blocks(content), ["JSON не распознан, поэтому содержимое обработано как обычный текст."]
    if isinstance(payload, list):
      statements = [compact_text(json.dumps(item, ensure_ascii=False)) for item in payload if item]
      return [item for item in statements if item], []
    return [compact_text(json.dumps(payload, ensure_ascii=False))], []
  return parse_text_blocks(content), []


def parse_text_blocks(content: str) -> list[str]:
  normalized = content.replace("\r\n", "\n")
  blocks = [clean_block(block) for block in normalized.split("\n\n")]
  return [block for block in blocks if block]


def clean_block(block: str) -> str:
  lines = [line.strip() for line in block.splitlines()]
  cleaned_lines = []
  for line in lines:
    if not line:
      continue
    cleaned_lines.append(line.removeprefix("- ").removeprefix("* ").strip())
  return compact_text("\n".join(cleaned_lines))


def parse_csv(content: str) -> list[str]:
  stream = io.StringIO(content)
  reader = csv.DictReader(stream)
  if reader.fieldnames:
    preferred = ("statement", "text", "content", "note", "message")
    keys = {name.lower(): name for name in reader.fieldnames if name}
    selected = next((keys[name] for name in preferred if name in keys), None)
    if selected is not None:
      return [compact_text(row.get(selected, "")) for row in reader if compact_text(row.get(selected, ""))]

  stream.seek(0)
  plain_reader = csv.reader(stream)
  statements = []
  for row in plain_reader:
    joined = compact_text(" ".join(cell.strip() for cell in row if cell.strip()))
    if joined:
      statements.append(joined)
  return statements


def parse_chatgpt_export(content: str) -> tuple[list[str], list[str]]:
  try:
    payload = json.loads(content)
  except json.JSONDecodeError:
    return parse_text_blocks(content), ["Экспорт ChatGPT не распознан, поэтому содержимое обработано как обычный текст."]

  conversations = []
  if isinstance(payload, list):
    conversations = payload
  elif isinstance(payload, dict) and isinstance(payload.get("conversations"), list):
    conversations = payload["conversations"]
  else:
    conversations = [payload]

  messages: list[str] = []
  for conversation in conversations:
    if not isinstance(conversation, dict):
      continue
    mapping = conversation.get("mapping")
    if isinstance(mapping, dict):
      for node in mapping.values():
        if not isinstance(node, dict):
          continue
        message = node.get("message") or {}
        author = ((message.get("author") or {}).get("role") or "").strip()
        parts = ((message.get("content") or {}).get("parts") or [])
        text = compact_text(" ".join(part for part in parts if isinstance(part, str)))
        if text:
          prefix = "Пользователь" if author == "user" else "Ассистент" if author == "assistant" else "Сообщение"
          messages.append(f"{prefix}: {text}")
    elif isinstance(conversation.get("messages"), list):
      for entry in conversation["messages"]:
        if not isinstance(entry, dict):
          continue
        role = str(entry.get("role") or "message")
        content_value = entry.get("content")
        if isinstance(content_value, list):
          text = compact_text(" ".join(part for part in content_value if isinstance(part, str)))
        else:
          text = compact_text(str(content_value or ""))
        if text:
          messages.append(f"{role.title()}: {text}")

  if not messages:
    return parse_text_blocks(content), ["Структура экспорта ChatGPT не распознана, поэтому содержимое обработано как обычный текст."]
  return messages, []


def build_import_metadata(
  *,
  statement: str,
  detected_format: str,
  filename: str | None,
  index: int,
) -> dict[str, Any]:
  source_id = hashlib.sha256(
    f"{detected_format}:{filename or 'pasted'}:{index}:{statement}".encode("utf-8")
  ).hexdigest()[:24]
  metadata: dict[str, Any] = {
    "source_type": "ui_import",
    "source_id": source_id,
    "import_format": detected_format,
    "import_index": index,
  }
  if filename:
    metadata["import_filename"] = filename
  return metadata


def compact_text(value: str) -> str:
  return " ".join(segment for segment in value.replace("\n", " ").split() if segment).strip()

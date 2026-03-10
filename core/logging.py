import json
import logging
import sys
from datetime import UTC, datetime

STANDARD_LOG_RECORD_KEYS = {
  "args",
  "asctime",
  "created",
  "exc_info",
  "exc_text",
  "filename",
  "funcName",
  "levelname",
  "levelno",
  "lineno",
  "module",
  "msecs",
  "message",
  "msg",
  "name",
  "pathname",
  "process",
  "processName",
  "relativeCreated",
  "stack_info",
  "thread",
  "threadName",
  "taskName",
}


class JsonFormatter(logging.Formatter):
  def format(self, record: logging.LogRecord) -> str:
    payload = {
      "timestamp": datetime.now(UTC).isoformat(),
      "level": record.levelname,
      "logger": record.name,
      "message": record.getMessage(),
    }
    for key, value in record.__dict__.items():
      if key in STANDARD_LOG_RECORD_KEYS:
        continue
      if key.startswith("_"):
        continue
      payload[key] = value
    if record.exc_info:
      payload["exception"] = self.formatException(record.exc_info)
    return json.dumps(payload, ensure_ascii=True)


def setup_logging(log_level: str) -> None:
  root = logging.getLogger()
  root.setLevel(log_level.upper())
  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(JsonFormatter())
  root.handlers = [handler]
  logging.getLogger("httpx").setLevel(logging.WARNING)
  logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
  return logging.getLogger(name)

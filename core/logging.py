import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
  def format(self, record: logging.LogRecord) -> str:
    payload = {
      "timestamp": datetime.now(UTC).isoformat(),
      "level": record.levelname,
      "logger": record.name,
      "message": record.getMessage(),
    }
    for key in ("event", "path", "method"):
      value = getattr(record, key, None)
      if value is not None:
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


def get_logger(name: str) -> logging.Logger:
  return logging.getLogger(name)

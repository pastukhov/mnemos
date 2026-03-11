#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup.sql.gz|backup.sql>" >&2
  exit 2
fi

BACKUP_PATH="$1"
if [[ ! -f "$BACKUP_PATH" ]]; then
  echo "backup file not found: $BACKUP_PATH" >&2
  exit 1
fi

echo "Restoring PostgreSQL from: $BACKUP_PATH"

if [[ "$BACKUP_PATH" == *.gz ]]; then
  gzip -dc "$BACKUP_PATH" | docker compose exec -T postgres psql \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-mnemos}"
else
  cat "$BACKUP_PATH" | docker compose exec -T postgres psql \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-mnemos}"
fi

echo "PostgreSQL restore completed."

if [[ "${SKIP_REINDEX:-0}" == "1" ]]; then
  echo "SKIP_REINDEX=1, skipping Qdrant rebuild."
  exit 0
fi

echo "Rebuilding Qdrant collections from PostgreSQL..."
"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/reindex_qdrant.py"
echo "Restore and reindex completed."

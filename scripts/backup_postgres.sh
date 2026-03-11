#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

mkdir -p backups

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${1:-backups/mnemos-postgres-${STAMP}.sql.gz}"

echo "Creating PostgreSQL backup at: $TARGET"

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-mnemos}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  | gzip -c >"$TARGET"

echo "Backup completed: $TARGET"

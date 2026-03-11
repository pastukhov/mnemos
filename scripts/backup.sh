#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET_DIR="${1:-backups/${STAMP}}"

mkdir -p "$TARGET_DIR"

"$ROOT_DIR/scripts/backup_postgres.sh" "$TARGET_DIR/postgres.sql.gz"
"$ROOT_DIR/scripts/backup_qdrant.sh" "$TARGET_DIR/qdrant-storage.tar.gz"
"$ROOT_DIR/scripts/backup_config.sh" "$TARGET_DIR/config.tar.gz"

echo "Backup completed: $TARGET_DIR"

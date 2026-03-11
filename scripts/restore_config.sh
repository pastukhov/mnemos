#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <config-backup.tar.gz>" >&2
  exit 2
fi

BACKUP_PATH="$1"
if [[ ! -f "$BACKUP_PATH" ]]; then
  echo "backup file not found: $BACKUP_PATH" >&2
  exit 1
fi

echo "Restoring config backup from: $BACKUP_PATH"
tar -xzf "$BACKUP_PATH"
echo "Config restore completed."

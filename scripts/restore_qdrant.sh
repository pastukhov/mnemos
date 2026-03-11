#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup.tar.gz>" >&2
  exit 2
fi

BACKUP_PATH="$1"
if [[ ! -f "$BACKUP_PATH" ]]; then
  echo "backup file not found: $BACKUP_PATH" >&2
  exit 1
fi

QDRANT_CONTAINER_ID="$(docker compose ps -q qdrant)"
if [[ -z "$QDRANT_CONTAINER_ID" ]]; then
  echo "qdrant container is not available for volume resolution" >&2
  exit 1
fi

QDRANT_VOLUME="$(docker inspect "$QDRANT_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/qdrant/storage"}}{{.Name}}{{end}}{{end}}')"
if [[ -z "$QDRANT_VOLUME" ]]; then
  echo "failed to resolve Docker volume name for qdrant" >&2
  exit 1
fi

echo "Stopping qdrant before restore..."
docker compose stop qdrant

echo "Restoring Qdrant backup from: $BACKUP_PATH"
docker run --rm \
  -v "$QDRANT_VOLUME":/target/qdrant \
  -v "$ROOT_DIR":/workspace \
  alpine:3.20 \
  sh -c "rm -rf /target/qdrant/* && tar -xzf /workspace/${BACKUP_PATH} -C /target"

echo "Starting qdrant after restore..."
docker compose up -d qdrant

echo "Qdrant restore completed."

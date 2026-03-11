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

echo "Stopping services before full restore..."
docker compose stop mnemos mnemos-mcp postgres qdrant

POSTGRES_CONTAINER_ID="$(docker compose ps -q postgres)"
QDRANT_CONTAINER_ID="$(docker compose ps -q qdrant)"

if [[ -z "$POSTGRES_CONTAINER_ID" || -z "$QDRANT_CONTAINER_ID" ]]; then
  echo "postgres or qdrant container is not available for volume resolution" >&2
  exit 1
fi

POSTGRES_VOLUME="$(docker inspect "$POSTGRES_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
QDRANT_VOLUME="$(docker inspect "$QDRANT_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/qdrant/storage"}}{{.Name}}{{end}}{{end}}')"

if [[ -z "$POSTGRES_VOLUME" || -z "$QDRANT_VOLUME" ]]; then
  echo "failed to resolve Docker volume names for postgres or qdrant" >&2
  exit 1
fi

echo "Restoring full stack backup from: $BACKUP_PATH"
docker run --rm \
  -v "$POSTGRES_VOLUME":/target/postgres \
  -v "$QDRANT_VOLUME":/target/qdrant \
  -v "$ROOT_DIR":/workspace \
  alpine:3.20 \
  sh -c "rm -rf /target/postgres/* /target/qdrant/* && mkdir -p /target && tar -xzf /workspace/${BACKUP_PATH} -C /target"

echo "Starting services after restore..."
docker compose up -d

echo "Full stack restore completed."

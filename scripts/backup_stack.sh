#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p backups

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET_NAME="${1:-mnemos-stack-${STAMP}.tar.gz}"
TARGET_PATH="backups/${TARGET_NAME##*/}"
POSTGRES_CONTAINER_ID="$(docker compose ps -q postgres)"
QDRANT_CONTAINER_ID="$(docker compose ps -q qdrant)"

if [[ -z "$POSTGRES_CONTAINER_ID" || -z "$QDRANT_CONTAINER_ID" ]]; then
  echo "postgres or qdrant container is not running" >&2
  exit 1
fi

POSTGRES_VOLUME="$(docker inspect "$POSTGRES_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
QDRANT_VOLUME="$(docker inspect "$QDRANT_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/qdrant/storage"}}{{.Name}}{{end}}{{end}}')"

if [[ -z "$POSTGRES_VOLUME" || -z "$QDRANT_VOLUME" ]]; then
  echo "failed to resolve Docker volume names for postgres or qdrant" >&2
  exit 1
fi

echo "Creating full stack backup at: $TARGET_PATH"
docker run --rm \
  -v "$POSTGRES_VOLUME":/source/postgres:ro \
  -v "$QDRANT_VOLUME":/source/qdrant:ro \
  -v "$ROOT_DIR/backups":/backups \
  alpine:3.20 \
  sh -c "tar -czf /backups/${TARGET_NAME##*/} -C /source postgres qdrant"

echo "Full stack backup completed: $TARGET_PATH"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p backups

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${1:-backups/mnemos-qdrant-${STAMP}.tar.gz}"
QDRANT_CONTAINER_ID="$(docker compose ps -q qdrant)"

if [[ -z "$QDRANT_CONTAINER_ID" ]]; then
  echo "qdrant container is not running" >&2
  exit 1
fi

QDRANT_VOLUME="$(docker inspect "$QDRANT_CONTAINER_ID" --format '{{range .Mounts}}{{if eq .Destination "/qdrant/storage"}}{{.Name}}{{end}}{{end}}')"

if [[ -z "$QDRANT_VOLUME" ]]; then
  echo "failed to resolve Docker volume name for qdrant" >&2
  exit 1
fi

echo "Creating Qdrant backup at: $TARGET"
docker run --rm \
  -v "$QDRANT_VOLUME":/source/qdrant:ro \
  -v "$ROOT_DIR":/workspace \
  alpine:3.20 \
  sh -c "tar -czf /workspace/${TARGET} -C /source qdrant"

echo "Qdrant backup completed: $TARGET"

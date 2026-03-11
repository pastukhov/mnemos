#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p backups

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${1:-backups/mnemos-config-${STAMP}.tar.gz}"

INCLUDE_PATHS=()
for path in \
  .env \
  .env.example \
  .env.local-mock.example \
  docker-compose.yml \
  docker-compose.local-mock.yml; do
  if [[ -f "$path" ]]; then
    INCLUDE_PATHS+=("$path")
  fi
done

if [[ -d config ]]; then
  INCLUDE_PATHS+=("config")
fi

if [[ ${#INCLUDE_PATHS[@]} -eq 0 ]]; then
  echo "no configuration files found to back up" >&2
  exit 1
fi

echo "Creating config backup at: $TARGET"
tar -czf "$TARGET" "${INCLUDE_PATHS[@]}"
echo "Config backup completed: $TARGET"

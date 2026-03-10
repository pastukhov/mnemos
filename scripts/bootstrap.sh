#!/usr/bin/env bash
set -euo pipefail

python -m alembic upgrade head
python scripts/create_qdrant_collections.py
exec uvicorn api.main:app --host "${MNEMOS_HOST:-0.0.0.0}" --port "${MNEMOS_PORT:-8000}"

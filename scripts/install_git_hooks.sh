#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRE_COMMIT_BIN="$ROOT_DIR/.venv/bin/pre-commit"
HOOKS_DIR="$ROOT_DIR/.git/hooks"
HOOK_PATH="$HOOKS_DIR/commit-msg"

mkdir -p "$HOOKS_DIR"

if [[ ! -x "$PRE_COMMIT_BIN" ]]; then
  echo "missing $PRE_COMMIT_BIN; run 'make venv' first" >&2
  exit 1
fi

"$PRE_COMMIT_BIN" install --hook-type pre-commit

cat >"$HOOK_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
"$ROOT_DIR/scripts/validate_conventional_commit.sh" "\$1"
EOF

chmod +x "$HOOK_PATH"
echo "installed pre-commit hook via $PRE_COMMIT_BIN"
echo "installed commit-msg hook at $HOOK_PATH"

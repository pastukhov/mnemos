#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"
HOOK_PATH="$HOOKS_DIR/commit-msg"

mkdir -p "$HOOKS_DIR"

cat >"$HOOK_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
"$ROOT_DIR/scripts/validate_conventional_commit.sh" "\$1"
EOF

chmod +x "$HOOK_PATH"
echo "installed commit-msg hook at $HOOK_PATH"

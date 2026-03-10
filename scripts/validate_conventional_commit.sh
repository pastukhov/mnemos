#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <commit-message-or-path>" >&2
  exit 2
fi

INPUT="$1"
if [[ -f "$INPUT" ]]; then
  MESSAGE="$(sed -E '/^#/d' "$INPUT" | tr -d '\r')"
else
  MESSAGE="$INPUT"
fi

HEADER="$(printf '%s\n' "$MESSAGE" | sed -n '1p')"
if [[ -z "$HEADER" ]]; then
  echo "commit message must not be empty" >&2
  exit 1
fi

PATTERN='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: .+$'
if [[ ! "$HEADER" =~ $PATTERN ]]; then
  cat >&2 <<'EOF'
invalid Conventional Commit header
expected: <type>(optional-scope): <description>
allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
EOF
  exit 1
fi

exit 0

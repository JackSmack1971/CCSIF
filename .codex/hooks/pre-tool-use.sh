#!/usr/bin/env bash
set -uo pipefail

echo "[project-hook] PreToolUse" >&2

if command -v node >/dev/null 2>&1; then
  node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pre-tool-use-guard.js"
  status=$?
  exit "$status"
fi

echo "[project-hook] PreToolUse: blocked — node unavailable, Protected Area guard cannot run" >&2
exit 2

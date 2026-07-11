#!/usr/bin/env bash
set -uo pipefail

echo "[project-hook] PreToolUse" >&2

if command -v node >/dev/null 2>&1; then
  script_dir="$(dirname "$0")"
  script_dir="$(cd "$script_dir" && pwd)"
  node "$script_dir/lib/pre-tool-use-guard.js"
  status=$?
  exit "$status"
fi

echo "[project-hook] PreToolUse: blocked — node unavailable, Protected Area guard cannot run" >&2
exit 2

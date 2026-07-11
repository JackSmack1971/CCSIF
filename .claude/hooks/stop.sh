#!/usr/bin/env bash
set -euo pipefail

echo "[project-hook] Stop" >&2

if command -v node >/dev/null 2>&1; then
  script_dir=$(dirname "$0")
  script_dir=$(cd "$script_dir" && pwd)
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[project-hook] Stop: not inside a git work tree, skipping verification" >&2
  exit 0
fi

echo "[project-hook] Stop: working tree status" >&2
git status --short >&2

unstaged_check="$(git diff --check 2>&1)"
unstaged_status=$?
staged_check="$(git diff --cached --check 2>&1)"
staged_status=$?

if [ "$unstaged_status" -ne 0 ] || [ "$staged_status" -ne 0 ]; then
  echo "[project-hook] Stop: blocked: git diff --check found unresolved conflict markers or whitespace errors" >&2
  [ -n "$unstaged_check" ] && echo "$unstaged_check" >&2
  [ -n "$staged_check" ] && echo "$staged_check" >&2
  exit 2
fi

echo "[project-hook] Stop: git hygiene verified" >&2
exit 0

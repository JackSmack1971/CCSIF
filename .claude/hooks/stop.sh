#!/usr/bin/env bash
set -uo pipefail

echo "[project-hook] Stop" >&2

if command -v node >/dev/null 2>&1; then
  node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

if command -v python >/dev/null 2>&1; then
  python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../memory/hindsight.py" retain >/dev/null 2>&1 || true
  python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../memory/hindsight.py" observe >/dev/null 2>&1 || true
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
  echo "[project-hook] Stop: blocked — git diff --check found unresolved conflict markers or whitespace errors:" >&2
  [ -n "$unstaged_check" ] && echo "$unstaged_check" >&2
  [ -n "$staged_check" ] && echo "$staged_check" >&2
  exit 2
fi

# CLAUDE.md's "Source-of-Truth Commands" section is still an unfilled
# template (no package.json/test runner confirmed in this repo as of the
# 2026-07-09 architecture audit) — only git hygiene is verified here.
# Once that section names real install/test/lint/typecheck commands, wire
# them in below instead of claiming a check that was never run.
echo "[project-hook] Stop: git hygiene verified; no project test/lint/typecheck command is configured yet (CLAUDE.md 'Source-of-Truth Commands' still needs to be filled in)" >&2
exit 0

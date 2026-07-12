#!/usr/bin/env bash
set -euo pipefail

if command -v node >/dev/null 2>&1; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

set +e
unstaged_check="$(git diff --check 2>&1)" || unstaged_status=$?
staged_check="$(git diff --cached --check 2>&1)" || staged_status=$?
set -e

: "${unstaged_status:=0}"
: "${staged_status:=0}"

if [ "$unstaged_status" -ne 0 ] || [ "$staged_status" -ne 0 ]; then
  printf '%s\n' 'Blocked: git diff --check found unresolved conflict markers or whitespace errors.' >&2
  exit 2
fi

exit 0

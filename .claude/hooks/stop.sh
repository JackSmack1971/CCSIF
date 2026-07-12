#!/usr/bin/env bash
set -euo pipefail

if command -v node >/dev/null 2>&1; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# ponytail: keep stop-hook verification to deterministic repo checks; broader test runs can be invoked manually when a task needs them.
python3 .claude/scripts/control_plane_check.py
python3 .claude/scripts/rules_fidelity_check.py

exit 0

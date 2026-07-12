#!/usr/bin/env bash
set -euo pipefail

if command -v node >/dev/null 2>&1; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# ponytail: keep stop-hook verification to deterministic control-plane checks; repo-wide whitespace scans are manual because autocrlf noise makes them unreliable here.
# Run the deterministic control-plane verifier before ending the session.
python3 .claude/scripts/control_plane_check.py

exit 0

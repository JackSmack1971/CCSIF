#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [[ -z "$PYTHON" ]]; then
  printf '{"status":"error","message":"python3 or python is required to run validation"}\n' >&2
  exit 2
fi

exec "$PYTHON" "$ROOT/scripts/validate-skill.py" "$ROOT"

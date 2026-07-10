#!/usr/bin/env bash
# Usage: run_python.sh <script.py> [args...] — runs python3 if available, else
# python. Exit code: forwards the invoked script's exit code; 127 if neither
# python3 nor python is on PATH.
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$@"
fi

printf '%s\n' 'ERROR: Python 3.10 or later is required and must be available as python3 or python.' >&2
exit 127

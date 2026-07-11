#!/usr/bin/env bash
set -uo pipefail

if command -v python >/dev/null 2>&1; then
  python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../memory/hindsight.py" observe >/dev/null 2>&1 || true
  exit 0
fi

echo "[project-hook] hindsight-observe: python unavailable" >&2
exit 0

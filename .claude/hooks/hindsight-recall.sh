#!/usr/bin/env bash
set -uo pipefail

if command -v python >/dev/null 2>&1; then
  python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../memory/hindsight.py" recall
  exit $?
fi

echo "[project-hook] hindsight-recall: python unavailable" >&2
exit 2

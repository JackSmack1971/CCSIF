#!/usr/bin/env bash
set -uo pipefail

if command -v python >/dev/null 2>&1; then
  script_path="${BASH_SOURCE[0]//\\//}"
  script_dir="${script_path%/*}"
  if [ "$script_dir" = "$script_path" ]; then
    script_dir="."
  fi
  script_dir="$(cd -- "${script_dir:-.}" && pwd)"
  python "$script_dir/../memory/hindsight.py" recall
  exit $?
fi

echo "[project-hook] hindsight-recall: python unavailable" >&2
exit 2

#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_path="${BASH_SOURCE[0]//\\//}"
script_dir="${script_path%/*}"
if [ "$script_dir" = "$script_path" ]; then
  script_dir="."
fi
script_dir="$(cd -- "${script_dir:-.}" && pwd)"
phase2_script="$script_dir/../scripts/phase2_memory.py"

printf '%s' "$payload" | python3 "$phase2_script" postcompact >/dev/null 2>&1 || true

exit 0

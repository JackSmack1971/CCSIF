#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_path="${BASH_SOURCE[0]//\\//}"
script_dir="${script_path%/*}"
script_dir="$(cd -- "${script_dir:-.}" && pwd)"
phase3_script="$script_dir/../scripts/phase3_agents.py"

printf '%s' "$payload" | python3 "$phase3_script" subagent-start >/dev/null 2>&1 || true

exit 0

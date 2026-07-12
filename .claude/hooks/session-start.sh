#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
phase0_script="$script_dir/../scripts/phase0_control_plane.py"
phase2_script="$script_dir/../scripts/phase2_memory.py"

if command -v node >/dev/null 2>&1; then
  printf '%s' "$payload" | node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

python3 "$phase2_script" bootstrap-local-settings >/dev/null 2>&1 || true
printf '%s' "$payload" | python3 "$phase0_script" start >/dev/null
printf '%s' "$payload" | python3 "$phase2_script" session-start-restore || true

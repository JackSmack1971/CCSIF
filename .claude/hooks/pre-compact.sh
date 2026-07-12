#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
phase0_script="$script_dir/../scripts/phase0_control_plane.py"
phase2_script="$script_dir/../scripts/phase2_memory.py"

printf '%s' "$payload" | python3 "$phase0_script" compact >/dev/null
printf '%s' "$payload" | python3 "$phase2_script" precompact >/dev/null 2>&1 || true

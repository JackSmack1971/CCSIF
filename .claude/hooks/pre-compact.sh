#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
phase0_script="$script_dir/../scripts/phase0_control_plane.py"

printf '%s' "$payload" | python3 "$phase0_script" compact >/dev/null

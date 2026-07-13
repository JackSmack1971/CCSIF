#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
phase2_script="$script_dir/../scripts/phase2_memory.py"

printf '%s' "$payload" | python3 "$phase2_script" postcompact >/dev/null 2>&1 || true

exit 0

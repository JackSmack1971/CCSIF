#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_path="${BASH_SOURCE[0]//\\//}"
script_dir="${script_path%/*}"
if [ "$script_dir" = "$script_path" ]; then
  script_dir="."
fi
script_dir="$(cd -- "${script_dir:-.}" && pwd)"
phase0_script="$script_dir/../scripts/phase0_control_plane.py"
phase2_script="$script_dir/../scripts/phase2_memory.py"

if command -v node >/dev/null 2>&1; then
  printf '%s' "$payload" | node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

python3 "$phase2_script" bootstrap-local-settings >/dev/null 2>&1 || true
# Fail-open with evidence (Hardening 04/13, #152): a corrupt-but-recoverable
# phase0 state must never fail the whole SessionStart hook closed. The start
# subcommand durably records every decision/failure under
# .claude/state/logs/session-start/ before returning.
printf '%s' "$payload" | python3 "$phase0_script" start >/dev/null \
  || printf '%s\n' "phase0 session-start: start failed; decision evidence recorded under .claude/state/logs/session-start/" >&2
printf '%s' "$payload" | python3 "$phase2_script" session-start-restore || true

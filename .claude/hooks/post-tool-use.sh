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

if printf '%s' "$payload" | python3 "$phase0_script" hook-payload --hook-name PostToolUse >/dev/null; then
  :
else
  status=$?
  if [ "$status" -eq 2 ]; then
    printf '%s\n' "phase0 hook payload bug: repeated malformed PostToolUse payloads" >&2
    exit 2
  fi
  printf '%s\n' "phase0 hook payload tracking failed (exit $status); continuing" >&2
fi
lint_script="$script_dir/../scripts/phase6a_lint_on_edit.py"

if command -v node >/dev/null 2>&1; then
  printf '%s' "$payload" | node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

# Phase 0 result tracking is telemetry, never a gate: a rejected or
# duplicate result delivery must not fail the whole PostToolUse hook
# (Hardening 03/13).
printf '%s' "$payload" | python3 "$phase0_script" result >/dev/null \
  || printf '%s\n' "phase0 tracking: result recording failed; continuing" >&2
printf '%s' "$payload" | python3 "$lint_script" >/dev/null || true

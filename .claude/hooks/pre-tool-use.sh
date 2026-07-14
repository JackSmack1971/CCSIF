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

if printf '%s' "$payload" | python3 "$phase0_script" hook-payload --hook-name PreToolUse >/dev/null; then
  :
else
  status=$?
  if [ "$status" -eq 2 ]; then
    printf '%s\n' "phase0 hook payload bug: repeated malformed PreToolUse payloads" >&2
    exit 2
  fi
  printf '%s\n' "phase0 hook payload tracking failed (exit $status); continuing" >&2
fi
node_bin="$(command -v node 2>/dev/null || command -v node.exe 2>/dev/null || true)"
script_path="$script_dir/lib/pre-tool-use-guard.js"

if [ -z "$node_bin" ]; then
  printf '%s\n' 'Blocked: node unavailable; Protected Area guard cannot run.' >&2
  exit 2
fi

case "$node_bin" in
  *.exe) script_path="$(wslpath -w "$script_path")" ;;
esac

if printf '%s' "$payload" | "$node_bin" "$script_path"; then
  :
else
  status=$?
  exit "$status"
fi

# Phase 0 tracking: a genuine safety block (exit 2, e.g. workspace escape)
# still blocks the tool call; a tracking/state error (exit 1) must never
# deadlock the session's tool use — warn and continue (Hardening 03/13).
if printf '%s' "$payload" | python3 "$phase0_script" request >/dev/null; then
  :
else
  status=$?
  if [ "$status" -eq 2 ]; then
    exit 2
  fi
  printf '%s\n' "phase0 tracking: request failed (exit $status); tool call proceeds untracked" >&2
fi

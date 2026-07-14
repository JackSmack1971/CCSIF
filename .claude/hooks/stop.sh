#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_path="${BASH_SOURCE[0]//\\//}"
script_dir="${script_path%/*}"
if [ "$script_dir" = "$script_path" ]; then
  script_dir="."
fi
script_dir="$(cd -- "${script_dir:-.}" && pwd)"
gate_script="$script_dir/../scripts/phase6a_stop_gate.py"
phase0_script="$script_dir/../scripts/phase0_control_plane.py"

if printf '%s' "$payload" | python3 "$phase0_script" hook-payload --hook-name Stop >/dev/null; then
  :
else
  status=$?
  if [ "$status" -eq 2 ]; then
    printf '%s\n' "phase0 hook payload bug: repeated malformed Stop payloads" >&2
    exit 2
  fi
  printf '%s\n' "phase0 hook payload tracking failed (exit $status); continuing" >&2
fi

if command -v node >/dev/null 2>&1; then
  printf '%s' "$payload" | node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

# ponytail: keep stop-hook verification to deterministic repo checks
# (control-plane-check, rules-fidelity-check); broader test runs can be
# invoked manually when a task needs them. phase6a_stop_gate.py runs both,
# bounds retries per session, and escalates via the ledger instead of
# looping forever -- see .claude/rules/40-determinism-ladder.md.
printf '%s' "$payload" | python3 "$gate_script"
exit $?

#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
script_path="${BASH_SOURCE[0]//\\//}"
script_dir="${script_path%/*}"
script_dir="$(cd -- "${script_dir:-.}" && pwd)"
gate_script="$script_dir/../scripts/phase6a_stop_gate.py"

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

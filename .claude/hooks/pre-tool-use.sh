#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node_bin="$(command -v node 2>/dev/null || command -v node.exe 2>/dev/null || true)"
script_path="$script_dir/lib/pre-tool-use-guard.js"

if [ -n "$node_bin" ]; then
  if [[ "$node_bin" == *.exe ]]; then
    script_path="$(wslpath -w "$script_path")"
  fi
  if "$node_bin" "$script_path"; then
    printf '{}\n'
    exit 0
  fi

  status=$?
  if [ "$status" -eq 2 ]; then
    printf '%s\n' '{"decision":"block","reason":"Protected Area guard blocked the tool call."}'
    exit 2
  fi

  exit "$status"
fi

printf '%s\n' '{"decision":"block","reason":"node unavailable; Protected Area guard cannot run."}'
exit 2

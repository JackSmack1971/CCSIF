#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node_bin="$(command -v node 2>/dev/null || command -v node.exe 2>/dev/null || true)"
script_path="$script_dir/lib/pre-tool-use-guard.js"

if [ -z "$node_bin" ]; then
  printf '%s\n' 'Blocked: node unavailable; Protected Area guard cannot run.' >&2
  exit 2
fi

if [[ "$node_bin" == *.exe ]]; then
  script_path="$(wslpath -w "$script_path")"
fi

if "$node_bin" "$script_path"; then
  exit 0
else
  status=$?
  exit "$status"
fi

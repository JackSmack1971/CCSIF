#!/usr/bin/env bash
set -euo pipefail

echo "[project-hook] PostToolUse"

if command -v node >/dev/null 2>&1; then
  script_dir="$(dirname "$0")"
  script_dir="$(cd "$script_dir" && pwd)"
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

# Placeholder: implement post-action verification hooks here.

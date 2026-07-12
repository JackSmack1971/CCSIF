#!/usr/bin/env bash
set -euo pipefail

if command -v node >/dev/null 2>&1; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  node "$script_dir/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

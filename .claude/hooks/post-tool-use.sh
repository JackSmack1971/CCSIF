#!/usr/bin/env bash
set -euo pipefail

echo "[project-hook] PostToolUse"

if command -v node >/dev/null 2>&1; then
  node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

# Placeholder: implement post-action verification hooks here.

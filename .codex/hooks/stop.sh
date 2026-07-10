#!/usr/bin/env bash
set -euo pipefail

echo "[project-hook] Stop"

if command -v node >/dev/null 2>&1; then
  node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/trace-writer.js" >/dev/null 2>&1 || true
fi

# Placeholder: final session checks.
# Example: git status --short

#!/usr/bin/env bash
set -euo pipefail

echo "[project-hook] SessionStart"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --short
fi

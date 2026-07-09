#!/usr/bin/env python3
"""List common dependency manifests and lockfiles."""

from pathlib import Path

NAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pyproject.toml", "requirements.txt", "poetry.lock", "Pipfile", "Pipfile.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "Gemfile", "Gemfile.lock", "composer.json", "composer.lock"
}

for path in sorted(Path(".").rglob("*")):
    if ".git" in path.parts or "node_modules" in path.parts:
        continue
    if path.name in NAMES:
        print(path)

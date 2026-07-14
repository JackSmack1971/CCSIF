#!/usr/bin/env python3
"""Lightweight fidelity check for `.claude/rules` corpus changes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT / ".claude" / "rules"
EXPECTED_SCOPES = {
    "00-core-workflow.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "10-karpathy-guidelines.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "20-lifecycle-gates.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "30-skill-taxonomy.md": [
        ".claude/commands/**",
        ".claude/skills/**",
        "CLAUDE.md",
    ],
    "40-determinism-ladder.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "architecture.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "claude-code-ecosystem.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "constitutional-agent-engineering-rules.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "control-plane.md": [
        ".claude/**",
        ".mcp.json",
        "managed-settings.json",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "dynamic-workflows.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
    "failure-escalation.md": ["**/*"],
    "hindsight-memory.md": ["**/*"],
    "mcp-resilience.md": [".mcp.json", ".claude/**", "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"],
    "memory-and-compaction.md": [".claude/**", "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"],
    "persona-profile.md": ["**/*"],
    "security.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "SECURITY.md",
        ".github/**",
        ".mcp.json",
        "managed-settings.json",
    ],
    "subagent-routing.md": [
        ".claude/agents/**",
        ".claude/commands/**",
        ".claude/skills/**",
        ".claude/workflows/**",
        ".claude/hooks/**",
        "CLAUDE.md",
    ],
    "surgical-density.md": ["**/*"],
    "testing.md": [
        ".claude/**",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/**",
    ],
}
MAX_LINES = {
    "constitutional-agent-engineering-rules.md": 40,
    "surgical-density.md": 40,
    "claude-code-ecosystem.md": 20,
    "control-plane.md": 25,
    "dynamic-workflows.md": 25,
    "security.md": 22,
    "testing.md": 20,
    "memory-and-compaction.md": 30,
    "10-karpathy-guidelines.md": 30,
    "20-lifecycle-gates.md": 40,
    "30-skill-taxonomy.md": 25,
    "40-determinism-ladder.md": 100,
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def split_frontmatter(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail("missing frontmatter start")
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        fail("missing frontmatter end")
    return lines[1:end], "\n".join(lines[end + 1 :])


def parse_paths(frontmatter: list[str]) -> list[str]:
    paths: list[str] = []
    in_paths = False
    for line in frontmatter:
        stripped = line.strip()
        if stripped == "paths:":
            in_paths = True
            continue
        if in_paths and stripped.startswith("- "):
            value = stripped[2:].strip()
            if not (value.startswith('"') and value.endswith('"')):
                fail(f"paths entry must be quoted: {value}")
            paths.append(value[1:-1])
            continue
        if in_paths and stripped and not stripped.startswith("#"):
            in_paths = False
    return paths


def main() -> int:
    if not RULES_DIR.is_dir():
        fail("missing .claude/rules directory")

    for path in sorted(RULES_DIR.glob("*.md")):
        if path.name in {"README.md", "AGENTS.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        expected = EXPECTED_SCOPES.get(path.name)
        if expected is None:
            fail(f"unexpected rules file: {path.name}")
        actual = parse_paths(frontmatter)
        if actual != expected:
            fail(f"path scope changed for {path.name}: {actual!r} != {expected!r}")
        if body.count("\n# ") != 0 and not body.lstrip().startswith("# "):
            fail(f"{path.name} must contain exactly one top-level H1")
        if not body.lstrip().startswith("# "):
            fail(f"{path.name} is missing a top-level H1")
        max_lines = MAX_LINES.get(path.name)
        if max_lines is not None and len(text.splitlines()) > max_lines:
            fail(f"{path.name} exceeds line budget of {max_lines}")

    print("rules-fidelity-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

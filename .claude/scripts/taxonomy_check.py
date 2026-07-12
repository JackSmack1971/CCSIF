#!/usr/bin/env python3
"""Phase 5A structural/routing linter for the portable control-plane layout.

Detects, against real repository files (never invented data):
  1. taxonomy violations   - a user-invoked command body calling another command
  2. duplicate responsibility - two skills/commands sharing one description string
  3. always-loaded context budget - CLAUDE.md + paths:["**/*"] rules vs a declared budget
  4. global-path dependency   - a hook/script hard-referencing ~/.claude or $HOME/.claude
  5. oversized root guidance  - CLAUDE.md line count vs a declared budget

Every check takes an explicit `root` so tests can exercise each detector
against isolated fixture trees instead of mutating this repository.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF_PATH = Path(__file__).resolve()

ROOT_GUIDANCE_MAX_LINES = 200
ALWAYS_LOADED_MAX_LINES = 400
GLOBAL_PATH_PATTERNS = (re.compile(r"~[/\\]\.claude"), re.compile(r"\$HOME[/\\]\.claude"))
NEGATION_WINDOW = 120
NEGATION_WORDS = re.compile(r"\bnever\b|\bnot require|\bavoid\b|\bmust not\b", re.IGNORECASE)

SKIP_NAMES = {"README.md", "AGENTS.md"}


class TaxonomyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise TaxonomyError(message)


def command_stems(commands_dir: Path) -> list[str]:
    if not commands_dir.is_dir():
        return []
    return [p.stem for p in commands_dir.glob("*.md") if p.name not in SKIP_NAMES]


def check_no_command_cross_invocation(root: Path = ROOT) -> None:
    commands_dir = root / ".claude" / "commands"
    stems = command_stems(commands_dir)
    for path in commands_dir.glob("*.md") if commands_dir.is_dir() else []:
        if path.name in SKIP_NAMES:
            continue
        body = path.read_text(encoding="utf-8")
        for other in stems:
            if other == path.stem:
                continue
            if re.search(rf"(?<![\w-])/{re.escape(other)}(?![\w-])", body):
                fail(
                    f"taxonomy violation: command {path.name} invokes another "
                    f"command (/{other}); user-invoked commands must orchestrate "
                    "skills, never call each other"
                )


def skill_description(skill_dir: Path) -> str | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("description:"):
            return stripped[len("description:") :].strip()
        if stripped == "---":
            break
    return None


def check_no_duplicate_responsibility(root: Path = ROOT) -> None:
    skills_dir = root / ".claude" / "skills"
    commands_dir = root / ".claude" / "commands"
    seen: dict[str, str] = {}
    entries: list[tuple[str, str]] = []
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            desc = skill_description(skill_dir)
            if desc:
                entries.append((f"skills/{skill_dir.name}", desc))
    if commands_dir.is_dir():
        for path in sorted(commands_dir.glob("*.md")):
            if path.name in SKIP_NAMES:
                continue
            text = path.read_text(encoding="utf-8")
            first_line = text.splitlines()[0] if text else ""
            entries.append((f"commands/{path.stem}", first_line.strip()))
    for name, desc in entries:
        if not desc:
            continue
        if desc in seen:
            fail(f"duplicate responsibility: {name!r} and {seen[desc]!r} share one description string: {desc!r}")
        seen[desc] = name


def parse_rule_paths(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    paths: list[str] = []
    in_paths = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped == "paths:":
            in_paths = True
            continue
        if in_paths and stripped.startswith("- "):
            value = stripped[2:].strip().strip('"')
            paths.append(value)
            continue
        if in_paths and stripped and not stripped.startswith("#"):
            in_paths = False
    return paths


def check_always_loaded_context_budget(root: Path = ROOT, budget: int = ALWAYS_LOADED_MAX_LINES) -> None:
    claude_md = root / "CLAUDE.md"
    rules_dir = root / ".claude" / "rules"
    total = 0
    parts = []
    if claude_md.is_file():
        n = len(claude_md.read_text(encoding="utf-8").splitlines())
        total += n
        parts.append(f"CLAUDE.md={n}")
    if rules_dir.is_dir():
        for path in sorted(rules_dir.glob("*.md")):
            if path.name in SKIP_NAMES:
                continue
            text = path.read_text(encoding="utf-8")
            if "**/*" in parse_rule_paths(text):
                n = len(text.splitlines())
                total += n
                parts.append(f"{path.name}={n}")
    if total > budget:
        fail(f"always-loaded instruction budget exceeded: {total} lines > {budget} ({', '.join(parts)})")


def check_no_global_path_dependency(root: Path = ROOT) -> None:
    scan_dirs = [root / ".claude" / "hooks", root / ".claude" / "scripts", root / ".claude" / "commands"]
    for directory in scan_dirs:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in {".sh", ".py", ".js", ".md"}:
                continue
            if path.resolve() == SELF_PATH:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in GLOBAL_PATH_PATTERNS:
                for match in pattern.finditer(text):
                    window = text[max(0, match.start() - NEGATION_WINDOW) : match.start()]
                    if NEGATION_WORDS.search(window):
                        continue
                    fail(
                        f"global-path dependency: {path.relative_to(root)} references a "
                        "~/.claude or $HOME/.claude path outside a documented non-dependency statement"
                    )


def check_root_guidance_size(root: Path = ROOT, max_lines: int = ROOT_GUIDANCE_MAX_LINES) -> None:
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        fail("missing root CLAUDE.md")
    n = len(claude_md.read_text(encoding="utf-8").splitlines())
    if n > max_lines:
        fail(f"CLAUDE.md exceeds root guidance budget: {n} lines > {max_lines}")


def run_all(root: Path = ROOT) -> None:
    check_no_command_cross_invocation(root)
    check_no_duplicate_responsibility(root)
    check_always_loaded_context_budget(root)
    check_no_global_path_dependency(root)
    check_root_guidance_size(root)


def main() -> int:
    try:
        run_all(ROOT)
    except TaxonomyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("taxonomy-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

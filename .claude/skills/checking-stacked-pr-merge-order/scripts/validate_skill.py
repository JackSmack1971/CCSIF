#!/usr/bin/env python3
"""Validate metadata, structure, scripts, tests, and safety invariants."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

NAME_MAX = 64
DESCRIPTION_MAX = 1024
SKILL_LINE_MAX = 500
FILE_MAX = 200


def fail(message: str, details: dict | None = None) -> None:
    payload = {"status": "error", "message": message}
    if details:
        payload["details"] = details
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(1)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        fail("SKILL.md frontmatter is missing or malformed")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            fail(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skill = root / "SKILL.md"
    if not skill.is_file():
        fail("SKILL.md is missing")
    text = skill.read_text(encoding="utf-8")
    values = parse_frontmatter(text)
    if set(values) != {"name", "description"}:
        fail("Frontmatter must contain only name and description")
    if not values["name"] or len(values["name"]) > NAME_MAX:
        fail("name is empty or exceeds 64 characters")
    description = values["description"]
    if not description or len(description) > DESCRIPTION_MAX:
        fail("description is empty or exceeds 1024 characters")
    if "\n" in description or ":" in description or "<" in description or ">" in description:
        fail("description must be one line without colons or angle brackets")
    if not description.startswith("Use when "):
        fail("description must lead with precise activation conditions")
    if "resolve" not in description.lower() or "merge cleanly" not in description.lower():
        fail("description must discover conflict-resolution and clean-merge requests")

    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    if len(re.findall(r"^# ", prose, flags=re.MULTILINE)) != 1:
        fail("SKILL.md must have exactly one top-level heading outside code fences")
    skill_lines = len(text.splitlines())
    if skill_lines > SKILL_LINE_MAX:
        fail(f"SKILL.md exceeds {SKILL_LINE_MAX} lines")

    required = [
        root / "scripts" / "check_merge_order.py",
        root / "scripts" / "conflict_pass.py",
        root / "scripts" / "validate_skill.py",
        root / "resources" / "conflict-resolution.md",
        root / "resources" / "report-contract.md",
        root / "resources" / "evaluations.md",
        root / "tests" / "test_check_merge_order.py",
        root / "tests" / "test_conflict_pass.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        fail("Missing required files", {"missing": missing})

    files = [path for path in root.rglob("*") if path.is_file()]
    if len(files) > FILE_MAX:
        fail(f"Skill contains {len(files)} files, exceeding the {FILE_MAX}-file portability limit")
    forbidden = [
        str(path.relative_to(root))
        for path in files
        if "__pycache__" in path.parts or path.suffix == ".pyc"
    ]
    if forbidden:
        fail("Generated Python cache files must not be packaged", {"files": forbidden})

    local_links = re.findall(r"\]\(([^)]+\.md)(?:#[^)]+)?\)", text)
    for link in local_links:
        target = (root / link).resolve()
        if root.resolve() not in target.parents or not target.is_file():
            fail(f"Invalid direct Markdown reference in SKILL.md: {link}")
    for resource in (root / "resources").glob("*.md"):
        resource_text = resource.read_text(encoding="utf-8")
        nested = re.findall(r"\]\((?!https?://)([^)]+\.md)(?:#[^)]+)?\)", resource_text)
        if nested:
            fail(f"Reference file {resource.name} contains nested Markdown references", {"links": nested})

    script_paths = [root / "scripts" / "check_merge_order.py", root / "scripts" / "conflict_pass.py"]
    for script_path in script_paths:
        source = script_path.read_text(encoding="utf-8")
        if "shell=True" in source:
            fail(f"Unsafe shell execution found in {script_path.name}")
        try:
            compile(source, str(script_path), "exec")
        except SyntaxError as exc:
            fail(f"Python compilation failed for {script_path.name}", {"error": str(exc)})

    test_result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if test_result.returncode != 0:
        fail("Unit tests failed", {"stdout": test_result.stdout, "stderr": test_result.stderr})
    match = re.search(r"Ran (\d+) tests?", test_result.stderr + test_result.stdout)
    test_count = int(match.group(1)) if match else None

    print(json.dumps({
        "status": "ok",
        "name": values["name"],
        "description_chars": len(description),
        "skill_lines": skill_lines,
        "skill_words": len(text.split()),
        "files": len(files),
        "tests": test_count,
        "safety_checks": [
            "no shell=True",
            "exact plan approval",
            "isolated worktrees",
            "exact-OID push lease",
            "no unqualified force push",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

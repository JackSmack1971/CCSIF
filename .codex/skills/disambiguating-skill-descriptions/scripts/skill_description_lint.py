#!/usr/bin/env python3
"""Lint Claude Code SKILL.md frontmatter descriptions for router disambiguation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

GENERIC_PATTERNS = [
    "use for analysis",
    "help with code",
    "improve docs",
    "documentation helper",
    "review changes",
    "optimize project",
    "general automation",
    "helps with",
]

STOPWORDS = {
    "use", "when", "for", "and", "or", "the", "that", "this", "with", "from", "into",
    "user", "users", "query", "queries", "trigger", "triggers", "only", "not", "requires",
    "instead", "route", "those", "skill", "skills", "general", "specific", "exact",
}


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def extract_frontmatter(text: str) -> Tuple[str | None, List[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, []
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx]), lines[1:idx]
    return None, []


def scalar_field(lines: List[str], field: str) -> Tuple[str | None, str | None, int | None]:
    pattern = re.compile(rf"^{re.escape(field)}\s*:\s*(.*)$")
    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            raw = match.group(1).strip()
            if raw in {"", "|", ">", "|-", ">-", "|+", ">+"}:
                return None, raw, idx
            return strip_quotes(raw), raw, idx
    return None, None, None


def natural_trigger_count(description: str) -> int:
    marker = "Trigger on"
    if marker not in description:
        return 0
    tail = description.split(marker, 1)[1]
    for boundary in [". NOT", " NOT for", ". Requires", " Requires"]:
        if boundary in tail:
            tail = tail.split(boundary, 1)[0]
            break
    phrases = [p.strip(" .;") for p in tail.split(",")]
    phrases = [p for p in phrases if p]
    return len(phrases)


def distinctive_keyword_count(description: str) -> int:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_.-]{4,}", description.lower())
    return len({w for w in words if w not in STOPWORDS})


def validate_description(description: str | None) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if description is None:
        return ["missing description scalar"], warnings

    if len(description) > 1024:
        errors.append(f"description exceeds 1024 characters by {len(description) - 1024}")
    if "\n" in description:
        errors.append("description must be a single line")
    if ":" in description:
        errors.append("description must not contain colons")
    if "<" in description or ">" in description:
        errors.append("description must not contain angle brackets")
    if not (description.startswith("Use when") or description.startswith("Trigger on queries that")):
        errors.append("description must start with Use when or Trigger on queries that")
    trigger_count = natural_trigger_count(description)
    if trigger_count < 3 or trigger_count > 5:
        errors.append(f"description must list 3 to 5 canonical trigger patterns after Trigger on, found {trigger_count}")
    if "NOT for" not in description:
        errors.append("description must carve out negative space with NOT for")
    if "Requires" not in description:
        warnings.append("description should include a Requires clause naming mandatory outputs or constraints")
    lower = description.lower()
    for phrase in GENERIC_PATTERNS:
        if phrase in lower:
            warnings.append(f"description contains broad collision-prone phrase {phrase!r}")
    if distinctive_keyword_count(description) < 6:
        warnings.append("description may lack distinctive domain keywords or constraints")
    if len(description) > 900:
        warnings.append("description is close to 1024 character limit")
    return errors, warnings


def iter_skill_files(root: Path) -> List[Path]:
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    skill_files: List[Path] = []
    for path in root.rglob("SKILL.md"):
        if any(part in ignored for part in path.parts):
            continue
        skill_files.append(path)
    return sorted(skill_files)


def lint_file(path: Path, root: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    fm, lines = extract_frontmatter(text)
    rel = path.relative_to(root).as_posix()
    errors: List[str] = []
    warnings: List[str] = []
    name = None
    description = None

    if fm is None:
        errors.append("missing YAML frontmatter bounded by ---")
    else:
        name, raw_name, _ = scalar_field(lines, "name")
        description, raw_description, _ = scalar_field(lines, "description")
        if name is None:
            errors.append("missing name scalar")
        elif len(name) > 64:
            errors.append("name exceeds 64 characters")
        elif not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
            warnings.append("name is not lowercase hyphen form")
        if raw_description in {"", "|", ">", "|-", ">-", "|+", ">+"}:
            errors.append("description must not use empty, folded, or block YAML style")
        d_errors, d_warnings = validate_description(description)
        errors.extend(d_errors)
        warnings.extend(d_warnings)

    status = "error" if errors else "warning" if warnings else "pass"
    return {
        "path": rel,
        "name": name,
        "description_length": len(description) if description else 0,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Skill Description Lint Report",
        "",
        f"Scanned skills: {report['summary']['scanned']}",
        f"Errors: {report['summary']['errors']}",
        f"Warnings: {report['summary']['warnings']}",
        "",
    ]
    for item in report["results"]:
        lines.append(f"## {item['path']}")
        lines.append("")
        lines.append(f"Status: {item['status']}")
        if item.get("name"):
            lines.append(f"Name: `{item['name']}`")
        if item["errors"]:
            lines.append("Errors:")
            for error in item["errors"]:
                lines.append(f"- {error}")
        if item["warnings"]:
            lines.append("Warnings:")
            for warning in item["warnings"]:
                lines.append(f"- {warning}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint SKILL.md descriptions for routing disambiguation.")
    parser.add_argument("root", help="Root directory containing one or more SKILL.md files")
    parser.add_argument("--json", dest="json_path", help="Write machine-readable JSON report")
    parser.add_argument("--markdown", dest="markdown_path", help="Write human-readable Markdown report")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR root is not a directory: {root}", file=sys.stderr)
        return 4

    try:
        results = [lint_file(path, root) for path in iter_skill_files(root)]
        error_count = sum(len(item["errors"]) for item in results)
        warning_count = sum(len(item["warnings"]) for item in results)
        report = {
            "summary": {
                "root": str(root),
                "scanned": len(results),
                "errors": error_count,
                "warnings": warning_count,
                "passed": sum(1 for item in results if item["status"] == "pass"),
            },
            "results": results,
        }
        if args.json_path:
            Path(args.json_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        if args.markdown_path:
            write_markdown(report, Path(args.markdown_path))
        print(json.dumps(report["summary"], sort_keys=True))
        if error_count:
            return 3
        if warning_count:
            return 2
        return 0
    except OSError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

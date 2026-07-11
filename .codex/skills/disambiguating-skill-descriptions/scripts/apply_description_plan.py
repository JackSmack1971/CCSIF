#!/usr/bin/env python3
"""Validate and optionally apply a JSON plan that rewrites SKILL.md descriptions."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
LINTER_PATH = SCRIPT_DIR / "skill_description_lint.py"
spec = importlib.util.spec_from_file_location("skill_description_lint", LINTER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load linter module")
linter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linter)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def replace_description_line(text: str, new_description: str) -> Tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, False
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return text, False
    pattern = re.compile(r"^(description\s*:\s*)(.*?)(\r?\n?)$")
    for idx in range(1, end_idx):
        match = pattern.match(lines[idx])
        if match:
            newline = match.group(3) or "\n"
            lines[idx] = f"description: {new_description}{newline}"
            return "".join(lines), True
    return text, False


def read_frontmatter_fields(path: Path) -> Tuple[str | None, str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    _, lines = linter.extract_frontmatter(text)
    name, _, _ = linter.scalar_field(lines, "name")
    description, raw_description, _ = linter.scalar_field(lines, "description")
    return name, description, raw_description


def validate_plan(root: Path, plan: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int, int]:
    report_items: List[Dict[str, Any]] = []
    errors_total = 0
    warnings_total = 0

    if not isinstance(plan, dict):
        return [{"path": None, "status": "error", "errors": ["plan must be a JSON object"], "warnings": []}], 1, 0
    if plan.get("version") != 1:
        return [{"path": None, "status": "error", "errors": ["plan version must be 1"], "warnings": []}], 1, 0
    changes = plan.get("changes")
    if not isinstance(changes, list) or not changes:
        return [{"path": None, "status": "error", "errors": ["changes must be a non-empty array"], "warnings": []}], 1, 0

    seen_paths = set()
    required = {"path", "name", "old_description", "new_description", "rationale", "negative_space"}

    for idx, change in enumerate(changes):
        item_errors: List[str] = []
        item_warnings: List[str] = []
        rel_path = change.get("path") if isinstance(change, dict) else None
        item = {"index": idx, "path": rel_path, "status": "pending", "errors": item_errors, "warnings": item_warnings}

        if not isinstance(change, dict):
            item_errors.append("change must be an object")
            report_items.append(item)
            continue
        missing = sorted(required - set(change.keys()))
        if missing:
            item_errors.append("missing required fields: " + ", ".join(missing))
        for field in required & set(change.keys()):
            if not isinstance(change[field], str) or not change[field].strip():
                item_errors.append(f"{field} must be a non-empty string")
        if not rel_path or not isinstance(rel_path, str):
            item_errors.append("path must be a string")
            report_items.append(item)
            continue
        if rel_path in seen_paths:
            item_errors.append("duplicate path in plan")
        seen_paths.add(rel_path)
        if not rel_path.endswith("SKILL.md"):
            item_errors.append("path must end with SKILL.md")

        target = (root / rel_path).resolve()
        if not is_under(target, root):
            item_errors.append("path resolves outside supplied root")
        elif not target.exists():
            item_errors.append("target SKILL.md does not exist")
        else:
            try:
                current_name, current_description, raw_description = read_frontmatter_fields(target)
                if raw_description in {"", "|", ">", "|-", ">-", "|+", ">+"}:
                    item_errors.append("current description is folded, block, or empty and requires manual repair")
                if current_name != change.get("name"):
                    item_errors.append("name does not match current frontmatter")
                if current_description != change.get("old_description"):
                    item_errors.append("old_description does not exactly match current frontmatter")
                d_errors, d_warnings = linter.validate_description(change.get("new_description"))
                item_errors.extend(d_errors)
                item_warnings.extend(d_warnings)
            except OSError as exc:
                item_errors.append(str(exc))

        if len(change.get("rationale", "")) < 20:
            item_warnings.append("rationale is short and may not explain the collision fixed")
        if len(change.get("negative_space", "")) < 20:
            item_warnings.append("negative_space is short and may not name adjacent routes")

        item["status"] = "error" if item_errors else "warning" if item_warnings else "pass"
        errors_total += len(item_errors)
        warnings_total += len(item_warnings)
        report_items.append(item)

    return report_items, errors_total, warnings_total


def apply_changes(root: Path, changes: List[Dict[str, Any]]) -> int:
    applied = 0
    for change in changes:
        target = (root / change["path"]).resolve()
        text = target.read_text(encoding="utf-8")
        updated, changed = replace_description_line(text, change["new_description"])
        if not changed:
            raise RuntimeError(f"could not replace description line in {change['path']}")
        target.write_text(updated, encoding="utf-8")
        applied += 1
    return applied


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and optionally apply a SKILL.md description edit plan.")
    parser.add_argument("root", help="Root directory containing target SKILL.md files")
    parser.add_argument("plan", help="description-plan.json path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate only and do not edit files")
    mode.add_argument("--apply", action="store_true", help="Apply validated description changes")
    parser.add_argument("--report", help="Write machine-readable JSON report")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    plan_path = Path(args.plan).resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR root is not a directory: {root}", file=sys.stderr)
        return 4
    if not plan_path.exists() or not plan_path.is_file():
        print(f"ERROR plan is not a file: {plan_path}", file=sys.stderr)
        return 4

    try:
        plan = load_json(plan_path)
        items, error_count, warning_count = validate_plan(root, plan)
        applied = 0
        if args.apply and error_count == 0:
            applied = apply_changes(root, plan["changes"])
        report = {
            "summary": {
                "root": str(root),
                "plan": str(plan_path),
                "mode": "apply" if args.apply else "dry-run",
                "changes": len(plan.get("changes", [])) if isinstance(plan, dict) and isinstance(plan.get("changes"), list) else 0,
                "applied": applied,
                "errors": error_count,
                "warnings": warning_count,
            },
            "results": items,
        }
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report["summary"], sort_keys=True))
        if error_count:
            return 3
        if warning_count:
            return 2
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

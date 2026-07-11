#!/usr/bin/env python3
"""Create and optionally apply safe mechanical fixes from a skill audit report.

This script intentionally does not rewrite domain-specific descriptions. It creates
an explicit plan for Claude or a human to inspect, then applies only low-risk fixes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def normalize_name(raw: str) -> str:
    name = raw.strip().lower().replace("_", "-").replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:64]


def split_frontmatter(text: str) -> tuple[Optional[List[str]], List[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[: i + 1], lines[i + 1 :]
    return None, lines


def has_key(fm_lines: List[str], key: str) -> bool:
    return any(re.match(rf"^{re.escape(key)}:\s*", line) for line in fm_lines)


def insert_after_open(fm_lines: List[str], line: str) -> List[str]:
    return [fm_lines[0], line, *fm_lines[1:]]


def make_plan(audit: Dict[str, Any]) -> Dict[str, Any]:
    actions: List[Dict[str, Any]] = []
    for skill in audit.get("skills", []):
        skill_path = Path(skill["path"])
        skill_dir = skill_path.parent
        finding_codes = {f["code"] for f in skill.get("findings", [])}
        if "missing-name" in finding_codes:
            candidate = normalize_name(skill_dir.name)
            actions.append({
                "type": "add_name",
                "path": str(skill_path),
                "value": candidate,
                "safe": bool(NAME_RE.match(candidate)),
                "reason": "Missing required name can be derived from containing directory.",
            })
        if "invalid-name" in finding_codes:
            candidate = normalize_name(skill_dir.name)
            actions.append({
                "type": "replace_name",
                "path": str(skill_path),
                "value": candidate,
                "safe": bool(NAME_RE.match(candidate)),
                "reason": "Invalid name can be replaced with a normalized form of the containing directory.",
            })
        if "reserved-name" in finding_codes:
            actions.append({
                "type": "manual_semantic_repair_required",
                "path": str(skill_path),
                "safe": False,
                "reason": "Name uses a reserved namespace (claude/anthropic); requires a domain-preserving rename by Claude.",
                "finding_codes": ["reserved-name"],
            })
        if "missing-verification-log" in finding_codes:
            actions.append({
                "type": "create_verification_placeholder",
                "path": str(skill_dir / "VERIFICATION.md"),
                "safe": True,
                "reason": "Verification log is missing. Placeholder is explicit and does not claim tests passed.",
            })
        if "missing-evals" in finding_codes:
            actions.append({
                "type": "create_evals_placeholder",
                "path": str(skill_dir / "evals" / "evals.json"),
                "safe": True,
                "reason": "Evals are missing. Placeholder marks evaluation design as pending.",
            })
        semantic_codes = sorted(c for c in finding_codes if c.startswith("description-") or c in {"missing-validation-loop", "missing-checklist", "missing-tool-boundaries", "skill-too-long", "deep-reference-chain"})
        if semantic_codes:
            actions.append({
                "type": "manual_semantic_repair_required",
                "path": str(skill_path),
                "safe": False,
                "reason": "Requires domain intent preservation and should be edited by Claude after reading the skill.",
                "finding_codes": semantic_codes,
            })
    return {"schema_version": "1.0", "actions": actions}


def apply_plan(plan: Dict[str, Any]) -> int:
    applied = 0
    skipped = 0
    for action in plan.get("actions", []):
        if not action.get("safe"):
            skipped += 1
            continue
        typ = action["type"]
        path = Path(action["path"])
        if typ == "add_name":
            text = path.read_text(encoding="utf-8", errors="replace")
            fm, body = split_frontmatter(text)
            if fm is None or has_key(fm, "name"):
                skipped += 1
                continue
            new_fm = insert_after_open(fm, f"name: {action['value']}")
            path.write_text("\n".join(new_fm + body) + "\n", encoding="utf-8")
            applied += 1
        elif typ == "replace_name":
            text = path.read_text(encoding="utf-8", errors="replace")
            fm, body = split_frontmatter(text)
            if fm is None:
                skipped += 1
                continue
            new_fm = [re.sub(r"^name:\s*.*$", f"name: {action['value']}", line) if re.match(r"^name:\s*", line) else line for line in fm]
            if new_fm == fm:
                skipped += 1
                continue
            path.write_text("\n".join(new_fm + body) + "\n", encoding="utf-8")
            applied += 1
        elif typ == "create_verification_placeholder":
            if path.exists():
                skipped += 1
                continue
            path.write_text("# Verification\n\nValidation pending. This file was created by skill-auditor as a placeholder and must not be treated as evidence that tests passed.\n", encoding="utf-8")
            applied += 1
        elif typ == "create_evals_placeholder":
            if path.exists():
                skipped += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "schema_version": "1.0",
                "status": "pending",
                "note": "Created by skill-auditor. Replace with targeted activation and task-quality evaluations.",
                "evals": []
            }, indent=2) + "\n", encoding="utf-8")
            applied += 1
    print(json.dumps({"status": "ok", "applied": applied, "skipped": skipped}, sort_keys=True))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Plan and apply safe mechanical skill fixes.")
    parser.add_argument("--audit", required=True, help="Audit JSON from audit_skill_corpus.py.")
    parser.add_argument("--plan", required=True, help="Plan JSON path to write or read.")
    parser.add_argument("--dry-run", action="store_true", help="Write plan only.")
    parser.add_argument("--apply", action="store_true", help="Apply safe actions from the plan.")
    args = parser.parse_args(argv)
    audit_path = Path(args.audit)
    plan_path = Path(args.plan)
    if args.dry_run or not plan_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        plan = make_plan(audit)
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "planned", "actions": len(plan["actions"]), "plan": str(plan_path)}, sort_keys=True))
        if args.dry_run and not args.apply:
            return 0
    if args.apply:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        return apply_plan(plan)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

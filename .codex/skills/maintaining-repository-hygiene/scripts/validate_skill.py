#!/usr/bin/env python3
"""Static validation for the maintaining-repository-hygiene skill package."""
from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


def validate(root: Path, zip_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, str]] = []
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        errors.append("SKILL.md is missing.")
        return {"status": "invalid", "errors": errors, "warnings": warnings, "checks": checks}
    text = skill_file.read_text(encoding="utf-8")
    meta = frontmatter(text)
    name = meta.get("name", "")
    description = meta.get("description", "")
    if not name or len(name) > 64:
        errors.append(f"name must be 1-64 characters; got {len(name)}.")
    if not description or len(description) > 1024:
        errors.append(f"description must be 1-1024 characters; got {len(description)}.")
    if re.search(r"\b(?:I|we|you)\b", description, flags=re.IGNORECASE):
        warnings.append("description may not be consistently third-person.")
    checks.append({"check": "metadata", "status": "pass" if not errors else "fail"})

    body = text.split("\n---\n", 1)[1] if "\n---\n" in text else text
    word_count = len(re.findall(r"\S+", body))
    if word_count > 4200:
        errors.append(f"SKILL.md body exceeds the 4,200-word token-discipline threshold: {word_count} words.")
    if len(body.splitlines()) > 100 and not re.search(r"(?im)^## Table of contents\s*$", body):
        errors.append("SKILL.md exceeds 100 lines without a Table of contents section.")
    checks.append({"check": "token-discipline", "status": "pass" if word_count <= 4200 else "fail"})

    local_links = re.findall(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)", text)
    for link in local_links:
        target = (root / link.split("#", 1)[0]).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            errors.append(f"Local reference escapes skill root: {link}")
            continue
        if not target.exists():
            errors.append(f"Broken local reference in SKILL.md: {link}")
    checks.append({"check": "direct-references", "status": "pass" if not any("reference" in item.lower() for item in errors) else "fail"})

    for markdown in sorted(root.rglob("*.md")):
        md_text = markdown.read_text(encoding="utf-8")
        h1_count = len(re.findall(r"(?m)^# (?!#)", md_text))
        if h1_count != 1:
            errors.append(f"{markdown.relative_to(root)} must contain exactly one top-level H1; found {h1_count}.")
        if markdown != skill_file:
            nested_local = re.findall(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+\.md(?:#[^)]+)?)\)", md_text)
            if nested_local:
                errors.append(f"{markdown.relative_to(root)} contains nested local Markdown references: {nested_local}")
    checks.append({"check": "markdown-structure", "status": "pass" if not any("top-level H1" in item or "nested local" in item for item in errors) else "fail"})

    for json_file in sorted(root.rglob("*.json")):
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON in {json_file.relative_to(root)}: {exc}")
    checks.append({"check": "json", "status": "pass" if not any("Invalid JSON" in item for item in errors) else "fail"})

    for script in sorted((root / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except Exception as exc:
            errors.append(f"Python compile failure in {script.name}: {exc}")
    checks.append({"check": "python-compile", "status": "pass" if not any("compile failure" in item for item in errors) else "fail"})

    required = [
        "references/audit-rubric.md",
        "references/issue-contract.md",
        "references/portability-security.md",
        "resources/default-policy.json",
        "resources/finding.schema.json",
        "resources/supplemental-findings.template.json",
        "evaluations/EVALUATIONS.md",
        "scripts/repository_hygiene.py",
    ]
    for relative in required:
        if not (root / relative).exists():
            errors.append(f"Required package file missing: {relative}")
    checks.append({"check": "package-layout", "status": "pass" if not any("Required package file" in item for item in errors) else "fail"})

    if zip_path:
        if not zip_path.exists():
            errors.append(f"ZIP does not exist: {zip_path}")
        else:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                expected_prefix = root.name + "/"
                if not names or any(not name.startswith(expected_prefix) for name in names):
                    errors.append(f"ZIP must contain exactly one root folder named {root.name}.")
                if expected_prefix + "SKILL.md" not in names:
                    errors.append("ZIP is missing root-folder/SKILL.md.")
        checks.append({"check": "zip-layout", "status": "pass" if not any("ZIP" in item for item in errors) else "fail"})

    return {
        "status": "valid" if not errors else "invalid",
        "metadata": {"name": name, "name_length": len(name), "description_length": len(description)},
        "skill_word_count": word_count,
        "file_count": sum(1 for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--zip")
    args = parser.parse_args()
    result = validate(Path(args.skill_root).resolve(), Path(args.zip).resolve() if args.zip else None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the official-docs-pack Claude Agent Skill package."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


DEFAULT_OUT_DIR_MARKER = ".claude/docs"


def check(name: str, passed: bool, details: str = "") -> dict:
    return {"name": name, "status": "pass" if passed else "fail", "details": details}


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def main() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else "."
    root = Path(raw).resolve()
    results: list[dict] = []

    skill_md = root / "SKILL.md"
    scripts = root / "scripts"
    resources = root / "resources"
    docpack_ts = scripts / "docpack.ts"
    fetch_ts = scripts / "fetch.ts"
    package_json = scripts / "package.json"

    results.append(check("root-folder-name", root.name == "official-docs-pack", f"root={root.name}"))
    results.append(check("skill-md-exists", skill_md.is_file(), str(skill_md)))

    text = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    argument_hint = frontmatter.get("argument-hint", "")
    allowed_tools = frontmatter.get("allowed-tools", "")

    results.append(check("frontmatter-name", name == "official-docs-pack", f"name={name!r}"))
    results.append(check("name-length", 0 < len(name) <= 64, f"length={len(name)}"))
    results.append(check("frontmatter-description", bool(description), "description present" if description else "missing"))
    results.append(check("description-length", 0 < len(description) <= 1024, f"length={len(description)}"))
    results.append(check("description-third-person", not re.search(r"\b(I|you|your)\b", description, re.I), "no first/second person pronouns"))

    trigger_terms = ["official", "documentation", "docs", "folder", "agent", "scrape"]
    missing_terms = [term for term in trigger_terms if term not in description.lower()]
    results.append(check("description-trigger-terms", not missing_terms, f"missing={missing_terms}"))
    results.append(check("skill-md-line-count", len(text.splitlines()) <= 500, f"lines={len(text.splitlines())}"))
    results.append(check("argument-hint-present", bool(argument_hint), f"argument-hint={argument_hint!r}"))
    results.append(check("allowed-tools-bash", "Bash" in allowed_tools, f"allowed-tools={allowed_tools!r}"))

    # Resource references from SKILL.md must be one-level resource files and must exist.
    local_refs = re.findall(r"\]\((resources/[^)]+)\)|`(resources/[^`]+)`", text)
    refs = [item for pair in local_refs for item in pair if item]
    bad_refs = [ref for ref in refs if len(Path(ref).parts) != 2]
    missing_refs = [ref for ref in refs if not (root / ref).is_file()]
    results.append(check("one-level-resource-references", not bad_refs, f"bad={bad_refs}"))
    results.append(check("resource-references-exist", not missing_refs, f"missing={missing_refs}"))

    expected_resources = ["SOP.md", "source-policy.md", "output-spec.md", "selectors.md", "validation.md"]
    missing_expected = [name for name in expected_resources if not (resources / name).is_file()]
    results.append(check("expected-resources-exist", not missing_expected, f"missing={missing_expected}"))

    nested_resources = [
        str(path.relative_to(root))
        for path in resources.glob("**/*")
        if path.is_file() and len(path.relative_to(resources).parts) > 1
    ] if resources.is_dir() else []
    results.append(check("no-nested-resources", not nested_resources, f"nested={nested_resources}"))

    resource_local_links: list[str] = []
    if resources.is_dir():
        for md in resources.glob("*.md"):
            md_text = md.read_text(encoding="utf-8")
            stripped = re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)
            resource_local_links.extend(re.findall(r"\]\((?!https?://)([^)#]+)", stripped))
    results.append(check("resources-no-local-chain-links", not resource_local_links, f"local_links={resource_local_links}"))

    results.append(check("docpack-ts-exists", docpack_ts.is_file(), str(docpack_ts)))
    results.append(check("fetch-ts-exists", fetch_ts.is_file(), str(fetch_ts)))
    results.append(check("scripts-dir-exists", scripts.is_dir(), str(scripts)))
    results.append(check("validation-wrapper-exists", (scripts / "validate-skill.sh").is_file(), str(scripts / "validate-skill.sh")))

    docpack_text = docpack_ts.read_text(encoding="utf-8") if docpack_ts.is_file() else ""
    results.append(check("docpack-official-gates", all(term in docpack_text for term in ["isAcceptedOfficialDocs", "REJECT_HOSTS", "officialDocsScore", "canCrawlLink"]), "official gating functions present"))
    results.append(check(
        "docpack-folder-output",
        "JSZip" not in docpack_text
        and "index/chunks.jsonl" in docpack_text
        and "AGENT_INDEX.md" in docpack_text
        and "writeDocsFolder" in docpack_text
        and DEFAULT_OUT_DIR_MARKER in docpack_text,
        "folder/index outputs present, no zip dependency",
    ))
    results.append(check("docpack-no-browser-dependency", "puppeteer" not in docpack_text.lower() and "from \"playwright\"" not in docpack_text.lower() and "from 'playwright'" not in docpack_text.lower(), "no browser-rendering dependency"))

    if not package_json.is_file():
        results.append(check("package-json-valid", False, f"not found: {package_json}"))
    else:
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
            deps = package.get("dependencies", {})
            required = {"linkedom", "turndown", "turndown-plugin-gfm"}
            missing_deps = sorted(required - set(deps))
            results.append(check("package-json-valid", True, "valid JSON"))
            results.append(check("dependencies-listed", not missing_deps, f"missing={missing_deps}"))
            results.append(check("package-private", package.get("private") is True, "private=true"))
        except Exception as exc:  # noqa: BLE001
            results.append(check("package-json-valid", False, str(exc)))

    windows_path_pattern = re.compile(r"([A-Za-z]:\\|\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+)")
    has_windows_paths = bool(windows_path_pattern.search(text))
    results.append(check("unix-style-paths", not has_windows_paths, "no Windows-style path patterns" if not has_windows_paths else "Windows-style path found"))

    hardcoded_path_pattern = re.compile(r"~/\.claude/skills/")
    has_hardcoded = bool(hardcoded_path_pattern.search(text))
    results.append(check("no-hardcoded-skill-paths", not has_hardcoded, "uses ${CLAUDE_SKILL_DIR}" if not has_hardcoded else "found ~/.claude/skills/"))

    status = "pass" if all(item["status"] == "pass" for item in results) else "fail"
    print(json.dumps({"status": status, "checks": results}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print(json.dumps({"status": "error", "message": "Usage: validate-skill.py [skill-root]"}, indent=2), file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())

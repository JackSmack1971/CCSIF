#!/usr/bin/env python3
"""Audit a Claude Code skill corpus for measurable authoring-quality gates.

Outputs machine-readable JSON and optional Markdown. Uses only the Python standard
library so it works in locked Claude Code and API-style containers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXCLUDE_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".cache"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RESERVED_NAMES = {"anthropic", "claude"}
GENERIC_WORDS = {"analysis", "analyze", "review", "improve", "helper", "tools", "utils", "documents", "data", "code", "docs"}
DANGEROUS_PATTERNS = [
    ("python-eval", re.compile(r"\beval\s*\(")),
    ("python-exec", re.compile(r"\bexec\s*\(")),
    ("shell-true", re.compile(r"shell\s*=\s*True")),
    ("os-system", re.compile(r"os\.system\s*\(")),
    ("subprocess-shell", re.compile(r"subprocess\.[a-zA-Z_]+\([^\n]*shell\s*=\s*True")),
    ("rm-rf", re.compile(r"rm\s+-rf")),
    ("git-push", re.compile(r"git\s+push")),
    ("curl-pipe-shell", re.compile(r"(?:^|\n)\s*curl\b.*\|\s*(sh|bash)")),
    ("wget-pipe-shell", re.compile(r"(?:^|\n)\s*wget\b.*\|\s*(sh|bash)")),
]

@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class SkillAudit:
    path: str
    root: str
    name: Optional[str]
    score: int
    line_count: int
    approx_tokens: int
    findings: List[Finding]
    metadata: Dict[str, Any]


def run_git(path: Path, args: List[str]) -> Optional[str]:
    try:
        return subprocess.check_output(["git", *args], cwd=str(path), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str, List[Finding]]:
    findings: List[Finding] = []
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text, [Finding("high", "missing-frontmatter", "SKILL.md must start with YAML frontmatter", "SKILL.md", 1, "Add --- name and description frontmatter.")]
    lines = text.splitlines()
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text, [Finding("high", "unterminated-frontmatter", "YAML frontmatter is not terminated", "SKILL.md", 1, "Close the frontmatter with ---.")]
    raw = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])
    data: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for offset, line in enumerate(raw, start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(stripped[2:].strip().strip('"\''))
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            current_key = key
            if value == "":
                data[key] = []
            elif value in {"true", "false"}:
                data[key] = value == "true"
            elif value.startswith("[") and value.endswith("]"):
                data[key] = [v.strip().strip('"\'') for v in value[1:-1].split(",") if v.strip()]
            else:
                data[key] = value.strip('"\'')
        else:
            findings.append(Finding("medium", "frontmatter-parse-warning", f"Unparsed frontmatter line: {stripped[:80]}", "SKILL.md", offset, "Use simple key: value or YAML list syntax."))
    return data, body, findings


def discover_skill_files(project_root: Path, include_user: bool, extra_roots: List[Path]) -> List[Path]:
    roots: List[Path] = []
    roots.extend(extra_roots)
    roots.append(project_root / ".claude" / "skills")
    # Nested project skill roots, bounded by directory exclusions.
    for dirpath, dirnames, _filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        p = Path(dirpath)
        if p.name == "skills" and p.parent.name == ".claude":
            roots.append(p)
    if include_user:
        home = Path.home() / ".claude" / "skills"
        roots.append(home)
    skill_files: List[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            if any(part in EXCLUDE_DIRS for part in skill_md.parts):
                continue
            key = str(skill_md.resolve())
            if key not in seen:
                seen.add(key)
                skill_files.append(skill_md)
    return sorted(skill_files)


def add(finds: List[Finding], severity: str, code: str, path: Path, msg: str, line: Optional[int] = None, suggestion: Optional[str] = None) -> None:
    finds.append(Finding(severity, code, msg, str(path), line, suggestion))


def approx_tokens(text: str) -> int:
    return max(1, int(len(re.findall(r"\S+", text)) * 1.3))


def has_toc(text: str) -> bool:
    head = "\n".join(text.splitlines()[:80]).lower()
    return "table of contents" in head or re.search(r"^##\s+contents", head, re.M) is not None


def line_number_for(text: str, needle: str) -> Optional[int]:
    idx = text.find(needle)
    if idx < 0:
        return None
    return text[:idx].count("\n") + 1


def audit_skill(skill_md: Path, corpus_root: Path) -> SkillAudit:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, body, parse_findings = parse_frontmatter(text)
    findings: List[Finding] = []
    for f in parse_findings:
        f.path = str(skill_md)
        findings.append(f)

    skill_dir = skill_md.parent
    name = fm.get("name") if isinstance(fm.get("name"), str) else None
    desc = fm.get("description") if isinstance(fm.get("description"), str) else None
    line_count = len(text.splitlines())
    token_count = approx_tokens(text)

    if not name:
        add(findings, "high", "missing-name", skill_md, "Frontmatter missing required name", 1, f"Add name: {skill_dir.name}")
    elif not NAME_RE.match(name):
        add(findings, "high", "invalid-name", skill_md, f"Invalid skill name {name!r}; use lowercase kebab-case <=64 chars", 2, "Rename to lowercase alphanumeric and hyphens.")
    elif name in RESERVED_NAMES or any(part in name for part in RESERVED_NAMES):
        add(findings, "high", "reserved-name", skill_md, f"Skill name {name!r} uses a reserved namespace", 2, "Avoid anthropic or claude in the skill name.")
    elif name in GENERIC_WORDS:
        add(findings, "medium", "generic-name", skill_md, f"Skill name {name!r} is too generic", 2, "Use a domain-specific gerund or action noun phrase.")

    if not desc:
        add(findings, "high", "missing-description", skill_md, "Frontmatter missing required description", 3, "Add a high-signal single-line discovery description.")
    else:
        desc_line = line_number_for(text, "description:")
        if len(desc) > 1024:
            add(findings, "high", "description-too-long", skill_md, f"Description is {len(desc)} characters; max target is 1024", desc_line, "Compress and move details to when_to_use or body.")
        if any(ch in desc for ch in [":", "<", ">"]):
            add(findings, "medium", "description-unsafe-yaml-chars", skill_md, "Description contains colon or angle brackets", desc_line, "Use a single-line scalar without colons or angle brackets.")
        if not (desc.startswith("Use when") or desc.startswith("Trigger on queries that")):
            add(findings, "high", "description-activation-prefix", skill_md, "Description should lead with precise activation conditions", desc_line, "Start with Use when or Trigger on queries that.")
        trigger_hits = len(re.findall(r"\b(audit|create|generate|fix|validate|review|update|commit|convert|analyze|summarize|plan|rewrite|optimize|merge|package|deploy|test)\b", desc.lower()))
        quoted_hits = len(re.findall(r"['\"]([^'\"]{3,80})['\"]", desc))
        comma_patterns = 0
        m = re.search(r"Trigger(?:s| on queries that)?(?:\s+on queries that)?\s+(?:say|says|include|contains?)\s+(.+?)(?:\.\s+NOT|\.\s+Not|$)", desc, re.I)
        if m:
            comma_patterns = len([p for p in re.split(r",|;|\bor\b", m.group(1)) if p.strip()])
        patterns = max(quoted_hits, comma_patterns, trigger_hits)
        if patterns < 3:
            add(findings, "medium", "description-trigger-patterns", skill_md, "Description does not expose 3 to 5 clear trigger patterns", desc_line, "List 3 to 5 user-sayable trigger phrases.")
        if not re.search(r"\bNOT for\b|\bNot for\b|\buse .+ instead\b", desc):
            add(findings, "high", "description-missing-negative-space", skill_md, "Description lacks negative-space routing", desc_line, "Name adjacent scenarios that should route elsewhere.")
        unique_terms = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{4,}", desc.lower()) if w not in GENERIC_WORDS]
        if len(set(unique_terms)) < 5:
            add(findings, "medium", "description-low-domain-signal", skill_md, "Description lacks distinctive domain keywords", desc_line, "Add unique artifacts, commands, file types, or constraints.")

    if "when_to_use" not in fm and "when-to-use" not in fm:
        add(findings, "low", "missing-when-to-use", skill_md, "No when_to_use field found", 4, "Add explicit trigger reinforcement when useful.")
    if "argument-hint" not in fm and "arguments" not in fm:
        add(findings, "low", "missing-arguments", skill_md, "No argument hint or argument mapping found", 5, "Add argument-hint for CLI discoverability when applicable.")
    if "allowed-tools" not in fm and "disallowed-tools" not in fm:
        add(findings, "medium", "missing-tool-boundaries", skill_md, "No explicit tool permission boundaries found", 6, "Add least-privilege allowed-tools or disallowed-tools for state-mutating workflows.")

    if line_count > 500:
        add(findings, "high", "skill-too-long", skill_md, f"SKILL.md has {line_count} lines; target <=500", None, "Move detailed material to one-level references.")
    elif line_count > 350:
        add(findings, "medium", "skill-long", skill_md, f"SKILL.md has {line_count} lines; consider compression", None, "Move examples and edge cases to references.")
    if token_count > 5000:
        add(findings, "high", "skill-token-heavy", skill_md, f"Approx loaded tokens {token_count}; target <=5000", None, "Reduce body or move details to references.")
    if line_count > 100 and not has_toc(text):
        add(findings, "low", "missing-toc", skill_md, "SKILL.md exceeds 100 lines without a visible table of contents", None, "Add a compact ToC or compress below 100 lines.")

    if not re.search(r"- \[ \]", body):
        add(findings, "medium", "missing-checklist", skill_md, "No markdown checklist found for task progress", None, "Add artifact-producing checklist steps for complex workflows.")
    if not re.search(r"validate|validation|verify|verification|test", body, re.I):
        add(findings, "high", "missing-validation-loop", skill_md, "No validation or verification loop found", None, "Add validate then fix then repeat instructions.")
    if not re.search(r"completion gate|stop condition|do not .*complete|exit code", body, re.I):
        add(findings, "medium", "missing-stop-conditions", skill_md, "No explicit completion gate or stop condition found", None, "Add completion gate and stop conditions.")

    # References.
    linked_refs = set()
    for link in MD_LINK_RE.findall(body):
        clean = link.split("#", 1)[0]
        if clean.startswith("references/"):
            linked_refs.add(clean)
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for ref in ref_dir.rglob("*.md"):
            rel = ref.relative_to(skill_dir).as_posix()
            rtext = ref.read_text(encoding="utf-8", errors="replace")
            if rel not in linked_refs:
                add(findings, "low", "unlinked-reference", ref, "Reference file is not directly linked from SKILL.md", None, "Link directly from SKILL.md or remove if obsolete.")
            if len(rtext.splitlines()) > 100 and not has_toc(rtext):
                add(findings, "medium", "reference-missing-toc", ref, "Reference over 100 lines lacks table of contents", None, "Add a ToC near the top.")
            for link in MD_LINK_RE.findall(rtext):
                if link.startswith("references/") or link.startswith("../references/"):
                    add(findings, "medium", "deep-reference-chain", ref, "Reference links to another reference creating a deeper chain", None, "Link all required references directly from SKILL.md.")

    # Scripts.
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.rglob("*"):
            if not script.is_file():
                continue
            if "__pycache__" in script.parts or script.suffix == ".pyc":
                continue
            if script.suffix == ".py":
                try:
                    compile(script.read_text(encoding="utf-8", errors="replace"), str(script), "exec")
                except SyntaxError as exc:
                    add(findings, "high", "python-syntax-error", script, f"Python syntax error: {exc.msg}", exc.lineno, "Fix syntax before using the skill.")
            stext = script.read_text(encoding="utf-8", errors="replace") if script.stat().st_size < 2_000_000 else ""
            for code, regex in DANGEROUS_PATTERNS:
                if regex.search(stext):
                    add(findings, "high", f"script-danger-{code}", script, f"Potentially unsafe script pattern {code}", None, "Add guardrails, dry-run, or remove the unsafe pattern.")
            if script.suffix in {".py", ".sh", ".js", ".ts", ".ps1"} and not re.search(r"usage|argparse|exit code|--help|commander|click", stext, re.I):
                add(findings, "medium", "script-missing-cli-contract", script, "Script lacks obvious CLI usage or exit-code contract", None, "Document arguments, output, and exit codes.")

    # Evals and verification.
    if not (skill_dir / "evals" / "evals.json").exists():
        add(findings, "medium", "missing-evals", skill_dir / "evals", "No evals/evals.json found", None, "Add targeted activation and task-quality evals.")
    if not any((skill_dir / name).exists() for name in ["VERIFICATION.md", "verification.md", "TESTING.md"]):
        add(findings, "medium", "missing-verification-log", skill_dir, "No verification log found", None, "Add VERIFICATION.md with tested and untested claims.")

    penalty = sum(20 if f.severity == "high" else 8 if f.severity == "medium" else 3 for f in findings)
    score = max(0, 100 - penalty)
    git_root = run_git(skill_dir, ["rev-parse", "--show-toplevel"])
    metadata = {
        "git_root": git_root,
        "description_length": len(desc or ""),
        "linked_references": sorted(linked_refs),
        "has_scripts": scripts_dir.exists(),
        "has_evals": (skill_dir / "evals" / "evals.json").exists(),
    }
    return SkillAudit(str(skill_md), str(corpus_root), name, score, line_count, token_count, findings, metadata)


def render_markdown(report: Dict[str, Any]) -> str:
    lines = ["# Skill Corpus Audit Report", "", f"Generated by skill-auditor.", ""]
    summary = report["summary"]
    lines.extend([
        "## Summary",
        "",
        f"- Skills audited: {summary['skills_audited']}",
        f"- Corpus score: {summary['corpus_score']}",
        f"- High findings: {summary['findings_by_severity'].get('high', 0)}",
        f"- Medium findings: {summary['findings_by_severity'].get('medium', 0)}",
        f"- Low findings: {summary['findings_by_severity'].get('low', 0)}",
        "",
        "## Skills",
        "",
    ])
    for skill in report["skills"]:
        lines.append(f"### {skill.get('name') or Path(skill['path']).parent.name}")
        lines.append("")
        lines.append(f"- Path: `{skill['path']}`")
        lines.append(f"- Score: {skill['score']}")
        lines.append(f"- Lines: {skill['line_count']}")
        lines.append(f"- Approx tokens: {skill['approx_tokens']}")
        if not skill["findings"]:
            lines.append("- Findings: none")
        else:
            lines.append("- Findings:")
            for f in skill["findings"]:
                loc = f"{f['path']}" + (f":{f['line']}" if f.get("line") else "")
                lines.append(f"  - **{f['severity']}** `{f['code']}` {f['message']} at `{loc}`")
                if f.get("suggestion"):
                    lines.append(f"    - Suggestion: {f['suggestion']}")
        lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit local Claude Code Agent Skills.")
    parser.add_argument("--root", default=".", help="Project root to scan. Defaults to current directory.")
    parser.add_argument("--include-user", action="store_true", help="Also scan ~/.claude/skills.")
    parser.add_argument("--skill-root", action="append", default=[], help="Additional explicit skill root. Can be repeated.")
    parser.add_argument("--output", default="skill-audit-report.json", help="Path to JSON report.")
    parser.add_argument("--markdown", default=None, help="Optional Markdown report path.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    extra = [Path(p).expanduser().resolve() for p in args.skill_root]
    skill_files = discover_skill_files(root, args.include_user, extra)
    audits = [audit_skill(path, root) for path in skill_files]
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for audit in audits:
        for f in audit.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
    corpus_score = round(sum(a.score for a in audits) / len(audits), 2) if audits else 0
    report = {
        "schema_version": "1.0",
        "summary": {
            "root": str(root),
            "include_user": args.include_user,
            "skills_audited": len(audits),
            "corpus_score": corpus_score,
            "findings_by_severity": severity_counts,
        },
        "skills": [
            {
                **asdict(a),
                "findings": [asdict(f) for f in a.findings],
            }
            for a in audits
        ],
    }
    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report) + "\n", encoding="utf-8")
    if severity_counts.get("high", 0) > 0:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

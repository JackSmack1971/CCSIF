#!/usr/bin/env python3
"""Deterministic Claude Code architecture audit.

Scans a repository for Claude Code configuration risks and writes a JSON plus
Markdown report. Uses only Python standard library.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
NEGATIVE_PATTERNS = [
    r"\bdo not\b",
    r"\bdon't\b",
    r"\bnever\b",
    r"\bavoid\b",
    r"\bmust not\b",
    r"\bshould not\b",
    r"\bcannot\b",
    r"\bcan't\b",
]
READ_FIRST_PATTERNS = [r"read first", r"read-first", r"read one nearby", r"before creating.*read"]


@dataclass
class Finding:
    id: str
    severity: str
    axis: str
    title: str
    path: str
    line: Optional[int]
    evidence: str
    recommendation: str
    stop_condition: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def add_finding(findings: List[Finding], severity: str, axis: str, title: str,
                path: str, line: Optional[int], evidence: str,
                recommendation: str, stop_condition: str) -> None:
    finding_id = f"CCA-{len(findings) + 1:03d}"
    findings.append(Finding(finding_id, severity, axis, title, path, line,
                            evidence.strip(), recommendation.strip(), stop_condition.strip()))


def parse_json_file(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(read_text(path))
        if not isinstance(data, dict):
            return None, "top-level JSON is not an object"
        return data, None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"


def extract_frontmatter(text: str) -> Tuple[Optional[str], str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5:]


def frontmatter_has_paths(frontmatter: Optional[str]) -> bool:
    if not frontmatter:
        return False
    return bool(re.search(r"(?m)^paths\s*:", frontmatter))


def frontmatter_has_unquoted_wildcards(frontmatter: Optional[str]) -> bool:
    if not frontmatter:
        return False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if "*" not in stripped:
            continue
        # Accept list item values wrapped in single or double quotes.
        if re.match(r"^-\s*['\"].*\*.*['\"]\s*$", stripped):
            continue
        # Accept inline arrays where every wildcard-containing item appears quoted.
        if "[" in stripped and "]" in stripped:
            wildcard_items = [item.strip() for item in stripped[stripped.find("[")+1:stripped.rfind("]")].split(",") if "*" in item]
            if wildcard_items and all((item.startswith("'") and item.endswith("'")) or (item.startswith('"') and item.endswith('"')) for item in wildcard_items):
                continue
        return True
    return False


def find_negative_phrasing(root: Path, findings: List[Finding], files: Iterable[Path]) -> None:
    combined = re.compile("|".join(NEGATIVE_PATTERNS), re.IGNORECASE)
    for path in files:
        if not path.exists() or not path.is_file():
            continue
        text = read_text(path)
        for idx, line in enumerate(text.splitlines(), start=1):
            if combined.search(line):
                add_finding(
                    findings, "medium", "linguistic architecture",
                    "Negative phrasing found in operational instructions",
                    rel(path, root), idx, line[:240],
                    "Rewrite as an affirmative imperative with a measurable target behavior.",
                    "The replacement line states the desired action and includes a verification condition where applicable.",
                )
                break


def discover_claude_files(root: Path) -> Dict[str, List[Path]]:
    all_md = [p for p in root.rglob("*.md") if ".git" not in p.parts]
    claude_roots = []
    for candidate in [root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"]:
        if candidate.exists():
            claude_roots.append(candidate)
    nested_claude = [p for p in all_md if p.name == "CLAUDE.md" and p not in claude_roots]
    rules = sorted((root / ".claude" / "rules").glob("*.md")) if (root / ".claude" / "rules").exists() else []
    return {"all_md": all_md, "root_manifests": claude_roots, "nested_claude": nested_claude, "rules": rules}


def scan_manifests(root: Path, findings: List[Finding], files: Dict[str, List[Path]]) -> None:
    root_manifests = files["root_manifests"]
    if not root_manifests:
        add_finding(
            findings, "high", "discovery and routing", "No root Claude Code manifest found",
            ".", None, "Neither CLAUDE.md nor .claude/CLAUDE.md exists.",
            "Create a concise root manifest that routes to path-scoped rules and names verification commands.",
            "A root manifest exists and is under 120 lines.",
        )
        return

    for manifest in root_manifests:
        text = read_text(manifest)
        count = line_count(text)
        if count > 120:
            add_finding(
                findings, "high", "context budget", "Root manifest exceeds 120-line hard budget",
                rel(manifest, root), None, f"{count} lines",
                "Extract domain-specific sections into .claude/rules/*.md and keep the root as a router.",
                "Root manifest is at or below 120 lines.",
            )
        elif count > 80:
            add_finding(
                findings, "medium", "context budget", "Root manifest exceeds 80-line warning budget",
                rel(manifest, root), None, f"{count} lines",
                "Review for extraction candidates before the file reaches the hard budget.",
                "Root manifest is at or below 80 lines or documented as intentionally dense.",
            )

        imports = re.findall(r"(?m)^\s*@import\s+(.+)$", text)
        if len(imports) > 5:
            add_finding(
                findings, "medium", "progressive disclosure", "Root manifest has many unconditional imports",
                rel(manifest, root), None, f"{len(imports)} @import directives",
                "Keep imports for globally applicable standards and move conditional detail into path-scoped rules.",
                "Import list contains only globally relevant references.",
            )
        if not any(re.search(pat, text, re.IGNORECASE | re.DOTALL) for pat in READ_FIRST_PATTERNS):
            add_finding(
                findings, "high", "path-scoped rules", "Read First protocol missing from root manifest",
                rel(manifest, root), None, "No Read First guidance detected.",
                "Add guidance to read one matching existing file before creating files in path-scoped areas.",
                "Root manifest contains explicit Read First guidance.",
            )

    if files["nested_claude"]:
        add_finding(
            findings, "medium", "context budget", "Nested CLAUDE.md files may add inherited context",
            ".", None, ", ".join(rel(p, root) for p in files["nested_claude"][:10]),
            "Use claudeMdExcludes or consolidate nested manifests where inheritance creates bloat or conflict.",
            "Nested manifests are intentionally included or excluded by settings.",
        )


def scan_rules(root: Path, findings: List[Finding], files: Dict[str, List[Path]]) -> None:
    rules_dir = root / ".claude" / "rules"
    root_lines = 0
    for manifest in files["root_manifests"]:
        root_lines += line_count(read_text(manifest))
    if not rules_dir.exists():
        if root_lines > 80 or files["root_manifests"]:
            add_finding(
                findings, "high", "progressive disclosure", ".claude/rules directory missing",
                rel(rules_dir, root), None, "No path-scoped rule directory found.",
                "Create .claude/rules and extract domain-specific instructions into scoped files.",
                "Rules directory exists with scoped files for each major domain.",
            )
        return

    rules = files["rules"]
    if not rules:
        add_finding(
            findings, "medium", "progressive disclosure", ".claude/rules directory is empty",
            rel(rules_dir, root), None, "Directory exists but contains no Markdown rules.",
            "Add path-scoped rules or remove the empty directory.",
            "Rules directory contains scoped rules or is intentionally absent.",
        )
        return

    for rule in rules:
        text = read_text(rule)
        count = line_count(text)
        fm, _body = extract_frontmatter(text)
        if count > 100:
            add_finding(findings, "high", "context budget", "Rule file exceeds 100 lines",
                        rel(rule, root), None, f"{count} lines",
                        "Split into one-domain rule files or move detailed reference material outside active rules.",
                        "Rule file is below 50 lines or the extra detail is moved to on-demand docs.")
        elif count > 50:
            add_finding(findings, "medium", "context budget", "Rule file exceeds 50-line target",
                        rel(rule, root), None, f"{count} lines",
                        "Trim or split this rule file to keep path-injected context lean.",
                        "Rule file is at or below 50 lines or documented as intentionally global.")
        if not frontmatter_has_paths(fm):
            add_finding(findings, "medium", "path-scoped rules", "Rule file lacks paths frontmatter",
                        rel(rule, root), 1, "No paths key detected in YAML frontmatter.",
                        "Add precise paths frontmatter unless this is an intentionally global habit file.",
                        "Rule file has paths frontmatter or a clear global label.")
        if frontmatter_has_unquoted_wildcards(fm):
            add_finding(findings, "medium", "path-scoped rules", "Wildcard path glob may be unquoted",
                        rel(rule, root), 1, "Wildcard detected in frontmatter without clear quotes.",
                        "Quote wildcard globs in YAML frontmatter.",
                        "All wildcard globs are wrapped in single or double quotes.")


def scan_settings(root: Path, findings: List[Finding], files: Dict[str, List[Path]]) -> None:
    settings_path = root / ".claude" / "settings.json"
    settings, error = parse_json_file(settings_path)
    if error == "missing":
        add_finding(findings, "medium", "settings hierarchy", "Project settings file missing",
                    rel(settings_path, root), None, "No .claude/settings.json found.",
                    "Create project settings for shared hooks, permissions, and MCP governance where relevant.",
                    "Project settings exist or the project documents why defaults are sufficient.")
        settings = None
    elif error:
        add_finding(findings, "critical", "settings hierarchy", "Project settings JSON is invalid",
                    rel(settings_path, root), None, error,
                    "Fix JSON syntax before relying on Claude Code settings.",
                    "settings.json parses as a JSON object.")
        settings = None

    if settings:
        hooks = settings.get("hooks")
        hooks_text = json.dumps(hooks or {}, sort_keys=True)
        if "PreToolUse" not in hooks_text:
            add_finding(findings, "high", "security boundaries", "PreToolUse hook not detected",
                        rel(settings_path, root), None, "No PreToolUse hook key found.",
                        "Add a PreToolUse hook for destructive command and sensitive file gates where repository risk warrants it.",
                        "Settings include a tested PreToolUse hook or document an equivalent external control.")
        if "Stop" not in hooks_text:
            add_finding(findings, "high", "verification boundaries", "Stop verification hook not detected",
                        rel(settings_path, root), None, "No Stop hook key found.",
                        "Add a Stop hook or equivalent verification gate for build, tests, typecheck, or lint.",
                        "Settings include a tested Stop hook or document why project-native verification is manual.")
        if settings.get("fileCheckpointingEnabled") is False:
            add_finding(findings, "medium", "settings hierarchy", "File checkpointing disabled",
                        rel(settings_path, root), None, "fileCheckpointingEnabled is false.",
                        "Enable checkpointing unless the repository has an explicit alternative rollback policy.",
                        "Checkpointing is enabled or a rollback alternative is documented.")
        if "skillListingBudgetFraction" in settings:
            try:
                frac = float(settings["skillListingBudgetFraction"])
                if frac > 0.01:
                    add_finding(findings, "low", "context budget", "Skill listing budget exceeds default fraction",
                                rel(settings_path, root), None, f"skillListingBudgetFraction={frac}",
                                "Keep skill listing budget near the default unless many skills require routing visibility.",
                                "Budget is justified or returned near 0.01.")
            except (TypeError, ValueError):
                add_finding(findings, "medium", "settings hierarchy", "skillListingBudgetFraction is not numeric",
                            rel(settings_path, root), None, repr(settings.get("skillListingBudgetFraction")),
                            "Use a numeric fraction such as 0.01.",
                            "Setting parses as a number.")
        mcp_keys = {"allowedMcpServers", "deniedMcpServers", "allowManagedMcpServersOnly"}
        if not any(key in settings for key in mcp_keys):
            add_finding(findings, "medium", "MCP governance", "MCP governance settings not detected",
                        rel(settings_path, root), None, "No allowedMcpServers, deniedMcpServers, or allowManagedMcpServersOnly key found.",
                        "Add explicit MCP server governance when external tools are used.",
                        "Settings define MCP access policy or document that the project uses no MCP servers.")
        if settings.get("disableSkillShellExecution") is not True:
            add_finding(findings, "low", "security boundaries", "Skill shell execution is not explicitly disabled",
                        rel(settings_path, root), None, "disableSkillShellExecution is not true.",
                        "Set disableSkillShellExecution true in managed or project settings when inline shell in skills is outside policy.",
                        "Policy is explicit in settings or documented as intentionally permissive.")
        if files["nested_claude"] and "claudeMdExcludes" not in settings:
            add_finding(findings, "medium", "context budget", "claudeMdExcludes missing with nested CLAUDE.md files",
                        rel(settings_path, root), None, "Nested CLAUDE.md files exist and settings lack claudeMdExcludes.",
                        "Add claudeMdExcludes for irrelevant inherited manifests in complex repositories.",
                        "Exclusion policy exists or nested manifests are confirmed relevant.")

    local_settings = root / ".claude" / "settings.local.json"
    if local_settings.exists():
        _local, local_error = parse_json_file(local_settings)
        if local_error:
            add_finding(findings, "medium", "settings hierarchy", "Local settings JSON is invalid",
                        rel(local_settings, root), None, local_error,
                        "Fix local JSON syntax or remove the invalid file.",
                        "settings.local.json parses as a JSON object.")
        gitignore = root / ".gitignore"
        ignored = False
        if gitignore.exists():
            ignore_text = read_text(gitignore)
            ignored = any(pattern in ignore_text for pattern in [".claude/settings.local.json", "settings.local.json"])
        if not ignored:
            add_finding(findings, "high", "settings hierarchy", "Local Claude settings may be committed",
                        rel(local_settings, root), None, ".gitignore does not mention .claude/settings.local.json.",
                        "Add .claude/settings.local.json to .gitignore.",
                        ".gitignore excludes .claude/settings.local.json.")


def scan_memory_and_decisions(root: Path, findings: List[Finding]) -> None:
    decision_log = root / ".claude" / "docs" / "decision-log.md"
    if not decision_log.exists():
        add_finding(findings, "medium", "metacognitive improvement", "Decision log missing",
                    rel(decision_log, root), None, "No .claude/docs/decision-log.md found.",
                    "Create a decision log for Claude Code architecture changes and promotion of stable memory findings.",
                    "Decision log exists and records architecture decisions with dates and evidence.")

    gitignore = root / ".gitignore"
    if gitignore.exists():
        ignore_text = read_text(gitignore)
        if ".claude/projects" not in ignore_text and ".claude/memory" not in ignore_text:
            add_finding(findings, "low", "memory hygiene", "No local Claude memory ignore pattern detected",
                        rel(gitignore, root), None, "No .claude/projects or .claude/memory ignore pattern found.",
                        "Exclude accidental local Claude memory paths if this repository stores any local memory artifacts.",
                        "Gitignore covers local memory artifacts or repository confirms none are created inside project root.")


def summarize(findings: List[Finding]) -> Dict[str, Any]:
    counts: Dict[str, int] = {k: 0 for k in SEVERITY_ORDER}
    axes: Dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
        axes[finding.axis] = axes.get(finding.axis, 0) + 1
    status = "pass"
    if counts.get("critical") or counts.get("high"):
        status = "fail"
    elif counts.get("medium"):
        status = "partial"
    return {"status": status, "counts": counts, "axes": axes, "total": len(findings)}


def render_markdown(root: Path, findings: List[Finding], summary: Dict[str, Any]) -> str:
    now = _dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Claude Code Architecture Audit Report",
        "",
        f"Repository: `{root}`",
        f"Generated: `{now}`",
        f"Status: **{summary['status'].upper()}**",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "| --- | ---: |",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        lines.append(f"| {sev} | {summary['counts'].get(sev, 0)} |")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings detected by deterministic audit.")
    else:
        lines.extend(["| ID | Severity | Axis | File | Evidence | Recommendation | Stop condition |", "| --- | --- | --- | --- | --- | --- | --- |"])
        for finding in sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.id)):
            loc = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
            evidence = finding.evidence.replace("|", "\\|").replace("\n", " ")[:300]
            recommendation = finding.recommendation.replace("|", "\\|").replace("\n", " ")[:300]
            stop = finding.stop_condition.replace("|", "\\|").replace("\n", " ")[:300]
            lines.append(f"| {finding.id} | {finding.severity} | {finding.axis} | `{loc}` | {evidence} | {recommendation} | {stop} |")
    lines.extend([
        "",
        "## Suggested Validation Loop",
        "",
        "```bash",
        "python scripts/audit_claude_code_architecture.py --repo . --write --fail-on-high",
        "# then run repository-native build, test, typecheck, and lint commands",
        "```",
        "",
    ])
    return "\n".join(lines)


def run_audit(root: Path) -> Tuple[List[Finding], Dict[str, Any]]:
    findings: List[Finding] = []
    files = discover_claude_files(root)
    scan_manifests(root, findings, files)
    scan_rules(root, findings, files)
    scan_settings(root, findings, files)
    md_targets = files["root_manifests"] + files["rules"]
    find_negative_phrasing(root, findings, md_targets)
    scan_memory_and_decisions(root, findings)
    summary = summarize(findings)
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.id)), summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Claude Code repository architecture.")
    parser.add_argument("--repo", default=".", help="Repository root to scan. Defaults to current directory.")
    parser.add_argument("--json-out", default=None, help="JSON output path. Defaults to .claude/audits/claude-code-architecture-audit.json")
    parser.add_argument("--md-out", default=None, help="Markdown output path. Defaults to .claude/audits/claude-code-architecture-audit.md")
    parser.add_argument("--write", action="store_true", help="Write report files. Without this flag, JSON is printed to stdout.")
    parser.add_argument("--fail-on-high", action="store_true", help="Exit 2 when high or critical findings exist.")
    args = parser.parse_args(argv)

    root = Path(args.repo).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(json.dumps({"status": "error", "error": f"Repository path does not exist or is not a directory: {root}"}), file=sys.stderr)
        return 1

    findings, summary = run_audit(root)
    payload = {
        "schema": "claude-code-architecture-audit-v1",
        "repo": str(root),
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "findings": [asdict(f) for f in findings],
    }

    if args.write:
        default_dir = root / ".claude" / "audits"
        json_out = Path(args.json_out).expanduser() if args.json_out else default_dir / "claude-code-architecture-audit.json"
        md_out = Path(args.md_out).expanduser() if args.md_out else default_dir / "claude-code-architecture-audit.md"
        json_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_out.write_text(render_markdown(root, findings, summary), encoding="utf-8")
        print(json.dumps({"status": summary["status"], "json_out": str(json_out), "md_out": str(md_out), "findings": summary["total"]}, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))

    if args.fail_on_high and (summary["counts"].get("critical", 0) or summary["counts"].get("high", 0)):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

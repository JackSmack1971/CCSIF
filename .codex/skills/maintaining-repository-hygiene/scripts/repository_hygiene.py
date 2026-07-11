#!/usr/bin/env python3
"""Repository Hygiene CLI: audit -> plan -> validate -> publish/apply."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_repository import report_markdown, run_audit  # noqa: E402
from github_operations import (  # noqa: E402
    apply_label_prune_plan,
    apply_worktree_prune_plan,
    create_issue_plan,
    create_label_prune_plan,
    create_worktree_prune_plan,
    publish_issue_plan,
    validate_issue_plan,
)
from hygiene_core import (  # noqa: E402
    HygieneError,
    SEVERITY_ORDER,
    fail_cli,
    fingerprint,
    git_root,
    json_status,
    make_finding,
    load_json,
    verify_digest,
    write_json,
    write_text,
)

DEFAULT_POLICY = SKILL_ROOT / "resources" / "default-policy.json"


def load_policy(path: Path | None) -> dict[str, Any]:
    base = load_json(DEFAULT_POLICY)
    if path is None:
        return base
    override = load_json(path)
    return deep_merge(base, override)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_repo(value: str) -> Path:
    return git_root(Path(value).expanduser().resolve())


def audit_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    policy = load_policy(Path(args.policy).resolve() if args.policy else None)
    out_dir = (repo / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir).resolve()
    report = run_audit(repo, policy, args.remote)
    label_plan_path = None
    if policy.get("label_pruning", {}).get("enabled", True) and report.get("remote"):
        try:
            label_plan = create_label_prune_plan(repo, policy)
            label_plan_path = out_dir / "label-prune-plan.json"
            write_json(label_plan_path, label_plan)
            report["coverage"].append({
                "check": "github-label-history",
                "status": "complete" if label_plan["scan"]["history_complete"] else "degraded",
                "detail": f"Scanned {label_plan['scan']['issues_and_pull_requests_scanned']} issues/pull requests; deletion candidates are suppressed when incomplete."
            })
            if label_plan["operations"]:
                finding = make_finding(
                    rule_id="LABELS-UNUSED-CANDIDATES",
                    category="github-labels",
                    severity="low",
                    confidence="high",
                    title="Prune confirmed unused GitHub labels",
                    summary="A complete history scan found labels with zero issue or pull-request use, no repository references, and no policy protection.",
                    evidence_items=[{"source": "GitHub labels", "observation": f"Unused candidate: {item['name']}"} for item in label_plan["operations"]],
                    remediation_key="github-labels/prune-unused",
                    actions=["Review the digest-bound label deletion plan.", "Retain any label with an undocumented external automation dependency and add that dependency to policy.", "Apply the plan only after the fresh zero-use and reference recheck succeeds."],
                    acceptance=["Every deletion-plan label is either deleted or retained with an explicit policy reason.", "No label used by an issue, pull request, issue form, workflow, automation, or documented process is deleted."],
                    verification=["Re-run labels-plan and confirm there are no unintended zero-use candidates.", "Inspect issue forms, workflows, and label taxonomy after deletion."],
                    destructive=True,
                    references=["https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels"],
                )
                report["findings"].append(finding.to_dict())
            duplicate_groups = label_plan.get("normalized_duplicates", [])
            missing_descriptions = [item["name"] for item in label_plan.get("inventory", []) if not (item.get("description") or "").strip()]
            if duplicate_groups or missing_descriptions:
                evidence_items = []
                evidence_items.extend({"source": "GitHub labels", "observation": "Normalized duplicate group: " + ", ".join(group)} for group in duplicate_groups)
                evidence_items.extend({"source": "GitHub labels", "observation": f"Missing description: {name}"} for name in missing_descriptions[:100])
                finding = make_finding(
                    rule_id="LABELS-TAXONOMY-QUALITY",
                    category="github-labels",
                    severity="low",
                    confidence="high",
                    title="Normalize and document the GitHub label taxonomy",
                    summary="The label inventory contains normalized duplicates or labels without descriptions.",
                    evidence_items=evidence_items,
                    remediation_key="github-labels/taxonomy",
                    actions=["Choose canonical names for normalized duplicate groups and migrate issue/PR associations before deleting aliases.", "Add concise descriptions that define intended use and boundaries.", "Align issue forms and automation with the canonical taxonomy."],
                    acceptance=["No case/punctuation-normalized duplicate labels remain without an explicit compatibility reason.", "Every operational label has a useful description and consistent naming convention."],
                    verification=["gh label list --limit 1000", "Search .github and documentation for retired label names."],
                    destructive=True,
                )
                report["findings"].append(finding.to_dict())
        except HygieneError as exc:
            report["coverage"].append({"check": "github-label-history", "status": "degraded", "detail": f"Label audit unavailable: {exc}"})

    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    deduped = {item["id"]: item for item in report["findings"]}
    report["findings"] = sorted(deduped.values(), key=lambda item: (-severity_rank[item["severity"]], item["category"], item["title"], item["id"]))
    report["summary"]["findings"] = len(report["findings"])
    report["summary"]["actionable"] = sum(1 for item in report["findings"] if item.get("actionable", True))
    report["summary"]["by_severity"] = {name: sum(1 for item in report["findings"] if item["severity"] == name) for name in severity_rank}

    write_json(out_dir / "report.json", report)
    write_text(out_dir / "report.md", report_markdown(report))
    write_json(out_dir / "stack-profile.json", report["stack_profile"])

    issue_plan_path = None
    issue_plan_error = None
    if not args.no_issue_plan:
        try:
            issue_plan = create_issue_plan(report, policy)
            issue_errors = validate_issue_plan(issue_plan)
            if issue_errors:
                raise HygieneError("Generated issue plan failed validation.", code="GENERATED_ISSUE_PLAN_INVALID", details=issue_errors)
            issue_plan_path = out_dir / "issue-plan.json"
            write_json(issue_plan_path, issue_plan)
            write_text(out_dir / "issue-plan.md", issue_plan_markdown(issue_plan))
        except HygieneError as exc:
            issue_plan_error = {"code": exc.code, "message": str(exc)}

    json_status(
        "ok",
        command="audit",
        repository=str(repo),
        report=str(out_dir / "report.json"),
        markdown_report=str(out_dir / "report.md"),
        stack_profile=str(out_dir / "stack-profile.json"),
        issue_plan=str(issue_plan_path) if issue_plan_path else None,
        issue_plan_error=issue_plan_error,
        label_prune_plan=str(label_plan_path) if label_plan_path else None,
        summary=report["summary"],
    )
    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[item["severity"]] >= threshold for item in report["findings"]):
            return 1
    return 0


def issue_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Repository Hygiene Issue Plan",
        "",
        f"Repository: `{plan['repository']}`  ",
        f"Source HEAD: `{plan.get('source_head') or 'unknown'}`  ",
        f"Digest: `{plan['digest']}`",
        "",
        f"Atomic implementation issues: **{len(plan['steps'])}**",
        "",
    ]
    for index, step in enumerate(plan["steps"], start=1):
        lines.extend([
            f"## {index}. {step['title']}",
            "",
            f"- Fingerprint: `{step['fingerprint']}`",
            f"- Severity: `{step['severity']}`",
            f"- Confidence: `{step['confidence']}`",
            f"- Remediation key: `{step['remediation_key']}`",
            f"- Destructive: `{str(step['destructive']).lower()}`",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"



def _validate_supplemental_finding(item: dict[str, Any], index: int) -> dict[str, Any]:
    required = [
        "rule_id", "category", "severity", "confidence", "title", "summary", "evidence",
        "remediation_key", "recommended_actions", "acceptance_criteria", "verification"
    ]
    missing = [key for key in required if not item.get(key)]
    if missing:
        raise HygieneError(f"Supplemental finding {index} is missing required fields.", code="SUPPLEMENTAL_FINDING_INVALID", details=missing)
    if item["severity"] not in SEVERITY_ORDER:
        raise HygieneError(f"Supplemental finding {index} has invalid severity.", code="SUPPLEMENTAL_FINDING_INVALID")
    if item["confidence"] not in {"high", "medium", "low"}:
        raise HygieneError(f"Supplemental finding {index} has invalid confidence.", code="SUPPLEMENTAL_FINDING_INVALID")
    if not isinstance(item["evidence"], list) or not all(isinstance(value, dict) and value.get("source") and value.get("observation") for value in item["evidence"]):
        raise HygieneError(f"Supplemental finding {index} requires source/observation evidence objects.", code="SUPPLEMENTAL_FINDING_INVALID")
    normalized = dict(item)
    normalized.setdefault("id", "RH-SUP-" + fingerprint(item["rule_id"], item["remediation_key"], item["evidence"]).upper())
    normalized.setdefault("destructive", False)
    normalized.setdefault("actionable", True)
    normalized.setdefault("dependencies", [])
    normalized.setdefault("non_goals", [])
    normalized.setdefault("references", [])
    return normalized


def findings_merge_command(args: argparse.Namespace) -> int:
    report_path = Path(args.report).resolve()
    report = load_json(report_path)
    supplement_payload = load_json(Path(args.supplement).resolve())
    raw_findings = supplement_payload.get("findings", []) if isinstance(supplement_payload, dict) else supplement_payload
    if not isinstance(raw_findings, list):
        raise HygieneError("Supplement must be a JSON array or an object with a findings array.", code="SUPPLEMENTAL_FINDINGS_INVALID")
    supplements = [_validate_supplemental_finding(item, index) for index, item in enumerate(raw_findings, start=1) if isinstance(item, dict)]
    if len(supplements) != len(raw_findings):
        raise HygieneError("Every supplemental finding must be a JSON object.", code="SUPPLEMENTAL_FINDINGS_INVALID")
    merged = {item["id"]: item for item in report.get("findings", [])}
    for item in supplements:
        if item["id"] in merged and merged[item["id"]] != item:
            raise HygieneError(f"Supplemental finding ID collides with a different finding: {item['id']}", code="SUPPLEMENTAL_FINDING_ID_COLLISION")
        merged[item["id"]] = item
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    report["findings"] = sorted(merged.values(), key=lambda item: (-severity_rank[item["severity"]], item["category"], item["title"], item["id"]))
    report.setdefault("supplemental_sources", []).append(str(Path(args.supplement).resolve()))
    report["summary"]["findings"] = len(report["findings"])
    report["summary"]["actionable"] = sum(1 for item in report["findings"] if item.get("actionable", True))
    report["summary"]["by_severity"] = {name: sum(1 for item in report["findings"] if item["severity"] == name) for name in severity_rank}
    out = Path(args.out).resolve()
    write_json(out, report)
    markdown = Path(args.markdown).resolve() if args.markdown else out.with_suffix(".md")
    write_text(markdown, report_markdown(report))
    json_status("ok", command="findings-merge", output=str(out), markdown=str(markdown), supplemental=len(supplements), findings=len(report["findings"]))
    return 0

def issues_plan_command(args: argparse.Namespace) -> int:
    report_path = Path(args.report).resolve()
    report = load_json(report_path)
    policy = load_policy(Path(args.policy).resolve() if args.policy else None)
    plan = create_issue_plan(report, policy)
    errors = validate_issue_plan(plan)
    if errors:
        raise HygieneError("Issue plan validation failed.", code="ISSUE_PLAN_INVALID", details=errors)
    out = Path(args.out).resolve()
    write_json(out, plan)
    if args.markdown:
        write_text(Path(args.markdown).resolve(), issue_plan_markdown(plan))
    json_status("ok", command="issues-plan", output=str(out), digest=plan["digest"], steps=len(plan["steps"]))
    return 0


def issues_validate_command(args: argparse.Namespace) -> int:
    plan = load_json(Path(args.plan).resolve())
    errors = validate_issue_plan(plan)
    if errors:
        json_status("invalid", command="issues-validate", errors=errors)
        return 1
    json_status("ok", command="issues-validate", digest=verify_digest(plan), steps=len(plan.get("steps", [])))
    return 0


def issues_publish_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    plan = load_json(Path(args.plan).resolve())
    journal = Path(args.journal).resolve()
    result = publish_issue_plan(
        repo,
        plan,
        args.confirm_digest,
        journal_path=journal,
        ensure_labels=args.ensure_labels,
        allow_head_change=args.allow_head_change,
        max_issues=args.max_issues,
    )
    created = sum(1 for item in result["results"] if item["status"] == "created")
    skipped = sum(1 for item in result["results"] if item["status"] == "skipped-existing")
    json_status("ok", command="issues-publish", journal=str(journal), created=created, skipped_existing=skipped)
    return 0


def labels_plan_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    policy = load_policy(Path(args.policy).resolve() if args.policy else None)
    plan = create_label_prune_plan(repo, policy)
    out = Path(args.out).resolve()
    write_json(out, plan)
    json_status(
        "ok",
        command="labels-plan",
        output=str(out),
        digest=plan["digest"],
        delete_candidates=len(plan["operations"]),
        history_complete=plan["scan"]["history_complete"],
        normalized_duplicate_groups=len(plan["normalized_duplicates"]),
    )
    return 0


def labels_apply_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    plan = load_json(Path(args.plan).resolve())
    result = apply_label_prune_plan(repo, plan, args.confirm_digest)
    if args.journal:
        write_json(Path(args.journal).resolve(), result)
    json_status("ok", command="labels-apply", deleted=len(result["results"]), journal=args.journal)
    return 0


def worktrees_plan_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    plan = create_worktree_prune_plan(repo)
    out = Path(args.out).resolve()
    write_json(out, plan)
    json_status("ok", command="worktrees-plan", output=str(out), digest=plan["digest"], operations=len(plan["operations"]))
    return 0


def worktrees_apply_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    plan = load_json(Path(args.plan).resolve())
    result = apply_worktree_prune_plan(repo, plan, args.confirm_digest)
    if args.journal:
        write_json(Path(args.journal).resolve(), result)
    json_status("ok", command="worktrees-apply", pruned=len(result["output"]), remaining=len(result["remaining_operations"]), journal=args.journal)
    return 0


def verify_command(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    baseline = load_json(Path(args.baseline).resolve())
    policy = load_policy(Path(args.policy).resolve() if args.policy else None)
    current = run_audit(repo, policy, args.remote)
    baseline_ids = {item["id"] for item in baseline.get("findings", [])}
    current_ids = {item["id"] for item in current.get("findings", [])}
    result = {
        "schema_version": 1,
        "kind": "repository-hygiene-verification",
        "baseline": str(Path(args.baseline).resolve()),
        "resolved": sorted(baseline_ids - current_ids),
        "remaining": sorted(baseline_ids & current_ids),
        "new": sorted(current_ids - baseline_ids),
        "current_report": current,
    }
    out = Path(args.out).resolve()
    write_json(out, result)
    json_status("ok", command="verify", output=str(out), resolved=len(result["resolved"]), remaining=len(result["remaining"]), new=len(result["new"]))
    return 1 if args.fail_if_remaining and result["remaining"] else 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="repository_hygiene.py",
        description="Code-agnostic repository hygiene audit, planning, and guarded maintenance.",
    )
    sub = root.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="Run the read-only local and optional GitHub audit.")
    audit.add_argument("--repo", default=".")
    audit.add_argument("--out-dir", default=".repository-hygiene")
    audit.add_argument("--policy")
    audit.add_argument("--remote", choices=("auto", "on", "off"), default="auto")
    audit.add_argument("--no-issue-plan", action="store_true")
    audit.add_argument("--fail-on", choices=("critical", "high", "medium", "low"))
    audit.set_defaults(func=audit_command)

    findings_merge = sub.add_parser("findings-merge", help="Validate and merge evidence-backed supplemental findings into an audit report.")
    findings_merge.add_argument("--report", required=True)
    findings_merge.add_argument("--supplement", required=True)
    findings_merge.add_argument("--out", required=True)
    findings_merge.add_argument("--markdown")
    findings_merge.set_defaults(func=findings_merge_command)

    issue_plan = sub.add_parser("issues-plan", help="Generate one issue draft per atomic implementation step.")
    issue_plan.add_argument("--report", required=True)
    issue_plan.add_argument("--out", default="issue-plan.json")
    issue_plan.add_argument("--markdown")
    issue_plan.add_argument("--policy")
    issue_plan.set_defaults(func=issues_plan_command)

    issue_validate = sub.add_parser("issues-validate", help="Validate issue-plan structure and digest.")
    issue_validate.add_argument("--plan", required=True)
    issue_validate.set_defaults(func=issues_validate_command)

    issue_publish = sub.add_parser("issues-publish", help="Idempotently publish all issue-plan steps.")
    issue_publish.add_argument("--repo", default=".")
    issue_publish.add_argument("--plan", required=True)
    issue_publish.add_argument("--confirm-digest", required=True)
    issue_publish.add_argument("--journal", default=".repository-hygiene/issue-publication-journal.json")
    issue_publish.add_argument("--ensure-labels", action="store_true")
    issue_publish.add_argument("--allow-head-change", action="store_true")
    issue_publish.add_argument("--max-issues", type=int, default=100)
    issue_publish.set_defaults(func=issues_publish_command)

    label_plan = sub.add_parser("labels-plan", help="Create a fail-closed unused-label deletion plan.")
    label_plan.add_argument("--repo", default=".")
    label_plan.add_argument("--out", default=".repository-hygiene/label-prune-plan.json")
    label_plan.add_argument("--policy")
    label_plan.set_defaults(func=labels_plan_command)

    label_apply = sub.add_parser("labels-apply", help="Recheck and apply a digest-confirmed label deletion plan.")
    label_apply.add_argument("--repo", default=".")
    label_apply.add_argument("--plan", required=True)
    label_apply.add_argument("--confirm-digest", required=True)
    label_apply.add_argument("--journal", default=".repository-hygiene/label-prune-journal.json")
    label_apply.set_defaults(func=labels_apply_command)

    worktree_plan = sub.add_parser("worktrees-plan", help="Create a dry-run stale worktree metadata plan.")
    worktree_plan.add_argument("--repo", default=".")
    worktree_plan.add_argument("--out", default=".repository-hygiene/worktree-prune-plan.json")
    worktree_plan.set_defaults(func=worktrees_plan_command)

    worktree_apply = sub.add_parser("worktrees-apply", help="Recheck and apply a digest-confirmed worktree metadata prune.")
    worktree_apply.add_argument("--repo", default=".")
    worktree_apply.add_argument("--plan", required=True)
    worktree_apply.add_argument("--confirm-digest", required=True)
    worktree_apply.add_argument("--journal", default=".repository-hygiene/worktree-prune-journal.json")
    worktree_apply.set_defaults(func=worktrees_apply_command)

    verify = sub.add_parser("verify", help="Re-audit and compare finding IDs with a baseline report.")
    verify.add_argument("--repo", default=".")
    verify.add_argument("--baseline", required=True)
    verify.add_argument("--out", default=".repository-hygiene/verification.json")
    verify.add_argument("--policy")
    verify.add_argument("--remote", choices=("auto", "on", "off"), default="auto")
    verify.add_argument("--fail-if-remaining", action="store_true")
    verify.set_defaults(func=verify_command)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:
        return fail_cli(exc)


if __name__ == "__main__":
    raise SystemExit(main())

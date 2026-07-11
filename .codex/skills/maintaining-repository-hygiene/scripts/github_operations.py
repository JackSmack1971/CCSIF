#!/usr/bin/env python3
"""Deterministic planning and guarded GitHub/Git maintenance operations."""
from __future__ import annotations

import json
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

from hygiene_core import (
    HygieneError,
    attach_digest,
    command_exists,
    digest_value,
    fingerprint,
    load_json,
    normalize_label,
    repository_identity,
    run,
    run_json,
    severity_at_least,
    tracked_files,
    utc_now,
    verify_digest,
    write_json,
)


def github_slug(repo: Path, report: dict[str, Any] | None = None) -> str:
    if report:
        remote = report.get("remote") or {}
        if remote.get("slug"):
            return str(remote["slug"])
        origin = (report.get("repository") or {}).get("origin")
    else:
        origin_result = run(["git", "remote", "get-url", "origin"], cwd=repo)
        origin = origin_result.stdout.strip() if origin_result.returncode == 0 else None
    if origin:
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", str(origin))
        if match:
            return match.group(1).removesuffix(".git")
    raise HygieneError("Could not resolve owner/repository from the GitHub origin.", code="GITHUB_REPOSITORY_UNRESOLVED")


def require_gh(repo: Path) -> None:
    if not command_exists("gh"):
        raise HygieneError("GitHub CLI (gh) is required for this operation.", code="GH_NOT_FOUND")
    auth = run(["gh", "auth", "status"], cwd=repo)
    if auth.returncode != 0:
        raise HygieneError("GitHub CLI is not authenticated.", code="GH_NOT_AUTHENTICATED", details=auth.stderr[-2000:])


def _issue_step_body(step: dict[str, Any], stack_summary: str) -> str:
    evidence_rows = []
    for item in step["evidence"]:
        source = str(item.get("source", "unknown"))
        if item.get("line"):
            source += f":{item['line']}"
        observation = str(item.get("observation", "")).replace("|", "\\|").replace("\n", " ")
        evidence_rows.append(f"| `{source}` | {observation} |")
    evidence_table = "\n".join(["| Source | Evidence |", "|---|---|", *evidence_rows])
    actions = "\n".join(f"- [ ] {item}" for item in step["actions"])
    acceptance = "\n".join(f"- [ ] {item}" for item in step["acceptance_criteria"])
    verification = "\n".join(step["verification"])
    dependencies = "\n".join(f"- {item}" for item in step["dependencies"]) or "- None"
    non_goals = "\n".join(f"- {item}" for item in step["non_goals"]) or "- Do not broaden this issue beyond the stated atomic outcome."
    destructive = "Yes — review the plan and rollback path before execution." if step["destructive"] else "No destructive operation is expected."
    return f"""<!-- repository-hygiene-step:{step['fingerprint']} -->

## Objective
{step['objective']}

## Context
- Detected stack: {stack_summary}
- Audit rule(s): {', '.join(step['rule_ids'])}
- Severity: {step['severity']}
- Confidence: {step['confidence']}
- Destructive or irreversible risk: {destructive}

## Evidence
{evidence_table}

## Implementation checklist
{actions}

## Acceptance criteria
{acceptance}

## Verification
```text
{verification}
```

## Dependencies
{dependencies}

## Risk and rollback
- Risk: {step['risk']}
- Rollback: {step['rollback']}

## Non-goals
{non_goals}

---
Generated from repository snapshot `{step['source_head'] or 'unknown'}` by the `maintaining-repository-hygiene` skill. Re-audit before closing.
"""


def _stack_summary(report: dict[str, Any]) -> str:
    stack = report.get("stack_profile") or {}
    ecosystems = [item.get("name") for item in stack.get("ecosystems", []) if item.get("name")]
    frameworks = [item.get("name") for item in stack.get("frameworks", []) if item.get("name")]
    parts = []
    if ecosystems:
        parts.append("ecosystems=" + ", ".join(ecosystems))
    if frameworks:
        parts.append("frameworks=" + ", ".join(frameworks))
    return "; ".join(parts) if parts else "No manifest-backed stack detected"


def create_issue_plan(report: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    minimum = str(policy.get("issue_min_severity", "low"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in report.get("findings", []):
        if not finding.get("actionable", True):
            continue
        if not severity_at_least(str(finding.get("severity", "info")), minimum):
            continue
        grouped[str(finding["remediation_key"])].append(finding)

    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    steps: list[dict[str, Any]] = []
    source_head = (report.get("repository") or {}).get("head")
    for remediation_key, findings in sorted(grouped.items()):
        rule_ids = sorted({str(item["rule_id"]) for item in findings})
        finding_ids = sorted({str(item["id"]) for item in findings})
        title_source = sorted(findings, key=lambda item: (-severity_rank[item["severity"]], item["title"]))[0]["title"]
        title = f"[Hygiene] {title_source}"
        if len(title) > 240:
            title = title[:237].rstrip() + "..."
        severity = max((item["severity"] for item in findings), key=severity_rank.get)
        confidence = min((item["confidence"] for item in findings), key=confidence_rank.get)
        evidence_items: list[dict[str, Any]] = []
        actions: list[str] = []
        acceptance: list[str] = []
        verification: list[str] = []
        dependencies: list[str] = []
        non_goals: list[str] = []
        for item in findings:
            evidence_items.extend(item.get("evidence", []))
            actions.extend(item.get("recommended_actions", []))
            acceptance.extend(item.get("acceptance_criteria", []))
            verification.extend(item.get("verification", []))
            dependencies.extend(item.get("dependencies", []))
            non_goals.extend(item.get("non_goals", []))
        unique = lambda values: list(dict.fromkeys(str(value) for value in values if str(value).strip()))
        step_fingerprint = fingerprint(remediation_key, finding_ids, source_head)
        objective = str(title_source).rstrip(".") + "."
        destructive = any(bool(item.get("destructive")) for item in findings)
        step = {
            "fingerprint": step_fingerprint,
            "remediation_key": remediation_key,
            "finding_ids": finding_ids,
            "rule_ids": rule_ids,
            "title": title,
            "objective": objective,
            "severity": severity,
            "confidence": confidence,
            "evidence": unique_dicts(evidence_items),
            "actions": unique(actions),
            "acceptance_criteria": unique(acceptance),
            "verification": unique(verification),
            "dependencies": unique(dependencies),
            "non_goals": unique(non_goals),
            "destructive": destructive,
            "risk": "Potential repository disruption or data loss if evidence is misclassified." if destructive else "A poorly scoped change could create contributor friction or weaken existing automation.",
            "rollback": "Restore the prior Git/ref/configuration state from the reviewed backup or revert commit; never rewrite shared history without a separate approved plan." if destructive else "Revert the implementing pull request or repository setting change.",
            "source_head": source_head,
        }
        step["body"] = _issue_step_body(step, _stack_summary(report))
        steps.append(step)

    steps.sort(key=lambda item: (-severity_rank[item["severity"]], item["remediation_key"], item["fingerprint"]))
    slug = github_slug(Path((report.get("repository") or {}).get("root", ".")), report)
    plan = {
        "schema_version": 1,
        "kind": "repository-hygiene-issue-plan",
        "generated_at": utc_now(),
        "repository": slug,
        "source_head": source_head,
        "source_report_digest": digest_value(report),
        "labels": list(policy.get("issue_labels", ["repository-hygiene"])),
        "step_semantics": "Each step is one atomic remediation boundary; each step maps to exactly one GitHub issue.",
        "steps": steps,
        "summary": {
            "steps": len(steps),
            "destructive_steps": sum(1 for step in steps if step["destructive"]),
            "by_severity": {name: sum(1 for step in steps if step["severity"] == name) for name in severity_rank},
        },
    }
    return attach_digest(plan)


def unique_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def validate_issue_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        verify_digest(plan)
    except HygieneError as exc:
        errors.append(str(exc))
    if plan.get("kind") != "repository-hygiene-issue-plan":
        errors.append("Unexpected plan kind.")
    fingerprints: set[str] = set()
    finding_ids: set[str] = set()
    for index, step in enumerate(plan.get("steps", []), start=1):
        prefix = f"step {index}"
        for key in ("fingerprint", "title", "body", "actions", "acceptance_criteria", "verification"):
            if not step.get(key):
                errors.append(f"{prefix}: missing {key}")
        marker = f"<!-- repository-hygiene-step:{step.get('fingerprint')} -->"
        if marker not in str(step.get("body", "")):
            errors.append(f"{prefix}: body is missing stable marker")
        if len(str(step.get("title", ""))) > 256:
            errors.append(f"{prefix}: title exceeds 256 characters")
        if len(str(step.get("body", "")).encode("utf-8")) > 65000:
            errors.append(f"{prefix}: body exceeds safe API size")
        if step.get("fingerprint") in fingerprints:
            errors.append(f"{prefix}: duplicate fingerprint")
        fingerprints.add(str(step.get("fingerprint")))
        for finding_id in step.get("finding_ids", []):
            if finding_id in finding_ids:
                errors.append(f"{prefix}: finding {finding_id} appears in multiple steps")
            finding_ids.add(finding_id)
    return errors


def _search_existing_issue(repo: Path, slug: str, fingerprint_value: str) -> list[dict[str, Any]]:
    query = f'repo:{slug} "repository-hygiene-step:{fingerprint_value}" in:body'
    result = run(["gh", "api", "search/issues", "--method", "GET", "-f", f"q={query}", "-f", "per_page=10"], cwd=repo)
    if result.returncode != 0:
        raise HygieneError("Unable to search for existing hygiene issues.", code="GH_ISSUE_SEARCH_FAILED", details=result.stderr[-2000:])
    payload = json.loads(result.stdout)
    return [item for item in payload.get("items", []) if isinstance(item, dict)]


def publish_issue_plan(
    repo: Path,
    plan: dict[str, Any],
    confirmation_digest: str,
    *,
    journal_path: Path,
    ensure_labels: bool,
    allow_head_change: bool,
    max_issues: int,
) -> dict[str, Any]:
    verify_digest(plan, confirmation_digest)
    errors = validate_issue_plan(plan)
    if errors:
        raise HygieneError("Issue plan validation failed.", code="ISSUE_PLAN_INVALID", details=errors)
    require_gh(repo)
    slug = github_slug(repo)
    if slug.casefold() != str(plan.get("repository", "")).casefold():
        raise HygieneError("Plan repository does not match the current checkout.", code="REPOSITORY_MISMATCH", details={"plan": plan.get("repository"), "current": slug})
    current_head = run(["git", "rev-parse", "HEAD"], cwd=repo, check=True).stdout.strip()
    if not allow_head_change and plan.get("source_head") and current_head != plan["source_head"]:
        raise HygieneError("Repository HEAD changed after the issue plan was generated. Re-audit or pass --allow-head-change.", code="SOURCE_HEAD_CHANGED", details={"plan": plan["source_head"], "current": current_head})
    steps = list(plan.get("steps", []))
    if len(steps) > max_issues:
        raise HygieneError(f"Plan contains {len(steps)} issues, above the publication cap of {max_issues}.", code="ISSUE_CAP_EXCEEDED")

    journal = {
        "schema_version": 1,
        "kind": "repository-hygiene-publication-journal",
        "plan_digest": plan["digest"],
        "repository": slug,
        "started_at": utc_now(),
        "results": [],
    }
    if journal_path.exists():
        existing = load_json(journal_path)
        if existing.get("plan_digest") == plan["digest"]:
            journal = existing
    completed = {item.get("fingerprint") for item in journal.get("results", []) if item.get("status") in {"created", "skipped-existing"}}

    labels = [str(item) for item in plan.get("labels", []) if str(item).strip()]
    if ensure_labels:
        for label in labels:
            result = run(["gh", "label", "create", label, "--repo", slug, "--description", "Repository hygiene audit and remediation", "--color", "5319e7", "--force"], cwd=repo)
            if result.returncode != 0:
                raise HygieneError(f"Unable to ensure issue label {label!r}.", code="GH_LABEL_ENSURE_FAILED", details=result.stderr[-2000:])

    for step in steps:
        fp = step["fingerprint"]
        if fp in completed:
            continue
        existing = _search_existing_issue(repo, slug, fp)
        if existing:
            item = existing[0]
            result_item = {"fingerprint": fp, "status": "skipped-existing", "number": item.get("number"), "url": item.get("html_url"), "title": item.get("title")}
            journal["results"].append(result_item)
            write_json(journal_path, journal)
            continue
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
            handle.write(step["body"])
            body_path = Path(handle.name)
        try:
            args = ["gh", "issue", "create", "--repo", slug, "--title", step["title"], "--body-file", str(body_path)]
            if labels:
                args.extend(["--label", ",".join(labels)])
            result = run(args, cwd=repo, timeout=120)
        finally:
            body_path.unlink(missing_ok=True)
        if result.returncode != 0:
            journal["results"].append({"fingerprint": fp, "status": "failed", "title": step["title"], "error": result.stderr[-2000:]})
            write_json(journal_path, journal)
            raise HygieneError(f"Issue publication failed for {step['title']!r}.", code="GH_ISSUE_CREATE_FAILED", details=result.stderr[-2000:])
        url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
        journal["results"].append({"fingerprint": fp, "status": "created", "title": step["title"], "url": url})
        write_json(journal_path, journal)
    journal["completed_at"] = utc_now()
    write_json(journal_path, journal)
    return journal


def _api_pages(repo: Path, endpoint: str, *, cap: int) -> tuple[list[dict[str, Any]], bool]:
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        result = run(["gh", "api", endpoint, "--method", "GET", "-f", "per_page=100", "-f", f"page={page}"], cwd=repo, timeout=120)
        if result.returncode != 0:
            raise HygieneError(f"GitHub API request failed for {endpoint}.", code="GH_API_FAILED", details=result.stderr[-2000:])
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise HygieneError(f"Unexpected GitHub API response for {endpoint}.", code="GH_API_UNEXPECTED_RESPONSE")
        batch = [item for item in payload if isinstance(item, dict)]
        if len(items) + len(batch) > cap:
            items.extend(batch[: max(0, cap - len(items))])
            return items, False
        items.extend(batch)
        if len(batch) < 100:
            return items, True
        page += 1


def _label_references(repo: Path, labels: list[str], max_text_bytes: int) -> dict[str, list[str]]:
    references: dict[str, list[str]] = defaultdict(list)
    relevant = []
    for path in tracked_files(repo):
        lower = path.casefold()
        if lower.startswith(".github/") or lower.startswith("docs/") or Path(path).name.casefold().startswith(("readme", "contributing", "security", "support")):
            relevant.append(path)
    for path in relevant:
        try:
            if (repo / path).stat().st_size > max_text_bytes:
                continue
            text = (repo / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lower_text = text.casefold()
        for label in labels:
            needle = label.casefold()
            # Configuration files are treated conservatively. In docs, require a quote/backtick or explicit 'label' context.
            if path.casefold().startswith(".github/"):
                matched = re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lower_text)
            else:
                matched = re.search(rf"(?:label[^\n]{{0,80}}|[`'\"]){re.escape(needle)}(?:[`'\"]|\b)", lower_text)
            if matched:
                line = lower_text[: matched.start()].count("\n") + 1
                references[label].append(f"{path}:{line}")
    return references


def create_label_prune_plan(repo: Path, policy: dict[str, Any]) -> dict[str, Any]:
    require_gh(repo)
    slug = github_slug(repo)
    cap = int(policy.get("max_remote_issues_to_scan", 10000))
    labels, labels_complete = _api_pages(repo, f"repos/{slug}/labels", cap=max(cap, 1000))
    issues, history_complete = _api_pages(repo, f"repos/{slug}/issues?state=all&sort=created&direction=asc", cap=cap)
    label_names = sorted(str(item.get("name")) for item in labels if item.get("name"))
    usage: dict[str, int] = {name: 0 for name in label_names}
    for issue in issues:
        for label in issue.get("labels", []):
            name = label.get("name") if isinstance(label, dict) else label
            if isinstance(name, str):
                usage[name] = usage.get(name, 0) + 1
    refs = _label_references(repo, label_names, int(policy.get("max_text_file_bytes", 1048576)))
    label_policy = policy.get("label_pruning", {})
    protected_names = {str(item).casefold() for item in label_policy.get("protected_names", [])}
    protected_prefixes = tuple(str(item).casefold() for item in label_policy.get("protected_prefixes", []))
    normalized: dict[str, list[str]] = defaultdict(list)
    for name in label_names:
        normalized[normalize_label(name)].append(name)
    duplicates = [names for names in normalized.values() if len(names) > 1]

    candidates: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for label in labels:
        name = str(label.get("name", ""))
        if not name:
            continue
        reasons = []
        if name.casefold() in protected_names or name.casefold().startswith(protected_prefixes):
            reasons.append("protected-by-policy")
        if usage.get(name, 0) > 0:
            reasons.append(f"used-by-{usage[name]}-issues-or-pull-requests")
        if refs.get(name):
            reasons.append("referenced-in-repository")
        if not history_complete:
            reasons.append("incomplete-history-scan")
        if reasons:
            suppressed.append({"name": name, "reasons": reasons, "usage_count": usage.get(name, 0), "references": refs.get(name, [])})
        else:
            candidates.append({
                "operation": "delete-label",
                "name": name,
                "color": label.get("color"),
                "description": label.get("description"),
                "evidence": {"usage_count": 0, "references": [], "history_scan_complete": True},
            })
    plan = {
        "schema_version": 1,
        "kind": "repository-hygiene-label-prune-plan",
        "generated_at": utc_now(),
        "repository": slug,
        "source_head": repository_identity(repo).get("head"),
        "scan": {"labels_complete": labels_complete, "history_complete": history_complete, "issues_and_pull_requests_scanned": len(issues), "cap": cap},
        "inventory": sorted([
            {
                "name": str(item.get("name", "")),
                "color": item.get("color"),
                "description": item.get("description"),
                "usage_count": usage.get(str(item.get("name", "")), 0),
                "references": refs.get(str(item.get("name", "")), []),
            }
            for item in labels if item.get("name")
        ], key=lambda item: item["name"].casefold()),
        "operations": sorted(candidates, key=lambda item: item["name"].casefold()),
        "suppressed": sorted(suppressed, key=lambda item: item["name"].casefold()),
        "normalized_duplicates": sorted(duplicates),
        "policy_snapshot": {
            "protected_names": sorted(protected_names),
            "protected_prefixes": list(protected_prefixes),
            "max_remote_issues_to_scan": cap,
            "max_text_file_bytes": int(policy.get("max_text_file_bytes", 1048576)),
        },
        "safety": "Only zero-use, unreferenced, unprotected labels are proposed. Apply requires this digest and a fresh complete recheck.",
    }
    return attach_digest(plan)


def apply_label_prune_plan(repo: Path, plan: dict[str, Any], confirmation_digest: str) -> dict[str, Any]:
    verify_digest(plan, confirmation_digest)
    if plan.get("kind") != "repository-hygiene-label-prune-plan":
        raise HygieneError("Unexpected label plan kind.", code="LABEL_PLAN_INVALID")
    require_gh(repo)
    slug = github_slug(repo)
    if slug.casefold() != str(plan.get("repository", "")).casefold():
        raise HygieneError("Label plan repository does not match current checkout.", code="REPOSITORY_MISMATCH")
    # Recreate the decision using the exact protected policy snapshot.
    synthetic_policy = {
        "max_remote_issues_to_scan": plan["policy_snapshot"]["max_remote_issues_to_scan"],
        "max_text_file_bytes": plan["policy_snapshot"]["max_text_file_bytes"],
        "label_pruning": {
            "protected_names": plan["policy_snapshot"]["protected_names"],
            "protected_prefixes": plan["policy_snapshot"]["protected_prefixes"],
        },
    }
    fresh = create_label_prune_plan(repo, synthetic_policy)
    planned_names = [item["name"] for item in plan.get("operations", [])]
    fresh_names = [item["name"] for item in fresh.get("operations", [])]
    if planned_names != fresh_names:
        raise HygieneError("Fresh label state differs from the reviewed plan; no labels were deleted.", code="LABEL_STATE_CHANGED", details={"planned": planned_names, "fresh": fresh_names})
    results = []
    for name in planned_names:
        endpoint = f"repos/{slug}/labels/{quote(name, safe='')}"
        result = run(["gh", "api", endpoint, "--method", "DELETE"], cwd=repo)
        if result.returncode != 0:
            results.append({"name": name, "status": "failed", "error": result.stderr[-2000:]})
            raise HygieneError(f"Failed to delete label {name!r}; remaining operations stopped.", code="LABEL_DELETE_FAILED", details=results)
        results.append({"name": name, "status": "deleted"})
    return {"status": "ok", "repository": slug, "plan_digest": plan["digest"], "completed_at": utc_now(), "results": results}


def create_worktree_prune_plan(repo: Path) -> dict[str, Any]:
    result = run(["git", "worktree", "prune", "--dry-run", "--verbose", "--expire", "now"], cwd=repo)
    if result.returncode != 0:
        raise HygieneError("Git worktree prune dry-run failed.", code="WORKTREE_DRY_RUN_FAILED", details=result.stderr[-2000:])
    lines = [line for line in (result.stdout + result.stderr).splitlines() if line.strip()]
    plan = {
        "schema_version": 1,
        "kind": "repository-hygiene-worktree-prune-plan",
        "generated_at": utc_now(),
        "repository": repository_identity(repo),
        "command": ["git", "worktree", "prune", "--verbose", "--expire", "now"],
        "dry_run_command": ["git", "worktree", "prune", "--dry-run", "--verbose", "--expire", "now"],
        "operations": lines,
        "safety": "git worktree prune removes stale administrative metadata, not registered live worktree directories. Lock intentionally offline worktrees before applying.",
    }
    return attach_digest(plan)


def apply_worktree_prune_plan(repo: Path, plan: dict[str, Any], confirmation_digest: str) -> dict[str, Any]:
    verify_digest(plan, confirmation_digest)
    if plan.get("kind") != "repository-hygiene-worktree-prune-plan":
        raise HygieneError("Unexpected worktree plan kind.", code="WORKTREE_PLAN_INVALID")
    current_root = repository_identity(repo)["root"]
    if current_root != (plan.get("repository") or {}).get("root"):
        raise HygieneError("Worktree plan was created for a different repository root.", code="REPOSITORY_MISMATCH")
    fresh = create_worktree_prune_plan(repo)
    if fresh.get("operations") != plan.get("operations"):
        raise HygieneError("Fresh worktree dry-run differs from the reviewed plan; nothing was pruned.", code="WORKTREE_STATE_CHANGED", details={"planned": plan.get("operations"), "fresh": fresh.get("operations")})
    result = run(["git", "worktree", "prune", "--verbose", "--expire", "now"], cwd=repo)
    if result.returncode != 0:
        raise HygieneError("Git worktree prune failed.", code="WORKTREE_PRUNE_FAILED", details=result.stderr[-2000:])
    verify = create_worktree_prune_plan(repo)
    return {
        "status": "ok",
        "plan_digest": plan["digest"],
        "completed_at": utc_now(),
        "output": [line for line in (result.stdout + result.stderr).splitlines() if line.strip()],
        "remaining_operations": verify["operations"],
    }

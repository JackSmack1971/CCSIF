#!/usr/bin/env python3
"""Deterministic discovery, planning, and journaling for issue-to-pr.

This script never edits code, creates branches, or calls `gh pr create` /
`gh issue create` itself. It only reads GitHub state (via `gh`) and produces
a digest-bound plan plus an idempotent journal. Implementation and PR
creation stay with the implementation-agent / pr-reviewer subagents, which
need to iterate (edit, test, retry) in a way a deterministic script cannot.

Subcommands:
  plan      Discover open issues carrying the hygiene marker, resolve
            dependencies and destructive flags, compute branch names, and
            check for an existing PR before proposing work.
  validate  Re-check a plan's internal consistency and digest.
  record    Append/update one journal entry for one issue (idempotent).
  status    Print a summary of a journal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MARKER_RE = re.compile(r"<!--\s*repository-hygiene-step:([0-9a-fA-F]+)\s*-->")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
SOURCE_MARKER = "issue-to-pr-source"


class IssueToPrError(Exception):
    def __init__(self, message: str, *, code: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def run_json(cmd: list[str], *, cwd: Path, timeout: int = 120) -> Any:
    result = run(cmd, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        raise IssueToPrError(f"Command failed: {' '.join(cmd)}", code="COMMAND_FAILED", details=result.stderr[-2000:])
    return json.loads(result.stdout or "null")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def require_gh(repo: Path) -> None:
    if not command_exists("gh"):
        raise IssueToPrError("GitHub CLI (gh) is required for this operation.", code="GH_NOT_FOUND")
    auth = run(["gh", "auth", "status"], cwd=repo)
    if auth.returncode != 0:
        raise IssueToPrError("GitHub CLI is not authenticated.", code="GH_NOT_AUTHENTICATED", details=auth.stderr[-2000:])


def github_slug(repo: Path) -> str:
    origin = run(["git", "remote", "get-url", "origin"], cwd=repo)
    if origin.returncode != 0:
        raise IssueToPrError("Could not resolve the origin remote.", code="ORIGIN_UNRESOLVED", details=origin.stderr[-2000:])
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", origin.stdout.strip())
    if not match:
        raise IssueToPrError("Could not resolve owner/repository from the GitHub origin.", code="GITHUB_REPOSITORY_UNRESOLVED")
    return match.group(1)


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in payload.items() if k != "digest"}, sort_keys=True, ensure_ascii=False)


def attach_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["digest"] = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
    return payload


def verify_digest(payload: dict[str, Any], expected: str | None = None) -> None:
    stated = payload.get("digest")
    recomputed = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
    if stated != recomputed:
        raise IssueToPrError("Plan digest does not match its contents; it was hand-edited or corrupted.", code="DIGEST_MISMATCH")
    if expected is not None and expected != stated:
        raise IssueToPrError("Provided --confirm-digest does not match the plan.", code="DIGEST_CONFIRM_MISMATCH", details={"expected": expected, "actual": stated})


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "issue"


def branch_name(fingerprint: str, title: str) -> str:
    return f"hygiene/{fingerprint[:12]}-{slugify(title)}"


def parse_sections(body: str) -> dict[str, str]:
    headers = list(SECTION_RE.finditer(body))
    sections: dict[str, str] = {}
    for index, header in enumerate(headers):
        start = header.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        sections[header.group(1).strip().casefold()] = body[start:end].strip()
    return sections


def parse_issue(issue: dict[str, Any]) -> dict[str, Any] | None:
    body = str(issue.get("body") or "")
    match = MARKER_RE.search(body)
    if not match:
        return None
    sections = parse_sections(body)
    context = sections.get("context", "")
    destructive = bool(re.search(r"destructive.*risk:\s*yes", context, re.IGNORECASE))
    deps_text = sections.get("dependencies", "")
    dependency_tokens = [
        line.lstrip("-* ").strip()
        for line in deps_text.splitlines()
        if line.strip().startswith(("-", "*"))
    ]
    dependency_tokens = [token for token in dependency_tokens if token and token.casefold() != "none"]
    return {
        "issue_number": issue["number"],
        "issue_url": issue.get("url") or issue.get("html_url"),
        "title": issue.get("title", ""),
        "fingerprint": match.group(1),
        "destructive": destructive,
        "dependency_tokens": dependency_tokens,
    }


def find_existing_pr(repo: Path, slug: str, issue_number: int) -> dict[str, Any] | None:
    query = f'repo:{slug} "{SOURCE_MARKER}:#{issue_number}" in:body'
    result = run(["gh", "api", "search/issues", "--method", "GET", "-f", f"q={query}", "-f", "per_page=5"], cwd=repo)
    if result.returncode != 0:
        raise IssueToPrError("Unable to search for an existing PR.", code="GH_PR_SEARCH_FAILED", details=result.stderr[-2000:])
    payload = json.loads(result.stdout)
    items = [item for item in payload.get("items", []) if isinstance(item, dict) and item.get("pull_request")]
    return items[0] if items else None


def build_plan(repo: Path, *, label: str, issue_filter: list[int] | None) -> dict[str, Any]:
    require_gh(repo)
    slug = github_slug(repo)
    open_issues = run_json(
        ["gh", "issue", "list", "--repo", slug, "--label", label, "--state", "open", "--limit", "500",
         "--json", "number,title,body,url"],
        cwd=repo,
    )
    closed_issues = run_json(
        ["gh", "issue", "list", "--repo", slug, "--label", label, "--state", "closed", "--limit", "500",
         "--json", "number,title,body,url"],
        cwd=repo,
    )
    all_parsed: dict[str, dict[str, Any]] = {}
    open_by_number: dict[int, dict[str, Any]] = {}
    closed_numbers: set[int] = set()
    for issue in open_issues:
        parsed = parse_issue(issue)
        if not parsed:
            continue
        open_by_number[parsed["issue_number"]] = parsed
        all_parsed[parsed["fingerprint"]] = parsed
    for issue in closed_issues:
        parsed = parse_issue(issue)
        if not parsed:
            continue
        closed_numbers.add(parsed["issue_number"])
        all_parsed.setdefault(parsed["fingerprint"], parsed)

    def resolve_token(token: str) -> dict[str, Any]:
        by_fingerprint = next((p for fp, p in all_parsed.items() if fp.startswith(token) or token.startswith(fp)), None)
        candidate = by_fingerprint
        if candidate is None:
            candidate = next(
                (p for p in all_parsed.values() if p["title"].casefold() == token.casefold() or token.casefold() in p["title"].casefold()),
                None,
            )
        if candidate is None:
            return {"token": token, "status": "unknown"}
        if candidate["issue_number"] in closed_numbers:
            return {"token": token, "issue_number": candidate["issue_number"], "status": "closed"}
        return {"token": token, "issue_number": candidate["issue_number"], "status": "open"}

    items: list[dict[str, Any]] = []
    for number in sorted(open_by_number):
        if issue_filter and number not in issue_filter:
            continue
        parsed = open_by_number[number]
        resolved_deps = [resolve_token(token) for token in parsed["dependency_tokens"]]
        blocking = [dep for dep in resolved_deps if dep["status"] != "closed"]
        existing_pr = find_existing_pr(repo, slug, number)
        if existing_pr:
            status, reason = "pr-exists", None
        elif parsed["destructive"]:
            status, reason = "destructive-skip", "Issue is marked destructive; requires explicit human-approved handling, not automatic PR generation."
        elif blocking:
            status, reason = "blocked", "Unresolved dependency: " + ", ".join(d["token"] for d in blocking)
        else:
            status, reason = "ready", None
        items.append({
            "issue_number": number,
            "issue_url": parsed["issue_url"],
            "title": parsed["title"],
            "fingerprint": parsed["fingerprint"],
            "branch": branch_name(parsed["fingerprint"], parsed["title"]),
            "destructive": parsed["destructive"],
            "dependencies_resolved": resolved_deps,
            "existing_pr_url": existing_pr.get("html_url") if existing_pr else None,
            "status": status,
            "block_reason": reason,
        })

    # Topological order among "ready" items only, by resolved-dependency count then issue number.
    ready = [item for item in items if item["status"] == "ready"]
    order = [item["issue_number"] for item in sorted(ready, key=lambda i: (len(i["dependencies_resolved"]), i["issue_number"]))]

    plan = {
        "schema_version": 1,
        "kind": "issue-to-pr-plan",
        "generated_at": utc_now(),
        "repository": slug,
        "label": label,
        "items": items,
        "order": order,
        "summary": {
            "total": len(items),
            "ready": len(ready),
            "blocked": sum(1 for item in items if item["status"] == "blocked"),
            "destructive_skipped": sum(1 for item in items if item["status"] == "destructive-skip"),
            "pr_exists": sum(1 for item in items if item["status"] == "pr-exists"),
        },
    }
    return attach_digest(plan)


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        verify_digest(plan)
    except IssueToPrError as exc:
        errors.append(str(exc))
    if plan.get("kind") != "issue-to-pr-plan":
        errors.append("Unexpected plan kind.")
    seen_numbers: set[int] = set()
    seen_branches: set[str] = set()
    for index, item in enumerate(plan.get("items", []), start=1):
        prefix = f"item {index} (#{item.get('issue_number')})"
        for key in ("issue_number", "fingerprint", "branch", "status"):
            if not item.get(key) and item.get(key) != 0:
                errors.append(f"{prefix}: missing {key}")
        number = item.get("issue_number")
        if number in seen_numbers:
            errors.append(f"{prefix}: duplicate issue number")
        seen_numbers.add(number)
        branch = item.get("branch")
        if branch in seen_branches:
            errors.append(f"{prefix}: duplicate branch name {branch!r}")
        seen_branches.add(branch)
        if item.get("status") not in {"ready", "blocked", "destructive-skip", "pr-exists"}:
            errors.append(f"{prefix}: unknown status {item.get('status')!r}")
    return errors


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_or_init_journal(path: Path, plan_digest: str, repository: str) -> dict[str, Any]:
    if path.exists():
        journal = load_json(path)
        if journal.get("plan_digest") == plan_digest:
            return journal
    return {
        "schema_version": 1,
        "kind": "issue-to-pr-journal",
        "plan_digest": plan_digest,
        "repository": repository,
        "started_at": utc_now(),
        "results": [],
    }


def record_result(journal_path: Path, plan_path: Path, *, issue_number: int, status: str,
                   branch: str | None, pr_url: str | None, review_verdict: str | None, error: str | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    verify_digest(plan)
    item = next((i for i in plan.get("items", []) if i.get("issue_number") == issue_number), None)
    if item is None:
        raise IssueToPrError(f"Issue #{issue_number} is not part of this plan.", code="ISSUE_NOT_IN_PLAN")
    journal = load_or_init_journal(journal_path, plan["digest"], plan["repository"])
    entry = {
        "issue_number": issue_number,
        "fingerprint": item["fingerprint"],
        "status": status,
        "branch": branch or item.get("branch"),
        "pr_url": pr_url,
        "review_verdict": review_verdict,
        "error": error,
        "recorded_at": utc_now(),
    }
    journal["results"] = [entry_ for entry_ in journal["results"] if entry_.get("issue_number") != issue_number]
    journal["results"].append(entry)
    journal["updated_at"] = utc_now()
    write_json(journal_path, journal)
    return journal


def summarize_journal(journal: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for entry in journal.get("results", []):
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return {"repository": journal.get("repository"), "total_recorded": len(journal.get("results", [])), "by_status": counts}


def cmd_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    issue_filter = args.issue or None
    plan = build_plan(repo, label=args.label, issue_filter=issue_filter)
    if args.out:
        write_json(Path(args.out), plan)
    print(json.dumps({"status": "ok", "digest": plan["digest"], "summary": plan["summary"]}))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    plan = load_json(Path(args.plan))
    errors = validate_plan(plan)
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}))
        return 2
    print(json.dumps({"status": "ok", "digest": plan["digest"]}))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    journal = record_result(
        Path(args.journal), Path(args.plan),
        issue_number=args.issue, status=args.status, branch=args.branch,
        pr_url=args.pr_url, review_verdict=args.review_verdict, error=args.error,
    )
    print(json.dumps({"status": "ok", "recorded": args.issue, "summary": summarize_journal(journal)}))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    journal = load_json(Path(args.journal))
    print(json.dumps({"status": "ok", "summary": summarize_journal(journal)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan_cmd = sub.add_parser("plan", help="Discover open hygiene issues and build a digest-bound work plan.")
    plan_cmd.add_argument("--repo", default=".")
    plan_cmd.add_argument("--label", default="repository-hygiene")
    plan_cmd.add_argument("--issue", type=int, action="append", help="Restrict the plan to specific issue numbers (repeatable).")
    plan_cmd.add_argument("--out", default=None)
    plan_cmd.set_defaults(func=cmd_plan)

    validate_cmd = sub.add_parser("validate", help="Validate a plan's schema, uniqueness, and digest.")
    validate_cmd.add_argument("--plan", required=True)
    validate_cmd.set_defaults(func=cmd_validate)

    record_cmd = sub.add_parser("record", help="Record one issue's outcome into the journal (idempotent).")
    record_cmd.add_argument("--journal", required=True)
    record_cmd.add_argument("--plan", required=True)
    record_cmd.add_argument("--issue", type=int, required=True)
    record_cmd.add_argument("--status", required=True, choices=["opened", "needs-changes", "failed", "skipped"])
    record_cmd.add_argument("--branch", default=None)
    record_cmd.add_argument("--pr-url", default=None)
    record_cmd.add_argument("--review-verdict", default=None)
    record_cmd.add_argument("--error", default=None)
    record_cmd.set_defaults(func=cmd_record)

    status_cmd = sub.add_parser("status", help="Summarize a journal.")
    status_cmd.add_argument("--journal", required=True)
    status_cmd.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except IssueToPrError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "message": str(exc), "details": exc.details}), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface unexpected failures verbatim
        print(json.dumps({"status": "error", "code": "UNEXPECTED", "message": str(exc)}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

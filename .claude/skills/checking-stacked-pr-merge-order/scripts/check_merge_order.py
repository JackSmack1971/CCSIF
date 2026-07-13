#!/usr/bin/env python3
"""Determine stacked GitHub PR merge constraints from current Git ancestry.

This program does not modify the working tree, index, branches, or GitHub state.
It may fetch objects into temporary refs under refs/merge-order-check/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_PREREQUISITE = 2
EXIT_GITHUB = 3
EXIT_INCOMPLETE = 4
EXIT_BLOCKED = 5


class AnalyzerError(RuntimeError):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class WarningItem:
    code: str
    message: str
    blocking: bool = False
    pr_numbers: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "blocking": self.blocking,
            "pr_numbers": self.pr_numbers,
        }


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    head_ref_name: str
    head_ref_oid: str
    base_ref_name: str
    base_ref_oid: str
    head_owner: str | None
    head_repository: str | None
    is_cross_repository: bool
    is_draft: bool
    merge_state_status: str | None
    mergeable: str | None
    updated_at: str | None
    effective_head_oid: str | None = None
    effective_base_oid: str | None = None
    head_resolved: bool = False
    base_resolved: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "head_ref_name": self.head_ref_name,
            "head_ref_oid": self.head_ref_oid,
            "base_ref_name": self.base_ref_name,
            "base_ref_oid": self.base_ref_oid,
            "head_owner": self.head_owner,
            "head_repository": self.head_repository,
            "is_cross_repository": self.is_cross_repository,
            "is_draft": self.is_draft,
            "merge_state_status": self.merge_state_status,
            "mergeable": self.mergeable,
            "updated_at": self.updated_at,
            "effective_head_oid": self.effective_head_oid,
            "effective_base_oid": self.effective_base_oid,
            "head_resolved": self.head_resolved,
            "base_resolved": self.base_resolved,
        }


@dataclass
class Dependency:
    before: int
    after: int
    evidence: set[str] = field(default_factory=set)
    direct: bool = True
    blocking_mismatch: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "before": self.before,
            "after": self.after,
            "evidence": sorted(self.evidence),
            "direct": self.direct,
            "blocking_mismatch": self.blocking_mismatch,
        }


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AnalyzerError(f"Required executable not found: {command[0]}", EXIT_PREREQUISITE) from exc
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise AnalyzerError(f"Command failed ({' '.join(command)}): {stderr}", EXIT_PREREQUISITE)
    return result


def require_git_repo(cwd: Path) -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if result.returncode != 0:
        raise AnalyzerError("Run this analyzer inside a Git worktree.", EXIT_PREREQUISITE)
    return Path(result.stdout.strip()).resolve()


def parse_repo_path(remote_url: str) -> tuple[str | None, str | None]:
    value = remote_url.strip()
    if not value:
        return None, None
    if "://" in value:
        parsed = urlparse(value)
        host = parsed.hostname
        path = parsed.path.strip("/")
    else:
        match = re.match(r"^(?:[^@]+@)?([^:]+):(.+)$", value)
        if match:
            host, path = match.group(1), match.group(2).strip("/")
        else:
            host, path = None, value.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) < 2:
        return host, None
    return host, "/".join(parts[-2:])


def resolve_repository(repo_root: Path, repo_arg: str | None) -> dict[str, Any]:
    command = ["gh", "repo", "view"]
    if repo_arg:
        command.extend(["--repo", repo_arg])
    command.extend(["--json", "nameWithOwner,url"])
    result = run(command, cwd=repo_root, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown GitHub CLI error"
        raise AnalyzerError(f"Unable to resolve GitHub repository: {detail}", EXIT_GITHUB)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AnalyzerError("GitHub CLI returned invalid repository JSON.", EXIT_GITHUB) from exc
    if not data.get("nameWithOwner") or not data.get("url"):
        raise AnalyzerError("GitHub repository response lacks nameWithOwner or url.", EXIT_GITHUB)
    return data


def select_remote(repo_root: Path, repository: dict[str, Any], requested: str | None) -> str:
    remotes_result = run(["git", "remote"], cwd=repo_root)
    remotes = [line.strip() for line in remotes_result.stdout.splitlines() if line.strip()]
    if requested:
        if requested not in remotes:
            raise AnalyzerError(f"Git remote '{requested}' does not exist.", EXIT_PREREQUISITE)
        return requested

    _, expected_path = parse_repo_path(str(repository["url"]))
    matches: list[str] = []
    for remote in remotes:
        url_result = run(["git", "remote", "get-url", remote], cwd=repo_root, check=False)
        if url_result.returncode != 0:
            continue
        _, actual_path = parse_repo_path(url_result.stdout.strip())
        if expected_path and actual_path and expected_path.lower() == actual_path.lower():
            matches.append(remote)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        preferred = [name for name in ("upstream", "origin") if name in matches]
        if len(preferred) == 1:
            return preferred[0]
        raise AnalyzerError(
            f"Multiple remotes match {repository['nameWithOwner']}: {', '.join(matches)}. Pass --remote.",
            EXIT_PREREQUISITE,
        )
    raise AnalyzerError(
        f"No local Git remote matches base repository {repository['nameWithOwner']}. Add the base remote or pass --remote.",
        EXIT_PREREQUISITE,
    )


def query_open_prs(
    repo_root: Path,
    repository_name: str,
    selected_numbers: set[int],
    exclude_drafts: bool,
    max_prs: int,
) -> tuple[list[PullRequest], list[PullRequest]]:
    fields = (
        "number,title,url,headRefName,headRefOid,baseRefName,baseRefOid,"
        "headRepository,headRepositoryOwner,isCrossRepository,isDraft,mergeStateStatus,mergeable,updatedAt"
    )
    command = [
        "gh", "pr", "list", "--repo", repository_name, "--state", "open",
        "--limit", str(max_prs + 1), "--json", fields,
    ]
    result = run(command, cwd=repo_root, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown GitHub CLI error"
        raise AnalyzerError(f"Unable to list open PRs: {detail}", EXIT_GITHUB)
    try:
        raw_items = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AnalyzerError("GitHub CLI returned invalid PR JSON.", EXIT_GITHUB) from exc
    if not isinstance(raw_items, list):
        raise AnalyzerError("GitHub CLI PR response is not a list.", EXIT_GITHUB)
    if len(raw_items) > max_prs:
        raise AnalyzerError(
            f"More than {max_prs} open PRs were returned. Increase --max-prs so the graph is complete.",
            EXIT_GITHUB,
        )

    all_prs: list[PullRequest] = []
    for item in raw_items:
        number = int(item["number"])
        owner_value = item.get("headRepositoryOwner")
        owner = owner_value.get("login") if isinstance(owner_value, dict) else None
        repository_value = item.get("headRepository")
        head_repository = None
        if isinstance(repository_value, dict):
            head_repository = repository_value.get("nameWithOwner")
            if not head_repository and owner and repository_value.get("name"):
                head_repository = f"{owner}/{repository_value['name']}"
        elif isinstance(repository_value, str):
            head_repository = repository_value
        all_prs.append(
            PullRequest(
                number=number,
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                head_ref_name=str(item.get("headRefName") or ""),
                head_ref_oid=str(item.get("headRefOid") or ""),
                base_ref_name=str(item.get("baseRefName") or ""),
                base_ref_oid=str(item.get("baseRefOid") or ""),
                head_owner=owner,
                head_repository=head_repository,
                is_cross_repository=bool(item.get("isCrossRepository")),
                is_draft=bool(item.get("isDraft")),
                merge_state_status=item.get("mergeStateStatus"),
                mergeable=item.get("mergeable"),
                updated_at=item.get("updatedAt"),
            )
        )
    all_prs.sort(key=lambda pr: pr.number)
    prs = [
        pr for pr in all_prs
        if (not selected_numbers or pr.number in selected_numbers)
        and (not exclude_drafts or not pr.is_draft)
    ]
    if selected_numbers:
        found = {pr.number for pr in prs}
        missing = sorted(selected_numbers - found)
        if missing:
            raise AnalyzerError(
                "Selected PRs are not open or were not returned: " + ", ".join(f"#{n}" for n in missing),
                EXIT_GITHUB,
            )
    return prs, all_prs


def git_object_exists(repo_root: Path, oid: str) -> bool:
    if not oid:
        return False
    result = run(["git", "cat-file", "-e", f"{oid}^{{commit}}"], cwd=repo_root, check=False)
    return result.returncode == 0


def rev_parse(repo_root: Path, ref: str) -> str | None:
    result = run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=repo_root, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def fetch_ref(repo_root: Path, remote: str, source: str, destination: str) -> tuple[bool, str | None, str | None]:
    result = run(
        ["git", "fetch", "--force", "--no-tags", "--quiet", remote, f"+{source}:{destination}"],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown fetch error"
        return False, None, detail
    return True, rev_parse(repo_root, destination), None


def delete_refs(repo_root: Path, refs: Iterable[str]) -> None:
    for ref in refs:
        run(["git", "update-ref", "-d", ref], cwd=repo_root, check=False)


def is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool | None:
    result = run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=repo_root, check=False)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def add_dependency(
    dependencies: dict[tuple[int, int], Dependency],
    before: int,
    after: int,
    evidence: str,
    *,
    blocking_mismatch: bool = False,
) -> None:
    if before == after:
        return
    key = (before, after)
    dep = dependencies.setdefault(key, Dependency(before=before, after=after))
    dep.evidence.add(evidence)
    dep.blocking_mismatch = dep.blocking_mismatch or blocking_mismatch


def path_exists(start: int, target: int, adjacency: dict[int, set[int]], skip: tuple[int, int]) -> bool:
    queue = deque([start])
    seen = {start}
    while queue:
        node = queue.popleft()
        for nxt in adjacency.get(node, set()):
            if (node, nxt) == skip:
                continue
            if nxt == target:
                return True
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def mark_transitive_edges(dependencies: dict[tuple[int, int], Dependency]) -> None:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for dep in dependencies.values():
        adjacency[dep.before].add(dep.after)
    for key, dep in dependencies.items():
        if "base_target" in dep.evidence:
            continue
        if path_exists(dep.before, dep.after, adjacency, key):
            dep.direct = False


def topo_waves(nodes: set[int], dependencies: Iterable[Dependency]) -> tuple[list[list[int]], list[int]]:
    adjacency: dict[int, set[int]] = {node: set() for node in nodes}
    indegree: dict[int, int] = {node: 0 for node in nodes}
    for dep in dependencies:
        if not dep.direct or dep.before not in nodes or dep.after not in nodes:
            continue
        if dep.after not in adjacency[dep.before]:
            adjacency[dep.before].add(dep.after)
            indegree[dep.after] += 1
    remaining = set(nodes)
    waves: list[list[int]] = []
    while remaining:
        wave = sorted(node for node in remaining if indegree[node] == 0)
        if not wave:
            return waves, sorted(remaining)
        waves.append(wave)
        for node in wave:
            remaining.remove(node)
            for nxt in adjacency[node]:
                indegree[nxt] -= 1
    return waves, []


def weak_components(nodes: set[int], dependencies: Iterable[Dependency]) -> list[set[int]]:
    undirected: dict[int, set[int]] = {node: set() for node in nodes}
    for dep in dependencies:
        if not dep.direct:
            continue
        undirected[dep.before].add(dep.after)
        undirected[dep.after].add(dep.before)
    components: list[set[int]] = []
    unseen = set(nodes)
    while unseen:
        start = min(unseen)
        queue = [start]
        component: set[int] = set()
        while queue:
            node = queue.pop()
            if node in component:
                continue
            component.add(node)
            unseen.discard(node)
            queue.extend(undirected[node] - component)
        components.append(component)
    return components


def status_from(warnings: list[WarningItem], errors: list[str]) -> str:
    if errors:
        return "partial"
    if any(warning.blocking for warning in warnings):
        return "blocked"
    return "ok"


def markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = ["# Stacked PR Merge-Order Check", ""]
    lines.append(f"- **Status:** `{report['status']}`")
    lines.append(f"- **Repository:** `{report['repository']}`")
    lines.append(f"- **Remote:** `{report['remote']}`")
    lines.append(f"- **Generated:** `{report['generated_at']}`")
    lines.append(f"- **Fetch performed:** `{str(report['fetch_performed']).lower()}`")
    lines.append(f"- **Open PRs analyzed:** `{len(report['prs'])}`")
    lines.append("")

    if report["status"] in {"blocked", "partial", "error"}:
        lines.extend([
            "> **Stop:** The evidence is not sufficient for merge execution. Resolve the findings below and rerun the check.",
            "",
        ])

    lines.extend(["## Detected stacks", ""])
    multi_components = [c for c in report["components"] if len(c["pr_numbers"]) > 1]
    if not multi_components:
        lines.append("No multi-PR ancestry stack was proven.")
    else:
        for index, component in enumerate(multi_components, start=1):
            lines.append(f"### Stack {index}")
            for wave_index, wave in enumerate(component["waves"], start=1):
                labels = ", ".join(f"PR #{number}" for number in wave)
                lines.append(f"- Wave {wave_index}: {labels}")
            if component["cycle_nodes"]:
                cycle = ", ".join(f"PR #{number}" for number in component["cycle_nodes"])
                lines.append(f"- Cycle/unresolved nodes: {cycle}")
            lines.append("")

    lines.extend(["## Merge constraints", ""])
    direct_deps = [dep for dep in report["dependencies"] if dep["direct"]]
    if not direct_deps:
        lines.append("No direct inter-PR merge constraints were proven.")
    else:
        for dep in direct_deps:
            evidence = ", ".join(dep["evidence"])
            suffix = " — **BLOCKING MISMATCH**" if dep["blocking_mismatch"] else ""
            lines.append(f"- PR #{dep['before']} before PR #{dep['after']} — evidence: `{evidence}`{suffix}")
    lines.append("")

    lines.extend(["## Independent PRs", ""])
    if report["independent_prs"]:
        lines.append(", ".join(f"PR #{number}" for number in report["independent_prs"]))
    else:
        lines.append("None.")
    lines.append("")

    lines.extend(["## Warnings and stop conditions", ""])
    if not report["warnings"] and not report["errors"]:
        lines.append("None.")
    else:
        for warning in report["warnings"]:
            level = "BLOCKING" if warning["blocking"] else "warning"
            lines.append(f"- `{warning['code']}` ({level}) — {warning['message']}")
        for error in report["errors"]:
            lines.append(f"- `INCOMPLETE_EVIDENCE` — {error}")
    lines.append("")

    lines.extend(["## PR inventory", ""])
    for pr in report["prs"]:
        readiness = ", ".join(
            value for value in [
                "draft" if pr["is_draft"] else None,
                pr["merge_state_status"],
                pr["mergeable"],
            ] if value
        ) or "not evaluated"
        lines.append(
            f"- [PR #{pr['number']}]({pr['url']}) `{pr['head_ref_name']}` → `{pr['base_ref_name']}`; "
            f"head `{(pr['effective_head_oid'] or pr['head_ref_oid'])[:12]}`; {readiness}"
        )
    lines.append("")
    lines.extend([
        "## Required next step",
        "",
        "After any merge, retarget, rebase, or force-push, fetch again and rerun this check before acting on the next wave.",
    ])
    return "\n".join(lines) + "\n"


def analyze(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    cwd = Path(args.cwd).resolve()
    repo_root = require_git_repo(cwd)
    repository = resolve_repository(repo_root, args.repo)
    repository_name = str(repository["nameWithOwner"])
    repository_owner = repository_name.split("/", 1)[0]
    remote = select_remote(repo_root, repository, args.remote)
    selected_numbers = set(args.pr or [])
    prs, all_open_prs = query_open_prs(
        repo_root,
        repository_name,
        selected_numbers,
        args.exclude_drafts,
        args.max_prs,
    )

    warnings: list[WarningItem] = []
    errors: list[str] = []
    temp_refs: list[str] = []
    base_cache: dict[str, tuple[str | None, str | None]] = {}

    if selected_numbers:
        all_base_repo_heads: dict[str, list[PullRequest]] = defaultdict(list)
        for open_pr in all_open_prs:
            if open_pr.head_owner and open_pr.head_owner.lower() == repository_owner.lower():
                all_base_repo_heads[open_pr.head_ref_name].append(open_pr)
        selected_set = {pr.number for pr in prs}
        for selected_pr in prs:
            parents = [
                parent for parent in all_base_repo_heads.get(selected_pr.base_ref_name, [])
                if parent.number != selected_pr.number and parent.number not in selected_set
            ]
            if parents:
                warnings.append(WarningItem(
                    code="SELECTED_SUBSET_OMITS_PARENT",
                    message=(
                        f"Selected PR #{selected_pr.number} targets '{selected_pr.base_ref_name}', owned by omitted open "
                        f"PR(s) {', '.join(f'#{parent.number}' for parent in parents)}. Analyze the complete stack."
                    ),
                    blocking=True,
                    pr_numbers=[selected_pr.number] + sorted(parent.number for parent in parents),
                ))

    try:
        for pr in prs:
            if args.no_fetch:
                pr.effective_head_oid = pr.head_ref_oid if git_object_exists(repo_root, pr.head_ref_oid) else None
                pr.effective_base_oid = pr.base_ref_oid if git_object_exists(repo_root, pr.base_ref_oid) else None
            else:
                head_ref = f"refs/merge-order-check/pr/{pr.number}"
                temp_refs.append(head_ref)
                ok, oid, detail = fetch_ref(repo_root, remote, f"refs/pull/{pr.number}/head", head_ref)
                if ok:
                    pr.effective_head_oid = oid
                else:
                    errors.append(f"PR #{pr.number} head fetch failed: {detail}")

                if pr.base_ref_name not in base_cache:
                    base_ref = f"refs/merge-order-check/base/{pr.base_ref_name}"
                    temp_refs.append(base_ref)
                    base_ok, base_oid, base_detail = fetch_ref(
                        repo_root, remote, f"refs/heads/{pr.base_ref_name}", base_ref
                    )
                    base_cache[pr.base_ref_name] = (base_oid if base_ok else None, base_detail)
                pr.effective_base_oid, base_detail = base_cache[pr.base_ref_name]
                if not pr.effective_base_oid:
                    errors.append(f"PR #{pr.number} base '{pr.base_ref_name}' fetch failed: {base_detail}")

            pr.head_resolved = bool(pr.effective_head_oid and git_object_exists(repo_root, pr.effective_head_oid))
            pr.base_resolved = bool(pr.effective_base_oid and git_object_exists(repo_root, pr.effective_base_oid))
            if not pr.head_resolved:
                errors.append(f"PR #{pr.number} head object {pr.head_ref_oid or '<missing>'} is unavailable.")
            if not pr.base_resolved:
                errors.append(f"PR #{pr.number} base object {pr.base_ref_oid or '<missing>'} is unavailable.")
            if pr.effective_head_oid and pr.head_ref_oid and pr.effective_head_oid != pr.head_ref_oid:
                warnings.append(WarningItem(
                    code="HEAD_CHANGED_DURING_COLLECTION",
                    message=(
                        f"PR #{pr.number} GitHub head {pr.head_ref_oid[:12]} differs from fetched head "
                        f"{pr.effective_head_oid[:12]}; rerun against a stable snapshot."
                    ),
                    blocking=True,
                    pr_numbers=[pr.number],
                ))
            if pr.effective_base_oid and pr.base_ref_oid and pr.effective_base_oid != pr.base_ref_oid:
                warnings.append(WarningItem(
                    code="BASE_CHANGED_DURING_COLLECTION",
                    message=(
                        f"PR #{pr.number} GitHub base {pr.base_ref_oid[:12]} differs from fetched base "
                        f"{pr.effective_base_oid[:12]}; rerun against a stable snapshot."
                    ),
                    blocking=True,
                    pr_numbers=[pr.number],
                ))

        oid_groups: dict[str, list[int]] = defaultdict(list)
        for pr in prs:
            if pr.head_resolved and pr.effective_head_oid:
                oid_groups[pr.effective_head_oid].append(pr.number)
        for oid, numbers in oid_groups.items():
            if len(numbers) > 1:
                warnings.append(WarningItem(
                    code="DUPLICATE_HEAD_OID",
                    message=f"PRs {', '.join(f'#{n}' for n in numbers)} share head {oid[:12]}; order is ambiguous.",
                    blocking=True,
                    pr_numbers=sorted(numbers),
                ))

        dependencies: dict[tuple[int, int], Dependency] = {}
        comparable_prs = [pr for pr in prs if pr.head_resolved and pr.effective_head_oid]
        for index, left in enumerate(comparable_prs):
            for right in comparable_prs[index + 1:]:
                if left.effective_head_oid == right.effective_head_oid:
                    continue
                left_before = is_ancestor(repo_root, left.effective_head_oid or "", right.effective_head_oid or "")
                right_before = is_ancestor(repo_root, right.effective_head_oid or "", left.effective_head_oid or "")
                if left_before is None or right_before is None:
                    errors.append(f"Could not compare ancestry for PR #{left.number} and PR #{right.number}.")
                    continue
                if left_before:
                    add_dependency(dependencies, left.number, right.number, "ancestry")
                elif right_before:
                    add_dependency(dependencies, right.number, left.number, "ancestry")

        base_repo_heads: dict[str, list[PullRequest]] = defaultdict(list)
        for pr in prs:
            if pr.head_owner and pr.head_owner.lower() == repository_owner.lower():
                base_repo_heads[pr.head_ref_name].append(pr)
        for downstream in prs:
            candidates = base_repo_heads.get(downstream.base_ref_name, [])
            if len(candidates) > 1:
                warnings.append(WarningItem(
                    code="AMBIGUOUS_BASE_TARGET",
                    message=(
                        f"PR #{downstream.number} targets '{downstream.base_ref_name}', which matches multiple open PR heads."
                    ),
                    blocking=True,
                    pr_numbers=[downstream.number] + sorted(pr.number for pr in candidates),
                ))
                continue
            if len(candidates) == 1:
                upstream = candidates[0]
                if upstream.number == downstream.number:
                    continue
                confirmed = (
                    upstream.head_resolved and downstream.head_resolved and
                    upstream.effective_head_oid and downstream.effective_head_oid and
                    is_ancestor(repo_root, upstream.effective_head_oid, downstream.effective_head_oid) is True
                )
                add_dependency(
                    dependencies,
                    upstream.number,
                    downstream.number,
                    "base_target",
                    blocking_mismatch=not confirmed,
                )
                if not confirmed:
                    warnings.append(WarningItem(
                        code="DECLARED_ANCESTRY_MISMATCH",
                        message=(
                            f"PR #{downstream.number} targets branch '{downstream.base_ref_name}' from PR "
                            f"#{upstream.number}, but the upstream head is not an ancestor of the downstream head."
                        ),
                        blocking=True,
                        pr_numbers=[upstream.number, downstream.number],
                    ))

        for pr in prs:
            if pr.head_resolved and pr.base_resolved and pr.effective_head_oid and pr.effective_base_oid:
                base_in_head = is_ancestor(repo_root, pr.effective_base_oid, pr.effective_head_oid)
                if base_in_head is False:
                    warnings.append(WarningItem(
                        code="BASE_NOT_ANCESTOR_OF_HEAD",
                        message=(
                            f"PR #{pr.number} base {pr.effective_base_oid[:12]} is not an ancestor of head "
                            f"{pr.effective_head_oid[:12]}; the branch may be stale, force-pushed, or malformed."
                        ),
                        blocking=False,
                        pr_numbers=[pr.number],
                    ))
                elif base_in_head is None:
                    errors.append(f"Could not verify base ancestry for PR #{pr.number}.")

        mark_transitive_edges(dependencies)
        node_set = {pr.number for pr in prs}
        direct_dependencies = [dep for dep in dependencies.values() if dep.direct]
        components_data: list[dict[str, Any]] = []
        independent: list[int] = []
        cycle_nodes_global: set[int] = set()
        for component in weak_components(node_set, direct_dependencies):
            waves, cycle_nodes = topo_waves(component, direct_dependencies)
            cycle_nodes_global.update(cycle_nodes)
            if len(component) == 1:
                independent.extend(component)
            components_data.append({
                "pr_numbers": sorted(component),
                "waves": waves,
                "cycle_nodes": cycle_nodes,
            })
        components_data.sort(key=lambda item: item["pr_numbers"])

        global_waves, global_cycle = topo_waves(node_set, direct_dependencies)
        cycle_nodes_global.update(global_cycle)
        if cycle_nodes_global:
            numbers = sorted(cycle_nodes_global)
            warnings.append(WarningItem(
                code="DEPENDENCY_CYCLE",
                message=f"Dependency cycle or unresolved graph contains {', '.join(f'#{n}' for n in numbers)}.",
                blocking=True,
                pr_numbers=numbers,
            ))

        report_status = status_from(warnings, errors)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": report_status,
            "repository": repository_name,
            "repository_url": str(repository["url"]),
            "remote": remote,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "fetch_performed": not args.no_fetch,
            "selected_pr_numbers": sorted(selected_numbers),
            "prs": [pr.as_dict() for pr in prs],
            "dependencies": [dep.as_dict() for dep in sorted(
                dependencies.values(), key=lambda item: (item.before, item.after)
            )],
            "components": components_data,
            "global_waves": global_waves,
            "independent_prs": sorted(independent),
            "warnings": [warning.as_dict() for warning in warnings],
            "errors": errors,
        }
        if report_status == "ok":
            return report, EXIT_OK
        if report_status == "blocked":
            return report, EXIT_BLOCKED
        return report, EXIT_INCOMPLETE
    finally:
        if not args.keep_refs:
            delete_refs(repo_root, temp_refs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check merge order of open stacked GitHub PRs from Git ancestry.",
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Path inside the target Git worktree.")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO or HOST/OWNER/REPO form.")
    parser.add_argument("--remote", help="Local Git remote for the base repository.")
    parser.add_argument("--pr", type=int, action="append", help="Analyze only this open PR number; repeatable.")
    parser.add_argument("--exclude-drafts", action="store_true", help="Exclude draft PRs from analysis.")
    parser.add_argument("--no-fetch", action="store_true", help="Use only commit objects already present locally.")
    parser.add_argument("--keep-refs", action="store_true", help="Keep temporary refs under refs/merge-order-check/.")
    parser.add_argument("--max-prs", type=int, default=200, help="Maximum open PRs to query; default 200.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--json-out", help="Write deterministic JSON report to this path.")
    return parser


def write_json(path: str, report: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_prs < 1:
        parser.error("--max-prs must be at least 1")
    try:
        report, exit_code = analyze(args)
    except AnalyzerError as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "repository": args.repo,
            "repository_url": None,
            "remote": args.remote,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "fetch_performed": False,
            "selected_pr_numbers": sorted(set(args.pr or [])),
            "prs": [],
            "dependencies": [],
            "components": [],
            "global_waves": [],
            "independent_prs": [],
            "warnings": [],
            "errors": [str(exc)],
        }
        exit_code = exc.exit_code

    if args.json_out:
        write_json(args.json_out, report)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown_report(report), end="")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

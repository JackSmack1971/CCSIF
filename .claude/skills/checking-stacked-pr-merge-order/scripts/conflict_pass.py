#!/usr/bin/env python3
"""Plan, diagnose, resolve, verify, and publish stacked-PR conflict fixes.

The default strategy merges each PR's exact base commit into its exact head commit
inside an isolated worktree. It never modifies the caller's working tree. Publishing
requires explicit approval and an exact remote-OID lease.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_PREREQUISITE = 2
EXIT_INVALID = 3
EXIT_CONFLICTS = 10
EXIT_BLOCKED = 11
EXIT_VALIDATION = 12
EXIT_PUBLISH = 13
MAX_CAPTURE = 20000


class ConflictPassError(RuntimeError):
    def __init__(self, message: str, exit_code: int = EXIT_INVALID) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise ConflictPassError(f"Required executable not found: {command[0]}", EXIT_PREREQUISITE) from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ConflictPassError(f"Command failed ({' '.join(command)}): {detail}", EXIT_PREREQUISITE)
    return result


def require_repo(cwd: Path) -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if result.returncode != 0:
        raise ConflictPassError("Run this command inside the target Git worktree.", EXIT_PREREQUISITE)
    return Path(result.stdout.strip()).resolve()


def common_git_dir(repo_root: Path) -> Path:
    result = run(["git", "rev-parse", "--git-common-dir"], cwd=repo_root, check=True)
    value = Path(result.stdout.strip())
    if not value.is_absolute():
        value = (repo_root / value).resolve()
    return value


def git_oid(repo_root: Path, value: str) -> str | None:
    result = run(["git", "rev-parse", "--verify", f"{value}^{{commit}}"], cwd=repo_root)
    return result.stdout.strip() if result.returncode == 0 else None


def is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=repo_root)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ConflictPassError(
        f"Unable to compare ancestry between {ancestor[:12]} and {descendant[:12]}.",
        EXIT_VALIDATION,
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConflictPassError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConflictPassError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConflictPassError(f"Expected a JSON object in {path}.")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_hash(data: dict[str, Any], excluded: Iterable[str] = ()) -> str:
    excluded_set = set(excluded)
    material = {key: value for key, value in data.items() if key not in excluded_set}
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def short_capture(value: str) -> str:
    value = value.strip()
    if len(value) <= MAX_CAPTURE:
        return value
    return value[:MAX_CAPTURE] + "\n...[truncated]"


def remove_worktree(repo_root: Path, path: Path) -> None:
    if path.exists():
        run(["git", "worktree", "remove", "--force", str(path)], cwd=repo_root)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    run(["git", "worktree", "prune"], cwd=repo_root)


def merge_in_progress(worktree: Path) -> bool:
    result = run(["git", "rev-parse", "--verify", "MERGE_HEAD"], cwd=worktree)
    return result.returncode == 0


def abort_merge(worktree: Path) -> None:
    if merge_in_progress(worktree):
        run(["git", "merge", "--abort"], cwd=worktree)


def parse_unmerged(worktree: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["git", "ls-files", "-u", "-z"],
        cwd=str(worktree),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ConflictPassError(f"Unable to inspect unmerged index entries: {detail}", EXIT_VALIDATION)
    grouped: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        meta, raw_path = raw.split(b"\t", 1)
        mode, oid, stage_text = meta.decode("ascii").split(" ")
        path = raw_path.decode("utf-8", errors="surrogateescape")
        grouped[path][int(stage_text)] = {"mode": mode, "oid": oid}

    records: list[dict[str, Any]] = []
    for path in sorted(grouped):
        stages = grouped[path]
        mask = set(stages)
        if mask == {1, 2, 3}:
            kind = "content_or_mode"
        elif mask == {2, 3}:
            kind = "add_add"
        elif mask == {1, 2}:
            kind = "modified_in_head_deleted_in_base"
        elif mask == {1, 3}:
            kind = "deleted_in_head_modified_in_base"
        elif mask == {2}:
            kind = "head_only"
        elif mask == {3}:
            kind = "base_only"
        else:
            kind = "complex_or_rename"
        records.append({
            "path": path,
            "type": kind,
            "stages": {str(stage): values for stage, values in sorted(stages.items())},
        })
    return records


def merge_command(base_oid: str, hooks_dir: Path) -> list[str]:
    return [
        "git",
        "-c", f"core.hooksPath={hooks_dir}",
        "-c", "merge.conflictStyle=zdiff3",
        "merge", "--no-commit", "--no-ff", "--no-edit", base_oid,
    ]


def simulate_merge(repo_root: Path, head_oid: str, base_oid: str) -> dict[str, Any]:
    if not git_oid(repo_root, head_oid) or not git_oid(repo_root, base_oid):
        return {
            "status": "error",
            "conflicts": [],
            "messages": "Required head or base object is unavailable locally.",
        }
    git_dir = common_git_dir(repo_root)
    simulation_root = git_dir / "stack-conflict-sim"
    simulation_root.mkdir(parents=True, exist_ok=True)
    operation_dir = Path(tempfile.mkdtemp(prefix="run-", dir=simulation_root))
    worktree = operation_dir / "worktree"
    hooks_dir = operation_dir / "empty-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    added = False
    try:
        add_result = run(["git", "worktree", "add", "--detach", "--quiet", str(worktree), head_oid], cwd=repo_root)
        if add_result.returncode != 0:
            detail = add_result.stderr.strip() or add_result.stdout.strip()
            return {"status": "error", "conflicts": [], "messages": f"Worktree creation failed: {detail}"}
        added = True
        merge_result = run(merge_command(base_oid, hooks_dir), cwd=worktree)
        messages = short_capture("\n".join(part for part in (merge_result.stdout, merge_result.stderr) if part))
        conflicts = parse_unmerged(worktree)
        if merge_result.returncode == 0 and not conflicts:
            status = "clean"
        elif conflicts or merge_in_progress(worktree):
            status = "conflicted"
        else:
            status = "error"
            if not messages:
                messages = f"git merge exited with {merge_result.returncode} without a diagnosable merge state."
        return {"status": status, "conflicts": conflicts, "messages": messages}
    finally:
        if added:
            abort_merge(worktree)
            remove_worktree(repo_root, worktree)
        else:
            shutil.rmtree(worktree, ignore_errors=True)
        shutil.rmtree(operation_dir, ignore_errors=True)


def pr_map(analysis: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in analysis.get("prs", []):
        if isinstance(item, dict) and isinstance(item.get("number"), int):
            result[item["number"]] = item
    return result


def component_map(analysis: dict[str, Any]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for index, component in enumerate(analysis.get("components", []), start=1):
        if not isinstance(component, dict):
            continue
        for number in component.get("pr_numbers", []):
            if isinstance(number, int):
                mapping[number] = index
    return mapping


def direct_predecessors(analysis: dict[str, Any]) -> dict[int, list[int]]:
    predecessors: dict[int, list[int]] = defaultdict(list)
    for dep in analysis.get("dependencies", []):
        if not isinstance(dep, dict) or not dep.get("direct", False):
            continue
        before, after = dep.get("before"), dep.get("after")
        if isinstance(before, int) and isinstance(after, int):
            predecessors[after].append(before)
    return {key: sorted(set(value)) for key, value in predecessors.items()}


def build_plan(repo_root: Path, analysis: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if analysis.get("status") != "ok":
        raise ConflictPassError(
            f"Merge-order analysis status must be 'ok', got {analysis.get('status')!r}.",
            EXIT_BLOCKED,
        )
    prs = pr_map(analysis)
    waves = analysis.get("global_waves")
    if not isinstance(waves, list):
        raise ConflictPassError("Analysis lacks global_waves.", EXIT_BLOCKED)
    predecessors = direct_predecessors(analysis)
    components = component_map(analysis)
    actions: list[dict[str, Any]] = []
    errors: list[str] = []

    for wave_index, wave in enumerate(waves, start=1):
        if not isinstance(wave, list):
            raise ConflictPassError("Analysis contains an invalid wave.", EXIT_BLOCKED)
        for number in sorted(value for value in wave if isinstance(value, int)):
            pr = prs.get(number)
            if not pr:
                errors.append(f"PR #{number} is present in waves but absent from PR records.")
                continue
            head_oid = pr.get("effective_head_oid")
            base_oid = pr.get("effective_base_oid")
            if not isinstance(head_oid, str) or not isinstance(base_oid, str):
                errors.append(f"PR #{number} lacks resolved head/base OIDs.")
                continue
            simulation = simulate_merge(repo_root, head_oid, base_oid)
            action = {
                "pr_number": number,
                "component": components.get(number),
                "wave": wave_index,
                "predecessors": predecessors.get(number, []),
                "head_ref_name": pr.get("head_ref_name"),
                "base_ref_name": pr.get("base_ref_name"),
                "head_oid": head_oid,
                "base_oid": base_oid,
                "head_repository": pr.get("head_repository"),
                "is_cross_repository": bool(pr.get("is_cross_repository")),
                "preflight": simulation["status"],
                "conflicts": simulation["conflicts"],
                "messages": simulation["messages"],
                "eligible": False,
            }
            if simulation["status"] == "error":
                errors.append(f"PR #{number} conflict simulation failed: {simulation['messages']}")
            actions.append(action)

    conflicted = [action for action in actions if action["preflight"] == "conflicted"]
    if conflicted:
        conflicted[0]["eligible"] = True
    status = "blocked" if errors else ("conflicts" if conflicted else "clean")
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "stack_conflict_resolution_plan",
        "status": status,
        "generated_at": utc_now(),
        "repository": analysis.get("repository"),
        "repository_url": analysis.get("repository_url"),
        "remote": analysis.get("remote"),
        "strategy": "merge_exact_base_into_exact_head",
        "analysis_sha256": canonical_hash(analysis),
        "actions": actions,
        "blocking_errors": errors,
        "definition_of_done": {
            "analysis_status": "ok",
            "conflict_plan_status": "clean",
            "all_live_head_and_base_oids_match_snapshot": True,
        },
    }
    plan["plan_sha256"] = canonical_hash(plan, {"plan_sha256"})
    if status == "clean":
        return plan, EXIT_OK
    if status == "conflicts":
        return plan, EXIT_CONFLICTS
    return plan, EXIT_BLOCKED


def query_live_pr(repo_root: Path, repository: str, number: int) -> dict[str, Any]:
    fields = (
        "number,state,headRefName,headRefOid,baseRefName,baseRefOid,"
        "headRepository,headRepositoryOwner,isCrossRepository,maintainerCanModify"
    )
    result = run(
        ["gh", "pr", "view", str(number), "--repo", repository, "--json", fields],
        cwd=repo_root,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown GitHub CLI error"
        raise ConflictPassError(f"Unable to query PR #{number}: {detail}", EXIT_PUBLISH)
    try:
        item = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConflictPassError(f"GitHub returned invalid JSON for PR #{number}.", EXIT_PUBLISH) from exc
    if not isinstance(item, dict):
        raise ConflictPassError(f"GitHub returned an invalid PR record for #{number}.", EXIT_PUBLISH)
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
    item["headRepositoryNameWithOwner"] = head_repository
    return item


def verify_live_snapshot(action: dict[str, Any], live: dict[str, Any]) -> None:
    expected = {
        "headRefName": action["head_ref_name"],
        "headRefOid": action["head_oid"],
        "baseRefName": action["base_ref_name"],
        "baseRefOid": action["base_oid"],
    }
    differences = [
        f"{key}: expected {value}, live {live.get(key)}"
        for key, value in expected.items()
        if live.get(key) != value
    ]
    if live.get("state") != "OPEN":
        differences.append(f"state: expected OPEN, live {live.get('state')}")
    if differences:
        raise ConflictPassError(
            "PR snapshot changed; discard the plan and rerun analysis: " + "; ".join(differences),
            EXIT_BLOCKED,
        )


def find_action(plan: dict[str, Any], number: int) -> dict[str, Any]:
    for action in plan.get("actions", []):
        if isinstance(action, dict) and action.get("pr_number") == number:
            return action
    raise ConflictPassError(f"PR #{number} is not present in the plan.")


def validate_plan_hash(plan: dict[str, Any], approval: str) -> None:
    actual = canonical_hash(plan, {"plan_sha256"})
    stored = plan.get("plan_sha256")
    if stored != actual:
        raise ConflictPassError("Plan hash is invalid; the plan may have been edited.", EXIT_BLOCKED)
    if approval != actual:
        raise ConflictPassError(
            f"Plan approval does not match. Review the plan and pass --approve-plan {actual}.",
            EXIT_BLOCKED,
        )


def prepare_resolution(
    repo_root: Path,
    plan: dict[str, Any],
    action: dict[str, Any],
    approval: str,
    state_root: Path | None,
) -> dict[str, Any]:
    validate_plan_hash(plan, approval)
    if plan.get("status") != "conflicts":
        raise ConflictPassError("Only a plan with status 'conflicts' can be prepared.", EXIT_BLOCKED)
    if not action.get("eligible"):
        raise ConflictPassError(
            f"PR #{action['pr_number']} is deferred. Resolve the currently eligible PR, then rerun the full analysis.",
            EXIT_BLOCKED,
        )
    repository = plan.get("repository")
    if not isinstance(repository, str):
        raise ConflictPassError("Plan lacks a repository identifier.", EXIT_BLOCKED)
    live = query_live_pr(repo_root, repository, int(action["pr_number"]))
    verify_live_snapshot(action, live)

    root = state_root or (common_git_dir(repo_root) / "stack-conflict-resolution")
    operation_dir = root / f"pr-{action['pr_number']}-{str(action['head_oid'])[:12]}"
    worktree = operation_dir / "worktree"
    state_path = operation_dir / "state.json"
    record_path = operation_dir / "resolution-record.json"
    if operation_dir.exists():
        raise ConflictPassError(f"Resolution operation already exists: {operation_dir}", EXIT_BLOCKED)
    operation_dir.mkdir(parents=True)
    hooks_dir = operation_dir / "empty-hooks"
    hooks_dir.mkdir()

    add_result = run(
        ["git", "worktree", "add", "--detach", "--quiet", str(worktree), str(action["head_oid"])],
        cwd=repo_root,
    )
    if add_result.returncode != 0:
        shutil.rmtree(operation_dir, ignore_errors=True)
        detail = add_result.stderr.strip() or add_result.stdout.strip()
        raise ConflictPassError(f"Unable to create resolution worktree: {detail}", EXIT_PREREQUISITE)
    merge_result = run(merge_command(str(action["base_oid"]), hooks_dir), cwd=worktree)
    conflicts = parse_unmerged(worktree)
    if merge_result.returncode == 0 and not conflicts:
        abort_merge(worktree)
        remove_worktree(repo_root, worktree)
        shutil.rmtree(operation_dir, ignore_errors=True)
        raise ConflictPassError("The merge is now clean; discard the stale plan and rerun the full pass.", EXIT_BLOCKED)
    if not conflicts:
        abort_merge(worktree)
        remove_worktree(repo_root, worktree)
        shutil.rmtree(operation_dir, ignore_errors=True)
        detail = merge_result.stderr.strip() or merge_result.stdout.strip()
        raise ConflictPassError(f"Merge preparation failed without indexed conflicts: {detail}", EXIT_BLOCKED)

    planned_paths = {item.get("path") for item in action.get("conflicts", []) if isinstance(item, dict)}
    current_paths = {item["path"] for item in conflicts}
    if planned_paths != current_paths:
        abort_merge(worktree)
        remove_worktree(repo_root, worktree)
        shutil.rmtree(operation_dir, ignore_errors=True)
        raise ConflictPassError("Conflict set changed since planning; rerun the full pass.", EXIT_BLOCKED)

    state = {
        "schema_version": SCHEMA_VERSION,
        "kind": "stack_conflict_resolution_state",
        "status": "prepared",
        "created_at": utc_now(),
        "repository": repository,
        "repository_url": plan.get("repository_url"),
        "remote": plan.get("remote"),
        "plan_sha256": plan["plan_sha256"],
        "pr_number": action["pr_number"],
        "head_ref_name": action["head_ref_name"],
        "base_ref_name": action["base_ref_name"],
        "head_oid": action["head_oid"],
        "base_oid": action["base_oid"],
        "head_repository": action.get("head_repository") or live.get("headRepositoryNameWithOwner"),
        "is_cross_repository": bool(action.get("is_cross_repository")),
        "worktree_path": str(worktree.resolve()),
        "state_path": str(state_path.resolve()),
        "resolution_record_path": str(record_path.resolve()),
        "conflicts": conflicts,
        "merge_messages": short_capture("\n".join(
            part for part in (merge_result.stdout, merge_result.stderr) if part
        )),
    }
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": "stack_conflict_resolution_record",
        "pr_number": action["pr_number"],
        "plan_sha256": plan["plan_sha256"],
        "conflict_resolutions": [
            {
                "path": item["path"],
                "type": item["type"],
                "diagnosis": "",
                "resolution": "",
                "evidence": [],
            }
            for item in conflicts
        ],
        "validation_commands": [],
        "validation_waiver": "",
        "allow_marker_paths": [],
    }
    write_json(state_path, state)
    write_json(record_path, record)
    return state


def marker_findings(path: Path) -> list[int]:
    try:
        content = path.read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return []
    if b"\x00" in content:
        return []
    text = content.decode("utf-8", errors="replace")
    pattern = re.compile(r"^(?:<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)(?:\s|$)", re.MULTILINE)
    return [text.count("\n", 0, match.start()) + 1 for match in pattern.finditer(text)]


def validate_resolution_record(state: dict[str, Any], record: dict[str, Any], worktree: Path) -> None:
    if record.get("pr_number") != state.get("pr_number") or record.get("plan_sha256") != state.get("plan_sha256"):
        raise ConflictPassError("Resolution record does not match the prepared state.", EXIT_VALIDATION)
    rows = record.get("conflict_resolutions")
    if not isinstance(rows, list):
        raise ConflictPassError("resolution-record conflict_resolutions must be a list.", EXIT_VALIDATION)
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            by_path[row["path"]] = row
    required = {item["path"] for item in state.get("conflicts", []) if isinstance(item, dict)}
    missing = sorted(required - set(by_path))
    if missing:
        raise ConflictPassError("Resolution record omits conflicted paths: " + ", ".join(missing), EXIT_VALIDATION)
    incomplete = [
        path for path in sorted(required)
        if not str(by_path[path].get("diagnosis", "")).strip()
        or not str(by_path[path].get("resolution", "")).strip()
    ]
    if incomplete:
        raise ConflictPassError(
            "Diagnosis and resolution rationale are required for: " + ", ".join(incomplete),
            EXIT_VALIDATION,
        )
    allowed = set(record.get("allow_marker_paths") or [])
    marker_errors: list[str] = []
    for relative in sorted(required - allowed):
        lines = marker_findings(worktree / relative)
        if lines:
            marker_errors.append(f"{relative}:{','.join(map(str, lines))}")
    if marker_errors:
        raise ConflictPassError(
            "Conflict markers remain in resolved files: " + "; ".join(marker_errors),
            EXIT_VALIDATION,
        )


def run_validation_commands(worktree: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    commands = record.get("validation_commands")
    if not isinstance(commands, list):
        raise ConflictPassError("validation_commands must be a list of argv arrays.", EXIT_VALIDATION)
    if not commands:
        waiver = str(record.get("validation_waiver") or "").strip()
        if len(waiver) < 20:
            raise ConflictPassError(
                "Provide at least one validation command or a specific validation_waiver of 20+ characters.",
                EXIT_VALIDATION,
            )
        return []
    results: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
            raise ConflictPassError(f"Validation command #{index} must be a non-empty string array.", EXIT_VALIDATION)
        result = run(command, cwd=worktree)
        entry = {
            "argv": command,
            "exit_code": result.returncode,
            "stdout": short_capture(result.stdout),
            "stderr": short_capture(result.stderr),
        }
        results.append(entry)
        if result.returncode != 0:
            raise ConflictPassError(
                f"Validation command #{index} failed with exit {result.returncode}: {' '.join(command)}",
                EXIT_VALIDATION,
            )
    return results


def verify_and_commit(state_path: Path, record_path: Path | None, commit_message: str) -> dict[str, Any]:
    state = load_json(state_path)
    if state.get("status") != "prepared":
        raise ConflictPassError("State must be 'prepared' before verification.", EXIT_VALIDATION)
    worktree = Path(str(state.get("worktree_path"))).resolve()
    if not worktree.is_dir():
        raise ConflictPassError(f"Resolution worktree is missing: {worktree}", EXIT_VALIDATION)
    current_head = git_oid(worktree, "HEAD")
    if current_head != state.get("head_oid"):
        raise ConflictPassError("HEAD changed before verification; do not commit manually.", EXIT_VALIDATION)
    merge_head = git_oid(worktree, "MERGE_HEAD")
    if merge_head != state.get("base_oid"):
        raise ConflictPassError("MERGE_HEAD does not match the planned base OID.", EXIT_VALIDATION)
    unmerged = parse_unmerged(worktree)
    if unmerged:
        raise ConflictPassError(
            "Unresolved paths remain: " + ", ".join(item["path"] for item in unmerged),
            EXIT_VALIDATION,
        )
    record = load_json(record_path or Path(str(state.get("resolution_record_path"))))
    validate_resolution_record(state, record, worktree)

    unstaged = run(["git", "diff", "--quiet"], cwd=worktree)
    if unstaged.returncode != 0:
        raise ConflictPassError("Unstaged tracked changes remain; stage the intended resolution first.", EXIT_VALIDATION)
    status_result = run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=worktree, check=True)
    untracked = [line for line in status_result.stdout.splitlines() if line.startswith("?? ")]
    if untracked:
        raise ConflictPassError("Untracked files remain in the resolution worktree: " + ", ".join(untracked), EXIT_VALIDATION)

    validation_results = run_validation_commands(worktree, record)
    post_validation_diff = run(["git", "diff", "--quiet"], cwd=worktree)
    post_validation_status = run(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=worktree, check=True
    )
    post_untracked = [line for line in post_validation_status.stdout.splitlines() if line.startswith("?? ")]
    if post_validation_diff.returncode != 0 or post_untracked:
        raise ConflictPassError(
            "Validation commands changed tracked or untracked files; inspect, stage intentional changes, and rerun verification.",
            EXIT_VALIDATION,
        )
    if not commit_message.strip():
        raise ConflictPassError("A non-empty merge commit message is required.", EXIT_VALIDATION)
    commit_result = run(["git", "commit", "-m", commit_message], cwd=worktree)
    if commit_result.returncode != 0:
        detail = commit_result.stderr.strip() or commit_result.stdout.strip()
        raise ConflictPassError(f"Merge commit failed: {detail}", EXIT_VALIDATION)
    new_oid = git_oid(worktree, "HEAD")
    if not new_oid:
        raise ConflictPassError("Unable to resolve the new merge commit OID.", EXIT_VALIDATION)
    parents_result = run(["git", "rev-list", "--parents", "-n", "1", new_oid], cwd=worktree, check=True)
    tokens = parents_result.stdout.strip().split()
    parents = tokens[1:]
    if len(parents) != 2 or parents[0] != state.get("head_oid") or parents[1] != state.get("base_oid"):
        raise ConflictPassError("Created commit does not have the exact planned head and base parents.", EXIT_VALIDATION)

    state.update({
        "status": "verified",
        "verified_at": utc_now(),
        "resolution_commit_oid": new_oid,
        "commit_message": commit_message,
        "validation_results": validation_results,
        "resolution_record_sha256": canonical_hash(record),
    })
    write_json(state_path, state)
    return state


def repo_path_from_url(value: str) -> str | None:
    if not value:
        return None
    if "://" in value:
        parsed = urlparse(value)
        path = parsed.path.strip("/")
    else:
        match = re.match(r"^(?:[^@]+@)?[^:]+:(.+)$", value)
        path = match.group(1).strip("/") if match else value.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def matching_remote(repo_root: Path, repository: str) -> str | None:
    remotes = run(["git", "remote"], cwd=repo_root, check=True).stdout.split()
    matches: list[str] = []
    for remote in remotes:
        result = run(["git", "remote", "get-url", "--push", remote], cwd=repo_root)
        if result.returncode == 0 and repo_path_from_url(result.stdout.strip()) == repository:
            matches.append(remote)
    if len(matches) == 1:
        return matches[0]
    for preferred in ("origin", "upstream"):
        if preferred in matches:
            return preferred
    return None


def construct_https_target(repository_url: str | None, head_repository: str | None) -> str | None:
    if not repository_url or not head_repository:
        return None
    parsed = urlparse(repository_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/{head_repository}.git"


def publish_resolution(
    repo_root: Path,
    state_path: Path,
    approval: str,
    push_target: str | None,
) -> dict[str, Any]:
    state = load_json(state_path)
    if state.get("status") != "verified":
        raise ConflictPassError("State must be 'verified' before publishing.", EXIT_PUBLISH)
    new_oid = str(state.get("resolution_commit_oid") or "")
    if approval != new_oid:
        raise ConflictPassError(
            f"Push approval does not match. Review the verified commit and pass --approve-push {new_oid}.",
            EXIT_PUBLISH,
        )
    repository = str(state.get("repository") or "")
    live = query_live_pr(repo_root, repository, int(state["pr_number"]))
    action = {
        "head_ref_name": state["head_ref_name"],
        "head_oid": state["head_oid"],
        "base_ref_name": state["base_ref_name"],
        "base_oid": state["base_oid"],
    }
    verify_live_snapshot(action, live)
    if not is_ancestor(repo_root, str(state["head_oid"]), new_oid):
        raise ConflictPassError("Resolution commit does not descend from the original PR head.", EXIT_PUBLISH)
    if not is_ancestor(repo_root, str(state["base_oid"]), new_oid):
        raise ConflictPassError("Resolution commit does not contain the exact planned base.", EXIT_PUBLISH)

    head_repository = live.get("headRepositoryNameWithOwner") or state.get("head_repository")
    target = push_target or matching_remote(repo_root, str(head_repository or ""))
    if not target and not state.get("is_cross_repository"):
        target = str(state.get("remote") or "") or None
    if not target:
        target = construct_https_target(state.get("repository_url"), head_repository)
    if not target:
        raise ConflictPassError(
            "Unable to determine the PR head repository push target; pass --push-target explicitly.",
            EXIT_PUBLISH,
        )
    branch = str(state["head_ref_name"])
    expected = str(state["head_oid"])
    lease = f"--force-with-lease=refs/heads/{branch}:{expected}"
    refspec = f"{new_oid}:refs/heads/{branch}"
    push_result = run(["git", "push", "--porcelain", lease, target, refspec], cwd=repo_root)
    if push_result.returncode != 0:
        detail = push_result.stderr.strip() or push_result.stdout.strip()
        raise ConflictPassError(f"Push failed without updating the PR branch: {detail}", EXIT_PUBLISH)

    after = query_live_pr(repo_root, repository, int(state["pr_number"]))
    if after.get("headRefOid") != new_oid:
        raise ConflictPassError(
            f"Push reported success but GitHub head is {after.get('headRefOid')}, expected {new_oid}.",
            EXIT_PUBLISH,
        )
    state.update({
        "status": "published",
        "published_at": utc_now(),
        "push_target": target,
        "live_head_oid_after_push": after.get("headRefOid"),
    })
    write_json(state_path, state)
    return state


def cleanup_resolution(repo_root: Path, state_path: Path, force: bool) -> dict[str, Any]:
    state = load_json(state_path)
    if state.get("status") != "published" and not force:
        raise ConflictPassError("Cleanup before publish requires --force-cleanup.", EXIT_BLOCKED)
    worktree = Path(str(state.get("worktree_path"))).resolve()
    if worktree.exists():
        abort_merge(worktree)
        remove_worktree(repo_root, worktree)
    state["worktree_removed"] = True
    state["cleaned_at"] = utc_now()
    write_json(state_path, state)
    return state


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve stacked-PR branch conflicts through approved isolated-worktree operations.",
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Path inside the target Git worktree.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Simulate every PR-to-base merge and write a reviewable plan.")
    plan.add_argument("--analysis", required=True, help="JSON report from check_merge_order.py.")
    plan.add_argument("--out", required=True, help="Output path for the conflict plan JSON.")

    prepare = subparsers.add_parser("prepare", help="Create the approved isolated conflict-resolution worktree.")
    prepare.add_argument("--plan", required=True)
    prepare.add_argument("--pr", type=int, required=True)
    prepare.add_argument("--approve-plan", required=True, help="Exact plan_sha256 shown in the reviewed plan.")
    prepare.add_argument("--state-root", help="Optional directory for operation state and worktrees.")

    verify = subparsers.add_parser("verify", help="Validate diagnosis, staged resolution, tests, and create merge commit.")
    verify.add_argument("--state", required=True)
    verify.add_argument("--record", help="Resolution record path; defaults to the path in state.json.")
    verify.add_argument("--commit-message", required=True)

    publish = subparsers.add_parser("publish", help="Push the verified merge commit with an exact-OID lease.")
    publish.add_argument("--state", required=True)
    publish.add_argument("--approve-push", required=True, help="Exact verified resolution_commit_oid.")
    publish.add_argument("--push-target", help="Explicit Git remote name or repository URL.")

    cleanup = subparsers.add_parser("cleanup", help="Remove the isolated worktree while retaining audit records.")
    cleanup.add_argument("--state", required=True)
    cleanup.add_argument("--force-cleanup", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo_root = require_repo(Path(args.cwd).resolve())
        if args.command == "plan":
            analysis = load_json(Path(args.analysis).resolve())
            plan, exit_code = build_plan(repo_root, analysis)
            write_json(Path(args.out).resolve(), plan)
            emit(plan)
            return exit_code
        if args.command == "prepare":
            plan = load_json(Path(args.plan).resolve())
            action = find_action(plan, args.pr)
            state = prepare_resolution(
                repo_root,
                plan,
                action,
                args.approve_plan,
                Path(args.state_root).resolve() if args.state_root else None,
            )
            emit(state)
            return EXIT_CONFLICTS
        if args.command == "verify":
            state = verify_and_commit(
                Path(args.state).resolve(),
                Path(args.record).resolve() if args.record else None,
                args.commit_message,
            )
            emit(state)
            return EXIT_OK
        if args.command == "publish":
            state = publish_resolution(
                repo_root,
                Path(args.state).resolve(),
                args.approve_push,
                args.push_target,
            )
            emit(state)
            return EXIT_OK
        if args.command == "cleanup":
            state = cleanup_resolution(repo_root, Path(args.state).resolve(), args.force_cleanup)
            emit(state)
            return EXIT_OK
        raise ConflictPassError(f"Unsupported command: {args.command}")
    except ConflictPassError as exc:
        emit({"status": "error", "exit_code": exc.exit_code, "message": str(exc)})
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())

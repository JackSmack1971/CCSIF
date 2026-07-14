#!/usr/bin/env python3
"""Phase 4 dynamic workflows: a static-first, allowlisted-graph engine.

This does not reinvent a planner or a graph runtime. It wraps two native
Phase 0 primitives (verified checkpoints, durable state under
`.claude/state/`) with the smallest layer that lets a declarative workflow
definition (`.claude/workflows/defs/*.json`) drive execution:

- A "planner" is bounded to `propose_next()`, which returns only the current
  node's declared `allowed_next` list. It cannot invent a node or a tool; the
  caller (Claude, or a human) picks from that list and `advance()` rejects
  anything not on it.
- A node marked `checkpoint_required` cannot be entered without a real,
  verified Phase 0 checkpoint (`Phase0ControlPlane.load_checkpoint`), so
  write/merge/deploy/delegate/handoff transitions are gated by the same
  mechanism Phase 0 already built, not a new one.
- Every transition, rejection, retry, and resume is appended to
  `path_trace`, so a run is replayable from disk without opening a
  transcript (`replay`), matching the Phase 2/3 "reconstruct from state"
  convention.
- Retries are bounded per node (`max_retries`, default 2, matching Phase 0's
  `MAX_RETRIES`); exceeding the bound is an explicit terminal state
  (`failed-exhausted-retries`), never a silent infinite loop.
- `fallback()` records that the static path was pinned instead of the
  graph's optional branches, so the fallback is visible state, not silence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase0_control_plane import (  # noqa: E402
    Phase0ControlPlane,
    Phase0Error,
    VerifiedCheckpointError,
    make_id,
    now,
    read_stdin_json,
    stable_json,
    state_root,
    atomic_write_text,
    workspace_root,
)

DEFAULT_MAX_RETRIES = 2
HIGH_RISK_TRANSITIONS = {"write", "merge", "deploy", "delegate", "handoff"}
VALID_RISKS = {"low", "medium", "high"}
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
APPROVED_PERSISTENCE_DIRS = ((".claude", "state"), (".claude", "traces"))


class Phase4Error(RuntimeError):
    pass


class UnknownWorkflowError(Phase4Error):
    pass


class InvalidWorkflowDefError(Phase4Error):
    pass


class UnsupportedBranchError(Phase4Error):
    pass


class CheckpointRequiredError(Phase4Error):
    pass


class RetriesExhaustedError(Phase4Error):
    pass


class UnverifiedNodeError(Phase4Error):
    pass


class UnsafeWorkflowIdentifierError(Phase4Error):
    pass


class UnsafeWorkflowPersistenceError(Phase4Error):
    pass


def validate_workflow_id(value: str, *, kind: str = "workflow id") -> str:
    """Return a normalized, filename-safe workflow identifier or raise.

    Workflow identifiers are persisted in file paths, embedded in state, and
    compared across workflow definitions. Keep them deliberately boring:
    lowercase ASCII letters/digits separated by single hyphen-compatible runs.
    This rejects absolute paths, traversal, path separators, ambiguous dot IDs,
    whitespace, case variants, and shell/path metacharacters before any state is
    read from or written to disk.
    """
    if not isinstance(value, str):
        raise UnsafeWorkflowIdentifierError(f"{kind} must be a string")
    if value != value.strip() or not value:
        raise UnsafeWorkflowIdentifierError(f"{kind} must be non-empty with no surrounding whitespace")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise UnsafeWorkflowIdentifierError(f"{kind} must not contain path components")
    path = Path(value)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise UnsafeWorkflowIdentifierError(f"{kind} must not be absolute or traverse directories")
    normalized = value.lower()
    if value != normalized:
        raise UnsafeWorkflowIdentifierError(f"{kind} must already be normalized lowercase")
    if not SAFE_ID_RE.fullmatch(value):
        raise UnsafeWorkflowIdentifierError(
            f"{kind} contains unsafe characters; use lowercase letters, digits, and hyphens"
        )
    return value


def _validate_persistence_root(root: Path | None, workspace: Path | None = None) -> Path:
    ws = (workspace or workspace_root()).resolve()
    candidate = (root or state_root()).expanduser().resolve()
    approved = [(ws.joinpath(*parts)).resolve() for parts in APPROVED_PERSISTENCE_DIRS]
    if not any(candidate == base or base in candidate.parents for base in approved):
        allowed = ", ".join(str(base) for base in approved)
        raise UnsafeWorkflowPersistenceError(f"workflow persistence root must be under: {allowed}")
    return candidate


def _defs_dir(workspace: Path | None = None) -> Path:
    ws = (workspace or workspace_root()).resolve()
    return ws / ".claude" / "workflows" / "defs"


def _runs_dir(root: Path | None = None, workspace: Path | None = None) -> Path:
    path = _validate_persistence_root(root, workspace) / "workflows"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_path(root: Path | None, run_id: str, workspace: Path | None = None) -> Path:
    safe_run_id = validate_workflow_id(run_id, kind="run id")
    return _runs_dir(root, workspace) / f"{safe_run_id}.json"


def load_workflow_def(name: str, workspace: Path | None = None) -> dict[str, Any]:
    safe_name = validate_workflow_id(name, kind="workflow name")
    path = _defs_dir(workspace) / f"{safe_name}.json"
    if not path.exists():
        raise UnknownWorkflowError(f"no workflow definition: {name}")
    definition = json.loads(path.read_text(encoding="utf-8"))
    _validate_workflow_def(definition)
    if definition.get("workflow") not in (None, safe_name):
        raise InvalidWorkflowDefError(f"workflow field {definition.get('workflow')!r} does not match filename {safe_name!r}")
    definition["_source_path"] = str(path)
    definition["_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return definition


def _validate_workflow_def(definition: dict[str, Any]) -> None:
    workflow = definition.get("workflow")
    if workflow is not None:
        validate_workflow_id(workflow, kind="workflow field")
    nodes = definition.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise InvalidWorkflowDefError("workflow definition has no nodes")
    start = validate_workflow_id(definition.get("start"), kind="start node")
    normalized_node_ids: set[str] = set()
    for node_id in nodes:
        safe_node_id = validate_workflow_id(node_id, kind="node id")
        if safe_node_id in normalized_node_ids:
            raise InvalidWorkflowDefError(f"duplicate normalized node id: {node_id!r}")
        normalized_node_ids.add(safe_node_id)
    if start not in nodes:
        raise InvalidWorkflowDefError(f"start node {start!r} is not declared in nodes")
    for node_id, node in nodes.items():
        if node.get("risk") not in VALID_RISKS:
            raise InvalidWorkflowDefError(f"node {node_id!r} has an invalid risk value")
        for target in node.get("allowed_next", []):
            safe_target = validate_workflow_id(target, kind="allowed_next node id")
            if safe_target not in nodes:
                raise InvalidWorkflowDefError(
                    f"node {node_id!r} allows transition to undeclared node {target!r}"
                )


def _node_def(definition: dict[str, Any], node_id: str) -> dict[str, Any]:
    node = definition["nodes"].get(node_id)
    if node is None:
        raise Phase4Error(f"unknown node: {node_id}")
    return node


def _load_run(root: Path | None, run_id: str, workspace: Path | None = None) -> dict[str, Any]:
    path = _run_path(root, run_id, workspace)
    if not path.exists():
        raise Phase4Error(f"no workflow run: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_run(root: Path | None, record: dict[str, Any], workspace: Path | None = None) -> Path:
    record["run_id"] = validate_workflow_id(record["run_id"], kind="run id")
    record["workflow"] = validate_workflow_id(record["workflow"], kind="workflow name")
    record["updated_at"] = now()
    path = _run_path(root, record["run_id"], workspace)
    atomic_write_text(path, stable_json(record) + "\n")
    return path


def start_run(
    workflow_name: str,
    *,
    run_id: str | None = None,
    root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    definition = load_workflow_def(workflow_name, workspace)
    run_id = validate_workflow_id(run_id or make_id("wfrun"), kind="run id")
    if _run_path(root, run_id, workspace).exists():
        raise UnsafeWorkflowIdentifierError(f"workflow run id already exists: {run_id}")

    record: dict[str, Any] = {
        "kind": "workflow-run",
        "run_id": run_id,
        "workflow": workflow_name,
        "workflow_sha256": definition["_sha256"],
        "status": "active",
        "current_node": definition["start"],
        "verified_node": None,
        "created_at": now(),
        "updated_at": now(),
        "retries": {},
        "fallback_used": False,
        "fallback_reason": None,
        "path_trace": [
            {
                "event": "enter",
                "node": definition["start"],
                "at": now(),
                "checkpoint_id": None,
            }
        ],
        "metrics": {
            "branch_depth": 0,
            "checkpoints_used": [],
            "retries_total": 0,
            "resumes_total": 0,
            "planner_tokens": None,
            "planner_cost_usd": None,
        },
    }
    _save_run(root, record, workspace)
    return record


def propose_next(run_id: str, *, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    """The bounded 'planner' surface: the only nodes a caller may choose
    among for the next transition. Nothing outside this list is valid."""
    record = _load_run(root, run_id, workspace)
    definition = load_workflow_def(record["workflow"], workspace)
    node = _node_def(definition, record["current_node"])
    return {
        "current_node": record["current_node"],
        "allowed_next": list(node.get("allowed_next", [])),
        "verifier": node.get("verifier"),
        "risk": node.get("risk"),
        "checkpoint_required": bool(node.get("checkpoint_required")),
        "current_node_verified": record["verified_node"] == record["current_node"],
    }


def verify_node(
    run_id: str,
    *,
    passed: bool,
    details: str | None = None,
    root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    record = _load_run(root, run_id, workspace)
    if record["status"] not in ("active",):
        raise Phase4Error(f"cannot verify a run in status={record['status']!r}")
    definition = load_workflow_def(record["workflow"], workspace)
    node_id = record["current_node"]
    node = _node_def(definition, node_id)
    max_retries = int(node.get("max_retries", DEFAULT_MAX_RETRIES))

    if passed:
        record["verified_node"] = node_id
        record["retries"][node_id] = 0
        record["path_trace"].append({"event": "verify", "node": node_id, "at": now(), "passed": True, "details": details})
    else:
        attempts = int(record["retries"].get(node_id, 0)) + 1
        record["retries"][node_id] = attempts
        record["metrics"]["retries_total"] += 1
        record["path_trace"].append(
            {"event": "verify", "node": node_id, "at": now(), "passed": False, "details": details, "attempt": attempts}
        )
        if attempts > max_retries:
            record["status"] = "failed-exhausted-retries"
            record["path_trace"].append(
                {"event": "retries-exhausted", "node": node_id, "at": now(), "attempts": attempts, "max_retries": max_retries}
            )
    _save_run(root, record, workspace)
    if record["status"] == "failed-exhausted-retries":
        raise RetriesExhaustedError(
            f"node {node_id!r} exceeded max_retries={max_retries} ({record['retries'][node_id]} failed attempts)"
        )
    return record


def advance(
    run_id: str,
    next_node_id: str,
    *,
    checkpoint_id: str | None = None,
    checkpoint_session_id: str | None = None,
    root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    record = _load_run(root, run_id, workspace)
    next_node_id = validate_workflow_id(next_node_id, kind="next node id")
    if record["status"] != "active":
        raise Phase4Error(f"cannot advance a run in status={record['status']!r}")
    definition = load_workflow_def(record["workflow"], workspace)
    current_id = record["current_node"]
    current = _node_def(definition, current_id)
    allowed = list(current.get("allowed_next", []))

    if next_node_id not in allowed:
        record["path_trace"].append(
            {
                "event": "rejected-branch",
                "from": current_id,
                "attempted": next_node_id,
                "allowed_next": allowed,
                "at": now(),
            }
        )
        _save_run(root, record, workspace)
        raise UnsupportedBranchError(
            f"{next_node_id!r} is not an allowed transition from {current_id!r}; allowed: {allowed}"
        )

    if record["verified_node"] != current_id:
        raise UnverifiedNodeError(f"cannot advance past {current_id!r} before it is verified")

    target = _node_def(definition, next_node_id)
    checkpoint = None
    if target.get("checkpoint_required"):
        if not checkpoint_id:
            raise CheckpointRequiredError(f"node {next_node_id!r} requires a verified checkpoint before entry")
        control = Phase0ControlPlane(root=root or state_root())
        try:
            checkpoint = control.load_checkpoint(checkpoint_id)
        except VerifiedCheckpointError as exc:
            raise CheckpointRequiredError(str(exc)) from exc
        if not checkpoint.get("verified"):
            raise CheckpointRequiredError(f"checkpoint {checkpoint_id} is not verified")
        if checkpoint_session_id and checkpoint.get("session_id") != checkpoint_session_id:
            raise CheckpointRequiredError("checkpoint session_id does not match the supplied session")
        record["metrics"]["checkpoints_used"].append(
            {"node": next_node_id, "checkpoint_id": checkpoint_id, "at": now()}
        )

    if len(allowed) > 1:
        record["metrics"]["branch_depth"] += 1

    record["current_node"] = next_node_id
    record["verified_node"] = None
    record["path_trace"].append(
        {
            "event": "enter",
            "node": next_node_id,
            "from": current_id,
            "at": now(),
            "checkpoint_id": checkpoint_id,
        }
    )

    terminal = not target.get("allowed_next")
    if terminal:
        record["status"] = "completed"
        record["verified_node"] = next_node_id
        record["path_trace"].append({"event": "completed", "node": next_node_id, "at": now()})

    _save_run(root, record, workspace)
    return record


def resume(run_id: str, *, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    """Resume from the last verified node. A run interrupted mid-node (its
    `current_node` was entered but never verified) rolls back to the last
    verified node rather than silently continuing from an unproven state."""
    record = _load_run(root, run_id)
    if record["status"] not in ("active",):
        raise Phase4Error(f"cannot resume a run in status={record['status']!r}")

    resume_node = record["verified_node"] or record["path_trace"][0]["node"]
    was_interrupted = record["current_node"] != resume_node
    record["current_node"] = resume_node
    record["metrics"]["resumes_total"] += 1
    record["path_trace"].append(
        {
            "event": "resume",
            "node": resume_node,
            "at": now(),
            "was_interrupted": was_interrupted,
        }
    )
    _save_run(root, record, workspace)
    return record


def fallback(run_id: str, *, reason: str, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    record = _load_run(root, run_id, workspace)
    record["fallback_used"] = True
    record["fallback_reason"] = reason
    record["path_trace"].append({"event": "fallback", "node": record["current_node"], "at": now(), "reason": reason})
    _save_run(root, record, workspace)
    return record


def replay(run_id: str, *, root: Path | None = None, workspace: Path | None = None) -> list[dict[str, Any]]:
    return list(_load_run(root, run_id, workspace)["path_trace"])


def status(run_id: str, *, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    record = _load_run(root, run_id, workspace)
    plan = propose_next(run_id, root=root, workspace=workspace) if record["status"] == "active" else None
    return {"run": record, "plan": plan}


def list_runs(*, root: Path | None = None, workspace: Path | None = None) -> list[dict[str, Any]]:
    runs_dir = _runs_dir(root, workspace)
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(runs_dir.glob("*.json"))]
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def command_start(args: argparse.Namespace) -> int:
    record = start_run(args.workflow, run_id=args.run_id)
    print(stable_json(record))
    return 0


def command_propose(args: argparse.Namespace) -> int:
    print(stable_json(propose_next(args.run_id)))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    record = verify_node(args.run_id, passed=not args.failed, details=args.details)
    print(stable_json(record))
    return 0


def command_advance(args: argparse.Namespace) -> int:
    record = advance(
        args.run_id,
        args.next_node,
        checkpoint_id=args.checkpoint_id,
        checkpoint_session_id=args.checkpoint_session_id,
    )
    print(stable_json(record))
    return 0


def command_resume(args: argparse.Namespace) -> int:
    print(stable_json(resume(args.run_id)))
    return 0


def command_fallback(args: argparse.Namespace) -> int:
    print(stable_json(fallback(args.run_id, reason=args.reason)))
    return 0


def command_replay(args: argparse.Namespace) -> int:
    print(stable_json(replay(args.run_id)))
    return 0


def command_status(args: argparse.Namespace) -> int:
    print(stable_json(status(args.run_id)))
    return 0


def command_list(_: argparse.Namespace) -> int:
    print(stable_json(list_runs()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase4_workflows")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("workflow")
    p.add_argument("--run-id")
    p.set_defaults(func=command_start)

    p = sub.add_parser("propose")
    p.add_argument("run_id")
    p.set_defaults(func=command_propose)

    p = sub.add_parser("verify")
    p.add_argument("run_id")
    p.add_argument("--failed", action="store_true")
    p.add_argument("--details")
    p.set_defaults(func=command_verify)

    p = sub.add_parser("advance")
    p.add_argument("run_id")
    p.add_argument("next_node")
    p.add_argument("--checkpoint-id")
    p.add_argument("--checkpoint-session-id")
    p.set_defaults(func=command_advance)

    p = sub.add_parser("resume")
    p.add_argument("run_id")
    p.set_defaults(func=command_resume)

    p = sub.add_parser("fallback")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=command_fallback)

    p = sub.add_parser("replay")
    p.add_argument("run_id")
    p.set_defaults(func=command_replay)

    p = sub.add_parser("status")
    p.add_argument("run_id")
    p.set_defaults(func=command_status)

    sub.add_parser("list").set_defaults(func=command_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Phase4Error, Phase0Error) as exc:
        print(f"Phase4 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Phase 5B task-agnostic lifecycle: atomic plan files, disk-only status
reconstruction, cold-start session handoffs, and metric-gated experiments.

Reuses Phase 0's `now`/`make_id`/`stable_json`/`state_root`/`workspace_root`
helpers rather than duplicating them. Nothing here trusts an agent's own
narrative: a plan must declare its verification target before it can be
created, a handoff must carry real verification evidence or an explicit
`--summary-only` flag (mirroring `phase3_agents.handoff`'s pattern for the
same reason), and an experiment decision is derived from a recorded metric
value, never asserted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase0_control_plane import (  # noqa: E402
    Phase0Error,
    make_id,
    now,
    read_stdin_json,
    stable_json,
    state_root,
    workspace_root,
)

MAX_TASKS_PER_PLAN = 3


class Phase5bError(RuntimeError):
    pass


class PlanValidationError(Phase5bError):
    pass


class HandoffError(Phase5bError):
    pass


class ExperimentError(Phase5bError):
    pass


# ---------------------------------------------------------------------------
# Atomic plans
# ---------------------------------------------------------------------------


def _plans_dir(workspace: Path | None = None) -> Path:
    ws = (workspace or workspace_root()).resolve()
    path = ws / ".claude" / "plans"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _plan_path(plan_id: str, workspace: Path | None = None) -> Path:
    return _plans_dir(workspace) / f"{plan_id}.json"


def validate_plan_dict(data: dict[str, Any], *, workspace: Path | None = None) -> None:
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise PlanValidationError("plan requires a non-empty title")

    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        raise PlanValidationError(
            "plan requires at least one explicit assumption; an unstated "
            "assumption is a defect even if the plan happens to work"
        )

    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise PlanValidationError("plan requires at least one task")
    if len(tasks) > MAX_TASKS_PER_PLAN:
        raise PlanValidationError(
            f"plan has {len(tasks)} tasks; atomic plans are capped at {MAX_TASKS_PER_PLAN}"
        )
    seen_ids: set[str] = set()
    for task in tasks:
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise PlanValidationError("every task requires a non-empty task_id")
        if task_id in seen_ids:
            raise PlanValidationError(f"duplicate task_id: {task_id}")
        seen_ids.add(task_id)
        description = task.get("description")
        if not isinstance(description, str) or not description.strip():
            raise PlanValidationError(f"task {task_id!r} requires a non-empty description")
        verification = task.get("verification")
        if not isinstance(verification, dict) or not str(verification.get("target") or "").strip():
            raise PlanValidationError(
                f"task {task_id!r} requires a verification target (see .claude/hooks/verify.sh targets)"
            )
        if not isinstance(task.get("commit_boundary"), bool):
            raise PlanValidationError(f"task {task_id!r} requires an explicit commit_boundary boolean")

    blocking_edges = data.get("blocking_edges", [])
    if not isinstance(blocking_edges, list):
        raise PlanValidationError("blocking_edges must be a list of plan_ids")
    for edge in blocking_edges:
        if not _plan_path(str(edge), workspace).exists():
            raise PlanValidationError(f"blocking edge references a plan that does not exist on disk: {edge}")


def create_plan(
    *,
    title: str,
    assumptions: list[str],
    tasks: list[dict[str, Any]],
    blocking_edges: list[str] | None = None,
    plan_id: str | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    record = {
        "kind": "atomic-plan",
        "plan_id": plan_id or make_id("plan"),
        "title": title,
        "status": "draft",
        "created_at": now(),
        "updated_at": now(),
        "assumptions": assumptions,
        "blocking_edges": blocking_edges or [],
        "tasks": tasks,
    }
    validate_plan_dict(record, workspace=workspace)
    path = _plan_path(record["plan_id"], workspace)
    path.write_text(stable_json(record) + "\n", encoding="utf-8")
    return record


def load_plan(plan_id: str, *, workspace: Path | None = None) -> dict[str, Any]:
    path = _plan_path(plan_id, workspace)
    if not path.exists():
        raise Phase5bError(f"no plan: {plan_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan(plan_id: str, *, workspace: Path | None = None) -> dict[str, Any]:
    record = load_plan(plan_id, workspace=workspace)
    validate_plan_dict(record, workspace=workspace)
    return record


def set_plan_status(plan_id: str, status: str, *, workspace: Path | None = None) -> dict[str, Any]:
    record = load_plan(plan_id, workspace=workspace)
    record["status"] = status
    record["updated_at"] = now()
    _plan_path(plan_id, workspace).write_text(stable_json(record) + "\n", encoding="utf-8")
    return record


def list_plans(*, workspace: Path | None = None) -> list[dict[str, Any]]:
    plans_dir = _plans_dir(workspace)
    records = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(plans_dir.glob("*.json"))
        if p.name != ".gitkeep"
    ]
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


# ---------------------------------------------------------------------------
# Status reconstruction (disk-only)
# ---------------------------------------------------------------------------


def _read_json_files(directory: Path, glob: str = "*.json") -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.rglob(glob)):
        if path.name == ".gitkeep":
            continue
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def reconstruct_status(*, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    """Reconstruct where-are-we purely from `.claude/state/` and
    `.claude/plans/` on disk; no transcript or in-memory state is read."""
    state = root or state_root()
    ws = workspace or workspace_root()

    plans = list_plans(workspace=ws)
    plan_summary = {
        "total": len(plans),
        "by_status": {},
        "plans": [
            {"plan_id": p["plan_id"], "title": p["title"], "status": p["status"], "tasks": len(p["tasks"])}
            for p in plans
        ],
    }
    for p in plans:
        plan_summary["by_status"][p["status"]] = plan_summary["by_status"].get(p["status"], 0) + 1

    ledger_path = state / "ledger.md"
    ledger_tail: list[str] = []
    if ledger_path.exists():
        lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        ledger_tail = lines[-10:]

    checkpoints_dir = state / "checkpoints"
    checkpoints = _read_json_files(checkpoints_dir, "*.json")
    checkpoints.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    latest_checkpoint = checkpoints[0] if checkpoints else None

    handoffs_dir = state / "handoffs"
    handoff_files = sorted(
        (p for p in handoffs_dir.glob("*.md") if p.name != ".gitkeep"),
        key=lambda p: p.name,
        reverse=True,
    ) if handoffs_dir.exists() else []

    workflow_runs = _read_json_files(state / "workflows", "*.json")
    active_workflow_runs = [r for r in workflow_runs if r.get("status") == "active"]

    agent_tasks = _read_json_files(state / "agents", "*.task.json")
    running_agent_tasks = [t for t in agent_tasks if t.get("status") == "running"]

    experiments = _read_json_files(state / "experiments", "*.json")

    return {
        "reconstructed_at": now(),
        "source": "disk-only",
        "plans": plan_summary,
        "ledger_tail": ledger_tail,
        "latest_checkpoint": {
            "checkpoint_id": latest_checkpoint.get("checkpoint_id"),
            "session_id": latest_checkpoint.get("session_id"),
            "verified": latest_checkpoint.get("verified"),
        } if latest_checkpoint else None,
        "recent_handoffs": [p.name for p in handoff_files[:5]],
        "active_workflow_runs": [r.get("run_id") for r in active_workflow_runs],
        "running_agent_tasks": [t.get("task_id") for t in running_agent_tasks],
        "experiments": [
            {"experiment_id": e.get("experiment_id"), "metric": e.get("metric"), "status": e.get("status")}
            for e in experiments
        ],
    }


# ---------------------------------------------------------------------------
# Session handoff (cold-start takeover document)
# ---------------------------------------------------------------------------


def _handoffs_dir(root: Path | None = None) -> Path:
    path = (root or state_root()) / "handoffs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_handoff(
    *,
    session_summary: str,
    next_steps: str,
    verification_evidence: list[dict[str, Any]] | None = None,
    summary_only: bool = False,
    plan_id: str | None = None,
    open_risks: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    if not summary_only and not verification_evidence:
        raise HandoffError(
            "handoff requires verification_evidence (list of {command, exit_code}) "
            "or explicit summary_only=True to record an unverified handoff"
        )

    handoff_id = make_id("handoff")
    timestamp = now().replace(":", "").replace("-", "")
    filename = f"{timestamp}-{handoff_id}.md"
    path = _handoffs_dir(root) / filename

    if summary_only:
        verified_section = (
            "**UNVERIFIED — summary only.** No verification-command evidence was "
            "supplied; do not treat this handoff's claimed state as proven."
        )
    else:
        rows = "\n".join(
            f"| `{e.get('command')}` | {e.get('exit_code')} |" for e in (verification_evidence or [])
        )
        verified_section = f"| Command | Exit code |\n| --- | --- |\n{rows}"

    plan_pointer = f"`.claude/plans/{plan_id}.json`" if plan_id else "none referenced"

    body = f"""# Session Handoff: {handoff_id}

Generated: {now()}

## Session Context

{session_summary}

## Verified State

{verified_section}

## What's Next

{next_steps}

## Open Risks / Assumptions

{open_risks or "None recorded."}

## Pointers

- Plan: {plan_pointer}
- Ledger: `.claude/state/ledger.md`
- Status reconstruction: `python3 .claude/scripts/phase5b_lifecycle.py status`
"""
    path.write_text(body, encoding="utf-8")
    return {
        "handoff_id": handoff_id,
        "path": str(path),
        "verified": not summary_only,
        "created_at": now(),
    }


# ---------------------------------------------------------------------------
# Metric-gated experiments (Karpathy AutoResearch loop)
# ---------------------------------------------------------------------------


def _experiments_dir(root: Path | None = None) -> Path:
    path = (root or state_root()) / "experiments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _experiment_path(experiment_id: str, root: Path | None = None) -> Path:
    return _experiments_dir(root) / f"{experiment_id}.json"


def start_experiment(
    *,
    metric: str,
    baseline_value: float,
    budget_minutes: int,
    direction: str = "higher_is_better",
    experiment_id: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    if direction not in ("higher_is_better", "lower_is_better"):
        raise ExperimentError("direction must be 'higher_is_better' or 'lower_is_better'")
    if budget_minutes <= 0:
        raise ExperimentError("budget_minutes must be a positive, fixed budget")
    record = {
        "kind": "metric-gated-experiment",
        "experiment_id": experiment_id or make_id("exp"),
        "metric": metric,
        "direction": direction,
        "baseline_value": baseline_value,
        "budget_minutes": budget_minutes,
        "status": "running",
        "observations": [],
        "decision": None,
        "started_at": now(),
        "updated_at": now(),
    }
    _experiment_path(record["experiment_id"], root).write_text(stable_json(record) + "\n", encoding="utf-8")
    return record


def load_experiment(experiment_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _experiment_path(experiment_id, root)
    if not path.exists():
        raise ExperimentError(f"no experiment: {experiment_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def record_observation(experiment_id: str, value: float, *, root: Path | None = None) -> dict[str, Any]:
    record = load_experiment(experiment_id, root=root)
    if record["status"] != "running":
        raise ExperimentError(f"cannot record an observation on a {record['status']} experiment")
    record["observations"].append({"value": value, "at": now()})
    record["updated_at"] = now()
    _experiment_path(experiment_id, root).write_text(stable_json(record) + "\n", encoding="utf-8")
    return record


def decide_experiment(experiment_id: str, *, root: Path | None = None) -> dict[str, Any]:
    record = load_experiment(experiment_id, root=root)
    if record["status"] != "running":
        raise ExperimentError(f"experiment {experiment_id} was already decided: {record['status']}")
    if not record["observations"]:
        raise ExperimentError("cannot decide an experiment with no recorded observations")

    latest = record["observations"][-1]["value"]
    baseline = record["baseline_value"]
    if record["direction"] == "higher_is_better":
        improved = latest > baseline
    else:
        improved = latest < baseline

    record["decision"] = {
        "outcome": "keep" if improved else "revert",
        "latest_value": latest,
        "baseline_value": baseline,
        "improved": improved,
        "decided_at": now(),
    }
    record["status"] = "kept" if improved else "reverted"
    record["updated_at"] = now()
    _experiment_path(experiment_id, root).write_text(stable_json(record) + "\n", encoding="utf-8")
    return record


def list_experiments(*, root: Path | None = None) -> list[dict[str, Any]]:
    return sorted(
        _read_json_files(_experiments_dir(root), "*.json"),
        key=lambda r: r.get("started_at") or "",
        reverse=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def command_plan_create(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.tasks_json).read_text(encoding="utf-8")) if args.tasks_json else read_stdin_json()
    record = create_plan(
        title=args.title,
        assumptions=payload.get("assumptions", []),
        tasks=payload.get("tasks", []),
        blocking_edges=payload.get("blocking_edges", []),
    )
    print(stable_json(record))
    return 0


def command_plan_validate(args: argparse.Namespace) -> int:
    record = validate_plan(args.plan_id)
    print(stable_json(record))
    return 0


def command_plan_status(args: argparse.Namespace) -> int:
    record = set_plan_status(args.plan_id, args.status)
    print(stable_json(record))
    return 0


def command_plan_list(_: argparse.Namespace) -> int:
    print(stable_json(list_plans()))
    return 0


def command_status(_: argparse.Namespace) -> int:
    print(stable_json(reconstruct_status()))
    return 0


def command_handoff_create(args: argparse.Namespace) -> int:
    evidence = json.loads(args.verification_evidence) if args.verification_evidence else None
    record = create_handoff(
        session_summary=args.summary,
        next_steps=args.next_steps,
        verification_evidence=evidence,
        summary_only=args.summary_only,
        plan_id=args.plan_id,
        open_risks=args.open_risks,
    )
    print(stable_json(record))
    return 0


def command_experiment_start(args: argparse.Namespace) -> int:
    record = start_experiment(
        metric=args.metric,
        baseline_value=args.baseline,
        budget_minutes=args.budget_minutes,
        direction=args.direction,
    )
    print(stable_json(record))
    return 0


def command_experiment_record(args: argparse.Namespace) -> int:
    print(stable_json(record_observation(args.experiment_id, args.value)))
    return 0


def command_experiment_decide(args: argparse.Namespace) -> int:
    print(stable_json(decide_experiment(args.experiment_id)))
    return 0


def command_experiment_list(_: argparse.Namespace) -> int:
    print(stable_json(list_experiments()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase5b_lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan-create")
    p.add_argument("--title", required=True)
    p.add_argument("--tasks-json", help="path to a JSON file with assumptions/tasks/blocking_edges; else read stdin")
    p.set_defaults(func=command_plan_create)

    p = sub.add_parser("plan-validate")
    p.add_argument("plan_id")
    p.set_defaults(func=command_plan_validate)

    p = sub.add_parser("plan-set-status")
    p.add_argument("plan_id")
    p.add_argument("status")
    p.set_defaults(func=command_plan_status)

    sub.add_parser("plan-list").set_defaults(func=command_plan_list)

    sub.add_parser("status").set_defaults(func=command_status)

    p = sub.add_parser("handoff-create")
    p.add_argument("--summary", required=True)
    p.add_argument("--next-steps", required=True)
    p.add_argument("--verification-evidence", help='JSON list: [{"command": "...", "exit_code": 0}]')
    p.add_argument("--summary-only", action="store_true")
    p.add_argument("--plan-id")
    p.add_argument("--open-risks")
    p.set_defaults(func=command_handoff_create)

    p = sub.add_parser("experiment-start")
    p.add_argument("--metric", required=True)
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--budget-minutes", type=int, required=True)
    p.add_argument("--direction", default="higher_is_better")
    p.set_defaults(func=command_experiment_start)

    p = sub.add_parser("experiment-record")
    p.add_argument("experiment_id")
    p.add_argument("value", type=float)
    p.set_defaults(func=command_experiment_record)

    p = sub.add_parser("experiment-decide")
    p.add_argument("experiment_id")
    p.set_defaults(func=command_experiment_decide)

    sub.add_parser("experiment-list").set_defaults(func=command_experiment_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Phase5bError, Phase0Error) as exc:
        print(f"Phase5b error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

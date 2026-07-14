#!/usr/bin/env python3
"""Phase 3 sub-agent orchestration: parent-child task tracking, role routing,
stale-worker detection, and verified merge/handoff — all under
`.claude/state/agents/`, built on Phase 0's state root and Phase 2's
subagent-export convention.

Nothing here trusts a subagent's own summary as proof of completion: `handoff`
records a summary-only report as explicitly unverified unless the caller
supplies real verification-command evidence.
"""
from __future__ import annotations

import argparse
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
    now,
    read_stdin_json,
    stable_json,
    state_root,
    atomic_write_text,
    update_json_file_locked,
    workspace_root,
)

MAX_SUMMARY_CHARS = 4000
DEFAULT_STALE_AFTER_MINUTES = 120

# Built-in Claude Code subagents that never have a `.claude/agents/*.md`
# definition to inspect. Routed to a fixed role rather than "unrouted".
BUILTIN_ROLES = {
    "Explore": "read-only-researcher",
    "Plan": "planner",
    "general-purpose": "general-purpose",
}

# Maps a project-scoped `.claude/agents/<name>.md` frontmatter `name` to the
# recurring role it fills in the Phase 3 catalog. Anything not listed here
# (but present on disk) is routed as "custom"; anything present in neither
# this dict nor BUILTIN_ROLES nor the agents directory is "unrouted".
ROLE_BY_AGENT_NAME = {
    "scout": "read-only-researcher",
    "planner": "planner",
    "builder": "scoped-builder",
    "verifier": "independent-verifier",
    "implementation-agent": "scoped-builder",
    "pr-reviewer": "independent-verifier",
    "upstream-auditor": "read-only-researcher",
    "reflect-agent": "memory-synthesis",
}


class Phase3Error(RuntimeError):
    pass


def _agents_dir(root: Path) -> Path:
    path = root / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _task_path(root: Path, parent_session_id: str, agent_id: str) -> Path:
    dest_dir = _agents_dir(root) / parent_session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{agent_id}.task.json"


def task_id_for(parent_session_id: str, agent_id: str) -> str:
    return f"{parent_session_id}:{agent_id}"


def _parse_agent_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}
    fields: dict[str, Any] = {}
    for line in lines[1:end]:
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        fields[key] = value
    tools = fields.get("tools", "")
    fields["tools_list"] = [t.strip() for t in tools.split(",") if t.strip()]
    return fields


def agent_catalog(workspace: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read every `.claude/agents/*.md` file's frontmatter once. This is the
    single source of truth for tool scope / isolation — never duplicated by
    hand into this script, so it cannot drift from the real agent files."""
    ws = (workspace or workspace_root()).resolve()
    agents_dir = ws / ".claude" / "agents"
    catalog: dict[str, dict[str, Any]] = {}
    if not agents_dir.exists():
        return catalog
    for path in sorted(agents_dir.glob("*.md")):
        if path.name in {"README.md", "AGENTS.md"}:
            continue
        fields = _parse_agent_frontmatter(path)
        name = fields.get("name")
        if not name:
            continue
        catalog[name] = {
            "definition_path": str(path),
            "tools": fields.get("tools_list", []),
            "isolation": fields.get("isolation", "none"),
            "permission_mode": fields.get("permissionMode", "default"),
            "role": ROLE_BY_AGENT_NAME.get(name, "custom"),
        }
    return catalog


def route(agent_type: str, workspace: Path | None = None) -> dict[str, Any]:
    if agent_type in BUILTIN_ROLES:
        return {
            "role": BUILTIN_ROLES[agent_type],
            "definition_path": None,
            "tools": [],
            "isolation": "none",
            "permission_mode": "default",
            "routing": "builtin",
        }
    catalog = agent_catalog(workspace)
    entry = catalog.get(agent_type)
    if entry is None:
        return {
            "role": "unrouted",
            "definition_path": None,
            "tools": [],
            "isolation": "unknown",
            "permission_mode": "unknown",
            "routing": "unrouted",
        }
    return {**entry, "routing": "catalog"}


def _latest_verified_checkpoint(session_id: str, state: Path) -> dict[str, Any] | None:
    try:
        control = Phase0ControlPlane(root=state)
        return control.load_latest_verified_checkpoint(session_id)
    except (VerifiedCheckpointError, Phase0Error):
        return None


def subagent_start(payload: dict[str, Any], root: Path | None = None, workspace: Path | None = None) -> Path:
    parent_session_id = str(payload.get("session_id") or "")
    agent_id = str(payload.get("agent_id") or "")
    agent_type = str(payload.get("agent_type") or "")
    if not parent_session_id or not agent_id:
        raise Phase3Error("SubagentStart payload is missing session_id or agent_id")
    state = root or state_root()
    routing = route(agent_type, workspace)
    checkpoint = _latest_verified_checkpoint(parent_session_id, state)

    record = {
        "kind": "subagent-task",
        "task_id": task_id_for(parent_session_id, agent_id),
        "parent_session_id": parent_session_id,
        "agent_id": agent_id,
        "agent_type": agent_type,
        "role": routing["role"],
        "tool_scope": routing["tools"],
        "isolation": routing["isolation"],
        "routing": routing["routing"],
        "status": "running",
        "started_at": now(),
        "completed_at": None,
        "checkpoint": checkpoint,
        "exported_summary": None,
        "transcript_pointer": None,
        "stop_resume_state": "running",
        "merge_handoff_result": None,
    }
    dest = _task_path(state, parent_session_id, agent_id)
    atomic_write_text(dest, stable_json(record) + "\n")
    return dest


def subagent_stop(payload: dict[str, Any], root: Path | None = None) -> Path:
    parent_session_id = str(payload.get("session_id") or "")
    agent_id = str(payload.get("agent_id") or "")
    if not parent_session_id or not agent_id:
        raise Phase3Error("SubagentStop payload is missing session_id or agent_id")
    state = root or state_root()
    dest = _task_path(state, parent_session_id, agent_id)

    def update(record: dict[str, Any] | None) -> dict[str, Any]:
        if record is None:
            # SubagentStart wasn't wired/observed for this task (e.g. hook added
            # mid-session); reconstruct a minimal record rather than dropping
            # the completion evidence.
            record = {
                "kind": "subagent-task",
                "task_id": task_id_for(parent_session_id, agent_id),
                "parent_session_id": parent_session_id,
                "agent_id": agent_id,
                "agent_type": str(payload.get("agent_type") or ""),
                "role": route(str(payload.get("agent_type") or "")).get("role", "unrouted"),
                "tool_scope": [],
                "isolation": "unknown",
                "routing": "reconstructed-at-stop",
                "started_at": None,
                "checkpoint": None,
            }

        record["status"] = "completed"
        record["completed_at"] = now()
        record["stop_resume_state"] = "stopped"
        record["exported_summary"] = (payload.get("last_assistant_message") or "")[:MAX_SUMMARY_CHARS]
        record["transcript_pointer"] = payload.get("agent_transcript_path")
        return record

    update_json_file_locked(dest, update)
    return dest


def _iter_task_files(state: Path):
    agents_root = _agents_dir(state)
    if not agents_root.exists():
        return
    for path in sorted(agents_root.rglob("*.task.json")):
        yield path


def sweep(stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES, root: Path | None = None) -> list[str]:
    """Mark `running` tasks with no completion as `stale` once they exceed
    the threshold, so an interrupted worker is visible rather than silently
    assumed to still be in flight."""
    from datetime import datetime, timedelta, timezone

    state = root or state_root()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    changed: list[str] = []
    for path in _iter_task_files(state):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") != "running":
            continue
        started_at = record.get("started_at")
        if not started_at:
            continue
        try:
            started = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        except ValueError:
            continue
        if started < cutoff:
            record["status"] = "stale"
            record["stop_resume_state"] = "stale"
            record["stale_detected_at"] = now()
            atomic_write_text(path, stable_json(record) + "\n")
            changed.append(record["task_id"])
    return changed


def handoff(
    *,
    parent_session_id: str,
    agent_id: str,
    verification_command: str | None,
    verification_exit_code: int | None,
    note: str | None,
    summary_only: bool,
    root: Path | None = None,
) -> dict[str, Any]:
    state = root or state_root()
    dest = _task_path(state, parent_session_id, agent_id)
    if not dest.exists():
        raise Phase3Error(f"no task record for {task_id_for(parent_session_id, agent_id)}")
    record = json.loads(dest.read_text(encoding="utf-8"))
    if record.get("status") not in ("completed", "stale"):
        raise Phase3Error(
            f"cannot hand off a task that has not completed (status={record.get('status')!r})"
        )

    if summary_only:
        result = {
            "verified": False,
            "reason": "summary-only handoff; a subagent's self-report is not treated as proof",
            "note": note,
            "recorded_at": now(),
        }
        record["status"] = "handoff-unverified"
    else:
        if not verification_command or verification_exit_code is None:
            raise Phase3Error(
                "handoff requires --verification-command and --verification-exit-code, "
                "or explicit --summary-only to record an unverified handoff"
            )
        verified = verification_exit_code == 0
        result = {
            "verified": verified,
            "command": verification_command,
            "exit_code": verification_exit_code,
            "note": note,
            "recorded_at": now(),
        }
        record["status"] = "merged" if verified else "handoff-failed-verification"

    record["merge_handoff_result"] = result
    update_json_file_locked(dest, lambda _current: record)
    return record


def list_tasks(root: Path | None = None) -> list[dict[str, Any]]:
    """Reconstruct every active and completed delegated task from disk, for
    operators who need the full picture without opening any transcript."""
    state = root or state_root()
    records = [json.loads(path.read_text(encoding="utf-8")) for path in _iter_task_files(state)]
    records.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return records


def command_subagent_start(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    path = subagent_start(payload)
    print(stable_json({"task_path": str(path)}))
    return 0


def command_subagent_stop(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    path = subagent_stop(payload)
    print(stable_json({"task_path": str(path)}))
    return 0


def command_sweep(args: argparse.Namespace) -> int:
    changed = sweep(stale_after_minutes=args.stale_after_minutes)
    print(stable_json({"marked_stale": changed}))
    return 0


def command_handoff(args: argparse.Namespace) -> int:
    record = handoff(
        parent_session_id=args.parent_session_id,
        agent_id=args.agent_id,
        verification_command=args.verification_command,
        verification_exit_code=args.verification_exit_code,
        note=args.note,
        summary_only=args.summary_only,
        root=None,
    )
    print(stable_json(record))
    return 0


def command_list(_: argparse.Namespace) -> int:
    print(stable_json(list_tasks()))
    return 0


def command_route(args: argparse.Namespace) -> int:
    print(stable_json(route(args.agent_type)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase3_agents")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("subagent-start").set_defaults(func=command_subagent_start)
    sub.add_parser("subagent-stop").set_defaults(func=command_subagent_stop)

    p = sub.add_parser("sweep")
    p.add_argument("--stale-after-minutes", type=int, default=DEFAULT_STALE_AFTER_MINUTES)
    p.set_defaults(func=command_sweep)

    p = sub.add_parser("handoff")
    p.add_argument("--parent-session-id", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--verification-command")
    p.add_argument("--verification-exit-code", type=int)
    p.add_argument("--note")
    p.add_argument("--summary-only", action="store_true")
    p.set_defaults(func=command_handoff)

    sub.add_parser("list").set_defaults(func=command_list)

    p = sub.add_parser("route")
    p.add_argument("agent_type")
    p.set_defaults(func=command_route)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Phase3Error, Phase0Error) as exc:
        print(f"Phase3 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

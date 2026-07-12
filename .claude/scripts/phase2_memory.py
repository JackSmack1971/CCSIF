#!/usr/bin/env python3
"""Phase 2 project-level memory and state: repo-local bootstrap, compaction
snapshot/restore, subagent summary export, and memory-source reconstruction.

Everything here is a thin layer over Phase 0's durable state root
(`.claude/state/`) and the project's own memory files. It never depends on
`~/.claude/*` for correctness: every path is derived from `workspace_root()`
(itself overridable via `PHASE0_WORKSPACE_ROOT` for tests) or from the
Phase 0 `state_root()`.
"""
from __future__ import annotations

import argparse
import json
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
    workspace_root,
)

SETTINGS_LOCAL_NAME = "settings.local.json"
MEMORY_DIR_NAME = "memory"
MAX_SUMMARY_CHARS = 4000


class Phase2Error(RuntimeError):
    pass


def settings_local_path(workspace: Path) -> Path:
    return workspace / ".claude" / SETTINGS_LOCAL_NAME


def memory_dir(workspace: Path) -> Path:
    return workspace / ".claude" / MEMORY_DIR_NAME


def bootstrap_local_settings(workspace: Path | None = None) -> dict[str, Any]:
    """Idempotently ensure `.claude/settings.local.json` carries an absolute,
    machine-correct `autoMemoryDirectory` without touching any other key or
    committing machine paths/secrets (the file stays gitignored)."""
    ws = (workspace or workspace_root()).resolve()
    target_path = settings_local_path(ws)
    desired_memory_dir = str(memory_dir(ws).resolve())

    if target_path.exists():
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - fail closed, do not overwrite unreadable state
            raise Phase2Error(f"{target_path} is not valid JSON, refusing to overwrite: {exc}") from exc
        if not isinstance(data, dict):
            raise Phase2Error(f"{target_path} does not contain a JSON object, refusing to overwrite")
        current = data.get("autoMemoryDirectory")
        if current == desired_memory_dir:
            return {"status": "unchanged", "path": str(target_path), "autoMemoryDirectory": desired_memory_dir}
        data["autoMemoryDirectory"] = desired_memory_dir
        target_path.write_text(stable_json(data) + "\n", encoding="utf-8")
        return {"status": "updated", "path": str(target_path), "autoMemoryDirectory": desired_memory_dir}

    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "version": 1,
        "description": "Personal project overrides. Do not commit real local secrets.",
        "autoMemoryDirectory": desired_memory_dir,
    }
    target_path.write_text(stable_json(data) + "\n", encoding="utf-8")
    return {"status": "created", "path": str(target_path), "autoMemoryDirectory": desired_memory_dir}


def _compactions_dir(root: Path) -> Path:
    path = root / "compactions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _agents_dir(root: Path) -> Path:
    path = root / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_slug() -> str:
    return now().replace(":", "").replace("-", "").replace(".", "")


def precompact_snapshot(payload: dict[str, Any], root: Path | None = None) -> Path:
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise Phase2Error("PreCompact payload is missing session_id")
    state = root or state_root()
    control = Phase0ControlPlane(root=state)

    checkpoint: dict[str, Any] | None
    try:
        checkpoint = control.load_latest_verified_checkpoint(session_id)
    except (VerifiedCheckpointError, Phase0Error):
        checkpoint = None

    snapshot = {
        "kind": "precompact-snapshot",
        "session_id": session_id,
        "trigger": payload.get("trigger"),
        "custom_instructions": payload.get("custom_instructions") or "",
        "checkpoint": checkpoint,
        "created_at": now(),
    }
    dest = _compactions_dir(state) / f"{session_id}-{_timestamp_slug()}-snapshot.json"
    dest.write_text(stable_json(snapshot) + "\n", encoding="utf-8")
    return dest


def postcompact_record(payload: dict[str, Any], root: Path | None = None) -> Path:
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise Phase2Error("PostCompact payload is missing session_id")
    state = root or state_root()
    record = {
        "kind": "postcompact-summary",
        "session_id": session_id,
        "trigger": payload.get("trigger"),
        "compact_summary": (payload.get("compact_summary") or "")[:MAX_SUMMARY_CHARS],
        "created_at": now(),
    }
    dest = _compactions_dir(state) / f"{session_id}-{_timestamp_slug()}-summary.json"
    dest.write_text(stable_json(record) + "\n", encoding="utf-8")
    return dest


def _latest_compaction_file(state: Path, session_id: str, suffix: str) -> Path | None:
    candidates = sorted(_compactions_dir(state).glob(f"{session_id}-*-{suffix}.json"))
    return candidates[-1] if candidates else None


def session_start_restore(payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Restore only current, validated context after compaction or resume.
    A snapshot is validated only if its session_id matches the current
    session; anything else (missing file, foreign session_id, unreadable
    JSON) is rejected rather than silently reused."""
    state = root or state_root()
    session_id = str(payload.get("session_id") or "")
    source = str(payload.get("source") or "")
    decision: dict[str, Any] = {
        "kind": "session-start-restore",
        "session_id": session_id,
        "source": source,
        "created_at": now(),
    }

    if not session_id or source not in ("compact", "resume"):
        decision["validated"] = False
        decision["reason"] = "not a compaction/resume start" if session_id else "missing session_id"
        _write_restore_record(state, session_id or "unknown", decision)
        return decision

    snapshot_path = _latest_compaction_file(state, session_id, "snapshot")
    if snapshot_path is None:
        decision["validated"] = False
        decision["reason"] = "no precompact snapshot for this session_id"
        _write_restore_record(state, session_id, decision)
        return decision

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - stale/corrupt snapshot must be rejected, not guessed at
        decision["validated"] = False
        decision["reason"] = f"snapshot unreadable: {exc}"
        _write_restore_record(state, session_id, decision)
        return decision

    if snapshot.get("session_id") != session_id:
        decision["validated"] = False
        decision["reason"] = "snapshot session_id does not match current session_id (stale/foreign summary rejected)"
        _write_restore_record(state, session_id, decision)
        return decision

    summary_path = _latest_compaction_file(state, session_id, "summary")
    compact_summary = ""
    if summary_path is not None:
        try:
            summary_record = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_record.get("session_id") == session_id:
                compact_summary = str(summary_record.get("compact_summary") or "")
        except Exception:  # noqa: BLE001 - a bad summary file just means no summary text, not a hard failure
            compact_summary = ""

    checkpoint = snapshot.get("checkpoint")
    lines = ["Restored project memory after compaction/resume (validated, repo-local):"]
    if checkpoint:
        lines.append(
            f"- Last verified checkpoint: turn {checkpoint.get('turn_index')}, step {checkpoint.get('step_index')}"
            f" (checkpoint_id={checkpoint.get('checkpoint_id')})"
        )
    else:
        lines.append("- No verified checkpoint was recorded before this compaction.")
    if compact_summary:
        lines.append(f"- Compact summary: {compact_summary[:2000]}")
    lines.append(f"- Snapshot evidence: {snapshot_path}")

    decision["validated"] = True
    decision["snapshot_path"] = str(snapshot_path)
    decision["additional_context"] = "\n".join(lines)
    _write_restore_record(state, session_id, decision)
    return decision


def _write_restore_record(state: Path, session_id: str, decision: dict[str, Any]) -> None:
    dest = _compactions_dir(state) / f"{session_id}-{_timestamp_slug()}-restore.json"
    dest.write_text(stable_json(decision) + "\n", encoding="utf-8")


def subagent_export(payload: dict[str, Any], root: Path | None = None) -> Path:
    parent_session_id = str(payload.get("session_id") or "")
    agent_id = str(payload.get("agent_id") or "")
    if not parent_session_id or not agent_id:
        raise Phase2Error("SubagentStop payload is missing session_id or agent_id")
    state = root or state_root()
    dest_dir = _agents_dir(state) / parent_session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": "subagent-summary",
        "parent_session_id": parent_session_id,
        "agent_id": agent_id,
        "agent_type": payload.get("agent_type"),
        "agent_transcript_path": payload.get("agent_transcript_path"),
        "last_assistant_message": (payload.get("last_assistant_message") or "")[:MAX_SUMMARY_CHARS],
        "exported_at": now(),
    }
    dest = dest_dir / f"{agent_id}.json"
    dest.write_text(stable_json(record) + "\n", encoding="utf-8")
    return dest


def memory_status(workspace: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    ws = (workspace or workspace_root()).resolve()
    state = root or state_root()

    claude_md = ws / "CLAUDE.md"
    claude_local_md = ws / "CLAUDE.local.md"
    rules_dir = ws / ".claude" / "rules"
    plans_dir = ws / ".claude" / "plans"
    settings_local = settings_local_path(ws)

    auto_memory_dir_value: str | None = None
    auto_memory_absolute = False
    if settings_local.exists():
        try:
            local_data = json.loads(settings_local.read_text(encoding="utf-8"))
            auto_memory_dir_value = local_data.get("autoMemoryDirectory")
            if isinstance(auto_memory_dir_value, str):
                auto_memory_absolute = Path(auto_memory_dir_value).is_absolute()
        except Exception:  # noqa: BLE001 - status reporting must not crash on a bad local file
            auto_memory_dir_value = None

    compactions = sorted(_compactions_dir(state).glob("*.json"))
    snapshots = [p for p in compactions if p.name.endswith("-snapshot.json")]
    summaries = [p for p in compactions if p.name.endswith("-summary.json")]
    restores = [p for p in compactions if p.name.endswith("-restore.json")]

    agents_root = _agents_dir(state)
    agent_sessions = sorted(p.name for p in agents_root.iterdir() if p.is_dir()) if agents_root.exists() else []
    agent_export_count = sum(1 for _ in agents_root.rglob("*.json"))

    latest_checkpoint: dict[str, Any] | None = None
    try:
        control = Phase0ControlPlane(root=state)
        with control._db() as conn:  # noqa: SLF001 - read-only status introspection
            row = conn.execute(
                "select * from checkpoints where verified = 1 order by created_at desc limit 1"
            ).fetchone()
            if row is not None:
                latest_checkpoint = {
                    "checkpoint_id": row["checkpoint_id"],
                    "session_id": row["session_id"],
                    "turn_index": row["turn_index"],
                    "step_index": row["step_index"],
                    "created_at": row["created_at"],
                }
    except Exception:  # noqa: BLE001 - status must degrade gracefully if state root is fresh/absent
        latest_checkpoint = None

    return {
        "kind": "phase2-memory-status",
        "generated_at": now(),
        "workspace_root": str(ws),
        "sources": {
            "CLAUDE.md": claude_md.exists(),
            "CLAUDE.local.md": claude_local_md.exists(),
            "rules_count": len(list(rules_dir.glob("*.md"))) if rules_dir.exists() else 0,
            "settings_local_json": settings_local.exists(),
            "auto_memory_directory": auto_memory_dir_value,
            "auto_memory_directory_absolute": auto_memory_absolute,
            "plans_directory_exists": plans_dir.exists(),
        },
        "compactions": {
            "snapshot_count": len(snapshots),
            "summary_count": len(summaries),
            "restore_count": len(restores),
            "latest_snapshot": str(snapshots[-1]) if snapshots else None,
        },
        "agents": {
            "exported_summary_count": agent_export_count,
            "parent_sessions_with_exports": agent_sessions,
        },
        "latest_verified_checkpoint": latest_checkpoint,
        "recovery": {
            "source": "native-files",
            "external_index_configured": False,
        },
    }


def command_bootstrap(_: argparse.Namespace) -> int:
    result = bootstrap_local_settings()
    print(stable_json(result))
    return 0


def command_precompact(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    path = precompact_snapshot(payload)
    print(stable_json({"snapshot_path": str(path)}))
    return 0


def command_postcompact(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    path = postcompact_record(payload)
    print(stable_json({"summary_path": str(path)}))
    return 0


def command_session_start_restore(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    decision = session_start_restore(payload)
    if decision.get("validated") and decision.get("additional_context"):
        print(
            stable_json(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": decision["additional_context"],
                    }
                }
            )
        )
    return 0


def command_subagent_export(_: argparse.Namespace) -> int:
    payload = read_stdin_json()
    path = subagent_export(payload)
    print(stable_json({"export_path": str(path)}))
    return 0


def command_status(_: argparse.Namespace) -> int:
    print(stable_json(memory_status()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase2_memory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("bootstrap-local-settings").set_defaults(func=command_bootstrap)
    sub.add_parser("precompact").set_defaults(func=command_precompact)
    sub.add_parser("postcompact").set_defaults(func=command_postcompact)
    sub.add_parser("session-start-restore").set_defaults(func=command_session_start_restore)
    sub.add_parser("subagent-export").set_defaults(func=command_subagent_export)
    sub.add_parser("status").set_defaults(func=command_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Phase2Error, Phase0Error) as exc:
        print(f"Phase2 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

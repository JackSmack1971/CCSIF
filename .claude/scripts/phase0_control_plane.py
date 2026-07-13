#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_ROOT = ROOT / ".claude" / "state"
DEFAULT_WORKSPACE_ROOT = ROOT

RAW_EXPORT_NAME = "raw-events.jsonl"
DB_NAME = "phase0.sqlite3"

MAX_RETRIES = 2


class Phase0Error(RuntimeError):
    pass


class UnsafeToolRequestError(Phase0Error):
    pass


class TerminalToolFailure(Phase0Error):
    pass


class VerifiedCheckpointError(Phase0Error):
    pass


class TransientToolError(Phase0Error):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def monotonic_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - report exact failure
        raise Phase0Error(f"stdin is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise Phase0Error("stdin JSON must be an object")
    return payload


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    return Path(raw).expanduser().resolve()


def state_root() -> Path:
    return env_path("PHASE0_STATE_ROOT", DEFAULT_STATE_ROOT)


def workspace_root() -> Path:
    return env_path("PHASE0_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT)


def ensure_workspace(path: Path) -> None:
    resolved = path.expanduser().resolve()
    root = workspace_root().resolve()
    if resolved == root:
        return
    if root not in resolved.parents:
        raise UnsafeToolRequestError(f"path escapes workspace: {path}")


def is_retryable_failure(exc: BaseException) -> bool:
    return isinstance(exc, TransientToolError)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class SessionRecord:
    session_id: str
    status: str
    created_at: str
    updated_at: str
    current_turn_index: int
    current_step_index: int
    verified_turn_index: int
    verified_step_index: int
    pending_tool_call_id: str | None
    last_checkpoint_id: str | None
    raw_export_path: str
    notes: str | None = None


@dataclass
class EventRecord:
    event_id: str
    event_type: str
    session_id: str
    turn_index: int
    step_index: int
    tool_call_id: str | None
    created_at: str
    duration_ms: int | None
    status: str
    payload: dict[str, Any]
    raw_payload: dict[str, Any] | None = None


class Phase0ControlPlane:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or state_root()
        self.db_path = self.root / DB_NAME
        self.logs_dir = self.root / "logs"
        self.raw_dir = self.root / "raw"
        self.checkpoints_dir = self.root / "checkpoints"
        self.archive_dir = self.root / "archive"
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._db() as conn:
            conn.executescript(
                """
                create table if not exists sessions (
                    session_id text primary key,
                    status text not null,
                    created_at text not null,
                    updated_at text not null,
                    current_turn_index integer not null,
                    current_step_index integer not null,
                    verified_turn_index integer not null,
                    verified_step_index integer not null,
                    pending_tool_call_id text,
                    last_checkpoint_id text,
                    raw_export_path text not null,
                    notes text
                );

                create table if not exists events (
                    event_id text primary key,
                    event_type text not null,
                    session_id text not null,
                    turn_index integer not null,
                    step_index integer not null,
                    tool_call_id text,
                    created_at text not null,
                    duration_ms integer,
                    status text not null,
                    payload_json text not null,
                    raw_payload_json text
                );

                create table if not exists checkpoints (
                    checkpoint_id text primary key,
                    session_id text not null,
                    turn_index integer not null,
                    step_index integer not null,
                    created_at text not null,
                    path text not null,
                    verified integer not null
                );
                """
            )

    def _raw_export_path(self, session_id: str) -> Path:
        return self.raw_dir / session_id / RAW_EXPORT_NAME

    def _log_path(self, session_id: str) -> Path:
        return self.logs_dir / f"{session_id}.jsonl"

    def _checkpoint_path(self, session_id: str, turn_index: int, step_index: int) -> Path:
        return self.checkpoints_dir / f"{session_id}-t{turn_index}-s{step_index}.json"

    def _archive_path(self, session_id: str) -> Path:
        return self.archive_dir / f"{session_id}.json"

    def _insert_session(self, record: SessionRecord) -> None:
        with self._db() as conn:
            conn.execute(
                """
                insert or replace into sessions (
                    session_id, status, created_at, updated_at,
                    current_turn_index, current_step_index,
                    verified_turn_index, verified_step_index,
                    pending_tool_call_id, last_checkpoint_id,
                    raw_export_path, notes
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.session_id,
                    record.status,
                    record.created_at,
                    record.updated_at,
                    record.current_turn_index,
                    record.current_step_index,
                    record.verified_turn_index,
                    record.verified_step_index,
                    record.pending_tool_call_id,
                    record.last_checkpoint_id,
                    record.raw_export_path,
                    record.notes,
                ),
            )

    def _update_session(self, record: SessionRecord) -> None:
        record.updated_at = now()
        self._insert_session(record)

    def _fetch_session_row(self, session_id: str) -> sqlite3.Row:
        with self._db() as conn:
            row = conn.execute("select * from sessions where session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise Phase0Error(f"unknown session: {session_id}")
        return row

    def load_session(self, session_id: str) -> SessionRecord:
        row = self._fetch_session_row(session_id)
        return SessionRecord(**dict(row))

    def _write_raw_event(self, session_id: str, payload: dict[str, Any]) -> None:
        path = self._raw_export_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(stable_json(payload) + "\n")

    def _write_structured_event(self, session_id: str, event: EventRecord) -> None:
        path = self._log_path(session_id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(stable_json(asdict(event)) + "\n")
        with self._db() as conn:
            conn.execute(
                """
                insert or replace into events (
                    event_id, event_type, session_id, turn_index, step_index,
                    tool_call_id, created_at, duration_ms, status,
                    payload_json, raw_payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.session_id,
                    event.turn_index,
                    event.step_index,
                    event.tool_call_id,
                    event.created_at,
                    event.duration_ms,
                    event.status,
                    stable_json(event.payload),
                    stable_json(event.raw_payload) if event.raw_payload is not None else None,
                ),
            )

    def _record_event(
        self,
        *,
        session_id: str,
        event_type: str,
        turn_index: int,
        step_index: int,
        tool_call_id: str | None,
        status: str,
        payload: dict[str, Any],
        raw_payload: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> EventRecord:
        event = EventRecord(
            event_id=make_id("evt"),
            event_type=event_type,
            session_id=session_id,
            turn_index=turn_index,
            step_index=step_index,
            tool_call_id=tool_call_id,
            created_at=now(),
            duration_ms=duration_ms,
            status=status,
            payload=payload,
            raw_payload=raw_payload,
        )
        if raw_payload is not None:
            self._write_raw_event(session_id, raw_payload)
        self._write_structured_event(session_id, event)
        return event

    def start(self, *, session_id: str | None = None, notes: str | None = None) -> SessionRecord:
        session = SessionRecord(
            session_id=session_id or make_id("sess"),
            status="active",
            created_at=now(),
            updated_at=now(),
            current_turn_index=1,
            current_step_index=0,
            verified_turn_index=0,
            verified_step_index=0,
            pending_tool_call_id=None,
            last_checkpoint_id=None,
            raw_export_path=str(self._raw_export_path(session_id or "")),
            notes=notes,
        )
        session.raw_export_path = str(self._raw_export_path(session.session_id))
        self._insert_session(session)
        self._record_event(
            session_id=session.session_id,
            event_type="session.start",
            turn_index=1,
            step_index=0,
            tool_call_id=None,
            status="success",
            payload={"notes": notes},
        )
        return session

    def pause(self, session_id: str, *, reason: str | None = None) -> SessionRecord:
        session = self.load_session(session_id)
        session.status = "paused"
        session.notes = reason or session.notes
        self._update_session(session)
        self._record_event(
            session_id=session.session_id,
            event_type="session.pause",
            turn_index=session.current_turn_index,
            step_index=session.current_step_index,
            tool_call_id=session.pending_tool_call_id,
            status="success",
            payload={"reason": reason},
        )
        return session

    def resume(self, session_id: str, *, checkpoint_id: str | None = None) -> SessionRecord:
        session = self.load_session(session_id)
        checkpoint = self.load_latest_verified_checkpoint(session_id) if checkpoint_id is None else self.load_checkpoint(checkpoint_id)
        if not checkpoint["verified"]:
            raise VerifiedCheckpointError(f"checkpoint is not verified: {checkpoint['checkpoint_id']}")
        if checkpoint["session_id"] != session_id:
            raise VerifiedCheckpointError("checkpoint session mismatch")
        session.status = "active"
        session.current_turn_index = checkpoint["turn_index"] + 1
        session.current_step_index = 0
        session.verified_turn_index = checkpoint["turn_index"]
        session.verified_step_index = checkpoint["step_index"]
        session.pending_tool_call_id = None
        session.last_checkpoint_id = checkpoint["checkpoint_id"]
        self._update_session(session)
        self._record_event(
            session_id=session.session_id,
            event_type="session.resume",
            turn_index=session.current_turn_index,
            step_index=0,
            tool_call_id=None,
            status="success",
            payload={"checkpoint_id": checkpoint["checkpoint_id"]},
        )
        return session

    def archive(self, session_id: str, *, reason: str | None = None) -> dict[str, Any]:
        session = self.load_session(session_id)
        session.status = "archived"
        self._update_session(session)
        payload = {
            "session": asdict(session),
            "reason": reason,
            "archived_at": now(),
            "events": list(self.replay(session_id)),
        }
        archive_path = self._archive_path(session_id)
        archive_path.write_text(stable_json(payload) + "\n", encoding="utf-8")
        self._record_event(
            session_id=session.session_id,
            event_type="session.archive",
            turn_index=session.current_turn_index,
            step_index=session.current_step_index,
            tool_call_id=session.pending_tool_call_id,
            status="success",
            payload={"reason": reason, "archive_path": str(archive_path)},
        )
        return payload

    def record_context(self, session_id: str, *, context: str, turn_index: int | None = None) -> EventRecord:
        session = self.load_session(session_id)
        turn = turn_index or session.current_turn_index
        return self._record_event(
            session_id=session_id,
            event_type="turn.context",
            turn_index=turn,
            step_index=session.current_step_index,
            tool_call_id=session.pending_tool_call_id,
            status="success",
            payload={"context": context},
        )

    def _validate_tool_request(self, payload: dict[str, Any]) -> None:
        tool_name = str(payload.get("tool_name") or "")
        tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        cwd_value = str(payload.get("cwd") or workspace_root())
        cwd = Path(cwd_value).expanduser().resolve()
        ensure_workspace(cwd)

        for key in ("file_path", "path", "notebook_path"):
            raw_path = tool_input.get(key)
            if isinstance(raw_path, str) and raw_path.strip():
                candidate = Path(raw_path).expanduser()
                if not candidate.is_absolute():
                    candidate = (cwd / candidate).resolve()
                else:
                    candidate = candidate.resolve()
                if workspace_root().resolve() not in candidate.parents and candidate != workspace_root().resolve():
                    raise UnsafeToolRequestError(f"{tool_name} targets path outside workspace: {raw_path}")

        if tool_name == "Bash":
            command = str(tool_input.get("command") or "")
            normalized = command.replace("\\", "/")
            if any(token in normalized for token in ["rm -rf", "git reset --hard", "git clean -fd", "sudo "]):
                raise UnsafeToolRequestError(f"blocked unsafe Bash command: {command}")
            if ".." in normalized and any(marker in normalized for marker in [">", ">>", "tee", "cp ", "mv ", "cat "]):
                raise UnsafeToolRequestError(f"blocked out-of-workspace Bash command: {command}")

    def request_tool(self, payload: dict[str, Any]) -> EventRecord:
        session_id = str(payload.get("session_id") or "")
        if not session_id:
            raise Phase0Error("tool request is missing session_id")
        session = self.load_session(session_id)
        if session.status != "active":
            raise Phase0Error(f"session is not active: {session.status}")
        self._validate_tool_request(payload)
        if session.pending_tool_call_id is not None:
            raise Phase0Error("one verified step at a time: previous step is still pending")

        next_step = session.verified_step_index + 1
        if session.current_step_index not in (0, next_step):
            raise Phase0Error("step index is out of sequence")
        session.current_step_index = next_step
        session.pending_tool_call_id = str(payload.get("tool_use_id") or make_id("tool"))
        self._update_session(session)

        event = self._record_event(
            session_id=session_id,
            event_type="tool.request",
            turn_index=session.current_turn_index,
            step_index=session.current_step_index,
            tool_call_id=session.pending_tool_call_id,
            status="pending",
            payload=self._normalize_tool_request(payload, session),
            raw_payload=payload,
        )
        return event

    def _normalize_tool_request(self, payload: dict[str, Any], session: SessionRecord) -> dict[str, Any]:
        tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        return {
            "session_id": session.session_id,
            "turn_index": session.current_turn_index,
            "step_index": session.current_step_index,
            "tool_call_id": session.pending_tool_call_id,
            "tool_name": payload.get("tool_name"),
            "cwd": payload.get("cwd") or str(workspace_root()),
            "hook_event_name": payload.get("hook_event_name"),
            "permission_mode": payload.get("permission_mode"),
            "tool_input": tool_input,
        }

    def result_tool(self, payload: dict[str, Any]) -> EventRecord:
        session_id = str(payload.get("session_id") or "")
        if not session_id:
            raise Phase0Error("tool result is missing session_id")
        session = self.load_session(session_id)
        if session.pending_tool_call_id is None:
            raise Phase0Error("tool result has no pending request")
        tool_call_id = str(payload.get("tool_use_id") or session.pending_tool_call_id)
        if tool_call_id != session.pending_tool_call_id:
            raise Phase0Error("tool result does not match the pending tool call")

        duration_ms = int(payload.get("duration_ms") or 0) or None
        status = str(payload.get("status") or "success")
        event = self._record_event(
            session_id=session_id,
            event_type="tool.result",
            turn_index=session.current_turn_index,
            step_index=session.current_step_index,
            tool_call_id=tool_call_id,
            status=status,
            duration_ms=duration_ms,
            payload=self._normalize_tool_result(payload, session),
            raw_payload=payload,
        )
        if status == "success":
            session.pending_tool_call_id = tool_call_id
        else:
            session.status = "failed" if payload.get("terminal") else session.status
            session.pending_tool_call_id = None if payload.get("terminal") else tool_call_id
        self._update_session(session)
        return event

    def _normalize_tool_result(self, payload: dict[str, Any], session: SessionRecord) -> dict[str, Any]:
        tool_result = payload.get("tool_result")
        if tool_result is None and "tool_response" in payload:
            tool_result = payload.get("tool_response")
        return {
            "session_id": session.session_id,
            "turn_index": session.current_turn_index,
            "step_index": session.current_step_index,
            "tool_call_id": session.pending_tool_call_id,
            "tool_name": payload.get("tool_name"),
            "status": payload.get("status") or "success",
            "duration_ms": payload.get("duration_ms"),
            "result": tool_result,
            "error": payload.get("error"),
        }

    def verify(self, session_id: str, *, passed: bool, details: str | None = None) -> EventRecord:
        session = self.load_session(session_id)
        if session.current_step_index == 0:
            raise Phase0Error("no step is available to verify")
        if passed:
            session.verified_turn_index = session.current_turn_index
            session.verified_step_index = session.current_step_index
            session.current_turn_index += 1
            session.current_step_index = 0
            session.pending_tool_call_id = None
        session.status = "active" if passed else "needs-attention"
        self._update_session(session)
        return self._record_event(
            session_id=session.session_id,
            event_type="step.verify",
            turn_index=session.verified_turn_index if passed else session.current_turn_index,
            step_index=session.verified_step_index if passed else session.current_step_index,
            tool_call_id=None,
            status="success" if passed else "failure",
            payload={"passed": passed, "details": details},
        )

    def compact(self, session_id: str, *, reason: str | None = None) -> dict[str, Any]:
        session = self.load_session(session_id)
        if session.verified_step_index <= 0:
            raise VerifiedCheckpointError("cannot compact before a verified step exists")
        checkpoint_id = make_id("chk")
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "session_id": session.session_id,
            "turn_index": session.verified_turn_index,
            "step_index": session.verified_step_index,
            "verified": True,
            "created_at": now(),
            "reason": reason,
            "session": asdict(session),
        }
        checkpoint_path = self._checkpoint_path(session.session_id, session.verified_turn_index, session.verified_step_index)
        checkpoint_path.write_text(stable_json(checkpoint) + "\n", encoding="utf-8")
        with self._db() as conn:
            conn.execute(
                """
                insert or replace into checkpoints (
                    checkpoint_id, session_id, turn_index, step_index, created_at, path, verified
                ) values (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    checkpoint_id,
                    session.session_id,
                    session.verified_turn_index,
                    session.verified_step_index,
                    checkpoint["created_at"],
                    str(checkpoint_path),
                ),
            )
        session.last_checkpoint_id = checkpoint_id
        self._update_session(session)
        self._record_event(
            session_id=session.session_id,
            event_type="session.compact",
            turn_index=session.verified_turn_index,
            step_index=session.verified_step_index,
            tool_call_id=None,
            status="success",
            payload={"reason": reason, "checkpoint_id": checkpoint_id, "checkpoint_path": str(checkpoint_path)},
        )
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        with self._db() as conn:
            row = conn.execute("select * from checkpoints where checkpoint_id = ?", (checkpoint_id,)).fetchone()
        if row is None:
            raise VerifiedCheckpointError(f"unknown checkpoint: {checkpoint_id}")
        path = Path(row["path"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["checkpoint_id"] = row["checkpoint_id"]
        payload["session_id"] = row["session_id"]
        payload["turn_index"] = row["turn_index"]
        payload["step_index"] = row["step_index"]
        payload["verified"] = bool(row["verified"])
        return payload

    def load_latest_verified_checkpoint(self, session_id: str) -> dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                """
                select * from checkpoints
                where session_id = ? and verified = 1
                order by created_at desc, turn_index desc, step_index desc
                limit 1
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise VerifiedCheckpointError("no verified checkpoint available")
        return self.load_checkpoint(str(row["checkpoint_id"]))

    def replay(self, session_id: str) -> list[dict[str, Any]]:
        path = self._log_path(session_id)
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            records.append(json.loads(raw))
        return records

    def reconstruct(self, session_id: str) -> dict[str, Any]:
        session = asdict(self.load_session(session_id))
        events = self.replay(session_id)
        return {"session": session, "events": events}

    def execute_tool(
        self,
        payload: dict[str, Any],
        executor: Callable[[dict[str, Any]], dict[str, Any] | Any],
        *,
        retries: int = MAX_RETRIES,
    ) -> dict[str, Any]:
        request_event = self.request_tool(payload)
        attempts = 0
        start = time.monotonic()
        last_error: BaseException | None = None
        while attempts <= retries:
            attempts += 1
            try:
                result = executor(payload)
                duration_ms = monotonic_ms(start)
                result_payload = {
                    "session_id": request_event.session_id,
                    "tool_use_id": request_event.tool_call_id,
                    "tool_name": payload.get("tool_name"),
                    "status": "success",
                    "duration_ms": duration_ms,
                    "attempt": attempts,
                    "tool_result": result,
                }
                self.result_tool(result_payload)
                return result_payload
            except BaseException as exc:  # noqa: BLE001 - explicit terminal conversion below
                last_error = exc
                if attempts <= retries and is_retryable_failure(exc):
                    self._record_event(
                        session_id=request_event.session_id,
                        event_type="tool.retry",
                        turn_index=request_event.turn_index,
                        step_index=request_event.step_index,
                        tool_call_id=request_event.tool_call_id,
                        status="retry",
                        duration_ms=monotonic_ms(start),
                        payload={"attempt": attempts, "retryable": True, "error": f"{exc.__class__.__name__}: {exc}"},
                    )
                    continue
                duration_ms = monotonic_ms(start)
                failure_payload = {
                    "session_id": request_event.session_id,
                    "tool_use_id": request_event.tool_call_id,
                    "tool_name": payload.get("tool_name"),
                    "status": "failure",
                    "duration_ms": duration_ms,
                    "attempt": attempts,
                    "tool_result": None,
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "terminal": True,
                }
                self.result_tool(failure_payload)
                raise TerminalToolFailure(
                    f"terminal failure after {attempts} attempts for {payload.get('tool_name')}: {exc}"
                ) from exc
        raise TerminalToolFailure(f"terminal failure after {attempts} attempts: {last_error}")


def command_start(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session = control.start(
        session_id=args.session_id or str(payload.get("session_id") or payload.get("sessionId") or ""),
        notes=args.notes or payload.get("initialUserMessage") or payload.get("notes") or payload.get("message"),
    )
    print(stable_json(asdict(session)))
    return 0


def command_pause(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session_id = args.session_id or str(payload.get("session_id") or payload.get("sessionId") or "")
    session = control.pause(session_id, reason=args.reason or payload.get("reason"))
    print(stable_json(asdict(session)))
    return 0


def command_resume(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session_id = args.session_id or str(payload.get("session_id") or payload.get("sessionId") or "")
    checkpoint_id = args.checkpoint_id or payload.get("checkpoint_id") or payload.get("checkpointId")
    session = control.resume(session_id, checkpoint_id=checkpoint_id)
    print(stable_json(asdict(session)))
    return 0


def command_archive(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session_id = args.session_id or str(payload.get("session_id") or payload.get("sessionId") or "")
    archive = control.archive(session_id, reason=args.reason or payload.get("reason"))
    print(stable_json(archive))
    return 0


def command_compact(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session_id = args.session_id or str(payload.get("session_id") or payload.get("sessionId") or "")
    checkpoint = control.compact(session_id, reason=args.reason or payload.get("reason"))
    print(stable_json(checkpoint))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    session_id = args.session_id or str(payload.get("session_id") or payload.get("sessionId") or "")
    failed = args.failed or bool(payload.get("failed") or payload.get("is_error"))
    details = args.details or payload.get("details") or payload.get("reason") or payload.get("message")
    event = control.verify(session_id, passed=not failed, details=details)
    print(stable_json(asdict(event)))
    return 0


def command_request(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    if not payload:
        payload = {
            "session_id": args.session_id,
            "tool_name": args.tool_name,
            "tool_input": json.loads(args.tool_input) if args.tool_input else {},
            "cwd": args.cwd,
            "hook_event_name": args.hook_event_name,
            "permission_mode": args.permission_mode,
            "tool_use_id": args.tool_use_id,
        }
    event = control.request_tool(payload)
    print(stable_json(asdict(event)))
    return 0


def command_result(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    payload = read_stdin_json()
    if not payload:
        payload = {
            "session_id": args.session_id,
            "tool_name": args.tool_name,
            "tool_use_id": args.tool_use_id,
            "status": args.status,
            "duration_ms": args.duration_ms,
            "tool_result": json.loads(args.tool_result) if args.tool_result else None,
            "error": args.error,
        }
    event = control.result_tool(payload)
    print(stable_json(asdict(event)))
    return 0


def command_replay(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    print(stable_json(control.replay(args.session_id)))
    return 0


def command_reconstruct(args: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    print(stable_json(control.reconstruct(args.session_id)))
    return 0


def command_self_test(_: argparse.Namespace) -> int:
    control = Phase0ControlPlane()
    session = control.start(notes="self-test")
    control.record_context(session.session_id, context="gather context")
    request = {
        "session_id": session.session_id,
        "tool_name": "Write",
        "tool_input": {"file_path": "CLAUDE.md"},
        "cwd": str(workspace_root()),
        "tool_use_id": "tool-1",
    }
    control.request_tool(request)
    control.result_tool(
        {
            "session_id": session.session_id,
            "tool_use_id": "tool-1",
            "tool_name": "Write",
            "status": "success",
            "duration_ms": 1,
            "tool_result": {"ok": True},
        }
    )
    control.verify(session.session_id, passed=True, details="self-test")
    control.compact(session.session_id, reason="self-test")
    print("phase0 self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase0_control_plane")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("--session-id")
    p.add_argument("--notes")
    p.set_defaults(func=command_start)

    p = sub.add_parser("pause")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--reason")
    p.set_defaults(func=command_pause)

    p = sub.add_parser("resume")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--checkpoint-id")
    p.set_defaults(func=command_resume)

    p = sub.add_parser("archive")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--reason")
    p.set_defaults(func=command_archive)

    p = sub.add_parser("compact")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--reason")
    p.set_defaults(func=command_compact)

    p = sub.add_parser("verify")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--failed", action="store_true")
    p.add_argument("--details")
    p.set_defaults(func=command_verify)

    p = sub.add_parser("request")
    p.add_argument("--session-id")
    p.add_argument("--tool-name")
    p.add_argument("--tool-input")
    p.add_argument("--cwd")
    p.add_argument("--hook-event-name")
    p.add_argument("--permission-mode")
    p.add_argument("--tool-use-id")
    p.set_defaults(func=command_request)

    p = sub.add_parser("result")
    p.add_argument("--session-id")
    p.add_argument("--tool-name")
    p.add_argument("--tool-use-id")
    p.add_argument("--status", default="success")
    p.add_argument("--duration-ms", type=int)
    p.add_argument("--tool-result")
    p.add_argument("--error")
    p.set_defaults(func=command_result)

    p = sub.add_parser("replay")
    p.add_argument("session_id")
    p.set_defaults(func=command_replay)

    p = sub.add_parser("reconstruct")
    p.add_argument("session_id")
    p.set_defaults(func=command_reconstruct)

    p = sub.add_parser("self-test")
    p.set_defaults(func=command_self_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except UnsafeToolRequestError as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2
    except VerifiedCheckpointError as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2
    except TerminalToolFailure as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Phase0Error as exc:
        print(f"Phase0 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

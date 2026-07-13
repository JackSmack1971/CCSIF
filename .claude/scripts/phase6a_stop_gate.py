#!/usr/bin/env python3
"""Bounded Stop-gate (Phase 6A rung 4).

Reads the Stop hook JSON payload on stdin, runs the repo's two required
verification checks (`control_plane_check.py`, `rules_fidelity_check.py`),
and blocks the turn (exit 2) while they fail -- but only up to
`MAX_RETRIES` times per `session_id`. Exceeding the bound, or a Stop hook
invocation where `stop_hook_active` is already true (Claude Code is
re-invoking this same Stop hook as a direct result of a prior block),
appends an escalation record to the ledger via `ledger_append.py` and
allows the stop instead. An infinite stop loop is never reachable: the
retry counter is bounded, and `stop_hook_active=true` is treated as an
immediate escalate-and-allow case regardless of the counter.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Overridable for tests, mirroring Phase 0's PHASE0_STATE_ROOT pattern, so a
# unit test can point retry/event state and the ledger at a scratch
# directory instead of this repo's real .claude/state/.
STATE_ROOT = Path(os.getenv("PHASE6A_STATE_ROOT", str(ROOT / ".claude" / "state"))).expanduser().resolve()
LEDGER_PATH = Path(os.getenv("PHASE6A_LEDGER_PATH", str(ROOT / ".claude" / "state" / "ledger.md"))).expanduser().resolve()
RETRY_DIR = STATE_ROOT / "logs" / "stop-retries"
EVENT_LOG = STATE_ROOT / "logs" / "stop-gate-events.jsonl"
MAX_RETRIES = 3

CHECK_COMMANDS = [
    ["python3", str(ROOT / ".claude" / "scripts" / "control_plane_check.py")],
    ["python3", str(ROOT / ".claude" / "scripts" / "rules_fidelity_check.py")],
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def retry_path(session_id: str) -> Path:
    return RETRY_DIR / f"{session_id}.json"


def load_retry_state(session_id: str) -> dict:
    path = retry_path(session_id)
    if not path.exists():
        return {"retries": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - corrupt state file, start fresh
        return {"retries": 0}


def save_retry_state(session_id: str, state: dict) -> None:
    path = retry_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def clear_retry_state(session_id: str) -> None:
    path = retry_path(session_id)
    if path.exists():
        path.unlink()


def run_checks() -> tuple[bool, str]:
    output_lines = []
    ok = True
    for cmd in CHECK_COMMANDS:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        output_lines.append(f"$ {' '.join(cmd)}\n{proc.stdout}{proc.stderr}")
        if proc.returncode != 0:
            ok = False
    return ok, "\n".join(output_lines)


def log_event(event: dict) -> None:
    try:
        EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with EVENT_LOG.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:  # noqa: BLE001 - logging must never crash the gate
        pass


def escalate(session_id: str, retries: int, evidence: str) -> None:
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import ledger_append  # noqa: E402

    body = (
        f"- Session `{session_id}` exceeded the Stop-gate bound of "
        f"{MAX_RETRIES} verification retries (retries observed: {retries}).\n"
        f"- Evidence (last check output, truncated):\n\n```\n{evidence[-4000:]}\n```\n"
        f"- Preserved state: `.claude/state/logs/stop-retries/{session_id}.json` "
        f"(cleared after this escalation); the turn was allowed to stop rather "
        f"than looping forever."
    )
    try:
        ledger_append.append_entry("Phase 6A Stop-gate escalation", body, ledger_path=LEDGER_PATH)
    except Exception:  # noqa: BLE001 - escalation must never crash the gate
        pass


def evaluate(payload: dict) -> dict:
    session_id = payload.get("session_id") or "unknown-session"
    stop_hook_active = bool(payload.get("stop_hook_active", False))
    start = time.monotonic()
    correlation_id = str(uuid.uuid4())

    if not (ROOT / ".git").exists():
        decision = {"action": "allow", "reason": "not a git worktree", "correlation_id": correlation_id}
        log_event({
            "ts": now(),
            "session_id": session_id,
            "action": decision["action"],
            "reason": decision["reason"],
            "correlation_id": correlation_id,
            "duration_ms": int((time.monotonic() - start) * 1000),
        })
        return decision

    state = load_retry_state(session_id)
    retries = int(state.get("retries", 0))

    ok, evidence = run_checks()

    if ok:
        clear_retry_state(session_id)
        decision = {"action": "allow", "reason": "verification passed", "retries_used": retries}
        log_event({
            "ts": now(),
            "session_id": session_id,
            "action": decision["action"],
            "reason": decision["reason"],
            "retries_used": retries,
            "correlation_id": correlation_id,
            "duration_ms": int((time.monotonic() - start) * 1000),
        })
        return decision

    if stop_hook_active:
        clear_retry_state(session_id)
        escalate(session_id, retries, evidence)
        decision = {
            "action": "allow",
            "reason": "stop_hook_active=true; escalating instead of re-blocking",
            "retries_used": retries,
            "escalated": True,
        }
        log_event({
            "ts": now(),
            "session_id": session_id,
            "action": decision["action"],
            "reason": decision["reason"],
            "retries_used": retries,
            "escalated": True,
            "correlation_id": correlation_id,
            "duration_ms": int((time.monotonic() - start) * 1000),
        })
        return decision

    retries += 1
    if retries > MAX_RETRIES:
        clear_retry_state(session_id)
        escalate(session_id, retries, evidence)
        decision = {
            "action": "allow",
            "reason": f"retry bound ({MAX_RETRIES}) exceeded; escalating instead of looping forever",
            "retries_used": retries,
            "escalated": True,
        }
        log_event({
            "ts": now(),
            "session_id": session_id,
            "action": decision["action"],
            "reason": decision["reason"],
            "retries_used": retries,
            "escalated": True,
            "correlation_id": correlation_id,
            "duration_ms": int((time.monotonic() - start) * 1000),
        })
        return decision

    save_retry_state(session_id, {"retries": retries})
    decision = {
        "action": "block",
        "reason": f"verification failed (retry {retries}/{MAX_RETRIES})",
        "retries_used": retries,
        "evidence": evidence[-4000:],
    }
    log_event({
        "ts": now(),
        "session_id": session_id,
        "action": decision["action"],
        "reason": decision["reason"],
        "retries_used": retries,
        "correlation_id": correlation_id,
        "duration_ms": int((time.monotonic() - start) * 1000),
    })
    return decision


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as exc:  # noqa: BLE001
        # Malformed Stop payload: fail open (allow the stop) rather than
        # block indefinitely on unreadable input.
        log_event({"ts": now(), "session_id": None, "action": "allow", "reason": f"unreadable Stop payload: {exc}"})
        return 0

    decision = evaluate(payload)
    if decision["action"] == "block":
        sys.stderr.write(
            f"Stop-gate: verification failed (retry {decision['retries_used']}/{MAX_RETRIES}). "
            f"Fix the failing check(s) before ending the turn.\n{decision.get('evidence', '')}\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

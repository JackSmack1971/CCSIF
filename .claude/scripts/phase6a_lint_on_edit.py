#!/usr/bin/env python3
"""PostToolUse lint-on-edit (Phase 6A rung 4 format/lint-on-edit).

Reads the PostToolUse JSON payload on stdin. When the tool was a
file-mutating one (Write/Edit/NotebookEdit), runs the verify adapter's
`lint` target once and appends one JSONL event to
`.claude/state/logs/lint-events.jsonl`. PostToolUse cannot block a tool
call that already ran (per the documented hook contract), so this is
observational: it never raises the failure as a blocking error, it makes
the failure visible in logs and (best-effort) on stderr so the transcript
surfaces it as a non-blocking annotation.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / ".claude" / "state" / "logs" / "lint-events.jsonl"
MUTATING_TOOLS = {"Write", "Edit", "NotebookEdit"}

sys.path.insert(0, str(ROOT / ".claude" / "scripts"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_event(event: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:  # noqa: BLE001 - logging must never crash the hook
        pass


def main() -> int:
    start = time.monotonic()
    correlation_id = str(uuid.uuid4())
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as exc:  # noqa: BLE001
        log_event(
            {
                "ts": now(),
                "correlation_id": correlation_id,
                "decision": "error",
                "reason": f"unreadable PostToolUse payload: {exc}",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
        )
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in MUTATING_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path")

    # Import the verify adapter directly rather than shelling out to
    # verify.sh: a bare `bash` on PATH can resolve to a non-git-bash
    # interpreter (e.g. the WSL launcher) on Windows, which mis-resolves a
    # native Windows path. Calling `phase5b_verify.run_target` in-process is
    # still "the adapter" (same module verify.sh itself wraps), just without
    # the shell hop.
    import phase5b_verify  # noqa: E402

    result = phase5b_verify.run_target("lint", manifest=ROOT / ".claude" / "verification.json", cwd=ROOT)
    exit_code = result["exit_code"]
    event = {
        "ts": now(),
        "correlation_id": correlation_id,
        "tool_name": tool_name,
        "file_path": file_path,
        "decision": "pass" if exit_code == 0 else ("unavailable" if exit_code == 2 else "fail"),
        "exit_code": exit_code,
        "duration_ms": int((time.monotonic() - start) * 1000),
    }
    log_event(event)
    if exit_code == 1:
        sys.stderr.write(
            f"lint-on-edit: touched-file lint failed after editing {file_path!r} "
            f"(exit {exit_code}); see {LOG_PATH} for the correlation id "
            f"{correlation_id!r}.\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

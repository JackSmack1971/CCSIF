#!/usr/bin/env python3
"""Deterministic control-plane validation for CCSIF."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/scripts/phase0_control_plane.py",
    ".claude/hooks/pre-tool-use.sh",
    ".claude/hooks/lib/pre-tool-use-guard.js",
    ".claude/hooks/post-tool-use.sh",
    ".claude/hooks/session-start.sh",
    ".claude/hooks/pre-compact.sh",
    ".claude/hooks/stop.sh",
    ".claude/commands/control-plane-check.md",
]
PROTECTED_PROBES = [
    {"tool_name": "Write", "tool_input": {"file_path": ".env"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".github/workflows/release.yml"}},
    {"tool_name": "Write", "tool_input": {"file_path": "migrations/001_init.sql"}},
    {"tool_name": "Bash", "tool_input": {"command": "cat x >> .env"}},
    {"tool_name": "Bash", "tool_input": {"command": "cat x >> .github/workflows/release.yml"}},
]
ALLOWED_PROBES = [
    {"tool_name": "Write", "tool_input": {"file_path": "CLAUDE.md"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".claude/hooks/pre-tool-use.sh"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".7axes/ledger.jsonl"}},
    {"tool_name": "Bash", "tool_input": {"command": "cat x >> .claude/settings.json"}},
]


def run(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, input=input_text, text=True, capture_output=True, check=False)


def resolve_node() -> str:
    for candidate in ("node", "node.exe"):
        path = shutil.which(candidate)
        if path:
            return path

    for candidate in ("node", "node.exe"):
        proc = run(["where.exe", candidate])
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line:
                    return line

    fail("unable to locate node or node.exe on PATH")


def node_script_arg(node: str, path: Path) -> str:
    if node.lower().endswith(".exe") and os.name != "nt":
        proc = run(["wslpath", "-w", str(path)])
        if proc.returncode == 0:
            return proc.stdout.strip()
    return str(path)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        fail(f"missing required control-plane paths: {', '.join(missing)}")


def check_json() -> None:
    try:
        json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report exact parse failure
        fail(f".claude/settings.json is not valid JSON: {exc}")


def check_git_visibility() -> None:
    proc = run(["git", "check-ignore", *REQUIRED_PATHS])
    if proc.stdout.strip():
        fail(f"required control-plane paths are ignored by git: {proc.stdout.strip()}")


def check_guard_probes() -> None:
    guard = ROOT / ".claude/hooks/lib/pre-tool-use-guard.js"
    node = resolve_node()
    guard_arg = node_script_arg(node, guard)
    for probe in PROTECTED_PROBES:
        proc = run([node, guard_arg], input_text=json.dumps(probe))
        if proc.returncode != 2:
            fail(f"guard did not block protected probe {probe!r}; rc={proc.returncode}; stderr={proc.stderr.strip()}")


def check_allowed_probes() -> None:
    guard = ROOT / ".claude/hooks/lib/pre-tool-use-guard.js"
    node = resolve_node()
    guard_arg = node_script_arg(node, guard)
    for probe in ALLOWED_PROBES:
        proc = run([node, guard_arg], input_text=json.dumps(probe))
        if proc.returncode != 0:
            fail(f"guard incorrectly blocked allowed probe {probe!r}; rc={proc.returncode}; stderr={proc.stderr.strip()}")


def check_fd_dup_redirects() -> None:
    guard = ROOT / ".claude/hooks/lib/pre-tool-use-guard.js"
    node = resolve_node()
    guard_arg = node_script_arg(node, guard)
    for command in ["cat x 2>&1", "echo hi >&2", "printf ok 1>&2"]:
        probe = {"tool_name": "Bash", "tool_input": {"command": command}}
        proc = run([node, guard_arg], input_text=json.dumps(probe))
        if proc.returncode != 0:
            fail(f"guard incorrectly blocked fd-dup redirect probe {probe!r}; rc={proc.returncode}; stderr={proc.stderr.strip()}")


def check_shell_parse() -> None:
    for script in [
        ".claude/hooks/session-start.sh",
        ".claude/hooks/pre-tool-use.sh",
        ".claude/hooks/post-tool-use.sh",
        ".claude/hooks/pre-compact.sh",
        ".claude/hooks/stop.sh",
    ]:
        proc = run(["bash", "-n", script])
        if proc.returncode != 0:
            fail(f"{script} failed bash -n: {proc.stderr.strip()}")


def main() -> int:
    check_required_paths()
    check_json()
    check_git_visibility()
    check_shell_parse()
    check_allowed_probes()
    check_guard_probes()
    check_fd_dup_redirects()
    print("control-plane-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

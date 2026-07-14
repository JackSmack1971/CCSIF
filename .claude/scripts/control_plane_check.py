#!/usr/bin/env python3
"""Deterministic control-plane validation for CCSIF."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    "CLAUDE.md",
    ".claude/verification-manifest.json",
    ".claude/settings.json",
    ".claude/rules/00-core-workflow.md",
    ".claude/rules/10-karpathy-guidelines.md",
    ".claude/rules/20-lifecycle-gates.md",
    ".claude/rules/30-skill-taxonomy.md",
    ".claude/scripts/phase5b_lifecycle.py",
    ".claude/scripts/phase5b_verify.py",
    ".claude/scripts/verification_manifest.py",
    ".claude/scripts/control_plane_check.py",
    ".claude/hooks/verify.sh",
    ".claude/hooks/verify.ps1",
    ".claude/plans/.gitkeep",
    ".claude/state/ledger.md",
    ".claude/state/research/.gitkeep",
    ".claude/state/agents/.gitkeep",
    ".claude/state/handoffs/.gitkeep",
    ".claude/state/compactions/.gitkeep",
    ".claude/state/workflows/.gitkeep",
]

PROTECTED_PROBES = [
    {"tool_name": "Write", "tool_input": {"file_path": ".env"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".github/workflows/release.yml"}},
    {"tool_name": "Write", "tool_input": {"file_path": "migrations/001_init.sql"}},
    {"tool_name": "Bash", "tool_input": {"command": "cat x >> .env"}},
    {"tool_name": "Bash", "tool_input": {"command": "cat x >> .github/workflows/release.yml"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".claude/state/ledger.md"}},
    {"tool_name": "Write", "tool_input": {"file_path": "../../etc/passwd"}},
]
ALLOWED_PROBES = [
    {"tool_name": "Write", "tool_input": {"file_path": "CLAUDE.md"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".claude/hooks/pre-tool-use.sh"}},
    {"tool_name": "Write", "tool_input": {"file_path": ".7axes/ledger.jsonl"}},
    {"tool_name": "Bash", "tool_input": {"command": "npm install lodash"}},
    {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
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
    except Exception as exc:  # noqa: BLE001
        fail(f".claude/settings.json is not valid JSON: {exc}")


def check_verify_adapter() -> None:
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import phase5b_verify  # noqa: E402

    try:
        targets = phase5b_verify.list_targets()
    except phase5b_verify.VerifyAdapterError as exc:
        fail(f"verify adapter cannot parse verification manifest: {exc}")
    if not targets["individual_targets"]:
        fail("verify adapter parsed zero verification targets from the manifest")
    result = phase5b_verify.run_target("smoke", cwd=ROOT)
    if result["exit_code"] != 0:
        fail(f"verify adapter's own 'smoke' target did not pass: {result}")


def main() -> int:
    check_required_paths()
    check_json()
    check_verify_adapter()
    print("control-plane-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

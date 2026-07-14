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
    ".claude/scripts/phase2_memory.py",
    ".claude/scripts/phase3_agents.py",
    ".claude/scripts/phase4_workflows.py",
    ".claude/scripts/taxonomy_check.py",
    ".claude/hooks/pre-tool-use.sh",
    ".claude/hooks/lib/pre-tool-use-guard.js",
    ".claude/hooks/post-tool-use.sh",
    ".claude/hooks/session-start.sh",
    ".claude/hooks/pre-compact.sh",
    ".claude/hooks/post-compact.sh",
    ".claude/hooks/subagent-start.sh",
    ".claude/hooks/subagent-stop.sh",
    ".claude/hooks/stop.sh",
    ".claude/commands/control-plane-check.md",
    ".claude/agents/scout.md",
    ".claude/agents/planner.md",
    ".claude/agents/builder.md",
    ".claude/agents/verifier.md",
    ".claude/commands/workflow.md",
    ".claude/rules/dynamic-workflows.md",
    ".claude/workflows/defs/linear-static.json",
    ".claude/workflows/defs/evidence-branch.json",
    ".claude/plans/.gitkeep",
    ".claude/state/compactions/.gitkeep",
    ".claude/state/agents/.gitkeep",
    ".claude/state/workflows/.gitkeep",
    ".claude/scripts/phase5b_lifecycle.py",
    ".claude/scripts/phase5b_verify.py",
    ".claude/hooks/verify.sh",
    ".claude/hooks/verify.ps1",
    ".claude/commands/brainstorm.md",
    ".claude/commands/grill.md",
    ".claude/commands/research.md",
    ".claude/commands/plan.md",
    ".claude/commands/build.md",
    ".claude/commands/verify.md",
    ".claude/commands/ship.md",
    ".claude/commands/handoff.md",
    ".claude/commands/status.md",
    ".claude/commands/debug.md",
    ".claude/commands/experiment.md",
    ".claude/skills/alignment-interview/SKILL.md",
    ".claude/skills/atomic-planning/SKILL.md",
    ".claude/skills/session-takeover/SKILL.md",
    ".claude/skills/metric-gated-experiment/SKILL.md",
    ".claude/scripts/bootstrap_control_plane.py",
    ".claude/commands/bootstrap-control-plane.md",
    ".claude/scripts/phase5c_portability_proof.py",
    ".claude/scripts/phase5c_context_pressure.py",
    ".claude/rules/40-determinism-ladder.md",
    ".claude/scripts/ledger_append.py",
    ".claude/scripts/phase6a_lint_on_edit.py",
    ".claude/scripts/phase6a_stop_gate.py",
    ".claude/scripts/phase6a_metrics.py",
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
GENERATED_STATE_PATHS = [
    ".claude/state/phase0.sqlite3",
    ".claude/state/raw",
    ".claude/state/logs",
    ".claude/state/checkpoints",
    ".claude/state/archive",
    ".claude/state/compactions/example-restore.json",
    ".claude/state/agents/example-session/example-agent.json",
    ".claude/state/workflows/example-run.json",
]
TRACKED_STATE_PATHS = [
    ".claude/state/ledger.md",
    ".claude/state/baseline.md",
    ".claude/state/completion-matrix.md",
    ".claude/state/execution-manifest.json",
    ".claude/state/roadmap/phase-0-checkpoint.json",
    ".claude/state/compactions/.gitkeep",
    ".claude/state/agents/.gitkeep",
    ".claude/state/workflows/.gitkeep",
    ".claude/state/research/.gitkeep",
    ".claude/state/handoffs/.gitkeep",
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


# Vendored, pinned key set for `permissions.*` in project-scope
# `.claude/settings.json`, hand-derived from the packaged docs snapshot at
# `.claude/docs/claude-code-docs-2026-07-12-00-15-46/docs/
# code-claude-com-docs-en-settings-545f9c5a.md` (the "Available settings"
# table, lines ~396-405) rather than a live fetch of the external
# `$schema` URL, since that schema "may not include settings added in the
# most recent CLI releases" per the same doc. Update this set only after
# re-deriving it from a refreshed docs snapshot; do not silently widen it
# to make a new key pass.
PERMISSIONS_ALLOWED_KEYS = {
    "allow",
    "ask",
    "deny",
    "additionalDirectories",
    "defaultMode",
    "disableBypassPermissionsMode",
    "skipDangerousModePermissionPrompt",
}


def check_settings_permissions_schema() -> None:
    """Deterministic, offline check that `.claude/settings.json`'s
    `permissions` block contains no key outside the documented/vendored
    key set (Hardening 02/13, #150 finding 1: an unrecognized key such as
    the previous `permissions.mode` silently no-ops instead of raising a
    visible error, so this must be caught structurally, not by hoping
    JSON parses)."""
    data = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    permissions = data.get("permissions")
    if permissions is None:
        return
    if not isinstance(permissions, dict):
        fail("`.claude/settings.json`'s `permissions` key must be an object")
    unknown = sorted(set(permissions) - PERMISSIONS_ALLOWED_KEYS)
    if unknown:
        fail(
            "`.claude/settings.json` `permissions` block has unrecognized key(s) "
            f"not in the documented settings schema: {', '.join(unknown)}"
        )


def check_git_visibility() -> None:
    proc = run(["git", "check-ignore", *REQUIRED_PATHS])
    if proc.stdout.strip():
        fail(f"required control-plane paths are ignored by git: {proc.stdout.strip()}")


def check_state_privacy_ignore() -> None:
    proc = run(["git", "check-ignore", *GENERATED_STATE_PATHS])
    ignored = set(proc.stdout.split())
    missing = [path for path in GENERATED_STATE_PATHS if path not in ignored]
    if missing:
        fail(f"generated .claude/state/ paths are not gitignored: {', '.join(missing)}")

    proc = run(["git", "check-ignore", *TRACKED_STATE_PATHS])
    if proc.stdout.strip():
        fail(f"tracked .claude/state/ paths are unexpectedly gitignored: {proc.stdout.strip()}")


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
        ".claude/hooks/post-compact.sh",
        ".claude/hooks/subagent-start.sh",
        ".claude/hooks/subagent-stop.sh",
        ".claude/hooks/stop.sh",
        ".claude/hooks/verify.sh",
    ]:
        proc = run(["bash", "-n", script])
        if proc.returncode != 0:
            fail(f"{script} failed bash -n: {proc.stderr.strip()}")


def check_workflow_defs() -> None:
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import phase4_workflows  # noqa: E402

    for name in ("linear-static", "evidence-branch"):
        try:
            phase4_workflows.load_workflow_def(name, workspace=ROOT)
        except phase4_workflows.Phase4Error as exc:
            fail(f"workflow definition {name!r} is invalid: {exc}")


def check_taxonomy() -> None:
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import taxonomy_check  # noqa: E402

    try:
        taxonomy_check.run_all(ROOT)
    except taxonomy_check.TaxonomyError as exc:
        fail(f"taxonomy check failed: {exc}")


def check_verify_adapter() -> None:
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    import phase5b_verify  # noqa: E402

    try:
        targets = phase5b_verify.list_targets(claude_md=ROOT / "CLAUDE.md")
    except phase5b_verify.VerifyAdapterError as exc:
        fail(f"verify adapter cannot parse CLAUDE.md source-of-truth commands: {exc}")
    if not targets["individual_targets"]:
        fail("verify adapter parsed zero source-of-truth commands from CLAUDE.md")
    # Use the "rules" target, not "control-plane": the latter would shell
    # out to this very script and recurse.
    result = phase5b_verify.run_target("rules", claude_md=ROOT / "CLAUDE.md", cwd=ROOT)
    if result["exit_code"] != 0:
        fail(f"verify adapter's own 'rules' target did not pass: {result}")


def main() -> int:
    check_required_paths()
    check_json()
    check_settings_permissions_schema()
    check_git_visibility()
    check_state_privacy_ignore()
    check_shell_parse()
    check_allowed_probes()
    check_guard_probes()
    check_fd_dup_redirects()
    check_workflow_defs()
    check_taxonomy()
    check_verify_adapter()
    print("control-plane-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

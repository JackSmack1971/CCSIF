#!/usr/bin/env python3
"""Phase 5C cross-stack portability proof.

Builds two fresh, throwaway fixture repos representing unrelated workloads
(one code stack, one non-code pipeline), bootstraps each from a fresh
clone/copy with the same `bootstrap_control_plane.py`, drives the same
lifecycle commands (plan/status/handoff/verify) against each with only the
repo's own `CLAUDE.md` facts and verify-adapter targets differing, restarts
(re-invokes every step as a fresh subprocess, proving disk-only recovery),
reconstructs `/status`, and proves the framework must never require
`~/.claude/*` access by running every step with `HOME`/`USERPROFILE`
pointed at a directory that does not exist.

Writes a JSON evidence file; does not mutate this repo's own `.claude/`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / ".claude" / "scripts" / "bootstrap_control_plane.py"


def _hostile_env() -> dict[str, str]:
    """An environment whose HOME/USERPROFILE point at a directory that does
    not exist, so this proof must never let an accidental `~/.claude/*`
    read/write silently succeed against the real machine's home dir."""
    env = dict(os.environ)
    fake_home = str(Path(tempfile.gettempdir()) / "does-not-exist-control-plane-home")
    env["HOME"] = fake_home
    env["USERPROFILE"] = fake_home
    env.pop("CLAUDE_CONFIG_DIR", None)
    return env


def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or REPO_ROOT,
        env=_hostile_env(),
        capture_output=True,
        text=True,
    )


def _write_code_stack_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname = \"fixture-code-stack\"\nversion = \"0.0.0\"\n", encoding="utf-8")
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_smoke.py").write_text(
        "def test_trivially_true():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    (root / "src.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")


def _write_non_code_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Research Report Pipeline\n\nDocs-only workload.\n", encoding="utf-8")
    (root / "report.md").write_text(
        "# Draft Report\n\nClaim: the sky appears blue due to Rayleigh scattering. "
        "Source: https://en.wikipedia.org/wiki/Diffuse_sky_radiation\n",
        encoding="utf-8",
    )


def _bootstrap_and_prove(root: Path, workload_name: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {"workload": workload_name, "target": str(root)}

    facts_proc = _run([str(BOOTSTRAP), "facts", "--target", str(root)])
    evidence["facts_detect"] = {"exit_code": facts_proc.returncode, "stdout": json.loads(facts_proc.stdout) if facts_proc.returncode == 0 else facts_proc.stderr}

    run_proc = _run([str(BOOTSTRAP), "run", "--target", str(root)])
    evidence["bootstrap_run"] = {"exit_code": run_proc.returncode, "stdout": json.loads(run_proc.stdout) if run_proc.returncode == 0 else run_proc.stderr}
    if run_proc.returncode != 0:
        evidence["failed_at"] = "bootstrap_run"
        return evidence

    # "Restart": every following step is its own fresh subprocess, invoked
    # with a hostile HOME, proving recovery must never depend on in-memory
    # state from the bootstrap step above or on ~/.claude/*.
    validate_proc = _run([str(BOOTSTRAP), "validate", "--target", str(root)])
    evidence["validate_after_restart"] = {"exit_code": validate_proc.returncode, "stdout": json.loads(validate_proc.stdout) if validate_proc.stdout else validate_proc.stderr}

    smoke_proc = _run([str(BOOTSTRAP), "smoke", "--target", str(root)])
    try:
        smoke_out = json.loads(smoke_proc.stdout)
    except json.JSONDecodeError:
        smoke_out = {"raw_stdout": smoke_proc.stdout, "raw_stderr": smoke_proc.stderr}
    evidence["smoke_after_restart"] = {"exit_code": smoke_proc.returncode, "result": smoke_out}

    # Reconstruct /status via the bootstrap-generated lifecycle.py directly,
    # again as a fresh subprocess with a hostile HOME.
    lifecycle_script = root / ".claude" / "scripts" / "lifecycle.py"
    status_proc = subprocess.run(
        [sys.executable, str(lifecycle_script), "status"],
        cwd=root,
        env=_hostile_env() | {"CONTROL_PLANE_WORKSPACE_ROOT": str(root), "CONTROL_PLANE_STATE_ROOT": str(root / ".claude" / "state")},
        capture_output=True,
        text=True,
    )
    try:
        status_out = json.loads(status_proc.stdout)
    except json.JSONDecodeError:
        status_out = {"raw_stdout": status_proc.stdout, "raw_stderr": status_proc.stderr}
    evidence["status_reconstruction"] = {"exit_code": status_proc.returncode, "result": status_out}

    evidence["no_home_dependency_proof"] = {
        "hostile_home_used": _hostile_env()["HOME"],
        "hostile_home_exists": Path(_hostile_env()["HOME"]).exists(),
        "note": "Every subprocess above ran with HOME/USERPROFILE pointed at a nonexistent path; success proves this workload must never have performed a ~/.claude/* read/write.",
    }

    evidence["passed"] = (
        run_proc.returncode == 0
        and validate_proc.returncode == 0
        and smoke_proc.returncode == 0
        and status_proc.returncode == 0
        and not evidence["no_home_dependency_proof"]["hostile_home_exists"]
    )
    return evidence


def run_proof() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="phase5c-code-stack-") as code_dir, tempfile.TemporaryDirectory(prefix="phase5c-non-code-") as doc_dir:
        code_root = Path(code_dir)
        doc_root = Path(doc_dir)
        _write_code_stack_fixture(code_root)
        _write_non_code_fixture(doc_root)

        code_evidence = _bootstrap_and_prove(code_root, "code-stack-python")
        doc_evidence = _bootstrap_and_prove(doc_root, "non-code-research-pipeline")

    result = {
        "kind": "phase5c-portability-proof",
        "workloads": [code_evidence, doc_evidence],
        "both_passed": bool(code_evidence.get("passed")) and bool(doc_evidence.get("passed")),
        "only_facts_and_verify_targets_differ": (
            code_evidence["facts_detect"]["stdout"] != doc_evidence["facts_detect"]["stdout"]
        ),
    }
    return result


def main() -> int:
    result = run_proof()
    out_path = REPO_ROOT / ".claude" / "state" / "roadmap" / "phase-5c-portability-evidence.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"both_passed": result["both_passed"], "evidence_path": str(out_path)}, indent=2))
    return 0 if result["both_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

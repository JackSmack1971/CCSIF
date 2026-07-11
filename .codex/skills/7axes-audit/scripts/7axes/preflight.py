#!/usr/bin/env python3
"""
preflight.py — Phase 0 of the 7-Axes workflow.

Emits a JSON "mission brief" the orchestrator injects into each auditor
subagent. This is the mechanism that guarantees NEW findings every run:

  1. Coverage rotation: paths deeply covered in prior runs are demoted;
     uncovered paths are promoted as priority targets per axis.
  2. Learned directives: meta-auditor guidance from prior runs is injected.
  3. Suppression list: known false-positive rules/fingerprints are passed
     so auditors don't waste tokens re-reporting them.
  4. Staleness: open findings past the escalation threshold are flagged
     for re-verification instead of rediscovery.

Usage:
  python3 scripts/7axes/preflight.py --target src/ [--axes readability,security_compliance]
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import (ALL_AXES, ensure_state, load_calibration, new_run_id,
                      now_iso, read_ledger_state, run_dir, save_calibration)

EXCLUDE_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build",
                "__pycache__", ".7axes", "coverage", ".next", "target"}


def discover_files(target: str, limit: int = 4000) -> list:
    """Prefer git ls-files (respects .gitignore); fall back to a walk."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", target],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout.splitlines()
        files = [f for f in out if f and not any(p in EXCLUDE_DIRS for p in Path(f).parts)]
        if files:
            return files[:limit]
    except Exception:
        pass
    root = Path(target)
    files = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.parts):
            files.append(str(p))
            if len(files) >= limit:
                break
    return files


def split_coverage(files: list, covered_globs: list):
    covered, fresh = [], []
    for f in files:
        (covered if any(fnmatch.fnmatch(f, g) for g in covered_globs) else fresh).append(f)
    return covered, fresh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=".")
    ap.add_argument("--axes", default="")
    args = ap.parse_args()

    ensure_state()
    cal = load_calibration()
    ledger = read_ledger_state()
    run_id = new_run_id()
    rd = run_dir(run_id)

    axes = [a.strip() for a in args.axes.split(",") if a.strip()] or ALL_AXES
    bad = [a for a in axes if a not in ALL_AXES]
    if bad:
        print(json.dumps({"error": f"unknown axes: {bad}", "valid": ALL_AXES}))
        sys.exit(1)

    files = discover_files(args.target)
    open_findings = [r for r in ledger.values() if r.get("status") in ("new", "open", "escalated")]
    stale = [r for r in open_findings
             if r.get("seen_count", 1) >= cal["escalation_threshold"]]

    briefs = {}
    for axis in axes:
        covered, fresh = split_coverage(files, cal["coverage_map"].get(axis, []))
        axis_open = [
            {"fp": r["fp"], "file": r.get("file", ""), "title": r.get("title", "")}
            for r in open_findings if r.get("axis") == axis
        ]
        briefs[axis] = {
            "priority_paths": fresh[:150],          # push into uncovered territory
            "deprioritized_paths": covered[:50],     # skim only; already mined
            "known_open_findings": axis_open[:40],   # verify, don't rediscover
            "suppressed_rules": cal["suppressed_rules"],
            "learned_directives": cal["learned_directives"].get(axis, []),
            "novelty_mandate": (
                "At least 60% of your findings must NOT match any fingerprint in "
                "known_open_findings. Prefer priority_paths. For known_open_findings, "
                "only report status: still_present | resolved."
            ),
        }

    brief = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "target": args.target,
        "file_count": len(files),
        "axes": axes,
        "run_count_prior": cal["run_count"],
        "stale_findings_needing_escalation": [r["fp"] for r in stale],
        "axis_briefs": briefs,
    }

    (rd / "mission_brief.json").write_text(json.dumps(brief, indent=2))
    cal["last_run_id"] = run_id
    save_calibration(cal)
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()

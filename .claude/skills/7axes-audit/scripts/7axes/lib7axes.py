#!/usr/bin/env python3
"""
lib7axes — shared state engine for the self-improving 7-Axes audit workflow.

Three persistent stores under .7axes/ (all committed to git so learning
survives across machines, CI runs, and agents):

  ledger.jsonl       append-only log of every finding fingerprint ever seen,
                     with lifecycle status (new|open|escalated|resolved|suppressed)
  calibration.json   learned parameters: axis weights, rule suppressions,
                     coverage map, focus rotation, per-rule precision stats
  runs/<run_id>/     raw per-axis JSON + novelty diff for each run

Design invariants:
  - Fingerprints are content-addressed and stable across line-number churn.
  - The ledger is append-only; current state is derived by replay (last write wins).
  - Calibration is only mutated by deterministic scripts or the meta-auditor
    via explicit patch files — never silently.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(os.environ.get("SEVENAXES_STATE_DIR", ".7axes"))
LEDGER = STATE_DIR / "ledger.jsonl"
CALIBRATION = STATE_DIR / "calibration.json"
RUNS_DIR = STATE_DIR / "runs"

ALL_AXES = [
    "readability",
    "maintainability",
    "reliability",
    "security_compliance",
    "performance_scalability",
    "testability_coverage",
    "operability_observability",
]

DEFAULT_CALIBRATION = {
    "version": 1,
    "axis_weights": {a: 1.0 for a in ALL_AXES},
    # rule_id -> {"reported": int, "confirmed": int, "rejected": int}
    "rule_stats": {},
    # fingerprint prefixes or rule_ids the feedback loop has learned to mute
    "suppressed_rules": [],
    "suppressed_fingerprints": [],
    # axis -> list of path globs already deeply covered (rotated each run)
    "coverage_map": {a: [] for a in ALL_AXES},
    # freeform learned directives injected into auditor prompts (meta-auditor writes these)
    "learned_directives": {a: [] for a in ALL_AXES},
    # escalation: findings repeated N runs without resolution get bumped
    "escalation_threshold": 2,
    "last_run_id": None,
    "run_count": 0,
}

# ---------------------------------------------------------------- utilities

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_state():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if not CALIBRATION.exists():
        CALIBRATION.write_text(json.dumps(DEFAULT_CALIBRATION, indent=2))
    if not LEDGER.exists():
        LEDGER.touch()


def load_calibration() -> dict:
    ensure_state()
    cal = json.loads(CALIBRATION.read_text())
    # forward-fill any keys added in later versions
    for k, v in DEFAULT_CALIBRATION.items():
        cal.setdefault(k, v)
    return cal


def save_calibration(cal: dict):
    CALIBRATION.write_text(json.dumps(cal, indent=2))


# ------------------------------------------------------------ fingerprinting

_WS = re.compile(r"\s+")
_NUM = re.compile(r"\b\d+\b")


def _norm_snippet(s: str) -> str:
    """Normalize a code snippet so cosmetic churn doesn't change identity."""
    s = _WS.sub(" ", s or "").strip().lower()
    s = _NUM.sub("N", s)  # line numbers / literals drift; structure doesn't
    return s[:400]


def fingerprint(finding: dict) -> str:
    """
    Stable identity for a finding. Deliberately EXCLUDES line numbers and
    prose descriptions (models rephrase); INCLUDES axis, rule, file, and a
    normalized snippet/symbol.
    """
    basis = "|".join([
        finding.get("axis", ""),
        finding.get("rule_id", finding.get("category", "")),
        (finding.get("file", finding.get("location", "")) or "").split(":")[0],
        _norm_snippet(finding.get("snippet", "") or finding.get("symbol", "")),
    ])
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


# ------------------------------------------------------------------ ledger

def read_ledger_state() -> dict:
    """Replay ledger → {fingerprint: latest_record}."""
    ensure_state()
    state = {}
    with LEDGER.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                state[rec["fp"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue  # never let one bad line kill the pipeline
    return state


def append_ledger(records: list):
    ensure_state()
    with LEDGER.open("a") as f:
        for rec in records:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")


# ------------------------------------------------------------- run helpers

def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_dir(run_id: str) -> Path:
    d = RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def die(msg: str, code: int = 1):
    print(f"[7axes] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

#!/usr/bin/env python3
"""
validate_report.py — Phase 2 gate. Validates a single auditor's JSON output
against the 7axes contract, normalizes it, stamps fingerprints, and writes
the canonical copy into the run directory.

Exit codes: 0 valid · 2 invalid (details on stderr) — orchestrator treats
exit 2 as a failed axis and continues (failFast=false semantics).

Usage:
  python3 scripts/7axes/validate_report.py --run <run_id> --axis readability --file /tmp/readability.json
  cat out.json | python3 scripts/7axes/validate_report.py --run <run_id> --axis readability
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import ALL_AXES, fingerprint, run_dir

REQUIRED_TOP = {"axis", "score", "findings"}
REQUIRED_FINDING = {"rule_id", "severity", "title", "file"}
SEVERITIES = {"critical", "high", "medium", "low", "info"}
FINDING_STATUSES = {"new", "still_present", "resolved"}


def fail(msg):
    print(json.dumps({"valid": False, "error": msg}), file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--axis", required=True)
    ap.add_argument("--file", default=None)
    args = ap.parse_args()

    if args.axis not in ALL_AXES:
        fail(f"unknown axis '{args.axis}'")

    raw = Path(args.file).read_text() if args.file else sys.stdin.read()

    # Models sometimes wrap JSON in fences or prose — extract defensively.
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        candidates = [p.lstrip("json").strip() for p in parts if p.strip().startswith(("{", "["))]
        if candidates:
            raw = candidates[0]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        fail("no JSON object found in auditor output")
    try:
        doc = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        fail(f"JSON parse error: {e}")

    missing = REQUIRED_TOP - doc.keys()
    if missing:
        fail(f"missing top-level keys: {sorted(missing)}")
    if doc["axis"] != args.axis:
        fail(f"axis mismatch: expected {args.axis}, got {doc['axis']}")
    if not isinstance(doc["score"], (int, float)) or not 0 <= doc["score"] <= 10:
        fail(f"score must be a number in [0,10], got {doc['score']!r}")
    if not isinstance(doc["findings"], list):
        fail("findings must be an array")

    clean = []
    for i, f in enumerate(doc["findings"]):
        if not isinstance(f, dict):
            continue
        miss = REQUIRED_FINDING - f.keys()
        if miss:
            print(f"[7axes] dropping finding {i}: missing {sorted(miss)}", file=sys.stderr)
            continue
        f["severity"] = str(f["severity"]).lower()
        if f["severity"] not in SEVERITIES:
            f["severity"] = "medium"
        f.setdefault("status", "new")
        if f["status"] not in FINDING_STATUSES:
            f["status"] = "new"
        f["axis"] = args.axis
        f["fp"] = fingerprint(f)
        clean.append(f)

    doc["findings"] = clean
    doc.setdefault("top_strengths", [])
    doc.setdefault("coverage_claimed", [])  # path globs the auditor deeply examined

    out = run_dir(args.run) / f"{args.axis}.json"
    out.write_text(json.dumps(doc, indent=2))
    print(json.dumps({
        "valid": True, "axis": args.axis, "score": doc["score"],
        "findings": len(clean), "written": str(out),
    }))


if __name__ == "__main__":
    main()

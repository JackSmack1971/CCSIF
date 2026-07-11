#!/usr/bin/env python3
"""
ledger.py — Phase 3 & 6. The novelty engine.

  diff   — classify this run's findings against all history:
             NEW        never-seen fingerprint            → surfaces + issue
             REPEAT     seen, still open                  → seen_count++
             ESCALATED  repeat past escalation threshold  → priority bump
             RESOLVED   previously open, auditor confirms fixed (or absent
                        from a fully re-covered path)
             SUPPRESSED matches learned false-positive rules → dropped
  commit — append lifecycle records + update coverage map & run counters.

diff writes runs/<id>/novelty.json — the ONLY thing synthesis sees, which is
what keeps every run's report focused on what is actually new.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import (ALL_AXES, append_ledger, load_calibration, now_iso,
                      read_ledger_state, run_dir, save_calibration)

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def load_run_findings(run_id):
    rd = run_dir(run_id)
    per_axis, findings = {}, []
    for axis in ALL_AXES:
        p = rd / f"{axis}.json"
        if p.exists():
            doc = json.loads(p.read_text())
            per_axis[axis] = doc
            findings.extend(doc.get("findings", []))
    return per_axis, findings


def cmd_diff(args):
    cal = load_calibration()
    ledger = read_ledger_state()
    per_axis, findings = load_run_findings(args.run)
    if not per_axis:
        print(json.dumps({"error": f"no validated axis reports in run {args.run}"}))
        sys.exit(1)

    suppressed_rules = set(cal["suppressed_rules"])
    suppressed_fps = set(cal["suppressed_fingerprints"])
    thresh = cal["escalation_threshold"]

    buckets = {"new": [], "repeat": [], "escalated": [], "resolved": [], "suppressed": []}
    seen_fps = set()

    for f in findings:
        fp = f["fp"]
        seen_fps.add(fp)
        if f.get("status") == "resolved":
            if fp in ledger and ledger[fp].get("status") not in ("resolved", "suppressed"):
                buckets["resolved"].append(f)
            continue
        if f.get("rule_id") in suppressed_rules or fp in suppressed_fps:
            buckets["suppressed"].append(f)
            continue
        prior = ledger.get(fp)
        if prior is None or prior.get("status") in ("resolved",):
            buckets["new"].append(f)
        else:
            f["seen_count"] = prior.get("seen_count", 1) + 1
            if f["seen_count"] > thresh:
                f["escalated"] = True
                buckets["escalated"].append(f)
            else:
                buckets["repeat"].append(f)

    # Implicit resolution: open finding in a path an auditor claims full
    # re-coverage of, but did not re-report → probably fixed. Marked for
    # verification rather than auto-closed (conservative).
    recovered = []
    claimed = {axis: doc.get("coverage_claimed", []) for axis, doc in per_axis.items()}
    import fnmatch
    for fp, rec in ledger.items():
        if rec.get("status") in ("new", "open", "escalated") and fp not in seen_fps:
            globs = claimed.get(rec.get("axis", ""), [])
            if any(fnmatch.fnmatch(rec.get("file", ""), g) for g in globs):
                recovered.append({"fp": fp, "axis": rec.get("axis"),
                                  "title": rec.get("title"), "file": rec.get("file")})

    for b in ("new", "escalated", "repeat"):
        buckets[b].sort(key=lambda f: SEV_ORDER.get(f.get("severity", "medium"), 2))

    total_reported = len(findings)
    novelty_rate = round(len(buckets["new"]) / total_reported, 3) if total_reported else 0.0

    out = {
        "run_id": args.run,
        "generated_at": now_iso(),
        "counts": {k: len(v) for k, v in buckets.items()},
        "novelty_rate": novelty_rate,
        "likely_resolved_unverified": recovered,
        "axis_scores": {a: d.get("score") for a, d in per_axis.items()},
        **buckets,
    }
    p = run_dir(args.run) / "novelty.json"
    p.write_text(json.dumps(out, indent=2))
    print(json.dumps({"written": str(p), "counts": out["counts"],
                      "novelty_rate": novelty_rate}, indent=2))


def cmd_commit(args):
    cal = load_calibration()
    ledger = read_ledger_state()
    rd = run_dir(args.run)
    nov = json.loads((rd / "novelty.json").read_text())
    per_axis, _ = load_run_findings(args.run)

    records, ts = [], now_iso()

    def rec_from(f, status, seen=None):
        return {
            "fp": f["fp"], "axis": f.get("axis"), "rule_id": f.get("rule_id"),
            "severity": f.get("severity"), "title": f.get("title"),
            "file": f.get("file"), "status": status,
            "seen_count": seen if seen is not None else f.get("seen_count", 1),
            "first_seen": ledger.get(f["fp"], {}).get("first_seen", ts),
            "last_seen": ts, "run_id": args.run,
            "issue_url": f.get("issue_url") or ledger.get(f["fp"], {}).get("issue_url"),
        }

    for f in nov["new"]:
        records.append(rec_from(f, "open", seen=1))
        rs = cal["rule_stats"].setdefault(f.get("rule_id", "unknown"),
                                          {"reported": 0, "confirmed": 0, "rejected": 0})
        rs["reported"] += 1
    for f in nov["repeat"]:
        records.append(rec_from(f, "open"))
    for f in nov["escalated"]:
        records.append(rec_from(f, "escalated"))
    for f in nov["resolved"]:
        records.append(rec_from(f, "resolved"))

    append_ledger(records)

    # Merge auditor-claimed coverage into rotation map (capped to stay useful)
    for axis, doc in per_axis.items():
        merged = set(cal["coverage_map"].get(axis, [])) | set(doc.get("coverage_claimed", []))
        cal["coverage_map"][axis] = sorted(merged)[-200:]

    cal["run_count"] += 1
    save_calibration(cal)
    print(json.dumps({"committed": len(records), "run_count": cal["run_count"]}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("diff", "commit"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
    args = ap.parse_args()
    {"diff": cmd_diff, "commit": cmd_commit}[args.cmd](args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
feedback.py — the outer learning loop. Run at the START of each audit (the
orchestrator does this automatically) or ad hoc.

Reads outcomes of previously filed 7axes issues from GitHub and converts
human/agent judgment into calibration updates:

  issue closed as COMPLETED (or a merged PR references it)
      → rule confirmed: rule_stats.confirmed++, finding → resolved in ledger
  issue closed as NOT_PLANNED / labeled false-positive / wontfix
      → rule_stats.rejected++, fingerprint added to suppressed_fingerprints;
        if a rule's precision (confirmed / reported) drops below 0.34 with
        ≥3 reports, the whole rule_id is suppressed and a learned directive
        is written telling that axis's auditor why.

This is the mechanism that makes the system measurably better with use:
precision improves because rejected rules stop consuming attention.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import (append_ledger, load_calibration, now_iso,
                      read_ledger_state, save_calibration)

MARKER = "7axes-fp:"
PRECISION_FLOOR = 0.34
MIN_SAMPLES = 3
FP_LABELS = {"false-positive", "wontfix", "invalid"}


def sh(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main():
    out = sh(["gh", "issue", "list", "--label", "7axes", "--state", "closed",
              "--limit", "300",
              "--json", "number,body,stateReason,labels,closedAt"])
    if out is None:
        print(json.dumps({"skipped": "gh unavailable or unauthenticated — feedback loop idle"}))
        return

    cal = load_calibration()
    ledger = read_ledger_state()
    ts = now_iso()
    records, confirmed, rejected = [], 0, 0

    for issue in json.loads(out):
        body = issue.get("body") or ""
        fp = next((l.split(MARKER, 1)[1].strip().strip("`> -->")
                   for l in body.splitlines() if MARKER in l), None)
        if not fp or fp not in ledger:
            continue
        rec = ledger[fp]
        if rec.get("status") in ("resolved", "suppressed"):
            continue  # already learned from this one

        labels = {l["name"].lower() for l in issue.get("labels", [])}
        reason = (issue.get("stateReason") or "").upper()
        rule = rec.get("rule_id", "unknown")
        rs = cal["rule_stats"].setdefault(rule, {"reported": 1, "confirmed": 0, "rejected": 0})

        if reason == "NOT_PLANNED" or labels & FP_LABELS:
            rs["rejected"] += 1
            rejected += 1
            if fp not in cal["suppressed_fingerprints"]:
                cal["suppressed_fingerprints"].append(fp)
            records.append({**rec, "status": "suppressed", "last_seen": ts,
                            "closed_reason": reason or "labeled-fp"})
            # rule-level suppression once precision collapses
            total = rs["confirmed"] + rs["rejected"]
            if total >= MIN_SAMPLES and rs["confirmed"] / total < PRECISION_FLOOR \
                    and rule not in cal["suppressed_rules"]:
                cal["suppressed_rules"].append(rule)
                axis = rec.get("axis", "readability")
                cal["learned_directives"].setdefault(axis, []).append(
                    f"[{ts}] Rule '{rule}' suppressed: {rs['rejected']}/{total} reports "
                    f"rejected by maintainers. Do not report this pattern unless the "
                    f"evidence is qualitatively different."
                )
        else:  # COMPLETED or default close → treated as confirmed & fixed
            rs["confirmed"] += 1
            confirmed += 1
            records.append({**rec, "status": "resolved", "last_seen": ts,
                            "closed_reason": reason or "completed"})

    if records:
        append_ledger(records)
    save_calibration(cal)
    print(json.dumps({
        "synced_at": ts, "confirmed_fixed": confirmed, "rejected_fp": rejected,
        "suppressed_rules_total": len(cal["suppressed_rules"]),
        "suppressed_fingerprints_total": len(cal["suppressed_fingerprints"]),
    }, indent=2))


if __name__ == "__main__":
    main()

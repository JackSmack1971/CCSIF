#!/usr/bin/env python3
"""
report.py — Phase 7. Deterministic Markdown executive report from run state.
No model in the loop: same inputs → same report. Emphasizes what is NEW this
run, tracks trend vs prior runs, and surfaces the learning telemetry.

Usage: python3 scripts/7axes/report.py --run <run_id> [--out reports/]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import ALL_AXES, RUNS_DIR, load_calibration, run_dir

STATUS = lambda s: ("Strong" if s >= 8 else "Good" if s >= 6
                    else "Needs Work" if s >= 4 else "Critical")


def prior_scores(current_run):
    runs = sorted([d.name for d in RUNS_DIR.iterdir() if d.is_dir()])
    prior = [r for r in runs if r < current_run]
    if not prior:
        return {}
    p = RUNS_DIR / prior[-1] / "novelty.json"
    if p.exists():
        return json.loads(p.read_text()).get("axis_scores", {}) or {}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    rd = run_dir(args.run)
    nov = json.loads((rd / "novelty.json").read_text())
    brief = json.loads((rd / "mission_brief.json").read_text()) if (rd / "mission_brief.json").exists() else {}
    synth_p = rd / "synthesis.json"
    synth = json.loads(synth_p.read_text()) if synth_p.exists() else {}
    issues_p = rd / "issues_result.json"
    issues = json.loads(issues_p.read_text()) if issues_p.exists() else {}
    cal = load_calibration()
    prev = prior_scores(args.run)

    scores = {a: s for a, s in nov.get("axis_scores", {}).items() if isinstance(s, (int, float))}
    weights = cal["axis_weights"]
    if scores:
        composite = sum(s * weights.get(a, 1.0) for a, s in scores.items()) / \
                    sum(weights.get(a, 1.0) for a in scores)
    else:
        composite = None

    L = []
    L.append("# 7-Axes Code Quality Audit — Run Report")
    L.append("")
    L.append(f"**Run:** `{args.run}` · **Scope:** `{brief.get('target', '.')}` · "
             f"**Run # in this repo:** {cal.get('run_count', 0) + 1}")
    comp_s = f"{composite:.1f} / 10" if composite is not None else "N/A"
    L.append(f"**Weighted Composite:** **{comp_s}**")
    L.append("")

    c = nov["counts"]
    L.append("## What's New This Run")
    L.append("")
    L.append(f"- 🆕 **{c['new']} new findings** (novelty rate: {nov['novelty_rate']:.0%})")
    L.append(f"- ⏫ {c['escalated']} escalated (persisted ≥{cal['escalation_threshold']} runs unresolved)")
    L.append(f"- ✅ {c['resolved']} confirmed resolved since last run")
    L.append(f"- 🔇 {c['suppressed']} auto-suppressed by learned false-positive rules")
    if issues.get("created"):
        mode = issues.get("mode", "dry-run")
        L.append(f"- 📋 {len(issues['created'])} GitHub issues "
                 f"{'created' if mode == 'live' else 'staged (dry-run)'} for downstream PR agents")
    L.append("")

    L.append("## Axis Scores")
    L.append("")
    L.append("| Axis | Score | Δ vs last run | Status |")
    L.append("|---|---|---|---|")
    for axis in ALL_AXES:
        if axis not in scores:
            continue
        s = scores[axis]
        d = ""
        if axis in prev and isinstance(prev[axis], (int, float)):
            delta = s - prev[axis]
            d = f"{'▲' if delta > 0 else '▼' if delta < 0 else '—'} {delta:+.1f}" if delta else "—"
        name = axis.replace("_", " ").title()
        L.append(f"| {name} | {s:.1f} | {d or '—'} | {STATUS(s)} |")
    L.append("")

    def finding_lines(items, cap=10):
        for f in items[:cap]:
            url = f" → [{f['issue_url'].split('/')[-1]}]({f['issue_url']})" if f.get("issue_url") else ""
            yield (f"- **[{f.get('severity', '?').upper()}] {f.get('title')}** "
                   f"(`{f.get('file')}`, {f.get('axis')}){url}")

    if nov["new"]:
        L.append("## New Findings (top by severity)")
        L.append("")
        L.extend(finding_lines(nov["new"]))
        L.append("")
    if nov["escalated"]:
        L.append("## Escalated — Chronic Debt")
        L.append("")
        L.extend(finding_lines(nov["escalated"]))
        L.append("")
    if synth.get("cross_axis_insights"):
        L.append("## Cross-Axis Interactions")
        L.append("")
        for i in synth["cross_axis_insights"]:
            icon = {"positive": "✅", "negative": "⚠️"}.get(i.get("impact"), "ℹ️")
            L.append(f"- {icon} **{i.get('interaction')}**")
            if i.get("recommendation"):
                L.append(f"  - {i['recommendation']}")
        L.append("")

    L.append("## Learning Telemetry")
    L.append("")
    L.append(f"- Suppressed rules: {len(cal['suppressed_rules'])} · "
             f"Suppressed fingerprints: {len(cal['suppressed_fingerprints'])}")
    n_dir = sum(len(v) for v in cal["learned_directives"].values())
    L.append(f"- Learned directives active across auditors: {n_dir}")
    rs = cal["rule_stats"]
    graded = [(r, v) for r, v in rs.items() if v["confirmed"] + v["rejected"] >= 2]
    if graded:
        graded.sort(key=lambda kv: kv[1]["confirmed"] / max(1, kv[1]["confirmed"] + kv[1]["rejected"]),
                    reverse=True)
        best = graded[0]
        L.append(f"- Highest-precision rule so far: `{best[0]}` "
                 f"({best[1]['confirmed']}✓ / {best[1]['rejected']}✗)")
    L.append("")
    L.append("---")
    L.append("*Generated deterministically by the 7-Axes self-improving workflow · "
             "ISO/IEC 25010 + DORA/SPACE aligned*")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"7axes-{args.run}.md"
    out.write_text("\n".join(L))
    print(json.dumps({"written": str(out)}))


if __name__ == "__main__":
    main()

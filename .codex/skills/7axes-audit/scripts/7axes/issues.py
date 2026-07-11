#!/usr/bin/env python3
"""
issues.py — Phase 5. Turns NEW + ESCALATED findings into GitHub issues that
downstream PR agents can execute autonomously.

Guarantees:
  - Idempotent: dedupes against open issues via embedded fingerprint marker.
  - Agent-ready: every issue carries a fenced ```yaml agent-spec``` block with
    fingerprint, files, acceptance criteria, and suggested approach — a
    machine-parseable work order for `@claude`, Claude Code GitHub Action,
    or any PR agent.
  - Escalations update the existing issue (comment + priority label) instead
    of duplicating.
  - Dry-run by default in absence of --execute, so it's safe to test anywhere.

Requires: gh CLI authenticated in the target repo (`gh auth status`).

Usage:
  python3 scripts/7axes/issues.py --run <run_id> [--execute] [--max 15] [--min-severity medium] [--assign-agent]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import now_iso, run_dir

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
LABELS = ["7axes", "agent-ready"]
MARKER = "7axes-fp:"


def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} → {r.stderr.strip()}")
    return r.stdout.strip()


def gh_available():
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def ensure_labels(axes):
    wanted = LABELS + [f"axis:{a}" for a in axes] + \
             [f"priority:{p}" for p in ("critical", "high", "medium", "low")] + \
             ["escalated"]
    existing = set()
    try:
        existing = {l["name"] for l in json.loads(
            sh(["gh", "label", "list", "--limit", "200", "--json", "name"]))}
    except Exception:
        pass
    for lbl in wanted:
        if lbl not in existing:
            subprocess.run(["gh", "label", "create", lbl, "--force",
                            "--color", "5319e7" if lbl.startswith("axis:") else "0e8a16"],
                           capture_output=True)


def open_issue_index():
    """Map fingerprint → issue number for all open 7axes issues."""
    idx = {}
    try:
        issues = json.loads(sh([
            "gh", "issue", "list", "--label", "7axes", "--state", "open",
            "--limit", "500", "--json", "number,body,title"]))
        for it in issues:
            body = it.get("body") or ""
            for line in body.splitlines():
                if MARKER in line:
                    fp = line.split(MARKER, 1)[1].strip().strip("`> ")
                    idx[fp] = it["number"]
    except Exception as e:
        print(f"[7axes] warn: could not index open issues: {e}", file=sys.stderr)
    return idx


def build_body(f, run_id):
    spec = {
        "fingerprint": f["fp"],
        "axis": f.get("axis"),
        "rule_id": f.get("rule_id"),
        "severity": f.get("severity"),
        "files": [f.get("file")] + f.get("related_files", []),
        "acceptance_criteria": f.get("acceptance_criteria") or [
            "Root cause addressed, not symptom-patched",
            "Existing tests pass; new regression test added covering this finding",
            "No new findings introduced on the same axis (re-run /7axes-audit to verify)",
        ],
        "suggested_approach": f.get("recommendation", ""),
        "constraints": ["Minimal diff", "Follow existing code conventions",
                        "Reference this issue number in the PR body"],
    }
    lines = [
        f"## {f.get('title')}",
        "",
        f"**Axis:** `{f.get('axis')}` · **Severity:** `{f.get('severity')}` · "
        f"**Rule:** `{f.get('rule_id')}` · **Run:** `{run_id}`",
        "",
        "### Finding",
        f.get("description", f.get("title", "")),
        "",
    ]
    if f.get("snippet"):
        lines += ["### Evidence", "```", f["snippet"][:800], "```", ""]
    lines += [
        "### Agent Work Order",
        "The block below is machine-readable. A downstream PR agent should treat",
        "`acceptance_criteria` as the definition of done.",
        "",
        "```yaml agent-spec",
        json.dumps(spec, indent=2),
        "```",
        "",
        f"<!-- {MARKER} {f['fp']} -->",
        "",
        "---",
        "*Filed automatically by the 7-Axes self-improving audit workflow.*",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--execute", action="store_true", help="actually create issues (default: dry-run)")
    ap.add_argument("--max", type=int, default=15, help="cap issues per run to avoid backlog flooding")
    ap.add_argument("--min-severity", default="medium", choices=list(SEV_ORDER))
    ap.add_argument("--assign-agent", action="store_true",
                    help="append an @claude mention so the Claude Code GitHub Action picks it up")
    args = ap.parse_args()

    nov_path = run_dir(args.run) / "novelty.json"
    if not nov_path.exists():
        print(json.dumps({"error": "run ledger.py diff first"})); sys.exit(1)
    nov = json.loads(nov_path.read_text())

    cutoff = SEV_ORDER[args.min_severity]
    candidates = [f for f in nov["new"] if SEV_ORDER.get(f.get("severity"), 2) <= cutoff]
    candidates.sort(key=lambda f: SEV_ORDER.get(f.get("severity"), 2))
    candidates = candidates[:args.max]
    escalations = nov.get("escalated", [])

    live = args.execute and gh_available()
    if args.execute and not live:
        print(json.dumps({"error": "gh CLI not authenticated — run `gh auth login`"}))
        sys.exit(1)

    results = {"mode": "live" if live else "dry-run", "created": [],
               "escalated": [], "skipped_duplicates": [], "at": now_iso()}

    idx = open_issue_index() if live else {}
    if live:
        ensure_labels({f.get("axis") for f in candidates + escalations if f.get("axis")})

    for f in candidates:
        if f["fp"] in idx:
            results["skipped_duplicates"].append({"fp": f["fp"], "issue": idx[f["fp"]]})
            continue
        title = f"[7axes/{f.get('axis')}] {f.get('title', 'Finding')[:120]}"
        body = build_body(f, args.run)
        if args.assign_agent:
            body += "\n\n@claude please open a PR that satisfies the agent-spec above."
        labels = ",".join(LABELS + [f"axis:{f.get('axis')}", f"priority:{f.get('severity')}"])
        if live:
            url = sh(["gh", "issue", "create", "--title", title,
                      "--body", body, "--label", labels])
            f["issue_url"] = url
            results["created"].append({"fp": f["fp"], "url": url, "title": title})
        else:
            results["created"].append({"fp": f["fp"], "title": title,
                                       "labels": labels, "dry_run": True})

    for f in escalations:
        n = idx.get(f["fp"])
        if live and n:
            sh(["gh", "issue", "comment", str(n), "--body",
                f"⬆️ **Escalated** by run `{args.run}`: finding persisted "
                f"{f.get('seen_count')} consecutive runs without resolution."])
            sh(["gh", "issue", "edit", str(n), "--add-label", "escalated"])
            results["escalated"].append({"fp": f["fp"], "issue": n})
        elif not live:
            results["escalated"].append({"fp": f["fp"], "dry_run": True})

    # persist issue URLs back into the run so ledger commit records them
    nov["new"] = nov["new"]  # candidates mutated in place carry issue_url
    nov_path.write_text(json.dumps(nov, indent=2))
    (run_dir(args.run) / "issues_result.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

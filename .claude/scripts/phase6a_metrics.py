#!/usr/bin/env python3
"""Phase 6A measurement: trigger/block/error/latency/false-block-review.

Reads the three Phase 6A event logs
(`.claude/state/logs/guardrail-events.jsonl`,
`.claude/state/logs/lint-events.jsonl`,
`.claude/state/logs/stop-gate-events.jsonl`) plus `.claude/state/ledger.md`,
and reports:

- trigger/allow/ask/block/error counts per guardrail category
- latency percentiles (p50/p95/max) for the guard hook
- false-block-review candidates: any (tool, category) pair blocked/asked
  more than once on what looks like the same path/reason, a signal for a
  rung-4 demotion/refinement review
- ladder promotion/demotion record count, parsed from `## Phase 6 ladder
  change` / `## Phase 6A Stop-gate escalation` headings in the ledger

Never mutates any state; read-only measurement, per this repo's
audit-only-task convention.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / ".claude" / "state" / "logs"
GUARDRAIL_LOG = LOG_DIR / "guardrail-events.jsonl"
LINT_LOG = LOG_DIR / "lint-events.jsonl"
STOP_GATE_LOG = LOG_DIR / "stop-gate-events.jsonl"
LEDGER_PATH = ROOT / ".claude" / "state" / "ledger.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    k = (len(ordered) - 1) * pct
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return float(ordered[f])
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def guardrail_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(e.get("decision") for e in events)
    category_counts: Counter[str] = Counter()
    category_tool: dict[str, Counter] = defaultdict(Counter)
    latencies = [e["duration_ms"] for e in events if isinstance(e.get("duration_ms"), (int, float))]

    for e in events:
        if e.get("decision") in ("ask", "block") and e.get("category"):
            category_counts[e["category"]] += 1
            category_tool[e["category"]][e.get("tool_name")] += 1

    false_block_review = [
        {"category": category, "count": count, "by_tool": dict(category_tool[category])}
        for category, count in category_counts.items()
        if count > 1
    ]

    return {
        "total_events": len(events),
        "decision_counts": dict(decision_counts),
        "category_counts": dict(category_counts),
        "latency_ms": {
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": max(latencies) if latencies else 0,
            "count": len(latencies),
        },
        "false_block_review_candidates": sorted(
            false_block_review, key=lambda item: item["count"], reverse=True
        ),
    }


def lint_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(e.get("decision") for e in events)
    return {"total_events": len(events), "decision_counts": dict(decision_counts)}


def stop_gate_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(e.get("action") for e in events)
    escalations = [e for e in events if e.get("escalated")]
    return {
        "total_events": len(events),
        "action_counts": dict(decision_counts),
        "escalation_count": len(escalations),
    }


def ledger_ladder_changes(ledger_path: Path) -> dict[str, Any]:
    if not ledger_path.exists():
        return {"promotions": 0, "demotions": 0, "escalations": 0, "headings": []}
    text = ledger_path.read_text(encoding="utf-8")
    headings = [line.strip("# ").strip() for line in text.splitlines() if line.startswith("## ")]
    promotions = sum(1 for h in headings if "promot" in h.lower())
    demotions = sum(1 for h in headings if "demot" in h.lower() or "refin" in h.lower())
    escalations = sum(1 for h in headings if "escalat" in h.lower())
    return {
        "promotions": promotions,
        "demotions": demotions,
        "escalations": escalations,
        "headings": [h for h in headings if any(k in h.lower() for k in ("promot", "demot", "refin", "escalat", "ladder"))],
    }


def build_report() -> dict[str, Any]:
    return {
        "guardrail": guardrail_summary(read_jsonl(GUARDRAIL_LOG)),
        "lint_on_edit": lint_summary(read_jsonl(LINT_LOG)),
        "stop_gate": stop_gate_summary(read_jsonl(STOP_GATE_LOG)),
        "ledger_ladder_changes": ledger_ladder_changes(LEDGER_PATH),
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase6a_metrics as metrics  # noqa: E402


class GuardrailSummaryTests(unittest.TestCase):
    def test_counts_and_latency_and_false_block_review(self):
        events = [
            {"decision": "allow", "duration_ms": 1, "tool_name": "Bash", "category": None},
            {"decision": "block", "duration_ms": 3, "tool_name": "Write", "category": "secrets/credentials"},
            {"decision": "block", "duration_ms": 5, "tool_name": "Write", "category": "secrets/credentials"},
            {"decision": "ask", "duration_ms": 2, "tool_name": "Bash", "category": "git guardrail: git-force-push"},
            {"decision": "error", "duration_ms": 9, "tool_name": None, "category": None},
        ]
        summary = metrics.guardrail_summary(events)
        self.assertEqual(summary["total_events"], 5)
        self.assertEqual(summary["decision_counts"]["block"], 2)
        self.assertEqual(summary["decision_counts"]["allow"], 1)
        self.assertEqual(summary["decision_counts"]["ask"], 1)
        self.assertEqual(summary["decision_counts"]["error"], 1)
        self.assertEqual(summary["category_counts"]["secrets/credentials"], 2)
        self.assertEqual(summary["latency_ms"]["max"], 9)
        candidates = {c["category"] for c in summary["false_block_review_candidates"]}
        self.assertIn("secrets/credentials", candidates)
        self.assertNotIn("git guardrail: git-force-push", candidates)  # only 1 occurrence


class LedgerLadderChangeTests(unittest.TestCase):
    def test_parses_promotion_demotion_escalation_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.md"
            ledger_path.write_text(
                "# Ledger\n\n"
                "## Some unrelated entry (2026-01-01)\n\nbody\n\n"
                "## Phase 6 ladder promotion: git force-push (2026-01-02)\n\nbody\n\n"
                "## Phase 6 ladder demotion: fd-dup carve-out (2026-01-03)\n\nbody\n\n"
                "## Phase 6A Stop-gate escalation (2026-01-04)\n\nbody\n",
                encoding="utf-8",
            )
            result = metrics.ledger_ladder_changes(ledger_path)
            self.assertEqual(result["promotions"], 1)
            self.assertEqual(result["demotions"], 1)
            self.assertEqual(result["escalations"], 1)
            self.assertEqual(len(result["headings"]), 3)

    def test_missing_ledger_returns_zeroes(self):
        result = metrics.ledger_ladder_changes(Path("/does/not/exist/ledger.md"))
        self.assertEqual(result, {"promotions": 0, "demotions": 0, "escalations": 0, "headings": []})


class ReadJsonlTests(unittest.TestCase):
    def test_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"a": 1}\nnot json\n{"b": 2}\n', encoding="utf-8")
            events = metrics.read_jsonl(path)
            self.assertEqual(events, [{"a": 1}, {"b": 2}])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(metrics.read_jsonl(Path("/does/not/exist.jsonl")), [])


class BuildReportIntegrationTests(unittest.TestCase):
    def test_build_report_runs_against_real_repo_state(self):
        report = metrics.build_report()
        for key in ("guardrail", "lint_on_edit", "stop_gate", "ledger_ladder_changes"):
            self.assertIn(key, report)
        json.dumps(report)  # must be JSON-serializable


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase6a_stop_gate as gate  # noqa: E402


class BoundedRetryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp_root = Path(self._tmp.name)
        self._orig_state_root = gate.STATE_ROOT
        self._orig_retry_dir = gate.RETRY_DIR
        self._orig_event_log = gate.EVENT_LOG
        self._orig_ledger_path = gate.LEDGER_PATH
        self._orig_run_checks = gate.run_checks
        gate.STATE_ROOT = tmp_root
        gate.RETRY_DIR = tmp_root / "logs" / "stop-retries"
        gate.EVENT_LOG = tmp_root / "logs" / "stop-gate-events.jsonl"
        gate.LEDGER_PATH = tmp_root / "ledger.md"
        self.session_id = "test-session-bounded"

    def tearDown(self):
        gate.STATE_ROOT = self._orig_state_root
        gate.RETRY_DIR = self._orig_retry_dir
        gate.EVENT_LOG = self._orig_event_log
        gate.LEDGER_PATH = self._orig_ledger_path
        gate.run_checks = self._orig_run_checks

    def test_passing_checks_allow_immediately(self):
        gate.run_checks = lambda: (True, "all good")
        decision = gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
        self.assertEqual(decision["action"], "allow")
        self.assertEqual(decision["retries_used"], 0)

    def test_failing_checks_block_up_to_bound_then_escalates(self):
        gate.run_checks = lambda: (False, "control-plane-check: FAIL")
        seen_actions = []
        for _ in range(gate.MAX_RETRIES + 1):
            decision = gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
            seen_actions.append(decision["action"])

        # First MAX_RETRIES calls block; the call that pushes past the
        # bound escalates and allows instead of blocking forever.
        self.assertEqual(seen_actions[:-1], ["block"] * gate.MAX_RETRIES)
        self.assertEqual(seen_actions[-1], "allow")
        self.assertTrue(gate.LEDGER_PATH.exists())
        ledger_text = gate.LEDGER_PATH.read_text(encoding="utf-8")
        self.assertIn("Stop-gate escalation", ledger_text)
        self.assertIn(self.session_id, ledger_text)

    def test_retry_state_clears_after_success(self):
        gate.run_checks = lambda: (False, "fail once")
        gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
        self.assertTrue(gate.retry_path(self.session_id).exists())

        gate.run_checks = lambda: (True, "now passes")
        decision = gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
        self.assertEqual(decision["action"], "allow")
        self.assertFalse(gate.retry_path(self.session_id).exists())

    def test_stop_hook_active_escalates_without_reblocking(self):
        # Simulates Claude Code re-invoking this same Stop hook as a direct
        # result of a prior block: must never re-block on that same turn,
        # or the retry bound could be bypassed into an infinite loop.
        gate.run_checks = lambda: (False, "still failing")
        decision = gate.evaluate({"session_id": self.session_id, "stop_hook_active": True})
        self.assertEqual(decision["action"], "allow")
        self.assertTrue(decision.get("escalated"))
        self.assertTrue(gate.LEDGER_PATH.exists())

    def test_different_sessions_have_independent_retry_counters(self):
        gate.run_checks = lambda: (False, "fail")
        gate.evaluate({"session_id": "session-a", "stop_hook_active": False})
        gate.evaluate({"session_id": "session-a", "stop_hook_active": False})
        decision_b = gate.evaluate({"session_id": "session-b", "stop_hook_active": False})
        self.assertEqual(decision_b["retries_used"], 1)

    def test_missing_git_directory_allows(self):
        orig_root = gate.ROOT
        try:
            gate.ROOT = Path(self._tmp.name)  # no .git here
            decision = gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
            self.assertEqual(decision["action"], "allow")
            self.assertEqual(decision["reason"], "not a git worktree")
        finally:
            gate.ROOT = orig_root

    def test_events_are_logged(self):
        gate.run_checks = lambda: (True, "ok")
        gate.evaluate({"session_id": self.session_id, "stop_hook_active": False})
        self.assertTrue(gate.EVENT_LOG.exists())
        lines = [line for line in gate.EVENT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(lines)
        event = json.loads(lines[-1])
        for field in ("ts", "session_id", "action", "correlation_id", "duration_ms"):
            self.assertIn(field, event)


class MainEntrypointTests(unittest.TestCase):
    def test_malformed_stdin_fails_open(self):
        import io
        import contextlib

        orig_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("not json")
            with contextlib.redirect_stderr(io.StringIO()):
                code = gate.main()
            self.assertEqual(code, 0)
        finally:
            sys.stdin = orig_stdin


if __name__ == "__main__":
    unittest.main()

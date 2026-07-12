from __future__ import annotations

import io
import contextlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "scripts" / "phase6a_lint_on_edit.py"
LOG_PATH = ROOT / ".claude" / "state" / "logs" / "lint-events.jsonl"


def run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class LintOnEditTests(unittest.TestCase):
    def test_read_tool_is_ignored(self):
        before = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
        proc = run({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})
        self.assertEqual(proc.returncode, 0)
        after = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
        self.assertEqual(before, after)

    def test_write_tool_runs_lint_and_logs(self):
        before = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
        proc = run({"tool_name": "Write", "tool_input": {"file_path": "docs/notes.md"}})
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(LOG_PATH.exists())
        with LOG_PATH.open("r", encoding="utf-8") as fh:
            fh.seek(before)
            lines = [line for line in fh.read().splitlines() if line.strip()]
        self.assertTrue(lines)
        event = json.loads(lines[-1])
        self.assertEqual(event["tool_name"], "Write")
        self.assertIn(event["decision"], ("pass", "fail", "unavailable"))
        self.assertIn("duration_ms", event)

    def test_malformed_payload_never_crashes(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()

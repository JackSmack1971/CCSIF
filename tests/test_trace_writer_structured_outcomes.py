from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_WRITER = ROOT / ".claude" / "hooks" / "lib" / "trace-writer.js"


class TraceWriterStructuredOutcomeTests(unittest.TestCase):
    def _run_writer(self, payload: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            full_payload = {"cwd": str(cwd), "hook_event_name": "PostToolUse", **payload}
            subprocess.run(
                ["node", str(TRACE_WRITER)],
                input=json.dumps(full_payload),
                text=True,
                check=True,
            )
            trace_file = next((cwd / ".claude" / "traces").glob("*.jsonl"))
            return json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])

    def test_success_from_structured_fields_ignores_error_words(self) -> None:
        entry = self._run_writer(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "printf error"},
                "tool_response": {
                    "outcome": {"status": "success", "reason": "expected diagnostic", "source": "tool", "recoverable": False},
                    "output": "error is just payload text",
                },
            }
        )
        self.assertEqual(entry["status"], "success")
        self.assertEqual(entry["outcome"], "success")
        self.assertEqual(entry["source"], "tool")

    def test_failed_skipped_blocked_and_malformed_from_structured_fields(self) -> None:
        expected = {"failure": "failure", "skipped": "skipped", "blocked": "blocked", "bogus": "malformed"}
        for raw_status, normalized in expected.items():
            with self.subTest(raw_status=raw_status):
                entry = self._run_writer(
                    {
                        "tool_name": "Read",
                        "tool_input": {"file_path": "README.md"},
                        "tool_response": {
                            "outcome": {
                                "status": raw_status,
                                "reason": "structured status wins",
                                "error_code": "E_TEST",
                                "source": "hook-test",
                                "recoverable": raw_status == "skipped",
                            },
                            "content": "human-readable success message must not decide status",
                        },
                    }
                )
                self.assertEqual(entry["status"], normalized)
                self.assertEqual(entry["outcome_fields"]["status"], normalized)
                self.assertEqual(entry["reason"], "structured status wins")

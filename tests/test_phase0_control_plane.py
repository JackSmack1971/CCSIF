from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

import phase0_control_plane as phase0


class Phase0ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.state_root = self.workspace / ".claude" / "state"
        self.env_patch = patch.dict(
            os.environ,
            {
                "PHASE0_STATE_ROOT": str(self.state_root),
                "PHASE0_WORKSPACE_ROOT": str(self.workspace),
            },
            clear=False,
        )
        self.env_patch.start()
        self.control = phase0.Phase0ControlPlane(root=self.state_root)

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.tmp.cleanup()

    def _tool_payload(self, session_id: str, *, tool_use_id: str = "tool-1", file_path: str = "notes.txt") -> dict[str, object]:
        return {
            "session_id": session_id,
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": "alpha"},
            "cwd": str(self.workspace),
            "hook_event_name": "PreToolUse",
            "permission_mode": "default",
            "tool_use_id": tool_use_id,
        }

    def test_tool_request_and_result_replay_from_logs(self) -> None:
        session = self.control.start(notes="loop")
        request_payload = self._tool_payload(session.session_id)
        request_event = self.control.request_tool(request_payload)
        result_event = self.control.result_tool(
            {
                "session_id": session.session_id,
                "tool_use_id": request_event.tool_call_id,
                "tool_name": "Write",
                "status": "success",
                "duration_ms": 12,
                "tool_response": {"written": "notes.txt", "payload": {"nested": [1, 2, 3]}},
            }
        )

        replay = self.control.replay(session.session_id)
        self.assertEqual([event["event_type"] for event in replay[:3]], ["session.start", "tool.request", "tool.result"])
        self.assertEqual(replay[1]["payload"]["tool_input"]["file_path"], "notes.txt")
        self.assertEqual(replay[2]["payload"]["result"], {"written": "notes.txt", "payload": {"nested": [1, 2, 3]}})
        self.assertEqual(request_event.tool_call_id, result_event.tool_call_id)

        raw_path = self.state_root / "raw" / session.session_id / "raw-events.jsonl"
        raw_lines = raw_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(raw_lines), 2)
        self.assertEqual(json.loads(raw_lines[0])["tool_name"], "Write")
        self.assertEqual(json.loads(raw_lines[1])["tool_response"]["payload"]["nested"], [1, 2, 3])

    def test_restart_reconstructs_state_and_resume_restores_verified_checkpoint(self) -> None:
        session = self.control.start(notes="restart")
        self.control.request_tool(self._tool_payload(session.session_id))
        self.control.result_tool(
            {
                "session_id": session.session_id,
                "tool_use_id": "tool-1",
                "tool_name": "Write",
                "status": "success",
                "duration_ms": 7,
                "tool_result": {"ok": True},
            }
        )
        self.control.verify(session.session_id, passed=True, details="verified")
        checkpoint = self.control.compact(session.session_id, reason="smoke")
        self.control.pause(session.session_id, reason="simulated interruption")

        restarted = phase0.Phase0ControlPlane(root=self.state_root)
        reconstructed = restarted.reconstruct(session.session_id)
        self.assertEqual(reconstructed["session"]["verified_step_index"], 1)
        self.assertEqual(reconstructed["session"]["last_checkpoint_id"], checkpoint["checkpoint_id"])

        resumed = restarted.resume(session.session_id)
        self.assertEqual(resumed.current_turn_index, 2)
        self.assertEqual(resumed.verified_step_index, 1)
        self.assertEqual(resumed.status, "active")

    def test_sandbox_rejection_happens_before_execution(self) -> None:
        session = self.control.start(notes="sandbox")

        with self.assertRaises(phase0.UnsafeToolRequestError):
            self.control.request_tool(self._tool_payload(session.session_id, file_path="../outside.txt"))

        replay = self.control.replay(session.session_id)
        self.assertEqual([event["event_type"] for event in replay], ["session.start"])

    def test_one_verified_step_at_a_time_is_enforced(self) -> None:
        session = self.control.start(notes="single-step")
        self.control.request_tool(self._tool_payload(session.session_id, tool_use_id="tool-a"))

        with self.assertRaises(phase0.Phase0Error):
            self.control.request_tool(self._tool_payload(session.session_id, tool_use_id="tool-b"))

    def test_terminal_failure_after_retry_exhaustion_is_explicit(self) -> None:
        session = self.control.start(notes="retry")

        def executor(_: dict[str, object]) -> dict[str, object]:
            raise phase0.TransientToolError("timeout")

        with self.assertRaises(phase0.TerminalToolFailure):
            self.control.execute_tool(self._tool_payload(session.session_id), executor, retries=1)

        replay = self.control.replay(session.session_id)
        self.assertTrue(any(event["event_type"] == "tool.retry" for event in replay))
        failure = next(event for event in replay if event["event_type"] == "tool.result")
        self.assertEqual(failure["status"], "failure")
        self.assertEqual(failure["payload"]["error"], "TransientToolError: timeout")
        self.assertEqual(self.control.load_session(session.session_id).status, "failed")


if __name__ == "__main__":
    unittest.main()

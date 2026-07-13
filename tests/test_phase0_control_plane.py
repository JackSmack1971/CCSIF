from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import time
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
        # Non-secret nested structure must survive redaction unchanged.
        self.assertEqual(replay[2]["payload"]["result"], {"written": "notes.txt", "payload": {"nested": [1, 2, 3]}})
        self.assertEqual(request_event.tool_call_id, result_event.tool_call_id)

        # Raw payload capture is opt-in and off by default: no raw export is
        # ever created for this session.
        raw_path = self.state_root / "raw" / session.session_id / "raw-events.jsonl"
        self.assertFalse(raw_path.exists())

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

    def test_raw_capture_opt_in_captures_payload_verbatim(self) -> None:
        with patch.dict(os.environ, {"PHASE0_CAPTURE_RAW_PAYLOADS": "true"}, clear=False):
            session = self.control.start(notes="raw-opt-in")
            request_event = self.control.request_tool(self._tool_payload(session.session_id))
            self.control.result_tool(
                {
                    "session_id": session.session_id,
                    "tool_use_id": request_event.tool_call_id,
                    "tool_name": "Write",
                    "status": "success",
                    "duration_ms": 1,
                    "tool_response": {"nested": [1, 2, 3]},
                }
            )

        raw_path = self.state_root / "raw" / session.session_id / "raw-events.jsonl"
        self.assertTrue(raw_path.exists())
        raw_lines = raw_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(raw_lines), 2)
        self.assertEqual(json.loads(raw_lines[1])["tool_response"]["nested"], [1, 2, 3])

    def test_normalized_persistence_redacts_secret_shaped_values(self) -> None:
        session = self.control.start(notes="redact")
        canary_command = (
            "curl -H 'Authorization: Bearer canary-fake-token-do-not-persist-1234567890' "
            "https://example.test"
        )
        canary_key = "sk-canaryFAKEKEYFORTESTONLY1234567890"
        request_payload = {
            "session_id": session.session_id,
            "tool_name": "Bash",
            "tool_input": {"command": canary_command},
            "cwd": str(self.workspace),
            "hook_event_name": "PreToolUse",
            "permission_mode": "default",
            "tool_use_id": "tool-redact-1",
        }
        request_event = self.control.request_tool(request_payload)
        self.control.result_tool(
            {
                "session_id": session.session_id,
                "tool_use_id": request_event.tool_call_id,
                "tool_name": "Bash",
                "status": "success",
                "duration_ms": 1,
                "tool_response": {"stdout": f"token={canary_key}", "nested": {"count": 3}},
            }
        )

        log_path = self.state_root / "logs" / f"{session.session_id}.jsonl"
        log_text = log_path.read_text(encoding="utf-8")
        self.assertNotIn(canary_key, log_text)
        self.assertNotIn("canary-fake-token-do-not-persist", log_text)

        replay = self.control.replay(session.session_id)
        result_event = next(event for event in replay if event["event_type"] == "tool.result")
        # Non-secret nested structure is preserved exactly.
        self.assertEqual(result_event["payload"]["result"]["nested"], {"count": 3})

        with self.control._db() as conn:
            row = conn.execute(
                "select payload_json from events where event_type = 'tool.result'"
            ).fetchone()
        self.assertNotIn(canary_key, row["payload_json"])

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions only")
    def test_generated_files_get_restrictive_permissions(self) -> None:
        db_mode = stat.S_IMODE((self.state_root / "phase0.sqlite3").stat().st_mode)
        self.assertEqual(db_mode, 0o600)

        session = self.control.start(notes="perm")
        request_event = self.control.request_tool(self._tool_payload(session.session_id))
        self.control.result_tool(
            {
                "session_id": session.session_id,
                "tool_use_id": request_event.tool_call_id,
                "tool_name": "Write",
                "status": "success",
                "duration_ms": 1,
                "tool_result": {"ok": True},
            }
        )
        log_path = self.state_root / "logs" / f"{session.session_id}.jsonl"
        log_mode = stat.S_IMODE(log_path.stat().st_mode)
        self.assertEqual(log_mode, 0o600)

    def test_rotate_if_oversized_caps_growth(self) -> None:
        path = Path(self.tmp.name) / "rotate-test.jsonl"
        path.write_text("x" * 100, encoding="utf-8")
        phase0._rotate_if_oversized(path, max_bytes=10)
        self.assertFalse(path.exists())
        rotated = path.with_name(path.name + ".1")
        self.assertTrue(rotated.exists())

    def test_prune_removes_entries_older_than_retention_and_keeps_recent(self) -> None:
        with patch.dict(os.environ, {"PHASE0_CAPTURE_RAW_PAYLOADS": "true"}, clear=False):
            session = self.control.start(notes="prune")
            request_event = self.control.request_tool(self._tool_payload(session.session_id))
            self.control.result_tool(
                {
                    "session_id": session.session_id,
                    "tool_use_id": request_event.tool_call_id,
                    "tool_name": "Write",
                    "status": "success",
                    "duration_ms": 1,
                    "tool_result": {"ok": True},
                }
            )

        old_log = self.state_root / "logs" / f"{session.session_id}.jsonl"
        old_raw = self.state_root / "raw" / session.session_id / "raw-events.jsonl"
        old_time = time.time() - (phase0.DEFAULT_RETENTION_DAYS + 1) * 86400
        os.utime(old_log, (old_time, old_time))
        os.utime(old_raw, (old_time, old_time))

        removed = self.control.prune(retention_days=phase0.DEFAULT_RETENTION_DAYS)
        self.assertIn(str(old_log), removed)
        self.assertIn(str(old_raw), removed)
        self.assertFalse(old_log.exists())
        self.assertFalse(old_raw.exists())

    def test_secret_scan_detects_secret_and_passes_when_clean(self) -> None:
        repo_dir = Path(self.tmp.name) / "scan-repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
        fixture = repo_dir / "sample.txt"
        canary = "AKIACANARYFAKEEXAMPLE12"

        fixture.write_text(f"token={canary}\n", encoding="utf-8")
        subprocess.run(["git", "add", "sample.txt"], cwd=repo_dir, check=True)
        findings = phase0.scan_staged_diff(cwd=repo_dir)
        self.assertTrue(findings)

        fixture.write_text("no secrets here\n", encoding="utf-8")
        subprocess.run(["git", "add", "sample.txt"], cwd=repo_dir, check=True)
        findings_clean = phase0.scan_staged_diff(cwd=repo_dir)
        self.assertEqual(findings_clean, [])


if __name__ == "__main__":
    unittest.main()

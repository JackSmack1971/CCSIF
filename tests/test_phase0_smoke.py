from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "scripts" / "phase0_control_plane.py"


class Phase0SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.state_root = self.workspace / ".claude" / "state"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PHASE0_STATE_ROOT": str(self.state_root),
                "PHASE0_WORKSPACE_ROOT": str(self.workspace),
                # Raw payload capture is opt-in and off by default (issue #154);
                # this smoke test explicitly opts in to exercise the full
                # raw-export path end to end.
                "PHASE0_CAPTURE_RAW_PAYLOADS": "true",
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: str, input_payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [self._python_exe(), str(SCRIPT), *args],
            input=json.dumps(input_payload) if input_payload is not None else None,
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.strip())
        return proc

    def _python_exe(self) -> str:
        import sys

        return sys.executable

    def test_restart_resume_and_compaction_smoke(self) -> None:
        start = self.run_cli("start", input_payload={"initialUserMessage": "phase0 smoke"})
        session = json.loads(start.stdout)
        session_id = session["session_id"]

        request = self.run_cli(
            "request",
            input_payload={
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": "notes.txt", "content": "smoke"},
                "cwd": str(self.workspace),
                "hook_event_name": "PreToolUse",
                "permission_mode": "default",
                "tool_use_id": "tool-1",
            },
        )
        request_event = json.loads(request.stdout)

        result = self.run_cli(
            "result",
            input_payload={
                "session_id": session_id,
                "tool_use_id": request_event["tool_call_id"],
                "tool_name": "Write",
                "tool_response": {"written": "notes.txt"},
                "status": "success",
                "duration_ms": 4,
            },
        )
        self.assertEqual(json.loads(result.stdout)["status"], "success")

        verify = self.run_cli("verify", session_id)
        self.assertEqual(json.loads(verify.stdout)["status"], "success")

        compact = self.run_cli("compact", session_id, input_payload={"session_id": session_id, "reason": "smoke"})
        checkpoint = json.loads(compact.stdout)
        self.assertTrue(checkpoint["verified"])

        paused = self.run_cli("pause", session_id, input_payload={"session_id": session_id, "reason": "interruption"})
        self.assertEqual(json.loads(paused.stdout)["status"], "paused")

        resumed = self.run_cli("resume", session_id)
        resumed_session = json.loads(resumed.stdout)
        self.assertEqual(resumed_session["status"], "active")
        self.assertEqual(resumed_session["current_turn_index"], 2)

        archive = self.run_cli("archive", session_id, input_payload={"session_id": session_id, "reason": "smoke complete"})
        archive_payload = json.loads(archive.stdout)
        self.assertEqual(archive_payload["session"]["session_id"], session_id)

        checkpoint_path = self.state_root / "checkpoints" / f"{session_id}-t1-s1.json"
        self.assertTrue(checkpoint_path.exists())
        raw_path = self.state_root / "raw" / session_id / "raw-events.jsonl"
        self.assertTrue(raw_path.exists())
        self.assertGreaterEqual(len(raw_path.read_text(encoding="utf-8").splitlines()), 2)

    def _hook_tool_roundtrip(self, session_id: str, tool_use_id: str) -> None:
        """Exactly the PreToolUse -> PostToolUse CLI sequence the real hooks
        run: `request` then `result`, with no verify in between."""
        self.run_cli(
            "request",
            input_payload={
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": f"{tool_use_id}.txt", "content": "smoke"},
                "cwd": str(self.workspace),
                "hook_event_name": "PreToolUse",
                "permission_mode": "default",
                "tool_use_id": tool_use_id,
            },
        )
        self.run_cli(
            "result",
            input_payload={
                "session_id": session_id,
                "tool_use_id": tool_use_id,
                "tool_name": "Write",
                "tool_response": {"written": f"{tool_use_id}.txt"},
                "status": "success",
                "duration_ms": 2,
            },
        )

    def test_sequential_successful_tools_do_not_deadlock_the_hook_chain(self) -> None:
        """Hardening 03/13 (#151): the exact production sequence that used to
        raise 'one verified step at a time' on the second request now runs
        clean through the same CLI path pre-tool-use.sh/post-tool-use.sh use."""
        start = self.run_cli("start", input_payload={"initialUserMessage": "sequential smoke"})
        session_id = json.loads(start.stdout)["session_id"]
        self._hook_tool_roundtrip(session_id, "tool-1")
        self._hook_tool_roundtrip(session_id, "tool-2")
        self._hook_tool_roundtrip(session_id, "tool-3")
        reconstructed = json.loads(self.run_cli("reconstruct", session_id).stdout)
        self.assertEqual(reconstructed["session"]["step_state"], "tool_completed")
        self.assertIsNone(reconstructed["session"]["pending_tool_call_id"])
        results = [e for e in reconstructed["events"] if e["event_type"] == "tool.result"]
        self.assertEqual(len(results), 3)

    def test_precompact_before_any_verify_is_a_recorded_skip_not_a_failure(self) -> None:
        """pre-compact.sh runs `compact` on every real PreCompact event; with
        no hook ever calling `verify`, that must be a recorded skip (exit 0),
        not a hook-failing VerifiedCheckpointError."""
        start = self.run_cli("start", input_payload={"initialUserMessage": "compact smoke"})
        session_id = json.loads(start.stdout)["session_id"]
        self._hook_tool_roundtrip(session_id, "tool-1")
        compact = self.run_cli("compact", session_id, input_payload={"session_id": session_id, "reason": "auto"})
        payload = json.loads(compact.stdout)
        self.assertTrue(payload["skipped"])
        self.assertIsNone(payload["checkpoint_id"])

    def test_recover_subcommand_unwedges_a_stale_pending_step(self) -> None:
        start = self.run_cli("start", input_payload={"session_id": "sess-cli-stale"})
        session_id = json.loads(start.stdout)["session_id"]
        self.run_cli(
            "request",
            input_payload={
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": "wedged.txt"},
                "cwd": str(self.workspace),
                "tool_use_id": "tool-wedged",
            },
        )
        recovered = self.run_cli("recover", session_id, input_payload={"session_id": session_id})
        payload = json.loads(recovered.stdout)
        self.assertEqual(payload["step_state"], "tool_failed")
        self.assertIsNone(payload["pending_tool_call_id"])


if __name__ == "__main__":
    unittest.main()

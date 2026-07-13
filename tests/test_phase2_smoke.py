from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE2_SCRIPT = ROOT / ".claude" / "scripts" / "phase2_memory.py"
PHASE0_SCRIPT = ROOT / ".claude" / "scripts" / "phase0_control_plane.py"
SESSION_START_HOOK = ROOT / ".claude" / "hooks" / "session-start.sh"
PRE_COMPACT_HOOK = ROOT / ".claude" / "hooks" / "pre-compact.sh"
POST_COMPACT_HOOK = ROOT / ".claude" / "hooks" / "post-compact.sh"
SUBAGENT_STOP_HOOK = ROOT / ".claude" / "hooks" / "subagent-stop.sh"


def _bash() -> str | None:
    return shutil.which("bash")


@unittest.skipUnless(_bash(), "bash is required for hook-level smoke coverage")
class Phase2HookSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "CLAUDE.md").write_text("# facts\n", encoding="utf-8")
        self.state_root = self.workspace / ".claude" / "state"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PHASE0_STATE_ROOT": str(self.state_root),
                "PHASE0_WORKSPACE_ROOT": str(self.workspace),
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_cli(self, *args: str, input_payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PHASE2_SCRIPT), *args],
            input=json.dumps(input_payload) if input_payload is not None else None,
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )

    def _run_hook(self, hook: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [_bash(), str(hook)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )

    def test_fresh_clone_session_start_hook_bootstraps_and_starts_session(self) -> None:
        settings_local = self.workspace / ".claude" / "settings.local.json"
        self.assertFalse(settings_local.exists())

        proc = self._run_hook(
            SESSION_START_HOOK,
            {"session_id": "sess-smoke-1", "cwd": str(self.workspace), "source": "startup"},
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(settings_local.exists(), "SessionStart hook must bootstrap settings.local.json on a fresh clone")
        data = json.loads(settings_local.read_text(encoding="utf-8"))
        self.assertTrue(Path(data["autoMemoryDirectory"]).is_absolute())

    def test_session_start_hook_is_safe_when_settings_local_already_exists(self) -> None:
        settings_local = self.workspace / ".claude" / "settings.local.json"
        settings_local.parent.mkdir(parents=True, exist_ok=True)
        settings_local.write_text(json.dumps({"env": {"KEEP": "me"}}), encoding="utf-8")

        proc = self._run_hook(
            SESSION_START_HOOK,
            {"session_id": "sess-smoke-2", "cwd": str(self.workspace), "source": "startup"},
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(settings_local.read_text(encoding="utf-8"))
        self.assertEqual(data["env"], {"KEEP": "me"})
        self.assertTrue(Path(data["autoMemoryDirectory"]).is_absolute())

    def test_precompact_then_postcompact_then_session_start_restore_end_to_end(self) -> None:
        session_id = "sess-smoke-3"
        start_payload = {"session_id": session_id, "cwd": str(self.workspace), "source": "startup"}
        self.assertEqual(self._run_hook(SESSION_START_HOOK, start_payload).returncode, 0)

        request = subprocess.run(
            [sys.executable, str(PHASE0_SCRIPT), "request"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "tool_name": "Write",
                    "tool_input": {"file_path": "notes.txt"},
                    "cwd": str(self.workspace),
                    "tool_use_id": "tool-1",
                }
            ),
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )
        self.assertEqual(request.returncode, 0, request.stderr)

        result = subprocess.run(
            [sys.executable, str(PHASE0_SCRIPT), "result"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "tool_use_id": "tool-1",
                    "tool_name": "Write",
                    "status": "success",
                    "tool_result": {"ok": True},
                }
            ),
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        verify = subprocess.run(
            [sys.executable, str(PHASE0_SCRIPT), "verify", session_id, "--details", "smoke"],
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )
        self.assertEqual(verify.returncode, 0, verify.stderr)

        precompact = self._run_hook(
            PRE_COMPACT_HOOK, {"session_id": session_id, "trigger": "manual", "custom_instructions": ""}
        )
        self.assertEqual(precompact.returncode, 0, precompact.stderr)

        postcompact = self._run_hook(
            POST_COMPACT_HOOK,
            {"session_id": session_id, "trigger": "manual", "compact_summary": "Verified the ledger fixture."},
        )
        self.assertEqual(postcompact.returncode, 0, postcompact.stderr)

        restore_proc = self._run_hook(SESSION_START_HOOK, {"session_id": session_id, "cwd": str(self.workspace), "source": "compact"})
        self.assertEqual(restore_proc.returncode, 0, restore_proc.stderr)
        hook_output = json.loads(restore_proc.stdout.strip())
        self.assertIn("Restored project memory", hook_output["hookSpecificOutput"]["additionalContext"])
        self.assertIn("Verified the ledger fixture.", hook_output["hookSpecificOutput"]["additionalContext"])

        status = self._run_cli("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        status_payload = json.loads(status.stdout)
        self.assertEqual(status_payload["compactions"]["snapshot_count"], 1)
        self.assertEqual(status_payload["compactions"]["summary_count"], 1)

    def test_subagent_stop_hook_exports_summary(self) -> None:
        session_id = "sess-smoke-4"
        proc = self._run_hook(
            SUBAGENT_STOP_HOOK,
            {
                "session_id": session_id,
                "agent_id": "agent-99",
                "agent_type": "Explore",
                "agent_transcript_path": "~/.claude/projects/x/subagents/agent-99.jsonl",
                "last_assistant_message": "Found the target file.",
            },
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        export_path = self.state_root / "agents" / session_id / "agent-99.json"
        self.assertTrue(export_path.exists())
        record = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(record["parent_session_id"], session_id)
        self.assertEqual(record["agent_type"], "Explore")


if __name__ == "__main__":
    unittest.main()

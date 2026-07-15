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
PHASE3_SCRIPT = ROOT / ".claude" / "scripts" / "phase3_agents.py"
SUBAGENT_START_HOOK = ROOT / ".claude" / "hooks" / "subagent-start.sh"
SUBAGENT_STOP_HOOK = ROOT / ".claude" / "hooks" / "subagent-stop.sh"


def _bash() -> str | None:
    return shutil.which("bash")


@unittest.skipUnless(_bash(), "bash is required for hook-level smoke coverage")
class Phase3HookSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Only state is isolated to a temp root. Workspace root stays the real
        # repo (unlike the Phase 2 fresh-clone smoke tests) because role
        # routing reads the real `.claude/agents/*.md` catalog, which a fresh
        # empty temp workspace wouldn't have.
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PHASE0_STATE_ROOT": str(self.state_root),
                "PHASE0_WORKSPACE_ROOT": str(ROOT),
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_hook(self, hook: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [_bash(), hook.relative_to(ROOT).as_posix()],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PHASE3_SCRIPT), *args],
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            env=self.env,
            check=False,
        )

    def test_real_subagent_start_and_stop_hooks_produce_a_reconstructable_task(self) -> None:
        session_id = "sess-p3-smoke-1"
        agent_id = "agent-p3-smoke-1"

        start_proc = self._run_hook(
            SUBAGENT_START_HOOK,
            {"session_id": session_id, "agent_id": agent_id, "agent_type": "builder", "cwd": str(ROOT)},
        )
        self.assertEqual(start_proc.returncode, 0, start_proc.stderr)

        task_path = self.state_root / "agents" / session_id / f"{agent_id}.task.json"
        self.assertTrue(task_path.exists())
        record = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "running")
        self.assertEqual(record["role"], "scoped-builder")
        self.assertEqual(record["isolation"], "worktree")

        stop_proc = self._run_hook(
            SUBAGENT_STOP_HOOK,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "agent_type": "builder",
                "agent_transcript_path": "~/.claude/projects/x/subagents/agent-p3-smoke-1.jsonl",
                "last_assistant_message": "Implemented the change and ran the tests.",
                "cwd": str(ROOT),
            },
        )
        self.assertEqual(stop_proc.returncode, 0, stop_proc.stderr)
        updated = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["exported_summary"], "Implemented the change and ran the tests.")

        # Phase 2's own export must be untouched/co-existing, not replaced.
        phase2_export = self.state_root / "agents" / session_id / f"{agent_id}.json"
        self.assertTrue(phase2_export.exists())

        list_proc = self._run_cli("list")
        self.assertEqual(list_proc.returncode, 0, list_proc.stderr)
        tasks = json.loads(list_proc.stdout)
        self.assertEqual(len([t for t in tasks if t["task_id"] == f"{session_id}:{agent_id}"]), 1)

        handoff_proc = self._run_cli(
            "handoff",
            "--parent-session-id",
            session_id,
            "--agent-id",
            agent_id,
            "--verification-command",
            "true",
            "--verification-exit-code",
            "0",
        )
        self.assertEqual(handoff_proc.returncode, 0, handoff_proc.stderr)
        handed_off = json.loads(handoff_proc.stdout)
        self.assertEqual(handed_off["status"], "merged")
        self.assertTrue(handed_off["merge_handoff_result"]["verified"])

    def test_sweep_cli_reports_no_stale_tasks_for_a_fresh_run(self) -> None:
        self._run_hook(
            SUBAGENT_START_HOOK,
            {"session_id": "sess-p3-smoke-2", "agent_id": "agent-p3-smoke-2", "agent_type": "scout", "cwd": str(ROOT)},
        )
        sweep_proc = self._run_cli("sweep", "--stale-after-minutes", "120")
        self.assertEqual(sweep_proc.returncode, 0, sweep_proc.stderr)
        self.assertEqual(json.loads(sweep_proc.stdout)["marked_stale"], [])


if __name__ == "__main__":
    unittest.main()

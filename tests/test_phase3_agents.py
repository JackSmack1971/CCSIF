from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

import phase0_control_plane as phase0  # noqa: E402
import phase3_agents as phase3  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


class Phase3AgentsTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.tmp.cleanup()

    # -- role selection / routing -----------------------------------------

    def test_route_resolves_project_agent_role_from_real_catalog(self) -> None:
        routing = phase3.route("builder", workspace=REPO_ROOT)
        self.assertEqual(routing["role"], "scoped-builder")
        self.assertEqual(routing["isolation"], "worktree")
        self.assertIn("Edit", routing["tools"])

    def test_route_resolves_read_only_scout_with_no_write_tools(self) -> None:
        routing = phase3.route("scout", workspace=REPO_ROOT)
        self.assertEqual(routing["role"], "read-only-researcher")
        self.assertNotIn("Write", routing["tools"])
        self.assertNotIn("Edit", routing["tools"])
        self.assertNotIn("Bash", routing["tools"])

    def test_route_resolves_planner_with_no_write_tools(self) -> None:
        routing = phase3.route("planner", workspace=REPO_ROOT)
        self.assertEqual(routing["role"], "planner")
        self.assertNotIn("Write", routing["tools"])
        self.assertNotIn("Edit", routing["tools"])

    def test_route_builtin_agent(self) -> None:
        routing = phase3.route("Explore", workspace=REPO_ROOT)
        self.assertEqual(routing["role"], "read-only-researcher")
        self.assertEqual(routing["routing"], "builtin")

    def test_route_unknown_agent_is_unrouted_not_blocked(self) -> None:
        routing = phase3.route("totally-unknown-agent", workspace=REPO_ROOT)
        self.assertEqual(routing["role"], "unrouted")
        self.assertEqual(routing["routing"], "unrouted")

    # -- denied tool use (static catalog assertions) -----------------------

    def test_verifier_has_no_write_or_edit_tools(self) -> None:
        routing = phase3.route("verifier", workspace=REPO_ROOT)
        self.assertNotIn("Write", routing["tools"])
        self.assertNotIn("Edit", routing["tools"])

    # -- parent-child linkage / summary schema -----------------------------

    def test_subagent_start_then_stop_links_task_id_to_parent_and_agent(self) -> None:
        path = phase3.subagent_start(
            {"session_id": "sess-1", "agent_id": "agent-1", "agent_type": "builder"}
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["task_id"], "sess-1:agent-1")
        self.assertEqual(record["parent_session_id"], "sess-1")
        self.assertEqual(record["agent_id"], "agent-1")
        self.assertEqual(record["status"], "running")
        self.assertEqual(record["stop_resume_state"], "running")

        stop_path = phase3.subagent_stop(
            {
                "session_id": "sess-1",
                "agent_id": "agent-1",
                "agent_type": "builder",
                "last_assistant_message": "done, ran tests",
                "agent_transcript_path": "/tmp/agent-1.jsonl",
            }
        )
        self.assertEqual(stop_path, path)
        updated = json.loads(stop_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["stop_resume_state"], "stopped")
        self.assertEqual(updated["exported_summary"], "done, ran tests")
        self.assertEqual(updated["transcript_pointer"], "/tmp/agent-1.jsonl")
        self.assertIsNotNone(updated["completed_at"])

    def test_subagent_stop_without_prior_start_reconstructs_record(self) -> None:
        path = phase3.subagent_stop(
            {
                "session_id": "sess-2",
                "agent_id": "agent-2",
                "agent_type": "scout",
                "last_assistant_message": "findings: none",
                "agent_transcript_path": "/tmp/agent-2.jsonl",
            }
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["task_id"], "sess-2:agent-2")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["routing"], "reconstructed-at-stop")

    def test_subagent_start_missing_ids_raises(self) -> None:
        with self.assertRaises(phase3.Phase3Error):
            phase3.subagent_start({"session_id": "", "agent_id": ""})

    # -- stale worker cleanup / interruption visibility --------------------

    def test_sweep_marks_long_running_task_stale(self) -> None:
        path = phase3.subagent_start(
            {"session_id": "sess-3", "agent_id": "agent-3", "agent_type": "builder"}
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        record["started_at"] = (datetime.now(timezone.utc) - timedelta(minutes=200)).isoformat().replace(
            "+00:00", "Z"
        )
        path.write_text(json.dumps(record), encoding="utf-8")

        changed = phase3.sweep(stale_after_minutes=120)
        self.assertEqual(changed, ["sess-3:agent-3"])
        updated = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(updated["status"], "stale")
        self.assertEqual(updated["stop_resume_state"], "stale")
        self.assertIn("stale_detected_at", updated)

    def test_sweep_leaves_recent_running_task_alone(self) -> None:
        path = phase3.subagent_start(
            {"session_id": "sess-4", "agent_id": "agent-4", "agent_type": "builder"}
        )
        changed = phase3.sweep(stale_after_minutes=120)
        self.assertEqual(changed, [])
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "running")

    def test_sweep_does_not_touch_completed_tasks(self) -> None:
        phase3.subagent_start({"session_id": "sess-5", "agent_id": "agent-5", "agent_type": "builder"})
        stop_path = phase3.subagent_stop(
            {"session_id": "sess-5", "agent_id": "agent-5", "agent_type": "builder", "last_assistant_message": "ok"}
        )
        record = json.loads(stop_path.read_text(encoding="utf-8"))
        record["started_at"] = (datetime.now(timezone.utc) - timedelta(minutes=300)).isoformat().replace(
            "+00:00", "Z"
        )
        stop_path.write_text(json.dumps(record), encoding="utf-8")
        changed = phase3.sweep(stale_after_minutes=120)
        self.assertEqual(changed, [])

    # -- verified merge/handoff: summary is never treated as proof ---------

    def test_handoff_with_verification_evidence_marks_merged(self) -> None:
        phase3.subagent_start({"session_id": "sess-6", "agent_id": "agent-6", "agent_type": "builder"})
        phase3.subagent_stop(
            {"session_id": "sess-6", "agent_id": "agent-6", "agent_type": "builder", "last_assistant_message": "done"}
        )
        record = phase3.handoff(
            parent_session_id="sess-6",
            agent_id="agent-6",
            verification_command="pytest -q",
            verification_exit_code=0,
            note="re-ran the suite myself",
            summary_only=False,
        )
        self.assertEqual(record["status"], "merged")
        self.assertTrue(record["merge_handoff_result"]["verified"])
        self.assertEqual(record["merge_handoff_result"]["command"], "pytest -q")

    def test_handoff_with_failing_verification_is_not_merged(self) -> None:
        phase3.subagent_start({"session_id": "sess-7", "agent_id": "agent-7", "agent_type": "builder"})
        phase3.subagent_stop(
            {"session_id": "sess-7", "agent_id": "agent-7", "agent_type": "builder", "last_assistant_message": "done"}
        )
        record = phase3.handoff(
            parent_session_id="sess-7",
            agent_id="agent-7",
            verification_command="pytest -q",
            verification_exit_code=1,
            note=None,
            summary_only=False,
        )
        self.assertEqual(record["status"], "handoff-failed-verification")
        self.assertFalse(record["merge_handoff_result"]["verified"])

    def test_handoff_summary_only_is_recorded_unverified(self) -> None:
        phase3.subagent_start({"session_id": "sess-8", "agent_id": "agent-8", "agent_type": "scout"})
        phase3.subagent_stop(
            {"session_id": "sess-8", "agent_id": "agent-8", "agent_type": "scout", "last_assistant_message": "findings"}
        )
        record = phase3.handoff(
            parent_session_id="sess-8",
            agent_id="agent-8",
            verification_command=None,
            verification_exit_code=None,
            note="no runnable check for this research task",
            summary_only=True,
        )
        self.assertEqual(record["status"], "handoff-unverified")
        self.assertFalse(record["merge_handoff_result"]["verified"])
        self.assertIn("not treated as proof", record["merge_handoff_result"]["reason"])

    def test_handoff_without_evidence_and_without_summary_only_flag_raises(self) -> None:
        phase3.subagent_start({"session_id": "sess-9", "agent_id": "agent-9", "agent_type": "builder"})
        phase3.subagent_stop(
            {"session_id": "sess-9", "agent_id": "agent-9", "agent_type": "builder", "last_assistant_message": "done"}
        )
        with self.assertRaises(phase3.Phase3Error):
            phase3.handoff(
                parent_session_id="sess-9",
                agent_id="agent-9",
                verification_command=None,
                verification_exit_code=None,
                note=None,
                summary_only=False,
            )

    def test_handoff_on_still_running_task_raises(self) -> None:
        phase3.subagent_start({"session_id": "sess-10", "agent_id": "agent-10", "agent_type": "builder"})
        with self.assertRaises(phase3.Phase3Error):
            phase3.handoff(
                parent_session_id="sess-10",
                agent_id="agent-10",
                verification_command="pytest -q",
                verification_exit_code=0,
                note=None,
                summary_only=False,
            )

    def test_handoff_on_unknown_task_raises(self) -> None:
        with self.assertRaises(phase3.Phase3Error):
            phase3.handoff(
                parent_session_id="sess-missing",
                agent_id="agent-missing",
                verification_command="pytest -q",
                verification_exit_code=0,
                note=None,
                summary_only=False,
            )

    # -- reconstruction without opening transcripts ------------------------

    def test_list_tasks_reconstructs_across_parent_sessions(self) -> None:
        phase3.subagent_start({"session_id": "sess-11", "agent_id": "agent-11", "agent_type": "builder"})
        phase3.subagent_start({"session_id": "sess-12", "agent_id": "agent-12", "agent_type": "scout"})
        phase3.subagent_stop(
            {"session_id": "sess-12", "agent_id": "agent-12", "agent_type": "scout", "last_assistant_message": "x"}
        )
        tasks = phase3.list_tasks()
        task_ids = {t["task_id"] for t in tasks}
        self.assertIn("sess-11:agent-11", task_ids)
        self.assertIn("sess-12:agent-12", task_ids)
        statuses = {t["task_id"]: t["status"] for t in tasks}
        self.assertEqual(statuses["sess-11:agent-11"], "running")
        self.assertEqual(statuses["sess-12:agent-12"], "completed")

    # -- checkpoint linkage: best-effort attach of latest verified checkpoint

    def test_subagent_start_attaches_latest_verified_checkpoint_when_present(self) -> None:
        control = phase0.Phase0ControlPlane(root=self.state_root)
        session = control.start(session_id="sess-13", notes="fixture")
        control.request_tool(
            {
                "session_id": "sess-13",
                "tool_name": "Write",
                "tool_input": {"file_path": "notes.txt"},
                "cwd": str(self.workspace),
                "tool_use_id": "tool-1",
            }
        )
        control.result_tool(
            {
                "session_id": "sess-13",
                "tool_use_id": "tool-1",
                "tool_name": "Write",
                "status": "success",
                "tool_result": {"ok": True},
            }
        )
        control.verify("sess-13", passed=True, details="fixture")
        control.compact("sess-13", reason="fixture checkpoint")

        path = phase3.subagent_start(
            {"session_id": "sess-13", "agent_id": "agent-13", "agent_type": "builder"}
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNotNone(record["checkpoint"])
        self.assertEqual(record["checkpoint"]["session_id"], "sess-13")

    def test_subagent_start_checkpoint_is_none_when_no_verified_checkpoint(self) -> None:
        path = phase3.subagent_start(
            {"session_id": "sess-14", "agent_id": "agent-14", "agent_type": "builder"}
        )
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsNone(record["checkpoint"])


class Phase3AtomicWriteRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_issue_153_parallel_subagent_records_are_partitioned_and_durable(self) -> None:
        """Regression for issue #153: parallel subagents must not share one mutable state file."""
        from concurrent.futures import ThreadPoolExecutor

        def run_agent(index: int) -> str:
            agent_id = f"agent-{index}"
            phase3.subagent_start(
                {"session_id": "parent-153", "agent_id": agent_id, "agent_type": "builder"},
                root=self.state_root,
                workspace=REPO_ROOT,
            )
            path = phase3.subagent_stop(
                {
                    "session_id": "parent-153",
                    "agent_id": agent_id,
                    "agent_type": "builder",
                    "last_assistant_message": f"summary-{index}",
                },
                root=self.state_root,
            )
            return path.name

        with ThreadPoolExecutor(max_workers=8) as pool:
            names = list(pool.map(run_agent, range(24)))

        self.assertEqual(len(set(names)), 24)
        records = phase3.list_tasks(root=self.state_root)
        self.assertEqual(len(records), 24)
        self.assertEqual({record["status"] for record in records}, {"completed"})
        self.assertEqual(
            {record["exported_summary"] for record in records},
            {f"summary-{index}" for index in range(24)},
        )

    def test_issue_153_atomic_json_update_survives_parallel_stop_same_agent(self) -> None:
        """Regression for issue #153: a same-record stop race leaves valid JSON, not a torn file."""
        from concurrent.futures import ThreadPoolExecutor

        phase3.subagent_start(
            {"session_id": "parent-153", "agent_id": "agent-race", "agent_type": "builder"},
            root=self.state_root,
            workspace=REPO_ROOT,
        )

        def stop(index: int) -> None:
            phase3.subagent_stop(
                {
                    "session_id": "parent-153",
                    "agent_id": "agent-race",
                    "agent_type": "builder",
                    "last_assistant_message": f"winner-{index}",
                },
                root=self.state_root,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(stop, range(32)))

        path = self.state_root / "agents" / "parent-153" / "agent-race.task.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "completed")
        self.assertRegex(record["exported_summary"], r"^winner-\d+$")


if __name__ == "__main__":
    unittest.main()

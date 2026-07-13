from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

import phase0_control_plane as phase0  # noqa: E402
import phase2_memory as phase2  # noqa: E402


class Phase2MemoryTests(unittest.TestCase):
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

    def _make_verified_session(self) -> str:
        control = phase0.Phase0ControlPlane(root=self.state_root)
        session = control.start(notes="phase2 fixture")
        control.request_tool(
            {
                "session_id": session.session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": "notes.txt"},
                "cwd": str(self.workspace),
                "tool_use_id": "tool-1",
            }
        )
        control.result_tool(
            {
                "session_id": session.session_id,
                "tool_use_id": "tool-1",
                "tool_name": "Write",
                "status": "success",
                "tool_result": {"ok": True},
            }
        )
        control.verify(session.session_id, passed=True, details="fixture")
        control.compact(session.session_id, reason="fixture checkpoint")
        return session.session_id

    # -- fresh-clone bootstrap ------------------------------------------------

    def test_fresh_clone_bootstrap_creates_settings_local_with_absolute_path(self) -> None:
        settings_local = phase2.settings_local_path(self.workspace)
        self.assertFalse(settings_local.exists())

        result = phase2.bootstrap_local_settings(self.workspace)

        self.assertEqual(result["status"], "created")
        self.assertTrue(settings_local.exists())
        data = json.loads(settings_local.read_text(encoding="utf-8"))
        self.assertTrue(Path(data["autoMemoryDirectory"]).is_absolute())
        self.assertEqual(Path(data["autoMemoryDirectory"]), (self.workspace / ".claude" / "memory").resolve())

    def test_bootstrap_is_idempotent(self) -> None:
        first = phase2.bootstrap_local_settings(self.workspace)
        settings_local = phase2.settings_local_path(self.workspace)
        mtime_before = settings_local.stat().st_mtime_ns

        second = phase2.bootstrap_local_settings(self.workspace)

        self.assertEqual(first["autoMemoryDirectory"], second["autoMemoryDirectory"])
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(settings_local.stat().st_mtime_ns, mtime_before)

    # -- missing-local-settings recovery / preserving personal keys ----------

    def test_missing_auto_memory_key_is_added_without_clobbering_other_keys(self) -> None:
        settings_local = phase2.settings_local_path(self.workspace)
        settings_local.parent.mkdir(parents=True, exist_ok=True)
        settings_local.write_text(
            json.dumps({"description": "personal overrides", "env": {"FOO": "bar"}}),
            encoding="utf-8",
        )

        result = phase2.bootstrap_local_settings(self.workspace)

        self.assertEqual(result["status"], "updated")
        data = json.loads(settings_local.read_text(encoding="utf-8"))
        self.assertEqual(data["env"], {"FOO": "bar"})
        self.assertEqual(data["description"], "personal overrides")
        self.assertTrue(Path(data["autoMemoryDirectory"]).is_absolute())

    def test_bootstrap_refuses_to_overwrite_unreadable_settings_local(self) -> None:
        settings_local = phase2.settings_local_path(self.workspace)
        settings_local.parent.mkdir(parents=True, exist_ok=True)
        settings_local.write_text("not json", encoding="utf-8")

        with self.assertRaises(phase2.Phase2Error):
            phase2.bootstrap_local_settings(self.workspace)
        self.assertEqual(settings_local.read_text(encoding="utf-8"), "not json")

    # -- compaction snapshot / restore ----------------------------------------

    def test_precompact_snapshot_captures_latest_verified_checkpoint(self) -> None:
        session_id = self._make_verified_session()

        snapshot_path = phase2.precompact_snapshot(
            {"session_id": session_id, "trigger": "auto", "custom_instructions": ""}
        )

        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["session_id"], session_id)
        self.assertIsNotNone(snapshot["checkpoint"])
        self.assertEqual(snapshot["checkpoint"]["session_id"], session_id)

    def test_session_start_restore_validates_matching_snapshot(self) -> None:
        session_id = self._make_verified_session()
        phase2.precompact_snapshot({"session_id": session_id, "trigger": "manual", "custom_instructions": ""})
        phase2.postcompact_record(
            {"session_id": session_id, "trigger": "manual", "compact_summary": "Discussed the ledger module."}
        )

        decision = phase2.session_start_restore({"session_id": session_id, "source": "compact"})

        self.assertTrue(decision["validated"])
        self.assertIn("Restored project memory", decision["additional_context"])
        self.assertIn("Discussed the ledger module.", decision["additional_context"])

    def test_session_start_restore_rejects_stale_or_foreign_snapshot(self) -> None:
        session_id = self._make_verified_session()
        phase2.precompact_snapshot({"session_id": session_id, "trigger": "manual", "custom_instructions": ""})

        # A different session starting fresh must not inherit another session's snapshot.
        decision = phase2.session_start_restore({"session_id": "sess-unrelated", "source": "compact"})

        self.assertFalse(decision["validated"])
        self.assertIn("no precompact snapshot", decision["reason"])

    def test_session_start_restore_rejects_corrupt_snapshot(self) -> None:
        session_id = self._make_verified_session()
        snapshot_path = phase2.precompact_snapshot(
            {"session_id": session_id, "trigger": "manual", "custom_instructions": ""}
        )
        snapshot_path.write_text("{not valid json", encoding="utf-8")

        decision = phase2.session_start_restore({"session_id": session_id, "source": "compact"})

        self.assertFalse(decision["validated"])
        self.assertIn("unreadable", decision["reason"])

    def test_session_start_restore_no_op_for_plain_startup(self) -> None:
        session_id = self._make_verified_session()
        phase2.precompact_snapshot({"session_id": session_id, "trigger": "manual", "custom_instructions": ""})

        decision = phase2.session_start_restore({"session_id": session_id, "source": "startup"})

        self.assertFalse(decision["validated"])

    # -- restart reconstruction -------------------------------------------------

    def test_status_reconstructs_after_restart_from_a_fresh_process_instance(self) -> None:
        session_id = self._make_verified_session()
        phase2.precompact_snapshot({"session_id": session_id, "trigger": "manual", "custom_instructions": ""})
        phase2.postcompact_record({"session_id": session_id, "trigger": "manual", "compact_summary": "s"})
        phase2.subagent_export(
            {
                "session_id": session_id,
                "agent_id": "agent-1",
                "agent_type": "Explore",
                "agent_transcript_path": "~/.claude/projects/x/subagents/agent-1.jsonl",
                "last_assistant_message": "done",
            }
        )
        (self.workspace / "CLAUDE.md").write_text("# facts\n", encoding="utf-8")

        # A brand-new process/module state pointed at the same roots must see the same evidence.
        status = phase2.memory_status(workspace=self.workspace, root=self.state_root)

        self.assertTrue(status["sources"]["CLAUDE.md"])
        self.assertIsNotNone(status["latest_verified_checkpoint"])
        self.assertEqual(status["latest_verified_checkpoint"]["session_id"], session_id)
        self.assertEqual(status["compactions"]["snapshot_count"], 1)
        self.assertEqual(status["compactions"]["summary_count"], 1)
        self.assertEqual(status["agents"]["exported_summary_count"], 1)
        self.assertEqual(status["recovery"]["source"], "native-files")
        self.assertFalse(status["recovery"]["external_index_configured"])

    # -- subagent-summary linkage ------------------------------------------------

    def test_subagent_export_links_back_to_parent_session(self) -> None:
        session_id = self._make_verified_session()

        export_path = phase2.subagent_export(
            {
                "session_id": session_id,
                "agent_id": "agent-42",
                "agent_type": "pr-reviewer",
                "agent_transcript_path": "~/.claude/projects/x/subagents/agent-42.jsonl",
                "last_assistant_message": "Reviewed the diff; no blocking issues.",
            }
        )

        self.assertEqual(export_path, self.state_root / "agents" / session_id / "agent-42.json")
        record = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(record["parent_session_id"], session_id)
        self.assertEqual(record["agent_id"], "agent-42")
        self.assertEqual(record["agent_type"], "pr-reviewer")

    def test_subagent_export_requires_session_and_agent_id(self) -> None:
        with self.assertRaises(phase2.Phase2Error):
            phase2.subagent_export({"agent_id": "agent-1"})
        with self.assertRaises(phase2.Phase2Error):
            phase2.subagent_export({"session_id": "sess-1"})


if __name__ == "__main__":
    unittest.main()

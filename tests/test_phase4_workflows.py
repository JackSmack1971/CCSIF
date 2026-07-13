from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase4_workflows as p4  # noqa: E402
from phase0_control_plane import Phase0ControlPlane  # noqa: E402


class Phase4WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)
        # Workspace stays the real repo so workflow defs under
        # .claude/workflows/defs/ are readable, matching the Phase 3 smoke
        # test convention (state isolated, workspace real).
        self.workspace = ROOT

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _verified_checkpoint(self, session_id: str = "sess-p4") -> str:
        """Build a real, verified Phase 0 checkpoint in the same isolated
        state root, so the checkpoint gate test exercises the actual native
        primitive rather than a fabricated id."""
        control = Phase0ControlPlane(root=self.state_root)
        control.start(session_id=session_id, notes="phase4 checkpoint fixture")
        control.request_tool(
            {
                "session_id": session_id,
                "tool_name": "Write",
                "tool_input": {"file_path": "CLAUDE.md"},
                "cwd": str(self.workspace),
                "tool_use_id": "tool-1",
            }
        )
        control.result_tool(
            {
                "session_id": session_id,
                "tool_use_id": "tool-1",
                "tool_name": "Write",
                "status": "success",
                "tool_result": {"ok": True},
            }
        )
        control.verify(session_id, passed=True, details="fixture step verified")
        checkpoint = control.compact(session_id, reason="phase4 fixture")
        return checkpoint["checkpoint_id"]

    # 1. Linear static workflow -------------------------------------------------
    def test_linear_static_workflow_runs_to_completion(self) -> None:
        run = p4.start_run("linear-static", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]
        self.assertEqual(run["current_node"], "gather-context")

        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        run = p4.advance(run_id, "implement", root=self.state_root, workspace=self.workspace)
        self.assertEqual(run["current_node"], "implement")

        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        run = p4.advance(run_id, "verify", root=self.state_root, workspace=self.workspace)

        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        checkpoint_id = self._verified_checkpoint("sess-linear")
        run = p4.advance(
            run_id, "ship", checkpoint_id=checkpoint_id, root=self.state_root, workspace=self.workspace
        )

        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["current_node"], "ship")
        trace = p4.replay(run_id, root=self.state_root)
        node_sequence = [e["node"] for e in trace if e["event"] == "enter"]
        self.assertEqual(node_sequence, ["gather-context", "implement", "verify", "ship"])

    # 2. Evidence-driven branch ---------------------------------------------
    def test_evidence_driven_branch_routes_to_debug_then_ships(self) -> None:
        run = p4.start_run("evidence-branch", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]

        # The test step itself completed (verified), but the evidence it
        # produced says "tests failed" -> the caller branches to debug.
        p4.verify_node(run_id, passed=True, details="ran, 1 failure", root=self.state_root, workspace=self.workspace)
        run = p4.advance(run_id, "debug", root=self.state_root, workspace=self.workspace)
        self.assertEqual(run["current_node"], "debug")

        p4.verify_node(run_id, passed=True, details="fix applied", root=self.state_root, workspace=self.workspace)
        run = p4.advance(run_id, "run-tests", root=self.state_root, workspace=self.workspace)
        self.assertEqual(run["current_node"], "run-tests")

        p4.verify_node(run_id, passed=True, details="all green", root=self.state_root, workspace=self.workspace)
        checkpoint_id = self._verified_checkpoint("sess-branch")
        run = p4.advance(
            run_id, "ship", checkpoint_id=checkpoint_id, root=self.state_root, workspace=self.workspace
        )
        self.assertEqual(run["status"], "completed")
        # run-tests offers two options each time it's departed (ship/debug);
        # this run departs it twice (-> debug, then -> ship), so branch_depth
        # counts two independent branch decisions.
        self.assertEqual(run["metrics"]["branch_depth"], 2)

    # 3. Rejected unsupported branch -----------------------------------------
    def test_unsupported_branch_is_rejected_and_recorded(self) -> None:
        run = p4.start_run("evidence-branch", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]
        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)

        with self.assertRaises(p4.UnsupportedBranchError):
            p4.advance(run_id, "deploy-prod-directly", root=self.state_root, workspace=self.workspace)

        trace = p4.replay(run_id, root=self.state_root)
        rejections = [e for e in trace if e["event"] == "rejected-branch"]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]["attempted"], "deploy-prod-directly")
        self.assertEqual(sorted(rejections[0]["allowed_next"]), ["debug", "ship"])
        # A rejected branch must not have moved current_node.
        run = p4._load_run(self.state_root, run_id)  # noqa: SLF001 - internal reload for assertion
        self.assertEqual(run["current_node"], "run-tests")

    # 4. Interrupted resume ---------------------------------------------------
    def test_resume_rolls_back_to_last_verified_node_after_interruption(self) -> None:
        run = p4.start_run("linear-static", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]
        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        run = p4.advance(run_id, "implement", root=self.state_root, workspace=self.workspace)
        self.assertEqual(run["current_node"], "implement")

        # Simulate an interruption: "implement" was entered but never
        # verified, then a fresh process reloads the run from disk.
        resumed = p4.resume(run_id, root=self.state_root)
        self.assertEqual(resumed["current_node"], "gather-context")
        self.assertEqual(resumed["metrics"]["resumes_total"], 1)
        resume_events = [e for e in resumed["path_trace"] if e["event"] == "resume"]
        self.assertTrue(resume_events[-1]["was_interrupted"])

    # 5. Exhausted retry failure ----------------------------------------------
    def test_exhausted_retries_produce_explicit_terminal_failure(self) -> None:
        run = p4.start_run("evidence-branch", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]

        p4.verify_node(run_id, passed=False, details="attempt 1", root=self.state_root, workspace=self.workspace)
        p4.verify_node(run_id, passed=False, details="attempt 2", root=self.state_root, workspace=self.workspace)
        with self.assertRaises(p4.RetriesExhaustedError):
            p4.verify_node(run_id, passed=False, details="attempt 3", root=self.state_root, workspace=self.workspace)

        run = p4._load_run(self.state_root, run_id)  # noqa: SLF001 - internal reload for assertion
        self.assertEqual(run["status"], "failed-exhausted-retries")
        with self.assertRaises(p4.Phase4Error):
            p4.advance(run_id, "ship", root=self.state_root, workspace=self.workspace)

    # 6. High-risk checkpoint gate ---------------------------------------------
    def test_high_risk_transition_requires_a_real_verified_checkpoint(self) -> None:
        run = p4.start_run("linear-static", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]
        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        p4.advance(run_id, "implement", root=self.state_root, workspace=self.workspace)
        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)
        p4.advance(run_id, "verify", root=self.state_root, workspace=self.workspace)
        p4.verify_node(run_id, passed=True, root=self.state_root, workspace=self.workspace)

        # No checkpoint at all.
        with self.assertRaises(p4.CheckpointRequiredError):
            p4.advance(run_id, "ship", root=self.state_root, workspace=self.workspace)

        # Fabricated checkpoint id.
        with self.assertRaises(p4.CheckpointRequiredError):
            p4.advance(run_id, "ship", checkpoint_id="chk-does-not-exist", root=self.state_root, workspace=self.workspace)

        checkpoint_id = self._verified_checkpoint("sess-gate")
        run = p4.advance(
            run_id, "ship", checkpoint_id=checkpoint_id, root=self.state_root, workspace=self.workspace
        )
        self.assertEqual(run["status"], "completed")
        self.assertEqual(len(run["metrics"]["checkpoints_used"]), 1)
        self.assertEqual(run["metrics"]["checkpoints_used"][0]["checkpoint_id"], checkpoint_id)

    # Replayability sanity ------------------------------------------------------
    def test_list_and_status_reconstruct_from_disk_alone(self) -> None:
        run = p4.start_run("linear-static", root=self.state_root, workspace=self.workspace)
        run_id = run["run_id"]
        all_runs = p4.list_runs(root=self.state_root)
        self.assertEqual(len(all_runs), 1)
        self.assertEqual(all_runs[0]["run_id"], run_id)

        state = p4.status(run_id, root=self.state_root, workspace=self.workspace)
        self.assertEqual(state["run"]["run_id"], run_id)
        self.assertEqual(state["plan"]["allowed_next"], ["implement"])


class Phase4WorkflowDefValidationTests(unittest.TestCase):
    def test_unknown_workflow_raises(self) -> None:
        with self.assertRaises(p4.UnknownWorkflowError):
            p4.load_workflow_def("does-not-exist", workspace=ROOT)

    def test_shipped_definitions_are_structurally_valid(self) -> None:
        for name in ("linear-static", "evidence-branch"):
            definition = p4.load_workflow_def(name, workspace=ROOT)
            self.assertIn(definition["start"], definition["nodes"])


if __name__ == "__main__":
    unittest.main()

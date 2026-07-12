from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase5b_lifecycle as p5b  # noqa: E402


VALID_TASK = {
    "task_id": "t1",
    "description": "do the thing",
    "verification": {"target": "control-plane"},
    "commit_boundary": True,
}


class PlanSizingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_plan_within_cap_succeeds(self) -> None:
        record = p5b.create_plan(
            title="small plan",
            assumptions=["repo is clean"],
            tasks=[VALID_TASK],
            workspace=self.workspace,
        )
        self.assertEqual(record["status"], "draft")
        self.assertTrue((self.workspace / ".claude" / "plans" / f"{record['plan_id']}.json").exists())

    def test_plan_exceeding_three_tasks_rejected(self) -> None:
        tasks = [{**VALID_TASK, "task_id": f"t{i}"} for i in range(4)]
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(title="too big", assumptions=["x"], tasks=tasks, workspace=self.workspace)

    def test_plan_requires_explicit_assumptions(self) -> None:
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(title="no assumptions", assumptions=[], tasks=[VALID_TASK], workspace=self.workspace)

    def test_task_requires_verification_target(self) -> None:
        bad_task = {"task_id": "t1", "description": "x", "verification": {}, "commit_boundary": True}
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(title="no verify", assumptions=["x"], tasks=[bad_task], workspace=self.workspace)

    def test_task_requires_explicit_commit_boundary(self) -> None:
        bad_task = {"task_id": "t1", "description": "x", "verification": {"target": "control-plane"}}
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(title="no boundary", assumptions=["x"], tasks=[bad_task], workspace=self.workspace)

    def test_duplicate_task_id_rejected(self) -> None:
        tasks = [VALID_TASK, {**VALID_TASK}]
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(title="dup", assumptions=["x"], tasks=tasks, workspace=self.workspace)

    def test_blocking_edge_must_reference_existing_plan(self) -> None:
        with self.assertRaises(p5b.PlanValidationError):
            p5b.create_plan(
                title="bad edge",
                assumptions=["x"],
                tasks=[VALID_TASK],
                blocking_edges=["plan-does-not-exist"],
                workspace=self.workspace,
            )

    def test_blocking_edge_to_real_plan_succeeds(self) -> None:
        prerequisite = p5b.create_plan(
            title="prereq", assumptions=["x"], tasks=[VALID_TASK], workspace=self.workspace
        )
        dependent = p5b.create_plan(
            title="dependent",
            assumptions=["x"],
            tasks=[VALID_TASK],
            blocking_edges=[prerequisite["plan_id"]],
            workspace=self.workspace,
        )
        self.assertEqual(dependent["blocking_edges"], [prerequisite["plan_id"]])

    def test_plan_validate_roundtrips_from_disk(self) -> None:
        record = p5b.create_plan(title="x", assumptions=["x"], tasks=[VALID_TASK], workspace=self.workspace)
        revalidated = p5b.validate_plan(record["plan_id"], workspace=self.workspace)
        self.assertEqual(revalidated["plan_id"], record["plan_id"])

    def test_list_plans_sorted_most_recent_first(self) -> None:
        first = p5b.create_plan(title="a", assumptions=["x"], tasks=[VALID_TASK], workspace=self.workspace)
        second = p5b.create_plan(title="b", assumptions=["x"], tasks=[VALID_TASK], workspace=self.workspace)
        listed = p5b.list_plans(workspace=self.workspace)
        ids = [p["plan_id"] for p in listed]
        self.assertIn(first["plan_id"], ids)
        self.assertIn(second["plan_id"], ids)


class StatusReconstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.workspace = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_status_reflects_plans_on_disk(self) -> None:
        p5b.create_plan(title="a", assumptions=["x"], tasks=[VALID_TASK], workspace=self.workspace)
        status = p5b.reconstruct_status(root=self.state_root, workspace=self.workspace)
        self.assertEqual(status["source"], "disk-only")
        self.assertEqual(status["plans"]["total"], 1)
        self.assertEqual(status["plans"]["by_status"], {"draft": 1})

    def test_status_with_no_state_is_empty_but_well_formed(self) -> None:
        status = p5b.reconstruct_status(root=self.state_root, workspace=self.workspace)
        self.assertEqual(status["plans"]["total"], 0)
        self.assertEqual(status["ledger_tail"], [])
        self.assertIsNone(status["latest_checkpoint"])
        self.assertEqual(status["recent_handoffs"], [])

    def test_status_reflects_ledger_tail(self) -> None:
        ledger = self.state_root / "ledger.md"
        ledger.write_text("entry one\nentry two\n", encoding="utf-8")
        status = p5b.reconstruct_status(root=self.state_root, workspace=self.workspace)
        self.assertEqual(status["ledger_tail"], ["entry one", "entry two"])

    def test_status_reflects_running_experiment(self) -> None:
        p5b.start_experiment(metric="latency_ms", baseline_value=100, budget_minutes=10, root=self.state_root)
        status = p5b.reconstruct_status(root=self.state_root, workspace=self.workspace)
        self.assertEqual(len(status["experiments"]), 1)
        self.assertEqual(status["experiments"][0]["status"], "running")


class HandoffColdStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_handoff_requires_evidence_or_explicit_summary_only(self) -> None:
        with self.assertRaises(p5b.HandoffError):
            p5b.create_handoff(
                session_summary="did work", next_steps="do more", root=self.state_root
            )

    def test_handoff_summary_only_marks_unverified(self) -> None:
        result = p5b.create_handoff(
            session_summary="did work",
            next_steps="do more",
            summary_only=True,
            root=self.state_root,
        )
        self.assertFalse(result["verified"])
        text = Path(result["path"]).read_text(encoding="utf-8")
        self.assertIn("UNVERIFIED", text)

    def test_handoff_with_evidence_is_cold_start_complete(self) -> None:
        result = p5b.create_handoff(
            session_summary="did work",
            next_steps="do more",
            verification_evidence=[{"command": "python3 x.py", "exit_code": 0}],
            root=self.state_root,
        )
        self.assertTrue(result["verified"])
        text = Path(result["path"]).read_text(encoding="utf-8")
        for heading in (
            "## Session Context",
            "## Verified State",
            "## What's Next",
            "## Open Risks / Assumptions",
            "## Pointers",
        ):
            self.assertIn(heading, text)
        self.assertIn("python3 x.py", text)
        self.assertIn("| 0 |", text)

    def test_handoff_file_written_under_state_handoffs(self) -> None:
        result = p5b.create_handoff(
            session_summary="s", next_steps="n", summary_only=True, root=self.state_root
        )
        self.assertEqual(Path(result["path"]).parent, self.state_root / "handoffs")


class ExperimentKeepRevertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name) / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_higher_is_better_improvement_is_kept(self) -> None:
        exp = p5b.start_experiment(
            metric="throughput", baseline_value=100, budget_minutes=10,
            direction="higher_is_better", root=self.state_root,
        )
        p5b.record_observation(exp["experiment_id"], 150, root=self.state_root)
        decided = p5b.decide_experiment(exp["experiment_id"], root=self.state_root)
        self.assertEqual(decided["decision"]["outcome"], "keep")
        self.assertEqual(decided["status"], "kept")

    def test_higher_is_better_regression_is_reverted(self) -> None:
        exp = p5b.start_experiment(
            metric="throughput", baseline_value=100, budget_minutes=10,
            direction="higher_is_better", root=self.state_root,
        )
        p5b.record_observation(exp["experiment_id"], 80, root=self.state_root)
        decided = p5b.decide_experiment(exp["experiment_id"], root=self.state_root)
        self.assertEqual(decided["decision"]["outcome"], "revert")
        self.assertEqual(decided["status"], "reverted")

    def test_lower_is_better_improvement_is_kept(self) -> None:
        exp = p5b.start_experiment(
            metric="latency_ms", baseline_value=100, budget_minutes=10,
            direction="lower_is_better", root=self.state_root,
        )
        p5b.record_observation(exp["experiment_id"], 60, root=self.state_root)
        decided = p5b.decide_experiment(exp["experiment_id"], root=self.state_root)
        self.assertEqual(decided["decision"]["outcome"], "keep")

    def test_decide_without_observation_raises(self) -> None:
        exp = p5b.start_experiment(
            metric="m", baseline_value=1, budget_minutes=1, root=self.state_root
        )
        with self.assertRaises(p5b.ExperimentError):
            p5b.decide_experiment(exp["experiment_id"], root=self.state_root)

    def test_decide_is_not_re_decidable(self) -> None:
        exp = p5b.start_experiment(
            metric="m", baseline_value=1, budget_minutes=1, root=self.state_root
        )
        p5b.record_observation(exp["experiment_id"], 2, root=self.state_root)
        p5b.decide_experiment(exp["experiment_id"], root=self.state_root)
        with self.assertRaises(p5b.ExperimentError):
            p5b.decide_experiment(exp["experiment_id"], root=self.state_root)

    def test_invalid_direction_rejected(self) -> None:
        with self.assertRaises(p5b.ExperimentError):
            p5b.start_experiment(
                metric="m", baseline_value=1, budget_minutes=1, direction="sideways", root=self.state_root
            )

    def test_nonpositive_budget_rejected(self) -> None:
        with self.assertRaises(p5b.ExperimentError):
            p5b.start_experiment(metric="m", baseline_value=1, budget_minutes=0, root=self.state_root)


if __name__ == "__main__":
    unittest.main()

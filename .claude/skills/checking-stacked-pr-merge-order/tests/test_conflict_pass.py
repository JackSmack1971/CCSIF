#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "conflict_pass.py"
SPEC = importlib.util.spec_from_file_location("conflict_pass", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ConflictPassTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True)
        (self.repo / "shared.txt").write_text("root\n", encoding="utf-8")
        subprocess.run(["git", "add", "shared.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "root"], cwd=self.repo, check=True)
        self.root_oid = self.rev("HEAD")

        subprocess.run(["git", "switch", "-qc", "feature"], cwd=self.repo, check=True)
        (self.repo / "shared.txt").write_text("feature\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", "feature"], cwd=self.repo, check=True)
        self.feature_oid = self.rev("HEAD")

        subprocess.run(["git", "switch", "-q", "main"], cwd=self.repo, check=True)
        (self.repo / "shared.txt").write_text("main\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", "main"], cwd=self.repo, check=True)
        self.main_oid = self.rev("HEAD")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def rev(self, value: str) -> str:
        return subprocess.check_output(["git", "rev-parse", value], cwd=self.repo, text=True).strip()

    def analysis(self) -> dict:
        return {
            "schema_version": 1,
            "status": "ok",
            "repository": "owner/repo",
            "repository_url": "https://github.com/owner/repo",
            "remote": "origin",
            "generated_at": "2026-07-12T00:00:00Z",
            "fetch_performed": True,
            "selected_pr_numbers": [],
            "prs": [{
                "number": 1,
                "title": "feature",
                "url": "https://github.com/owner/repo/pull/1",
                "head_ref_name": "feature",
                "head_ref_oid": self.feature_oid,
                "base_ref_name": "main",
                "base_ref_oid": self.main_oid,
                "head_owner": "owner",
                "head_repository": "owner/repo",
                "is_cross_repository": False,
                "is_draft": False,
                "merge_state_status": "DIRTY",
                "mergeable": "CONFLICTING",
                "updated_at": "2026-07-12T00:00:00Z",
                "effective_head_oid": self.feature_oid,
                "effective_base_oid": self.main_oid,
                "head_resolved": True,
                "base_resolved": True,
            }],
            "dependencies": [],
            "components": [{"pr_numbers": [1], "waves": [[1]], "cycle_nodes": []}],
            "global_waves": [[1]],
            "independent_prs": [1],
            "warnings": [],
            "errors": [],
        }

    def test_simulate_merge_reports_conflict_and_cleans_worktree(self) -> None:
        result = MODULE.simulate_merge(self.repo, self.feature_oid, self.main_oid)
        self.assertEqual("conflicted", result["status"])
        self.assertEqual(["shared.txt"], [item["path"] for item in result["conflicts"]])
        worktrees = subprocess.check_output(["git", "worktree", "list", "--porcelain"], cwd=self.repo, text=True)
        self.assertEqual(1, worktrees.count("worktree "))

    def test_build_plan_marks_only_first_conflict_eligible(self) -> None:
        plan, exit_code = MODULE.build_plan(self.repo, self.analysis())
        self.assertEqual(MODULE.EXIT_CONFLICTS, exit_code)
        self.assertEqual("conflicts", plan["status"])
        self.assertTrue(plan["actions"][0]["eligible"])
        self.assertEqual(plan["plan_sha256"], MODULE.canonical_hash(plan, {"plan_sha256"}))

    def test_prepare_resolve_verify_commit_and_cleanup(self) -> None:
        plan, _ = MODULE.build_plan(self.repo, self.analysis())
        action = plan["actions"][0]
        live = {
            "state": "OPEN",
            "headRefName": "feature",
            "headRefOid": self.feature_oid,
            "baseRefName": "main",
            "baseRefOid": self.main_oid,
            "headRepositoryNameWithOwner": "owner/repo",
        }
        state_root = self.root / "operations"
        with patch.object(MODULE, "query_live_pr", return_value=live):
            state = MODULE.prepare_resolution(
                self.repo, plan, action, plan["plan_sha256"], state_root
            )
        worktree = Path(state["worktree_path"])
        self.assertTrue(worktree.is_dir())
        (worktree / "shared.txt").write_text("main and feature\n", encoding="utf-8")
        subprocess.run(["git", "add", "shared.txt"], cwd=worktree, check=True)

        record_path = Path(state["resolution_record_path"])
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["conflict_resolutions"][0]["diagnosis"] = "Both branches intentionally replaced the same root line."
        record["conflict_resolutions"][0]["resolution"] = "Preserve both intents in one combined line."
        record["validation_commands"] = [[sys.executable, "-c", "print('validated')"]]
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

        verified = MODULE.verify_and_commit(
            Path(state["state_path"]), record_path, "merge main into feature and resolve conflicts"
        )
        self.assertEqual("verified", verified["status"])
        new_oid = verified["resolution_commit_oid"]
        parents = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", new_oid], cwd=worktree, text=True
        ).strip().split()[1:]
        self.assertEqual([self.feature_oid, self.main_oid], parents)

        cleaned = MODULE.cleanup_resolution(
            self.repo, Path(state["state_path"]), force=True
        )
        self.assertTrue(cleaned["worktree_removed"])
        self.assertFalse(worktree.exists())


    def test_clean_simulation(self) -> None:
        subprocess.run(["git", "switch", "-qc", "clean-feature", self.root_oid], cwd=self.repo, check=True)
        (self.repo / "other.txt").write_text("independent\n", encoding="utf-8")
        subprocess.run(["git", "add", "other.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "independent change"], cwd=self.repo, check=True)
        clean_oid = self.rev("HEAD")
        result = MODULE.simulate_merge(self.repo, clean_oid, self.main_oid)
        self.assertEqual("clean", result["status"])
        self.assertEqual([], result["conflicts"])

    def test_plan_hash_rejects_tampering(self) -> None:
        plan, _ = MODULE.build_plan(self.repo, self.analysis())
        approval = plan["plan_sha256"]
        plan["actions"][0]["head_ref_name"] = "tampered"
        with self.assertRaises(MODULE.ConflictPassError):
            MODULE.validate_plan_hash(plan, approval)

    def test_construct_https_target(self) -> None:
        target = MODULE.construct_https_target(
            "https://git.example.test/base/project", "fork-owner/project"
        )
        self.assertEqual("https://git.example.test/fork-owner/project.git", target)

    def test_marker_detection(self) -> None:
        path = self.root / "markers.txt"
        path.write_text("before\n<<<<<<< HEAD\nours\n>>>>>>> base\n", encoding="utf-8")
        self.assertEqual([2, 4], MODULE.marker_findings(path))


if __name__ == "__main__":
    unittest.main()

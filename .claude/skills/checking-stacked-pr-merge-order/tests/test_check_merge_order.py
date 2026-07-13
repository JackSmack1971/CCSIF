#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_merge_order.py"
SPEC = importlib.util.spec_from_file_location("check_merge_order", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GraphTests(unittest.TestCase):
    def test_transitive_reduction_and_waves(self) -> None:
        deps = {}
        MODULE.add_dependency(deps, 1, 2, "ancestry")
        MODULE.add_dependency(deps, 2, 3, "ancestry")
        MODULE.add_dependency(deps, 1, 3, "ancestry")
        MODULE.mark_transitive_edges(deps)
        self.assertTrue(deps[(1, 2)].direct)
        self.assertTrue(deps[(2, 3)].direct)
        self.assertFalse(deps[(1, 3)].direct)
        waves, cycle = MODULE.topo_waves({1, 2, 3}, deps.values())
        self.assertEqual([[1], [2], [3]], waves)
        self.assertEqual([], cycle)

    def test_parallel_nodes_remain_same_wave(self) -> None:
        deps = {}
        waves, cycle = MODULE.topo_waves({7, 9}, deps.values())
        self.assertEqual([[7, 9]], waves)
        self.assertEqual([], cycle)

    def test_cycle_is_detected(self) -> None:
        deps = {}
        MODULE.add_dependency(deps, 1, 2, "base_target")
        MODULE.add_dependency(deps, 2, 1, "base_target")
        waves, cycle = MODULE.topo_waves({1, 2}, deps.values())
        self.assertEqual([], waves)
        self.assertEqual([1, 2], cycle)

    def test_explicit_base_edge_is_not_removed(self) -> None:
        deps = {}
        MODULE.add_dependency(deps, 1, 2, "base_target")
        MODULE.add_dependency(deps, 1, 2, "ancestry")
        MODULE.add_dependency(deps, 2, 3, "ancestry")
        MODULE.add_dependency(deps, 1, 3, "ancestry")
        MODULE.mark_transitive_edges(deps)
        self.assertTrue(deps[(1, 2)].direct)


class GitAncestryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        (self.repo / "file.txt").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "add", "file.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "A"], cwd=self.repo, check=True)
        self.a = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        (self.repo / "file.txt").write_text("a\nb\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", "B"], cwd=self.repo, check=True)
        self.b = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_is_ancestor(self) -> None:
        self.assertTrue(MODULE.is_ancestor(self.repo, self.a, self.b))
        self.assertFalse(MODULE.is_ancestor(self.repo, self.b, self.a))


if __name__ == "__main__":
    unittest.main()

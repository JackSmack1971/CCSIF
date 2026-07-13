from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase5c_portability_proof as proof  # noqa: E402


class PortabilityProofTests(unittest.TestCase):
    """Slow, real-subprocess proof: two unrelated fresh-clone fixtures,
    bootstrapped and driven through restart with a hostile HOME. Kept as
    one integration test (not per-assertion unit tests) because each
    workload spins up ~4 real subprocesses; splitting would just re-run
    the same expensive fixture repeatedly."""

    def test_both_workloads_bootstrap_restart_and_verify_with_no_home_dependency(self) -> None:
        result = proof.run_proof()
        self.assertTrue(result["both_passed"], result)
        self.assertTrue(result["only_facts_and_verify_targets_differ"], result)
        for workload in result["workloads"]:
            with self.subTest(workload=workload["workload"]):
                self.assertTrue(workload["passed"], workload)
                self.assertEqual(workload["bootstrap_run"]["exit_code"], 0)
                self.assertEqual(workload["validate_after_restart"]["exit_code"], 0)
                self.assertEqual(workload["smoke_after_restart"]["exit_code"], 0)
                self.assertEqual(workload["status_reconstruction"]["exit_code"], 0)
                self.assertEqual(workload["status_reconstruction"]["result"]["source"], "disk-only")
                self.assertFalse(workload["no_home_dependency_proof"]["hostile_home_exists"])


if __name__ == "__main__":
    unittest.main()

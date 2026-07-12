from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase5c_context_pressure as cp  # noqa: E402


class ContextPressureProxyTests(unittest.TestCase):
    def test_dispatcher_load_stays_within_roadmap_target(self) -> None:
        result = cp.measure()
        proxy = result["multi_plan_dispatcher_load_proxy"]
        self.assertTrue(proxy["within_target"], proxy)
        self.assertLess(proxy["dispatcher_load_as_pct_of_naive_inline"], 50.0)
        self.assertEqual(proxy["plan_count"], cp.PLAN_COUNT)

    def test_always_loaded_budget_is_measured_against_real_repo_files(self) -> None:
        result = cp.measure()
        budget = result["always_loaded_instruction_budget"]
        self.assertGreater(budget["measured_lines"], 0)
        self.assertLessEqual(budget["measured_lines"], budget["budget_lines"])


if __name__ == "__main__":
    unittest.main()

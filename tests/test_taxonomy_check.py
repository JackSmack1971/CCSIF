from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import taxonomy_check as tc  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TaxonomyCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_real_repo_passes_every_check(self) -> None:
        tc.run_all(ROOT)  # must not raise

    def test_command_cross_invocation_is_rejected(self) -> None:
        write(self.root / ".claude/commands/plan.md", "# /plan\n\nDoes planning.\n")
        write(self.root / ".claude/commands/ship.md", "# /ship\n\nRun /plan first, then ship.\n")
        with self.assertRaises(tc.TaxonomyError) as ctx:
            tc.check_no_command_cross_invocation(self.root)
        self.assertIn("invokes another", str(ctx.exception))

    def test_independent_commands_are_accepted(self) -> None:
        write(self.root / ".claude/commands/plan.md", "# /plan\n\nDoes planning.\n")
        write(self.root / ".claude/commands/ship.md", "# /ship\n\nShips the change.\n")
        tc.check_no_command_cross_invocation(self.root)  # must not raise

    def test_duplicate_skill_description_is_rejected(self) -> None:
        desc = "description: Use when doing the exact same thing twice.\n"
        write(self.root / ".claude/skills/alpha/SKILL.md", f"---\nname: alpha\n{desc}---\nbody\n")
        write(self.root / ".claude/skills/beta/SKILL.md", f"---\nname: beta\n{desc}---\nbody\n")
        with self.assertRaises(tc.TaxonomyError) as ctx:
            tc.check_no_duplicate_responsibility(self.root)
        self.assertIn("duplicate responsibility", str(ctx.exception))

    def test_distinct_skill_descriptions_are_accepted(self) -> None:
        write(
            self.root / ".claude/skills/alpha/SKILL.md",
            "---\nname: alpha\ndescription: Use for alpha work.\n---\nbody\n",
        )
        write(
            self.root / ".claude/skills/beta/SKILL.md",
            "---\nname: beta\ndescription: Use for beta work.\n---\nbody\n",
        )
        tc.check_no_duplicate_responsibility(self.root)  # must not raise

    def test_always_loaded_budget_is_enforced(self) -> None:
        write(self.root / "CLAUDE.md", "\n".join(f"line {i}" for i in range(10)))
        write(
            self.root / ".claude/rules/big.md",
            '---\npaths:\n  - "**/*"\n---\n# Big\n' + "\n".join(f"line {i}" for i in range(20)),
        )
        tc.check_always_loaded_context_budget(self.root, budget=100)  # under budget: fine
        with self.assertRaises(tc.TaxonomyError):
            tc.check_always_loaded_context_budget(self.root, budget=10)

    def test_path_scoped_rule_is_excluded_from_always_loaded_budget(self) -> None:
        write(self.root / "CLAUDE.md", "line\n")
        write(
            self.root / ".claude/rules/scoped.md",
            '---\npaths:\n  - "src/**"\n---\n# Scoped\n' + "\n".join(f"line {i}" for i in range(50)),
        )
        tc.check_always_loaded_context_budget(self.root, budget=5)  # scoped.md must not count

    def test_global_path_dependency_is_rejected(self) -> None:
        write(self.root / ".claude/hooks/session-start.sh", 'AUTO_MEMORY="~/.claude/memory"\n')
        with self.assertRaises(tc.TaxonomyError) as ctx:
            tc.check_no_global_path_dependency(self.root)
        self.assertIn("global-path dependency", str(ctx.exception))

    def test_documented_non_dependency_statement_is_accepted(self) -> None:
        write(
            self.root / ".claude/scripts/example.py",
            "# This script never depends on `~/.claude/*` for correctness.\n",
        )
        tc.check_no_global_path_dependency(self.root)  # must not raise

    def test_oversized_root_guidance_is_rejected(self) -> None:
        write(self.root / "CLAUDE.md", "\n".join(f"line {i}" for i in range(250)))
        with self.assertRaises(tc.TaxonomyError):
            tc.check_root_guidance_size(self.root, max_lines=200)

    def test_root_guidance_within_budget_is_accepted(self) -> None:
        write(self.root / "CLAUDE.md", "\n".join(f"line {i}" for i in range(50)))
        tc.check_root_guidance_size(self.root, max_lines=200)  # must not raise


if __name__ == "__main__":
    unittest.main()

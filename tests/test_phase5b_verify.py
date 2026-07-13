from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase5b_verify as pv  # noqa: E402


FAKE_CLAUDE_MD = """# Fake Project

## Source-of-Truth Commands

Update these commands to match the repository:

```bash
# control-plane
python3 -c "print('control-plane ok')"

# rules lint
python3 -c "print('rules ok')"

# unit tests
python3 -m unittest discover -s fixture_tests -v

# always fails
python3 -c "import sys; sys.exit(1)"
```

## Other Section
"""


class ParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.claude_md = Path(self.tmp.name) / "CLAUDE.md"
        self.claude_md.write_text(FAKE_CLAUDE_MD, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parses_labeled_commands(self) -> None:
        entries = pv.parse_source_of_truth(self.claude_md)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0]["label"], "control-plane")
        self.assertEqual(entries[0]["slug"], "control-plane")

    def test_missing_heading_raises(self) -> None:
        bad = Path(self.tmp.name) / "no_heading.md"
        bad.write_text("# Nothing here\n", encoding="utf-8")
        with self.assertRaises(pv.VerifyAdapterError):
            pv.parse_source_of_truth(bad)

    def test_list_targets_reports_all_groups(self) -> None:
        payload = pv.list_targets(claude_md=self.claude_md)
        self.assertEqual(payload["aggregate_targets"], ["full", "lint", "test"])
        self.assertIn("rules-lint", payload["individual_targets"])
        self.assertIn("rubric", payload["non_code_targets"])


class TargetResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.claude_md = Path(self.tmp.name) / "CLAUDE.md"
        self.claude_md.write_text(FAKE_CLAUDE_MD, encoding="utf-8")
        self.entries = pv.parse_source_of_truth(self.claude_md)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_lint_target_matches_lint_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "lint")
        self.assertEqual([e["slug"] for e in selected], ["rules-lint"])

    def test_test_target_matches_test_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "test")
        self.assertEqual([e["slug"] for e in selected], ["unit-tests"])

    def test_full_target_matches_every_entry(self) -> None:
        selected = pv.resolve_targets(self.entries, "full")
        self.assertEqual(len(selected), 4)

    def test_unknown_target_matches_nothing(self) -> None:
        selected = pv.resolve_targets(self.entries, "does-not-exist")
        self.assertEqual(selected, [])


class RunTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.claude_md = Path(self.tmp.name) / "CLAUDE.md"
        self.claude_md.write_text(FAKE_CLAUDE_MD, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_passing_target_exits_zero(self) -> None:
        result = pv.run_target("control-plane", claude_md=self.claude_md, cwd=ROOT)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "pass")

    def test_failure_propagates_nonzero_exit(self) -> None:
        result = pv.run_target("always-fails", claude_md=self.claude_md, cwd=ROOT)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["commands"][0]["exit_code"], 1)

    def test_full_target_fails_if_any_command_fails(self) -> None:
        result = pv.run_target("full", claude_md=self.claude_md, cwd=ROOT)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(len(result["commands"]), 4)

    def test_unavailable_target_returns_exit_code_two(self) -> None:
        result = pv.run_target("nonexistent", claude_md=self.claude_md, cwd=ROOT)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(result["status"], "unavailable")

    def test_non_code_verifier_returns_exit_code_two_with_guidance(self) -> None:
        for mode in ("rubric", "citation", "factcheck"):
            with self.subTest(mode=mode):
                result = pv.run_target(mode, claude_md=self.claude_md, cwd=ROOT)
                self.assertEqual(result["exit_code"], 2)
                self.assertTrue(result["message"])

    def test_missing_claude_md_is_unavailable_not_a_crash(self) -> None:
        missing = Path(self.tmp.name) / "does_not_exist.md"
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("full", claude_md=missing, cwd=ROOT)


class RealRepoIntegrationTests(unittest.TestCase):
    """Prove the adapter works against this repo's real CLAUDE.md, not just
    a synthetic fixture."""

    def test_real_claude_md_parses_and_control_plane_target_passes(self) -> None:
        result = pv.run_target("control-plane", cwd=ROOT)
        self.assertEqual(result["exit_code"], 0)

    @staticmethod
    def _bash_exe() -> str | None:
        # subprocess's PATH search for a plain "bash" can resolve to
        # Windows' WSL bash.exe instead of Git Bash, which then can't see
        # Windows-style paths. Prefer Git Bash explicitly; skip if absent
        # (e.g. a non-Windows CI runner where plain "bash" is correct).
        for candidate in (r"C:\Program Files\Git\usr\bin\bash.exe", r"C:\Program Files\Git\bin\bash.exe"):
            if Path(candidate).exists():
                return candidate
        return shutil.which("bash")

    def test_bash_hook_wrapper_delegates_to_adapter(self) -> None:
        bash = self._bash_exe()
        if not bash:
            self.skipTest("no bash executable available")
        proc = subprocess.run(
            [bash, str(ROOT / ".claude" / "hooks" / "verify.sh"), "run", "control-plane"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_bash_hook_wrapper_propagates_unavailable_exit_code(self) -> None:
        bash = self._bash_exe()
        if not bash:
            self.skipTest("no bash executable available")
        proc = subprocess.run(
            [bash, str(ROOT / ".claude" / "hooks" / "verify.sh"), "run", "rubric"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)


if __name__ == "__main__":
    unittest.main()

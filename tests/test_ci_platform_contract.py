from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CiPlatformContractTests(unittest.TestCase):
    def test_ci_runs_documented_authoritative_test_command_on_all_claimed_platforms(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        command = "python -m unittest discover -s tests -v"
        for text in (workflow, readme, contributing, claude):
            self.assertIn(command, text)
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
            self.assertIn(runner, workflow)
        for python_version in ("'3.11'", "'3.12'"):
            self.assertIn(python_version, workflow)
        for node_version in ("'20'", "'22'"):
            self.assertIn(node_version, workflow)

    def test_bash_verify_wrapper_resolves_from_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccsif path contract ") as tmp:
            target = Path(tmp) / "repo copy"
            hooks_dir = target / ".claude" / "hooks"
            scripts_dir = target / ".claude" / "scripts"
            hooks_dir.mkdir(parents=True)
            scripts_dir.mkdir(parents=True)
            (hooks_dir / "verify.sh").write_text((ROOT / ".claude" / "hooks" / "verify.sh").read_text(encoding="utf-8"), encoding="utf-8")
            sentinel = "import sys\nprint('adapter:' + sys.argv[1])\nsys.exit(0)\n"
            (scripts_dir / "phase5b_verify.py").write_text(sentinel, encoding="utf-8")

            proc = subprocess.run(
                ["bash", ".claude/hooks/verify.sh", "smoke"],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("adapter:smoke", proc.stdout)

    def test_session_start_wrapper_contains_backslash_normalization_for_git_bash_paths(self) -> None:
        script = (ROOT / ".claude" / "hooks" / "session-start.sh").read_text(encoding="utf-8")
        self.assertIn(r'${BASH_SOURCE[0]//\\//}', script)
        self.assertIn('cd -- "${script_dir:-.}"', script)

    @unittest.skipUnless(os.name == "nt", "PowerShell wrapper execution is covered by CI on windows-latest")
    def test_powershell_verify_wrapper_executes_on_windows(self) -> None:
        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / ".claude" / "hooks" / "verify.ps1"), "run", "rules"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()

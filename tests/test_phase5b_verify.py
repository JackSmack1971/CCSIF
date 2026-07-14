from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import phase5b_verify as pv  # noqa: E402


FAKE_MANIFEST = {
    "schema_version": 1,
    "targets": [
        {
            "id": "control-plane",
            "label": "control-plane",
            "command": ["python3", "-c", "print('control-plane ok')"],
        },
        {
            "id": "rules-lint",
            "label": "rules lint",
            "command": ["python3", "-c", "print('rules ok')"],
        },
        {
            "id": "unit-tests",
            "label": "unit tests",
            "command": ["python3", "-m", "unittest", "discover", "-s", "fixture_tests", "-v"],
        },
        {
            "id": "always-fails",
            "label": "always fails",
            "command": ["python3", "-c", "raise SystemExit(1)"],
        },
        {
            "id": "smoke",
            "label": "smoke",
            "command": ["python3", "-c", "print('smoke ok')"],
        },
    ],
}


def write_manifest(root: Path, manifest: dict) -> Path:
    manifest_path = root / ".claude" / "verification-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


class ParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = write_manifest(self.root, FAKE_MANIFEST)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parses_manifest_targets(self) -> None:
        entries = pv.parse_manifest(self.manifest)
        self.assertEqual(len(entries), 5)
        self.assertEqual(entries[0]["label"], "control-plane")
        self.assertEqual(entries[0]["slug"], "control-plane")

    def test_missing_manifest_raises(self) -> None:
        with self.assertRaises(pv.VerifyAdapterError):
            pv.parse_manifest(self.root / ".claude" / "missing.json")

    def test_list_targets_reports_all_groups(self) -> None:
        payload = pv.list_targets(manifest=self.manifest)
        self.assertEqual(payload["aggregate_targets"], ["full", "lint", "test"])
        self.assertIn("rules-lint", payload["individual_targets"])
        self.assertIn("rubric", payload["non_code_targets"])


class TargetResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = write_manifest(self.root, FAKE_MANIFEST)
        self.entries = pv.parse_manifest(self.manifest)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_lint_target_matches_lint_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "lint")
        self.assertEqual([entry["slug"] for entry in selected], ["rules-lint"])

    def test_test_target_matches_test_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "test")
        self.assertEqual([entry["slug"] for entry in selected], ["unit-tests"])

    def test_full_target_matches_every_entry(self) -> None:
        selected = pv.resolve_targets(self.entries, "full")
        self.assertEqual(len(selected), 5)

    def test_unknown_target_matches_nothing(self) -> None:
        selected = pv.resolve_targets(self.entries, "does-not-exist")
        self.assertEqual(selected, [])


class RunTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "fixture_tests").mkdir(parents=True)
        (self.root / "fixture_tests" / "test_ok.py").write_text(
            "import unittest\n\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        self.manifest = write_manifest(self.root, FAKE_MANIFEST)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_passing_target_exits_zero(self) -> None:
        result = pv.run_target("control-plane", manifest=self.manifest, cwd=self.root)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "pass")
        self.assertIsInstance(result["commands"][0]["command"], list)

    def test_failure_propagates_nonzero_exit(self) -> None:
        result = pv.run_target("always-fails", manifest=self.manifest, cwd=self.root)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["commands"][0]["exit_code"], 1)

    def test_full_target_fails_if_any_command_fails(self) -> None:
        result = pv.run_target("full", manifest=self.manifest, cwd=self.root)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(len(result["commands"]), 5)

    def test_unavailable_target_returns_exit_code_two(self) -> None:
        result = pv.run_target("nonexistent", manifest=self.manifest, cwd=self.root)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(result["status"], "unavailable")

    def test_non_code_verifier_returns_exit_code_two_with_guidance(self) -> None:
        for mode in ("rubric", "citation", "factcheck"):
            with self.subTest(mode=mode):
                result = pv.run_target(mode, manifest=self.manifest, cwd=self.root)
                self.assertEqual(result["exit_code"], 2)
                self.assertTrue(result["message"])

    def test_shell_metacharacters_are_rejected_before_subprocess(self) -> None:
        manifest = write_manifest(
            self.root,
            {
                "schema_version": 1,
                "targets": [
                    {
                        "id": "pwn",
                        "label": "pwn",
                        "command": ["python3", "-c", "print('safe'); touch pwned"],
                    }
                ],
            },
        )
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("pwn", manifest=manifest, cwd=self.root)

    def test_disallowed_executable_is_rejected(self) -> None:
        manifest = write_manifest(
            self.root,
            {
                "schema_version": 1,
                "targets": [
                    {"id": "perl", "label": "perl", "command": ["perl", "-e", "print 1"]},
                ],
            },
        )
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("perl", manifest=manifest, cwd=self.root)

    def test_path_escape_is_rejected(self) -> None:
        manifest = write_manifest(
            self.root,
            {
                "schema_version": 1,
                "targets": [
                    {
                        "id": "escape",
                        "label": "escape",
                        "command": ["python3", "../outside.py"],
                    }
                ],
            },
        )
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("escape", manifest=manifest, cwd=self.root)

    def test_missing_manifest_is_unavailable_not_a_crash(self) -> None:
        missing = self.root / "does_not_exist.json"
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("full", manifest=missing, cwd=self.root)

    def test_manifest_root_is_used_when_cwd_is_omitted(self) -> None:
        manifest_root = Path(self.tmp.name) / "manifest-root"
        manifest_root.mkdir()
        manifest = manifest_root / ".claude" / "verification-manifest.json"
        marker = manifest_root / "marker.txt"
        marker.write_text("manifest cwd ok\n", encoding="utf-8")
        check_script = manifest_root / "check.py"
        check_script.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "sys.exit(0 if Path('marker.txt').read_text(encoding='utf-8').strip() == 'manifest cwd ok' else 1)\n",
            encoding="utf-8",
        )
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "targets": [
                        {
                            "id": "manifest-root-check",
                            "label": "manifest root check",
                            "command": ["python3", "check.py"],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        result = pv.run_target("manifest-root-check", manifest=manifest)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "pass")


class RealRepoIntegrationTests(unittest.TestCase):
    """Prove the adapter works against this repo's real manifest."""

    def test_real_manifest_parses_and_control_plane_target_passes(self) -> None:
        result = pv.run_target("control-plane", cwd=ROOT)
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["manifest_digest"])

    @staticmethod
    def _bash_exe() -> str | None:
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

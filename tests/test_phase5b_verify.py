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


def make_manifest(tmp: Path, targets: list[dict] | None = None, **overrides) -> Path:
    """Write a <tmp>/.claude/verification.json manifest and return its path."""
    default_targets = [
        {"id": "control-plane", "label": "control-plane", "command": ["python3", "-c", "print('control-plane ok')"]},
        {"id": "rules-lint", "label": "rules lint", "command": ["python3", "-c", "print('rules ok')"]},
        {"id": "unit-tests", "label": "unit tests", "command": ["python3", "-m", "unittest", "discover", "-s", "fixture_tests", "-v"]},
        {"id": "always-fails", "label": "always fails", "command": ["python3", "-c", "raise SystemExit(1)"]},
    ]
    data = {"schema_version": 1, "targets": targets if targets is not None else default_targets}
    data.update(overrides)
    manifest = tmp / ".claude" / "verification.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return manifest


class ManifestLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = make_manifest(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_loads_valid_manifest(self) -> None:
        entries = pv.load_manifest(self.manifest)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0]["label"], "control-plane")
        self.assertEqual(entries[0]["slug"], "control-plane")
        self.assertEqual(entries[0]["argv"][0], "python3")

    def test_missing_manifest_raises(self) -> None:
        with self.assertRaises(pv.VerifyAdapterError):
            pv.load_manifest(self.root / "nope" / "verification.json")

    def test_list_targets_reports_all_groups(self) -> None:
        payload = pv.list_targets(manifest=self.manifest)
        self.assertEqual(payload["aggregate_targets"], ["full", "lint", "test"])
        self.assertIn("rules-lint", payload["individual_targets"])
        self.assertIn("rubric", payload["non_code_targets"])


class ManifestValidationTests(unittest.TestCase):
    """Every malformed-manifest case must fail closed (VerifyAdapterError ->
    exit 2), never a stack trace or partial execution."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _assert_rejected(self, **manifest_kwargs) -> None:
        manifest = make_manifest(self.root, **manifest_kwargs)
        with self.assertRaises(pv.VerifyAdapterError):
            pv.load_manifest(manifest)

    def test_missing_schema_version_rejected(self) -> None:
        manifest = make_manifest(self.root)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        del data["schema_version"]
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(pv.VerifyAdapterError):
            pv.load_manifest(manifest)

    def test_wrong_schema_version_rejected(self) -> None:
        self._assert_rejected(schema_version=99)

    def test_non_object_root_rejected(self) -> None:
        manifest = self.root / ".claude" / "verification.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
        with self.assertRaises(pv.VerifyAdapterError):
            pv.load_manifest(manifest)

    def test_invalid_json_rejected(self) -> None:
        manifest = self.root / ".claude" / "verification.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{truncated", encoding="utf-8")
        with self.assertRaises(pv.VerifyAdapterError):
            pv.load_manifest(manifest)

    def test_unknown_top_level_key_rejected(self) -> None:
        self._assert_rejected(shell="/bin/sh")

    def test_non_list_command_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": "python3 -c 'print(1)'"}])

    def test_non_string_argv_element_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": ["python3", 42]}])

    def test_empty_argv_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": []}])

    def test_duplicate_ids_rejected(self) -> None:
        target = {"id": "x", "label": "x", "command": ["python3", "-c", "print(1)"]}
        self._assert_rejected(targets=[target, dict(target)])

    def test_empty_targets_rejected(self) -> None:
        self._assert_rejected(targets=[])

    def test_disallowed_executable_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": ["curl", "https://evil.example"]}])

    def test_absolute_executable_outside_repo_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": ["/usr/bin/env", "python3"]}])

    def test_path_traversal_argument_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": ["python3", "../../outside/escape.py"]}])

    def test_absolute_path_argument_outside_repo_rejected(self) -> None:
        self._assert_rejected(targets=[{"id": "x", "label": "x", "command": ["python3", "/etc/passwd"]}])

    def test_malformed_manifest_returns_exit_code_two_via_cli(self) -> None:
        for targets in (
            [{"id": "x", "label": "x", "command": "not-a-list"}],
            [{"id": "x", "label": "x", "command": ["curl", "https://evil.example"]}],
            [{"id": "x", "label": "x", "command": ["python3", "../../escape.py"]}],
        ):
            with self.subTest(targets=targets):
                manifest = make_manifest(self.root, targets=targets)
                rc = pv.main(["run", "full", "--manifest", str(manifest)])
                self.assertEqual(rc, 2)


class AdversarialInjectionTests(unittest.TestCase):
    """A shell-metacharacter payload in a manifest entry must never execute."""

    PAYLOADS = [
        "; touch pwned",
        "&& touch pwned",
        "|| touch pwned",
        "| touch pwned",
        "`touch pwned`",
        "$(touch pwned)",
        "> pwned",
    ]

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_injected_payload_is_rejected_before_any_subprocess(self) -> None:
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                manifest = make_manifest(
                    self.root,
                    targets=[{"id": "evil", "label": "evil", "command": ["python3", "-c", f"print('x'){payload}"]}],
                )
                with self.assertRaises(pv.VerifyAdapterError):
                    pv.load_manifest(manifest)
                rc = pv.main(["run", "evil", "--manifest", str(manifest)])
                self.assertEqual(rc, 2)
                self.assertFalse((self.root / "pwned").exists(), f"side effect created by {payload!r}")

    def test_no_shell_true_anywhere_in_adapter_or_bootstrap(self) -> None:
        for rel in (".claude/scripts/phase5b_verify.py", ".claude/scripts/bootstrap_control_plane.py"):
            with self.subTest(path=rel):
                self.assertNotIn("shell=True", (ROOT / rel).read_text(encoding="utf-8"))


class TargetResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.entries = pv.load_manifest(make_manifest(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_lint_target_matches_lint_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "lint")
        self.assertEqual([e["slug"] for e in selected], ["rules-lint"])

    def test_test_target_matches_test_labeled_entry_only(self) -> None:
        selected = pv.resolve_targets(self.entries, "test")
        self.assertEqual([e["slug"] for e in selected], ["unit-tests"])

    def test_full_target_matches_every_entry(self) -> None:
        self.assertEqual(len(pv.resolve_targets(self.entries, "full")), 4)

    def test_unknown_target_matches_nothing(self) -> None:
        self.assertEqual(pv.resolve_targets(self.entries, "does-not-exist"), [])


class RunTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = make_manifest(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_passing_target_exits_zero(self) -> None:
        result = pv.run_target("control-plane", manifest=self.manifest, cwd=ROOT)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "pass")

    def test_failure_propagates_nonzero_exit(self) -> None:
        result = pv.run_target("always-fails", manifest=self.manifest, cwd=ROOT)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["commands"][0]["exit_code"], 1)

    def test_full_target_fails_if_any_command_fails(self) -> None:
        result = pv.run_target("full", manifest=self.manifest, cwd=ROOT)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(len(result["commands"]), 4)

    def test_unavailable_target_returns_exit_code_two(self) -> None:
        result = pv.run_target("nonexistent", manifest=self.manifest, cwd=ROOT)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(result["status"], "unavailable")

    def test_non_code_verifier_returns_exit_code_two_with_guidance(self) -> None:
        for mode in ("rubric", "citation", "factcheck"):
            with self.subTest(mode=mode):
                result = pv.run_target(mode, manifest=self.manifest, cwd=ROOT)
                self.assertEqual(result["exit_code"], 2)
                self.assertTrue(result["message"])

    def test_missing_manifest_raises_adapter_error(self) -> None:
        missing = self.root / "elsewhere" / ".claude" / "verification.json"
        with self.assertRaises(pv.VerifyAdapterError):
            pv.run_target("full", manifest=missing, cwd=ROOT)

    def test_manifest_root_is_used_when_cwd_is_omitted(self) -> None:
        marker = self.root / "marker.txt"
        marker.write_text("manifest cwd ok\n", encoding="utf-8")
        manifest = make_manifest(
            self.root,
            targets=[
                {
                    "id": "manifest-root-check",
                    "label": "manifest-root check",
                    "command": [
                        "python3",
                        "-c",
                        "raise SystemExit(0 if __import__('pathlib').Path('marker.txt').read_text(encoding='utf-8').strip() == 'manifest cwd ok' else 1)",
                    ],
                }
            ],
        )
        result = pv.run_target("manifest-root-check", manifest=manifest)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "pass")

    def test_run_reports_manifest_change_signal(self) -> None:
        result = pv.run_target("control-plane", manifest=self.manifest, cwd=ROOT)
        # First run against a never-verified manifest surfaces the signal.
        self.assertTrue(result["manifest_changed"])
        self.assertTrue(result["manifest_sha256"])
        # A passing run records the hash; an identical re-run is trusted.
        result2 = pv.run_target("control-plane", manifest=self.manifest, cwd=ROOT)
        self.assertFalse(result2["manifest_changed"])
        # Editing the manifest re-raises the signal.
        make_manifest(self.root, description="edited")
        result3 = pv.run_target("control-plane", manifest=self.manifest, cwd=ROOT)
        self.assertTrue(result3["manifest_changed"])

    def test_pattern_appends_unittest_filter(self) -> None:
        argv = pv._augment_argv(
            ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"], pattern="foo"
        )
        self.assertEqual(argv[-2:], ["-k", "foo"])
        untouched = pv._augment_argv(["python3", "-c", "print(1)"], pattern="foo")
        self.assertNotIn("-k", untouched)


class RealRepoIntegrationTests(unittest.TestCase):
    """Prove the adapter works against this repo's real manifest, not just a
    synthetic fixture."""

    def test_real_manifest_loads_and_rules_target_passes(self) -> None:
        result = pv.run_target("rules", cwd=ROOT)
        self.assertEqual(result["exit_code"], 0)

    def test_real_manifest_lists_expected_targets(self) -> None:
        payload = pv.list_targets()
        for slug in ("control-plane", "rules", "memory-tests", "issue-to-pr-tests"):
            self.assertIn(slug, payload["individual_targets"])

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
            [bash, str(ROOT / ".claude" / "hooks" / "verify.sh"), "run", "rules"],
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

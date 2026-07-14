from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import bootstrap_control_plane as bcp  # noqa: E402


class IdempotenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_first_run_creates_full_tree(self) -> None:
        tree = bcp.scaffold_tree(self.target)
        self.assertGreater(len(tree["created"]), 20)
        self.assertEqual(tree["preserved"], [])
        for rel in (
            ".claude/rules/00-operating-doctrine.md",
            ".claude/rules/20-lifecycle-gates.md",
            ".claude/rules/30-skill-taxonomy.md",
            ".claude/scripts/verify_adapter.py",
            ".claude/scripts/lifecycle.py",
            ".claude/hooks/verify.sh",
            ".claude/hooks/verify.ps1",
            ".claude/commands/plan.md",
            ".claude/commands/build.md",
            ".claude/commands/verify.md",
            ".claude/skills/alignment-interview/SKILL.md",
            "docs/CONTEXT.md",
            "docs/adr/0000-template.md",
        ):
            self.assertTrue((self.target / rel).exists(), rel)

    def test_second_run_creates_nothing_new(self) -> None:
        bcp.scaffold_tree(self.target)
        tree2 = bcp.scaffold_tree(self.target)
        self.assertEqual(tree2["created"], [])
        self.assertGreater(len(tree2["preserved"]), 20)

    def test_full_run_command_is_idempotent_end_to_end(self) -> None:
        facts = bcp.Facts(test_command="python -m pytest -q")
        bcp.scaffold_tree(self.target)
        r1 = bcp.merge_claude_md(self.target, facts)
        r1_settings = bcp.bootstrap_settings_json(self.target)
        r1_local = bcp.bootstrap_local_settings(self.target)
        r1_gitignore = bcp.update_gitignore(self.target)

        r2 = bcp.merge_claude_md(self.target, facts)
        r2_settings = bcp.bootstrap_settings_json(self.target)
        r2_local = bcp.bootstrap_local_settings(self.target)
        r2_gitignore = bcp.update_gitignore(self.target)

        self.assertEqual(r1, "created")
        self.assertEqual(r2, "preserved")
        self.assertEqual(r1_settings, "created")
        self.assertEqual(r2_settings, "preserved")
        self.assertEqual(r1_local["status"], "created")
        self.assertEqual(r2_local["status"], "unchanged")
        self.assertIn(".claude/settings.local.json", r1_gitignore)
        self.assertIn("CLAUDE.local.md", r1_gitignore)
        self.assertEqual(r2_gitignore, [])


class MigrationPreservesCustomizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_preexisting_rule_file_is_never_overwritten(self) -> None:
        rule_path = self.target / ".claude" / "rules" / "00-operating-doctrine.md"
        rule_path.parent.mkdir(parents=True)
        custom_content = "# Custom Doctrine\n\nProject-specific override.\n"
        rule_path.write_text(custom_content, encoding="utf-8")

        tree = bcp.scaffold_tree(self.target)

        self.assertEqual(rule_path.read_text(encoding="utf-8"), custom_content)
        self.assertIn(str(rule_path), tree["preserved"])
        self.assertNotIn(str(rule_path), tree["created"])

    def test_preexisting_claude_md_source_of_truth_block_is_never_overwritten(self) -> None:
        claude_md = self.target / "CLAUDE.md"
        custom = "# Project\n\n## Source-of-Truth Commands\n\n```bash\n# test\nmake test\n```\n"
        claude_md.write_text(custom, encoding="utf-8")

        result = bcp.merge_claude_md(self.target, bcp.Facts(test_command="npm test"))

        self.assertEqual(result, "preserved")
        self.assertEqual(claude_md.read_text(encoding="utf-8"), custom)

    def test_preexisting_settings_local_json_extra_keys_are_untouched(self) -> None:
        settings_path = self.target / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps({"version": 1, "env": {"FOO": "bar"}}),
            encoding="utf-8",
        )

        result = bcp.bootstrap_local_settings(self.target)

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(data["env"], {"FOO": "bar"})
        self.assertIn("autoMemoryDirectory", data)
        self.assertEqual(result["status"], "updated")

    def test_unreadable_settings_local_json_refuses_to_overwrite(self) -> None:
        settings_path = self.target / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text("not valid json {{{", encoding="utf-8")

        with self.assertRaises(RuntimeError):
            bcp.bootstrap_local_settings(self.target)
        # File must be left exactly as-is, not truncated or replaced.
        self.assertEqual(settings_path.read_text(encoding="utf-8"), "not valid json {{{")


class PathHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_auto_memory_directory_is_absolute(self) -> None:
        result = bcp.bootstrap_local_settings(self.target)
        data = json.loads((self.target / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(data["autoMemoryDirectory"]).is_absolute())

    def test_gitignore_append_uses_native_newlines_and_no_duplicates(self) -> None:
        bcp.update_gitignore(self.target)
        first_pass = (self.target / ".gitignore").read_text(encoding="utf-8")
        added_second = bcp.update_gitignore(self.target)
        second_pass = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(added_second, [])
        self.assertEqual(first_pass, second_pass)


class RollbackSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_interrupted_scaffold_can_be_resumed_by_rerunning(self) -> None:
        # Simulate an interrupted first run: only part of the tree exists.
        partial_rule = self.target / ".claude" / "rules" / "00-operating-doctrine.md"
        partial_rule.parent.mkdir(parents=True)
        partial_rule.write_text(bcp.OPERATING_DOCTRINE, encoding="utf-8")

        # Re-running completes the rest without touching the already-written file.
        tree = bcp.scaffold_tree(self.target)
        self.assertIn(str(partial_rule), tree["preserved"])
        self.assertGreater(len(tree["created"]), 15)
        # No file is ever deleted or truncated by a re-run.
        self.assertEqual(partial_rule.read_text(encoding="utf-8"), bcp.OPERATING_DOCTRINE)

    def test_dry_run_writes_nothing(self) -> None:
        plan = bcp.scaffold_tree(self.target, dry_run=True)
        self.assertGreater(len(plan["would_create"]), 0)
        self.assertFalse((self.target / ".claude").exists())


class ValidateAndSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        bcp.scaffold_tree(self.target)
        bcp.merge_claude_md(self.target, bcp.Facts())
        bcp.add_smoke_target_to_claude_md(self.target)
        bcp.merge_verification_manifest(self.target, bcp.Facts())
        bcp.bootstrap_settings_json(self.target)
        bcp.bootstrap_local_settings(self.target)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_validate_passes_after_full_bootstrap(self) -> None:
        result = bcp.validate(self.target)
        self.assertEqual(result["status"], "pass")

    def test_validate_fails_on_missing_required_path(self) -> None:
        (self.target / ".claude" / "scripts" / "verify_adapter.py").unlink()
        with self.assertRaises(SystemExit):
            sys.path.insert(0, str(self.target / ".claude" / "scripts"))
            for mod in ("control_plane_check",):
                sys.modules.pop(mod, None)
            import control_plane_check  # noqa

            control_plane_check.check_required_paths(self.target)

    def test_smoke_runs_all_five_gates_and_passes(self) -> None:
        result = bcp.run_smoke(self.target)
        self.assertTrue(result["align"]["exists"])
        self.assertTrue(result["research"]["exists"])
        self.assertTrue(result["plan"]["plan_id"])
        self.assertTrue(result["build"]["exists"])
        self.assertEqual(result["verify"]["exit_code"], 0)
        self.assertTrue(result["all_artifacts_present"])

    def test_smoke_status_reconstruction_is_disk_only(self) -> None:
        result = bcp.run_smoke(self.target)
        self.assertEqual(result["status_reconstruction"]["source"], "disk-only")
        self.assertEqual(result["status_reconstruction"]["plans"]["total"], 1)


class StackDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_detects_npm_stack(self) -> None:
        (self.target / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest", "lint": "eslint .", "build": "tsc"}}),
            encoding="utf-8",
        )
        facts = bcp.detect_stack(self.target)
        self.assertEqual(facts.test_command, "npm test")
        self.assertEqual(facts.lint_command, "npm run lint")
        self.assertEqual(facts.build_command, "npm run build")

    def test_detects_python_stack(self) -> None:
        (self.target / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (self.target / "tests").mkdir()
        facts = bcp.detect_stack(self.target)
        self.assertEqual(facts.test_command, "python -m pytest -q")

    def test_docs_only_repo_gets_no_fabricated_shell_command(self) -> None:
        (self.target / "README.md").write_text("# Docs\n", encoding="utf-8")
        facts = bcp.detect_stack(self.target)
        self.assertIsNone(facts.test_command)
        self.assertIsNone(facts.lint_command)


class SafeVerifyTemplateTests(unittest.TestCase):
    """Hardening 01/13 (#149): the scaffolded verify adapter must execute
    argv arrays with shell=False from a validated manifest, and must reject
    shell-metacharacter payloads the same way the parent repo's adapter
    does."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        bcp.scaffold_tree(self.target)
        bcp.merge_claude_md(self.target, bcp.Facts())
        bcp.merge_verification_manifest(self.target, bcp.Facts())

    def tearDown(self) -> None:
        self.tmp.cleanup()
        for mod in ("verify_adapter",):
            sys.modules.pop(mod, None)

    def _import_scaffolded_adapter(self):
        sys.path.insert(0, str(self.target / ".claude" / "scripts"))
        sys.modules.pop("verify_adapter", None)
        import verify_adapter  # noqa: E402

        return verify_adapter

    def test_scaffolded_adapter_contains_no_shell_true(self) -> None:
        text = (self.target / ".claude" / "scripts" / "verify_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", text)
        self.assertIn("shell=False", text)

    def test_scaffolded_manifest_is_valid_and_smoke_target_passes(self) -> None:
        adapter = self._import_scaffolded_adapter()
        manifest = self.target / ".claude" / "verification.json"
        entries = adapter.load_manifest(manifest)
        self.assertIn("smoke", [e["slug"] for e in entries])
        result = adapter.run_target("smoke", manifest=manifest, cwd=self.target)
        self.assertEqual(result["exit_code"], 0)

    def test_scaffolded_adapter_rejects_adversarial_payload(self) -> None:
        adapter = self._import_scaffolded_adapter()
        manifest = self.target / ".claude" / "verification.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["targets"] = [{"id": "evil", "label": "evil", "command": ["python3", "-c", "print('x'); touch pwned"]}]
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(adapter.VerifyAdapterError):
            adapter.load_manifest(manifest)
        self.assertFalse((self.target / "pwned").exists())

    def test_detected_npm_stack_produces_argv_manifest(self) -> None:
        npm_target = Path(self.tmp.name) / "npm-repo"
        npm_target.mkdir()
        (npm_target / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest", "lint": "eslint ."}}), encoding="utf-8"
        )
        facts = bcp.detect_stack(npm_target)
        bcp.merge_verification_manifest(npm_target, facts)
        data = json.loads((npm_target / ".claude" / "verification.json").read_text(encoding="utf-8"))
        by_id = {t["id"]: t["command"] for t in data["targets"]}
        self.assertEqual(by_id["test"], ["npm", "test"])
        self.assertEqual(by_id["lint"], ["npm", "run", "lint"])

    def test_manifest_merge_is_idempotent_and_preserving(self) -> None:
        manifest = self.target / ".claude" / "verification.json"
        before = manifest.read_text(encoding="utf-8")
        self.assertEqual(bcp.merge_verification_manifest(self.target, bcp.Facts(test_command="npm test")), "preserved")
        self.assertEqual(manifest.read_text(encoding="utf-8"), before)

class RuntimeManifestDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_single_language_python_repo_selects_python_guidance(self) -> None:
        (self.target / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (self.target / "tests").mkdir()
        facts = bcp.detect_stack(self.target)
        self.assertEqual(facts.runtimes, ["python"])
        self.assertIn("pyproject.toml", facts.manifests)
        self.assertIn("python --version", facts.prerequisite_checks)
        self.assertEqual(facts.test_command, "python -m pytest -q")
        self.assertTrue(any("Python" in item for item in facts.verification_guidance))

    def test_polyglot_repo_accumulates_runtime_prerequisites(self) -> None:
        (self.target / "package.json").write_text(json.dumps({"scripts": {"test": "jest", "build": "tsc"}}), encoding="utf-8")
        (self.target / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (self.target / "tests").mkdir()
        (self.target / "tool.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        workflow = self.target / ".github" / "workflows" / "ci.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: ci\n", encoding="utf-8")
        (self.target / ".claude").mkdir()
        (self.target / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        facts = bcp.detect_stack(self.target)
        for runtime in ("python", "node", "shell", "ci-workflows", "claude-control-plane"):
            self.assertIn(runtime, facts.runtimes)
        for prereq in ("python --version", "node --version", "bash --version", "python .claude/scripts/control_plane_check.py"):
            self.assertIn(prereq, facts.prerequisite_checks)
        self.assertIn(".github/workflows/*", facts.manifests)

    def test_missing_manifests_get_non_shell_guidance(self) -> None:
        facts = bcp.detect_stack(self.target)
        self.assertEqual(facts.runtimes, [])
        self.assertEqual(facts.manifests, [])
        self.assertIsNone(facts.test_command)
        self.assertTrue(any("No runtime manifest" in item for item in facts.verification_guidance))

    def test_older_control_plane_marker_is_migrated_additively(self) -> None:
        marker = self.target / ".claude" / "control-plane.json"
        marker.parent.mkdir(parents=True)
        marker.write_text(json.dumps({"schema_version": 1, "control_plane_version": 1, "custom": "keep"}), encoding="utf-8")
        result = bcp.bootstrap_control_plane_marker(self.target)
        data = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(result, "upgraded")
        self.assertEqual(data["control_plane_version"], bcp.CONTROL_PLANE_VERSION)
        self.assertEqual(data["previous_control_plane_version"], 1)
        self.assertEqual(data["custom"], "keep")
        self.assertIn("upgrade_path", data)


if __name__ == "__main__":
    unittest.main()

"""Regression coverage for Hardening 02/13 (#150): `.claude/settings.json`
`permissions.*` schema validity and the corrected/added native permission
rules.

Scope note: these tests are reference-implementation fixtures against the
documented Claude Code permission-rule syntax (see
`.claude/docs/claude-code-docs-2026-07-12-00-15-46/docs/
code-claude-com-docs-en-settings-545f9c5a.md`). They do not invoke Claude
Code's own native permission resolver, which requires a live, authenticated
`claude` session and is not reachable from this offline/deterministic
unittest suite. `pre-tool-use-guard.js` regression coverage (a separate,
already-native-adjacent layer) is exercised by `test_phase6a_guardrails.py`.
"""
from __future__ import annotations

import fnmatch
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import control_plane_check as cpc  # noqa: E402

SETTINGS_PATH = ROOT / ".claude" / "settings.json"


def load_settings() -> dict:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def bash_rule_matches(specifier: str, command: str) -> bool:
    """Reference matcher for the documented Bash(...) rule syntax: a
    literal command-string match, or a literal prefix followed by a
    trailing space + * glob token (Bash(npm run *), Bash(git diff *)
    per the settings doc examples)."""
    if specifier == command:
        return True
    if specifier.endswith(" *"):
        prefix = specifier[: -len(" *")]
        return command == prefix or command.startswith(prefix + " ")
    return False


def path_rule_matches(specifier: str, target: str) -> bool:
    """Reference matcher for the documented Read(...)/Edit(...)/
    Write(...) glob path syntax (./secrets/**, **/*.pem, ./.env.*
    per the same doc page). A leading "**/" is treated as matching zero
    or more directories (common minimatch-style semantics), so
    "**/foo" also matches a top-level "foo", not only a nested one."""
    normalized_target = target.replace("\\", "/")
    if normalized_target.startswith("./"):
        normalized_target = normalized_target[2:]
    pattern = specifier.replace("\\", "/")
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if fnmatch.fnmatch(normalized_target, pattern):
        return True
    if pattern.startswith("**/") and fnmatch.fnmatch(normalized_target, pattern[3:]):
        return True
    return False


def extract(tool: str, entries):
    prefix, suffix = f"{tool}(", ")"
    return [e[len(prefix):-len(suffix)] for e in entries if e.startswith(prefix) and e.endswith(suffix)]


class SettingsPermissionsSchemaTests(unittest.TestCase):
    def test_no_unrecognized_permissions_keys(self):
        permissions = load_settings()["permissions"]
        unknown = set(permissions) - cpc.PERMISSIONS_ALLOWED_KEYS
        self.assertEqual(unknown, set())

    def test_permissions_mode_key_is_gone(self):
        self.assertNotIn("mode", load_settings()["permissions"])

    def test_default_mode_is_documented_manual_value(self):
        self.assertEqual(load_settings()["permissions"]["defaultMode"], "default")

    def test_bypass_permissions_mode_is_disabled(self):
        self.assertEqual(
            load_settings()["permissions"]["disableBypassPermissionsMode"], "disable"
        )

    def test_control_plane_check_rejects_unknown_permissions_key(self):
        original = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        original.setdefault("permissions", {})["mode"] = "ask"
        backup = SETTINGS_PATH.read_text(encoding="utf-8")
        try:
            SETTINGS_PATH.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(SystemExit):
                cpc.check_settings_permissions_schema()
        finally:
            SETTINGS_PATH.write_text(backup, encoding="utf-8")


class BashAllowRuleFixtureTests(unittest.TestCase):
    def setUp(self):
        self.allow = extract("Bash", load_settings()["permissions"]["allow"])

    def test_git_status_bare_is_allowed(self):
        self.assertTrue(any(bash_rule_matches(s, "git status") for s in self.allow))

    def test_git_status_short_is_allowed(self):
        self.assertTrue(any(bash_rule_matches(s, "git status --short") for s in self.allow))

    def test_git_diff_bare_is_allowed(self):
        self.assertTrue(any(bash_rule_matches(s, "git diff") for s in self.allow))

    def test_git_diff_stat_is_allowed(self):
        self.assertTrue(any(bash_rule_matches(s, "git diff --stat") for s in self.allow))

    def test_git_log_oneline_is_allowed(self):
        self.assertTrue(any(bash_rule_matches(s, "git log --oneline -20") for s in self.allow))

    def test_control_plane_check_command_is_allowed(self):
        self.assertTrue(
            any(
                bash_rule_matches(s, "python3 .claude/scripts/control_plane_check.py")
                for s in self.allow
            )
        )

    def test_old_colon_glob_form_would_not_have_matched(self):
        self.assertFalse(bash_rule_matches("git status:*", "git status --short"))
        self.assertFalse(bash_rule_matches("git status:*", "git status"))


class NativeDenyRuleFixtureTests(unittest.TestCase):
    def setUp(self):
        deny = load_settings()["permissions"]["deny"]
        self.read_deny = extract("Read", deny)
        self.edit_deny = extract("Edit", deny)
        self.write_deny = extract("Write", deny)

    def test_dotenv_read_is_denied(self):
        self.assertTrue(any(path_rule_matches(s, ".env") for s in self.read_deny))

    def test_pem_read_is_denied(self):
        self.assertTrue(any(path_rule_matches(s, "keys/server.pem") for s in self.read_deny))

    def test_credentials_write_is_denied(self):
        self.assertTrue(
            any(path_rule_matches(s, "config/credentials.json") for s in self.write_deny)
        )

    def test_github_workflow_edit_is_denied(self):
        self.assertTrue(
            any(path_rule_matches(s, ".github/workflows/release.yml") for s in self.edit_deny)
        )

    def test_migration_write_is_denied(self):
        self.assertTrue(
            any(path_rule_matches(s, "migrations/001_init.sql") for s in self.write_deny)
        )

    def test_ledger_edit_is_denied(self):
        self.assertTrue(
            any(path_rule_matches(s, ".claude/state/ledger.md") for s in self.edit_deny)
        )

    def test_ledger_write_is_denied(self):
        self.assertTrue(
            any(path_rule_matches(s, ".claude/state/ledger.md") for s in self.write_deny)
        )


class NativeLockfileAskRuleFixtureTests(unittest.TestCase):
    def setUp(self):
        ask = load_settings()["permissions"]["ask"]
        self.edit_ask = extract("Edit", ask)
        self.write_ask = extract("Write", ask)

    def test_package_lock_edit_is_ask(self):
        self.assertTrue(any(path_rule_matches(s, "package-lock.json") for s in self.edit_ask))

    def test_yarn_lock_write_is_ask(self):
        self.assertTrue(any(path_rule_matches(s, "yarn.lock") for s in self.write_ask))


if __name__ == "__main__":
    unittest.main()

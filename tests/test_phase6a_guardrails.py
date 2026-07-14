from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import control_plane_check as cpc  # noqa: E402

GUARD = ROOT / ".claude" / "hooks" / "lib" / "pre-tool-use-guard.js"


def invoke(probe: dict) -> "cpc.subprocess.CompletedProcess[str]":
    node = cpc.resolve_node()
    guard_arg = cpc.node_script_arg(node, GUARD)
    return cpc.run([node, guard_arg], input_text=json.dumps(probe))


def decision_of(proc) -> str:
    if proc.returncode == 2:
        return "block"
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return "allow"
        decision = payload.get("hookSpecificOutput", {}).get("permissionDecision")
        if decision:
            return decision
    return "allow"


class GitGuardrailTests(unittest.TestCase):
    """Force push, hard reset, clean, branch deletion, history rewrites."""

    def test_force_push_long_flag(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_force_push_short_flag(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push -f origin main"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_force_push_with_lease(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push --force-with-lease origin main"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_force_push_compound_command(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "npm test && git push -f origin main"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_force_push_env_prefixed(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "GIT_TRACE=1 git push --force origin main"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_remote_ref_delete(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push origin :feature/x"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_reset_hard(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~3"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_clean_force_dirs(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git clean -fdx"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_branch_force_delete(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git branch -D old-feature"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_tag_delete(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git tag -d v1.0.0"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_history_rewrite_filter_branch(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git filter-branch --force --tree-filter 'rm secret'"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_history_rewrite_filter_repo(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git filter-repo --invert-paths --path secret.txt"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_history_rewrite_rebase(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git rebase -i HEAD~5"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_rebase_abort_is_allowed(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git rebase --abort"}})
        self.assertEqual(decision_of(proc), "allow")

    def test_stash_drop(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git stash drop"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_reflog_expire(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git reflog expire --expire=now --all"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_benign_git_push_is_allowed(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
        self.assertEqual(decision_of(proc), "allow")

    def test_benign_git_log_is_allowed(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git log --oneline -20"}})
        self.assertEqual(decision_of(proc), "allow")

    def test_two_sided_refspec_push_is_allowed(self):
        # `main:main` is a normal explicit refspec, not an empty-source
        # (delete) refspec like `:main` -- must not be flagged.
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push origin main:main"}})
        self.assertEqual(decision_of(proc), "allow")


class PathTraversalTests(unittest.TestCase):
    def test_write_dot_dot_segment_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "../../etc/passwd"}})
        self.assertEqual(decision_of(proc), "block")
        self.assertEqual(proc.returncode, 2)

    def test_edit_dot_dot_segment_blocked(self):
        proc = invoke({"tool_name": "Edit", "tool_input": {"file_path": "docs/../../secrets/leak.txt"}})
        self.assertEqual(decision_of(proc), "block")

    def test_bash_dot_dot_token_blocked(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "cat ../../etc/passwd >> out.txt"}})
        self.assertEqual(decision_of(proc), "block")

    def test_plain_relative_path_is_allowed(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "docs/notes.md"}})
        self.assertEqual(decision_of(proc), "allow")

    def test_absolute_path_without_traversal_is_allowed(self):
        # Legitimate absolute paths (e.g. this session's own tool calls, or
        # the scratchpad directory) are not path traversal by themselves.
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "C:/workspaces/CCSIF/docs/notes.md"}})
        self.assertEqual(decision_of(proc), "allow")


class SecretAccessTests(unittest.TestCase):
    def test_dotenv_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": ".env"}})
        self.assertEqual(decision_of(proc), "block")

    def test_pem_file_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "keys/server.pem"}})
        self.assertEqual(decision_of(proc), "block")

    def test_bash_append_to_dotenv_blocked(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "echo SECRET=1 >> .env"}})
        self.assertEqual(decision_of(proc), "block")


class BenignLookalikeTests(unittest.TestCase):
    """Documented current behavior for filenames that merely mention a
    protected-area keyword without being a real secret/protected file. The
    secrets regex is intentionally over-broad (fail-closed); repeated
    blocks on the same benign path are the false-block-review signal
    phase6a_metrics.py surfaces for a future rung-4 refinement, not a bug
    to silently patch here."""

    def test_credentials_policy_doc_is_blocked_by_design(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "docs/credentials-policy.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_authentication_overview_doc_is_blocked_by_design(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "auth/README.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_unrelated_readme_is_allowed(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "README.md"}})
        self.assertEqual(decision_of(proc), "allow")


class LockfileTests(unittest.TestCase):
    def test_direct_write_to_lockfile_is_ask(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "package-lock.json"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_direct_edit_to_lockfile_is_ask(self):
        proc = invoke({"tool_name": "Edit", "tool_input": {"file_path": "yarn.lock"}})
        self.assertEqual(decision_of(proc), "ask")

    def test_legitimate_package_manager_update_is_allowed(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "npm install lodash"}})
        self.assertEqual(decision_of(proc), "allow")

    def test_hand_edit_lockfile_via_sed_is_blocked_as_protected_path(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "sed -i 's/1.0.0/1.0.1/' package-lock.json"}})
        self.assertEqual(decision_of(proc), "ask")


class LedgerAppendOnlyTests(unittest.TestCase):
    def test_direct_write_to_ledger_is_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": ".claude/state/ledger.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_direct_edit_to_ledger_is_blocked(self):
        proc = invoke({"tool_name": "Edit", "tool_input": {"file_path": ".claude/state/ledger.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_bash_append_to_ledger_is_blocked(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "echo hi >> .claude/state/ledger.md"}})
        self.assertEqual(decision_of(proc), "block")


class GovernanceProtectedAreaTests(unittest.TestCase):
    def test_github_governance_path_is_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": ".github/CODEOWNERS"}})
        self.assertEqual(decision_of(proc), "block")

    def test_security_policy_file_is_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": "SECURITY.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_control_plane_rule_is_blocked(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": ".claude/rules/control-plane.md"}})
        self.assertEqual(decision_of(proc), "block")

    def test_block_reason_requires_halt_not_workaround(self):
        proc = invoke({"tool_name": "Write", "tool_input": {"file_path": ".github/CODEOWNERS"}})
        self.assertIn("Halt immediately on this first protected-area block", proc.stderr)
        self.assertIn("do not retry", proc.stderr)


class ProtectedAreaGuidanceDocumentationTests(unittest.TestCase):
    def test_authoritative_docs_include_halt_guidance_and_examples(self):
        required = [
            ROOT / "CLAUDE.md",
            ROOT / ".claude" / "rules" / "control-plane.md",
            ROOT / ".claude" / "rules" / "security.md",
            ROOT / ".claude" / "commands" / "control-plane-check.md",
        ]
        for path in required:
            text = path.read_text(encoding="utf-8")
            self.assertIn("halt", text.lower(), msg=f"missing halt guidance in {path}")
            self.assertIn("workaround", text.lower(), msg=f"missing workaround guidance in {path}")
        control_plane = (ROOT / ".claude" / "rules" / "control-plane.md").read_text(encoding="utf-8")
        for example in (".github/**", "SECURITY.md", ".claude/rules/control-plane.md"):
            self.assertIn(example, control_plane)


class HookFailureAndTimeoutTests(unittest.TestCase):
    def test_malformed_json_fails_open(self):
        node = cpc.resolve_node()
        guard_arg = cpc.node_script_arg(node, GUARD)
        proc = cpc.run([node, guard_arg], input_text="not json")
        self.assertEqual(proc.returncode, 0)

    def test_empty_stdin_fails_open(self):
        node = cpc.resolve_node()
        guard_arg = cpc.node_script_arg(node, GUARD)
        proc = cpc.run([node, guard_arg], input_text="")
        self.assertEqual(proc.returncode, 0)

    def test_events_are_logged_with_correlation_id_and_latency(self):
        log_path = ROOT / ".claude" / "state" / "logs" / "guardrail-events.jsonl"
        before = log_path.stat().st_size if log_path.exists() else 0
        invoke({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        self.assertTrue(log_path.exists())
        with log_path.open("r", encoding="utf-8") as fh:
            fh.seek(before)
            new_lines = [line for line in fh.read().splitlines() if line.strip()]
        self.assertTrue(new_lines, "expected at least one new event to be appended")
        event = json.loads(new_lines[-1])
        for field in ("ts", "correlation_id", "decision", "duration_ms"):
            self.assertIn(field, event)
        self.assertIsInstance(event["duration_ms"], int)


class ApprovalOverridePathwayTests(unittest.TestCase):
    """'ask' decisions surface Claude Code's own native interactive
    approval prompt to the real user; this guard's only job is to emit the
    correct hookSpecificOutput shape, never to invent its own bypass
    token."""

    def test_ask_decision_has_native_hook_output_shape(self):
        proc = invoke({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}})
        payload = json.loads(proc.stdout)
        hook_output = payload["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "PreToolUse")
        self.assertEqual(hook_output["permissionDecision"], "ask")
        self.assertTrue(hook_output["permissionDecisionReason"])


class PreExistingBehaviorRegressionTests(unittest.TestCase):
    """Guards already proven by control_plane_check.py's own probes must
    keep working exactly as before this phase's changes."""

    def test_existing_protected_probes_still_blocked(self):
        for probe in cpc.PROTECTED_PROBES:
            proc = invoke(probe)
            self.assertEqual(proc.returncode, 2, msg=f"probe regressed: {probe!r}")

    def test_existing_allowed_probes_still_allowed(self):
        for probe in cpc.ALLOWED_PROBES:
            proc = invoke(probe)
            self.assertEqual(proc.returncode, 0, msg=f"probe regressed: {probe!r}")

    def test_fd_dup_redirects_still_allowed(self):
        for command in ["cat x 2>&1", "echo hi >&2", "printf ok 1>&2"]:
            proc = invoke({"tool_name": "Bash", "tool_input": {"command": command}})
            self.assertEqual(proc.returncode, 0, msg=f"fd-dup regressed: {command!r}")


if __name__ == "__main__":
    unittest.main()

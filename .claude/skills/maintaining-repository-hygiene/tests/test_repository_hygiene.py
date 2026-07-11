#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_repository import run_audit  # noqa: E402
from github_operations import (  # noqa: E402
    apply_worktree_prune_plan,
    create_issue_plan,
    create_label_prune_plan,
    create_worktree_prune_plan,
    validate_issue_plan,
)
from hygiene_core import HygieneError  # noqa: E402
from hygiene_core import verify_digest  # noqa: E402
from repository_hygiene import findings_merge_command  # noqa: E402

POLICY = json.loads((ROOT / "resources" / "default-policy.json").read_text(encoding="utf-8"))


class RepoFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run("git", "init", "-q")
        self.run("git", "config", "user.email", "test@example.invalid")
        self.run("git", "config", "user.name", "Repository Hygiene Test")

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def write(self, path: str, content: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self) -> None:
        self.run("git", "add", ".")
        self.run("git", "commit", "-qm", "fixture")

    def close(self) -> None:
        self.temp.cleanup()


class RepositoryHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RepoFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def audit(self):
        return run_audit(self.fixture.root, POLICY, "off")

    def test_polyglot_stack_detection(self) -> None:
        self.fixture.write("package.json", '{"packageManager":"pnpm@10.0.0","workspaces":["apps/*"],"scripts":{"test":"vitest"},"dependencies":{"next":"1"}}')
        self.fixture.write("pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        self.fixture.write("services/api/pyproject.toml", "[project]\nname='api'\ndependencies=['fastapi']\n")
        self.fixture.write("crates/core/Cargo.toml", "[package]\nname='core'\nversion='0.1.0'\n[dependencies]\ntokio='1'\n")
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.commit()
        report = self.audit()
        ecosystems = {item["name"] for item in report["stack_profile"]["ecosystems"]}
        frameworks = {item["name"] for item in report["stack_profile"]["frameworks"]}
        self.assertTrue({"javascript-typescript", "python", "rust"}.issubset(ecosystems))
        self.assertTrue({"Next.js", "FastAPI", "Tokio"}.issubset(frameworks))
        self.assertTrue(report["stack_profile"]["workspace"]["detected"])

    def test_workflow_hardening_findings(self) -> None:
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.write(".github/workflows/ci.yml", """name: CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo '${{ github.event.pull_request.title }}'
""")
        self.fixture.commit()
        report = self.audit()
        finding = next(item for item in report["findings"] if item["rule_id"] == "GHA-WORKFLOW-HARDENING")
        observations = "\n".join(item["observation"] for item in finding["evidence"])
        self.assertIn("permissions", observations)
        self.assertIn("full commit SHA", observations)
        self.assertIn("timeout", observations)
        self.assertIn("untrusted event data", observations)

    def test_documentation_rot_deterministic_checks(self) -> None:
        self.fixture.write("package.json", '{"scripts":{"test":"vitest"}}')
        self.fixture.write("package-lock.json", "{}")
        self.fixture.write("README.md", "# Fixture\n\n[Missing](docs/removed.md)\n\n```sh\nnpm run nonexistent\n```\n")
        self.fixture.commit()
        report = self.audit()
        rules = {item["rule_id"] for item in report["findings"]}
        self.assertIn("DOCS-BROKEN-LOCAL-REFERENCES", rules)
        self.assertIn("DOCS-COMMAND-NOT-IN-MANIFEST", rules)

    def test_ampersand_heading_anchor_matches_github_double_hyphen(self) -> None:
        # GitHub renders "## Testing & Verification" with anchor id
        # "testing--verification" (double hyphen): the stripped "&" leaves
        # both surrounding spaces in place, and GitHub converts each space
        # to its own hyphen rather than collapsing the run. A link using
        # that real anchor must not be reported as broken.
        self.fixture.write(
            "README.md",
            "# Fixture\n\n"
            "- [Testing & Verification](#testing--verification)\n\n"
            "## Testing & Verification\n\ncontent\n",
        )
        self.fixture.commit()
        report = self.audit()
        rules = {item["rule_id"] for item in report["findings"]}
        self.assertNotIn("DOCS-BROKEN-LOCAL-REFERENCES", rules)

    def test_issue_plan_is_atomic_and_valid(self) -> None:
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.write(".github/workflows/release.yml", "name: Release\non: push\njobs:\n  publish:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n")
        self.fixture.run("git", "remote", "add", "origin", "https://github.com/example/fixture.git")
        self.fixture.commit()
        report = self.audit()
        plan = create_issue_plan(report, POLICY)
        self.assertEqual([], validate_issue_plan(plan))
        verify_digest(plan)
        remediation_keys = [step["remediation_key"] for step in plan["steps"]]
        self.assertEqual(len(remediation_keys), len(set(remediation_keys)))
        for step in plan["steps"]:
            self.assertIn(f"<!-- repository-hygiene-step:{step['fingerprint']} -->", step["body"])

    def test_sensitive_filename_never_reads_contents_into_evidence(self) -> None:
        secret = "SUPER_SECRET_VALUE_SHOULD_NOT_APPEAR"
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.write(".env", secret)
        self.fixture.commit()
        report = self.audit()
        serialized = json.dumps(report)
        self.assertNotIn(secret, serialized)
        self.assertIn("CONTENTS-SENSITIVE-FILENAMES", {item["rule_id"] for item in report["findings"]})


    def test_label_prune_suppresses_candidates_when_history_is_incomplete(self) -> None:
        labels = [
            {"name": "unused", "color": "ffffff", "description": "candidate"},
            {"name": "bug", "color": "d73a4a", "description": "protected"},
        ]
        issues = []
        with patch("github_operations.require_gh"), \
             patch("github_operations.github_slug", return_value="example/fixture"), \
             patch("github_operations.repository_identity", return_value={"head": "abc"}), \
             patch("github_operations._api_pages", side_effect=[(labels, True), (issues, False)]), \
             patch("github_operations._label_references", return_value={}):
            plan = create_label_prune_plan(self.fixture.root, POLICY)
        self.assertFalse(plan["scan"]["history_complete"])
        self.assertEqual([], plan["operations"])
        unused = next(item for item in plan["suppressed"] if item["name"] == "unused")
        self.assertIn("incomplete-history-scan", unused["reasons"])

    def test_label_prune_only_selects_zero_use_unreferenced_unprotected_labels(self) -> None:
        labels = [
            {"name": "unused", "color": "ffffff", "description": "candidate"},
            {"name": "used", "color": "000000", "description": "used"},
            {"name": "external", "color": "111111", "description": "referenced"},
            {"name": "bug", "color": "d73a4a", "description": "protected"},
        ]
        issues = [{"labels": [{"name": "used"}]}]
        refs = {"external": [".github/ISSUE_TEMPLATE/bug.yml:5"]}
        with patch("github_operations.require_gh"), \
             patch("github_operations.github_slug", return_value="example/fixture"), \
             patch("github_operations.repository_identity", return_value={"head": "abc"}), \
             patch("github_operations._api_pages", side_effect=[(labels, True), (issues, True)]), \
             patch("github_operations._label_references", return_value=refs):
            plan = create_label_prune_plan(self.fixture.root, POLICY)
        self.assertEqual(["unused"], [item["name"] for item in plan["operations"]])
        verify_digest(plan)

    def test_worktree_apply_rejects_changed_fresh_dry_run(self) -> None:
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.commit()
        plan = create_worktree_prune_plan(self.fixture.root)
        changed = dict(plan)
        changed["operations"] = ["different"]
        # First call inside apply is the fresh plan. Simulate state drift.
        with patch("github_operations.create_worktree_prune_plan", return_value=changed):
            with self.assertRaises(HygieneError) as context:
                apply_worktree_prune_plan(self.fixture.root, plan, plan["digest"])
        self.assertEqual("WORKTREE_STATE_CHANGED", context.exception.code)


    def test_supplemental_snapshot_finding_merges_and_updates_summary(self) -> None:
        import argparse
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.commit()
        report = self.audit()
        report_path = self.fixture.root / "report.json"
        supplement_path = self.fixture.root / "supplement.json"
        out_path = self.fixture.root / "merged.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        supplement = {
            "findings": [{
                "rule_id": "DOCS-SNAPSHOT-MISALIGNMENT",
                "category": "documentation",
                "severity": "medium",
                "confidence": "high",
                "title": "Align architecture claim with current entry point",
                "summary": "A documented entry point conflicts with the tracked implementation.",
                "evidence": [
                    {"source": "README.md", "line": 1, "observation": "Claims old entry point."},
                    {"source": "src/main.py", "line": 1, "observation": "Current entry point."}
                ],
                "remediation_key": "docs/entry-point",
                "recommended_actions": ["Update the claim."],
                "acceptance_criteria": ["The claim matches the implementation."],
                "verification": ["Compare README.md with src/main.py."]
            }]
        }
        supplement_path.write_text(json.dumps(supplement), encoding="utf-8")
        args = argparse.Namespace(report=str(report_path), supplement=str(supplement_path), out=str(out_path), markdown=None)
        self.assertEqual(0, findings_merge_command(args))
        merged = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertTrue(any(item["rule_id"] == "DOCS-SNAPSHOT-MISALIGNMENT" for item in merged["findings"]))
        self.assertEqual(len(merged["findings"]), merged["summary"]["findings"])

    def test_worktree_plan_has_valid_digest(self) -> None:
        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.commit()
        plan = create_worktree_prune_plan(self.fixture.root)
        self.assertEqual("repository-hygiene-worktree-prune-plan", plan["kind"])
        verify_digest(plan)


if __name__ == "__main__":
    unittest.main()

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import issue_to_pr as itp  # noqa: E402


SAMPLE_BODY = """<!-- repository-hygiene-step:f9f5c0f38d2b3e83 -->

## Objective
Choose and add an explicit repository license.

## Context
- Detected stack: ecosystems=node
- Audit rule(s): license-missing
- Severity: high
- Confidence: high
- Destructive or irreversible risk: No destructive operation is expected.

## Evidence
| Source | Evidence |
|---|---|
| `LICENSE` | File is missing. |

## Implementation checklist
- [ ] Add a LICENSE file.

## Acceptance criteria
- [ ] GitHub recognizes the selected license.

## Verification
```text
Inspect the repository About/license metadata.
```

## Dependencies
- None

## Risk and rollback
- Risk: Low.
- Rollback: Revert the PR.

## Non-goals
- Do not broaden scope.
"""

SAMPLE_BODY_WITH_DEPENDENCY = SAMPLE_BODY.replace(
    "<!-- repository-hygiene-step:f9f5c0f38d2b3e83 -->",
    "<!-- repository-hygiene-step:aaaaaaaaaaaaaaaa -->",
).replace("## Dependencies\n- None", "## Dependencies\n- f9f5c0f38d2b3e83")

SAMPLE_BODY_DESTRUCTIVE = SAMPLE_BODY.replace(
    "- Destructive or irreversible risk: No destructive operation is expected.",
    "- Destructive or irreversible risk: Yes — review the plan and rollback path before execution.",
).replace(
    "<!-- repository-hygiene-step:f9f5c0f38d2b3e83 -->",
    "<!-- repository-hygiene-step:bbbbbbbbbbbbbbbb -->",
)


class ParseIssueTests(unittest.TestCase):
    def test_parses_marker_and_sections(self):
        issue = {"number": 1, "title": "[Hygiene] Add a license", "body": SAMPLE_BODY, "url": "https://x"}
        parsed = itp.parse_issue(issue)
        self.assertEqual(parsed["fingerprint"], "f9f5c0f38d2b3e83")
        self.assertFalse(parsed["destructive"])
        self.assertEqual(parsed["dependency_tokens"], [])

    def test_no_marker_returns_none(self):
        issue = {"number": 2, "title": "unrelated", "body": "no marker here", "url": "https://x"}
        self.assertIsNone(itp.parse_issue(issue))

    def test_parses_dependency_token(self):
        issue = {"number": 3, "title": "dependent", "body": SAMPLE_BODY_WITH_DEPENDENCY, "url": "https://x"}
        parsed = itp.parse_issue(issue)
        self.assertEqual(parsed["dependency_tokens"], ["f9f5c0f38d2b3e83"])

    def test_parses_destructive_flag(self):
        issue = {"number": 4, "title": "destructive", "body": SAMPLE_BODY_DESTRUCTIVE, "url": "https://x"}
        parsed = itp.parse_issue(issue)
        self.assertTrue(parsed["destructive"])


class BranchNameTests(unittest.TestCase):
    def test_deterministic_and_safe(self):
        name = itp.branch_name("f9f5c0f38d2b3e83", "[Hygiene] Choose and add an explicit repository license")
        self.assertTrue(name.startswith("hygiene/f9f5c0f38d2b"))
        self.assertNotIn(" ", name)
        self.assertNotIn("[", name)
        # Same inputs always produce the same branch name (idempotency).
        self.assertEqual(name, itp.branch_name("f9f5c0f38d2b3e83", "[Hygiene] Choose and add an explicit repository license"))


class DigestTests(unittest.TestCase):
    def test_attach_and_verify_round_trip(self):
        plan = {"kind": "issue-to-pr-plan", "items": [1, 2, 3]}
        signed = itp.attach_digest(plan)
        itp.verify_digest(signed)  # must not raise
        itp.verify_digest(signed, signed["digest"])  # must not raise

    def test_tampering_is_detected(self):
        plan = itp.attach_digest({"kind": "issue-to-pr-plan", "items": [1]})
        plan["items"] = [1, 2]
        with self.assertRaises(itp.IssueToPrError):
            itp.verify_digest(plan)

    def test_confirm_digest_mismatch(self):
        plan = itp.attach_digest({"kind": "issue-to-pr-plan", "items": [1]})
        with self.assertRaises(itp.IssueToPrError):
            itp.verify_digest(plan, "not-the-real-digest")


class ValidatePlanTests(unittest.TestCase):
    def _plan(self, items):
        return itp.attach_digest({
            "schema_version": 1,
            "kind": "issue-to-pr-plan",
            "items": items,
        })

    def test_valid_plan_has_no_errors(self):
        plan = self._plan([
            {"issue_number": 1, "fingerprint": "abc", "branch": "hygiene/abc-x", "status": "ready"},
            {"issue_number": 2, "fingerprint": "def", "branch": "hygiene/def-y", "status": "blocked"},
        ])
        self.assertEqual(itp.validate_plan(plan), [])

    def test_duplicate_issue_number_is_flagged(self):
        plan = self._plan([
            {"issue_number": 1, "fingerprint": "abc", "branch": "hygiene/abc-x", "status": "ready"},
            {"issue_number": 1, "fingerprint": "def", "branch": "hygiene/def-y", "status": "ready"},
        ])
        errors = itp.validate_plan(plan)
        self.assertTrue(any("duplicate issue number" in error for error in errors))

    def test_duplicate_branch_is_flagged(self):
        plan = self._plan([
            {"issue_number": 1, "fingerprint": "abc", "branch": "hygiene/same", "status": "ready"},
            {"issue_number": 2, "fingerprint": "def", "branch": "hygiene/same", "status": "ready"},
        ])
        errors = itp.validate_plan(plan)
        self.assertTrue(any("duplicate branch name" in error for error in errors))


class RecordResultTests(unittest.TestCase):
    def test_record_is_idempotent_per_issue(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            plan = itp.attach_digest({
                "schema_version": 1,
                "kind": "issue-to-pr-plan",
                "repository": "acme/widgets",
                "items": [{"issue_number": 1, "fingerprint": "abc", "branch": "hygiene/abc-x", "status": "ready"}],
            })
            plan_path = tmp_dir / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            journal_path = tmp_dir / "journal.json"

            itp.record_result(journal_path, plan_path, issue_number=1, status="opened",
                               branch=None, pr_url="https://x/pr/1", review_verdict=None, error=None)
            journal = itp.record_result(journal_path, plan_path, issue_number=1, status="needs-changes",
                                         branch=None, pr_url="https://x/pr/1", review_verdict="request changes", error=None)
            self.assertEqual(len(journal["results"]), 1)
            self.assertEqual(journal["results"][0]["status"], "needs-changes")

    def test_record_rejects_issue_not_in_plan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            plan = itp.attach_digest({
                "schema_version": 1, "kind": "issue-to-pr-plan", "repository": "acme/widgets",
                "items": [{"issue_number": 1, "fingerprint": "abc", "branch": "hygiene/abc-x", "status": "ready"}],
            })
            plan_path = tmp_dir / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            journal_path = tmp_dir / "journal.json"
            with self.assertRaises(itp.IssueToPrError):
                itp.record_result(journal_path, plan_path, issue_number=999, status="opened",
                                   branch=None, pr_url=None, review_verdict=None, error=None)


if __name__ == "__main__":
    unittest.main()

# Verification Log

## Build under test

- Skill: `issue-to-pr`
- Verification date: 2026-07-11
- Runtime: Python 3 (standard library only); GitHub CLI (`gh`) required for the `plan` subcommand's remote reads
- Companion changes: `.claude/agents/implementation-agent.md`, `.claude/agents/pr-reviewer.md` fleshed out with real input/output contracts; `.claude/workflows/issue-to-pr.js` rewritten from a scaffold stub into a real agent-orchestrated pipeline.

## Checks performed

- [x] Python compilation: `python -m py_compile scripts/issue_to_pr.py` — passed.
- [x] Unit tests: `python -m unittest discover -s tests -v` — 13/13 passed (marker parsing, dependency-token parsing, destructive-flag parsing, deterministic branch naming, digest attach/verify/tamper-detection, plan validation duplicate detection, idempotent journal recording, unknown-issue rejection).
- [x] `evals/evals.json` is valid JSON.
- [x] `python3 .claude/scripts/control_plane_check.py` — `control-plane-check: PASS` (required after any edit to agents/workflows/skills under `.claude/`).
- [x] `.claude/agents/implementation-agent.md` and `.claude/agents/pr-reviewer.md` were updated together so the contract set stays aligned.
- [x] `node --check .claude/workflows/issue-to-pr.js` — exits 0.

## Evaluated failure modes

- Issue body with no `repository-hygiene-step:` marker — excluded from the plan (`parse_issue` returns `None`).
- Destructive-flagged issue — routed to `destructive-skip`, excluded from `order`.
- Issue with an unresolved (still-open) dependency — routed to `blocked` with the blocking issue named.
- Dependency token that matches nothing — routed to `blocked` with `status: unknown` for human investigation, not silently dropped.
- Re-running `plan`/`record` after an interruption — journal entries are updated in place per issue number (idempotent), and a plan digest mismatch is rejected rather than silently accepted.
- Issue that already has an open PR (`issue-to-pr-source:#<n>` marker found) — routed to `pr-exists`, never duplicated.

## Security review

- `scripts/issue_to_pr.py` performs no writes to GitHub in the `plan`/`validate`/`status` paths — only `gh issue list` and `gh api search/issues` (read-only). `record` only writes a local journal file, never calls `gh`.
- Actual branch creation, code edits, and `gh pr create` remain the responsibility of `implementation-agent`, which now has an explicit input contract (repository, issue, plan-supplied branch name) so it cannot invent an unreviewed branch name.
- `implementation-agent`'s contract explicitly forbids merging, pushing to a protected branch, or force-pushing; `pr-reviewer`'s contract is advisory-only (no merge/close authority) — consistent with `.claude/settings.json`'s `tools.git.protectBranches` and this repository's git-workflow rule that PR creation/merge are separate, explicit-request operations.
- Destructive-flagged hygiene issues are excluded from automatic implementation by design (see `references/pr-contract.md`), matching this repository's `CLAUDE.md` Tier 1 rule that Protected Areas and destructive/irreversible changes require explicit human approval before apply.

## Verification boundary

No live GitHub repository with real `repository-hygiene`-labeled issues was available in this session, so `plan`'s `gh`-calling paths (`build_plan`, `find_existing_pr`, `github_slug`) were not exercised end-to-end against a real remote — only their pure/parsing logic (`parse_issue`, `branch_name`, digest functions, `validate_plan`, `record_result`) has direct unit-test coverage. `.claude/workflows/issue-to-pr.js` passed a syntax check only; it has not been executed via the Workflow tool, since doing so requires explicit user opt-in and a real issue backlog to act on. A dry-run acceptance pass against a repository with real hygiene issues should be the first real-world run before broader use.

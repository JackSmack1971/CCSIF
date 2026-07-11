# Contributing to CCSIF

Thanks for your interest in CCSIF, a repository-local Claude Code scaffold that centralizes shared agent rules, hooks, workflows, and review commands around a single project constitution. Contributions to the constitution, agents, commands, workflows, hooks, rules, and skills under `.claude/` and `.codex/` are all welcome.

## Contents

- [Before contributing](#before-contributing)
- [Find or propose work](#find-or-propose-work)
- [Repository scope](#repository-scope)
- [Local setup](#local-setup)
- [Development workflow](#development-workflow)
- [Merge policy](#merge-policy)
- [Quality standards](#quality-standards)
- [Pull requests](#pull-requests)
- [Getting help](#getting-help)

## Before contributing

- No `CODE_OF_CONDUCT` file, `LICENSE` file, or security policy file exists in this repository yet, so none of those processes are formalized. If your change should add one of these, open an issue first so the addition can be scoped and reviewed.
- Read [the repository constitution](./CLAUDE.md) before making changes. It defines Protected Areas, tiered change rules, and the engineering rules every contribution must follow.
- This repository has no package manager manifest, so there is no install step to run before you start.

## Find or propose work

- There are no issue forms or discussion channels checked into this repository. Open a GitHub issue on the repository to propose a change, report a problem, or ask a question before starting non-trivial work.
- The standard workflow is one issue per branch per pull request: [`implementation-agent`](./.claude/agents/implementation-agent.md) implements exactly one issue as an isolated branch and PR, and [`pr-reviewer`](./.claude/agents/pr-reviewer.md) reviews it for correctness, verification quality, and merge readiness.
- The [`/create-pr`](./.claude/commands/create-pr.md), [`/review-pr`](./.claude/commands/review-pr.md), and [`/audit-upstream`](./.claude/commands/audit-upstream.md) slash commands document the corresponding Claude Code workflows if you are contributing through Claude Code itself.

## Repository scope

- [The repository constitution](./CLAUDE.md) is a Protected Area: edits to it require explicit human approval (Tier 1) under its own tier rules.
- Other Protected Areas it declares are production configuration, secrets and credentials, database migrations, authentication and authorization, payment or trading logic, and CI/CD deployment workflows.
- Treat `.claude/` and `.codex/` control-plane sources (agents, commands, hooks, workflows, rules, settings, `.mcp.json`) as governance changes that need tighter review than ordinary documentation edits.
- `.claude/traces/` and `.codex/traces/` hold generated telemetry, not source; do not hand-edit trace files.
- `CLAUDE.local.md` and `.claude/settings.local.json` are local-only overrides that are gitignored; do not commit changes to them.

## Local setup

1. Clone the repository:

   ```bash
   git clone https://github.com/JackSmack1971/CCSIF.git
   cd CCSIF
   ```

2. No package manager manifest or install script was found, so there is no repository-defined install step.
3. Confirm your clone is clean:

   ```bash
   git status --short
   ```

## Development workflow

- Branch from the default branch, `main`. [`.claude/settings.json`](./.claude/settings.json) lists `main` and `master` as protected branches (`tools.git.protectBranches`), so make your changes on a feature branch and open a pull request rather than pushing directly to `main`.
- Keep changes small, reviewable, and scoped to a single issue, per the Engineering Rules in [the repository constitution](./CLAUDE.md).
- Keep audit-only tasks read-only: report findings without editing production code.

## Merge policy

- Merge pull requests with squash commits only.
- Keep automatic head-branch deletion enabled so merged issue branches do not linger.
- Leave merge commits and rebase merges disabled in the repository settings.

## Quality standards

No automated test suite, build pipeline, or CI workflow was found in this repository. Use the narrowest check that matches your change:

- Any change: confirm the working tree state and check for whitespace/line-ending issues.

  ```bash
  git status --short
  git diff --check
  ```

- Changes to hooks or settings: run the affected hook script directly. For example, to check the session-start hook:

  ```bash
  bash .claude/hooks/session-start.sh
  ```

  Expect it to print the `[project-hook] SessionStart` marker line followed by `git status --short` output when run inside a git worktree.

- Changes to workflow or agent docs: re-read the file and compare it against [the repository constitution](./CLAUDE.md) for consistency.

Update the relevant docs (`README.md`, [the repository constitution](./CLAUDE.md), or the specific agent/command/hook file) whenever you change the behavior they describe.

## Pull requests

- Target `main`.
- Reference the issue your change addresses.
- Follow the PR Expectations from [the repository constitution](./CLAUDE.md). Every PR should include:
  - Problem statement
  - Change summary
  - Verification commands and results
  - Risk and rollback notes
  - Screenshots or logs when relevant
- Verify real source-of-truth state (e.g. `git status --short`) after any write or external action before requesting review.

Pre-flight checklist before opening a PR:

- [ ] The change is scoped to a single issue and does not touch unrelated files.
- [ ] Any Protected Area edit has explicit human approval.
- [ ] `git status --short` and `git diff --check` were run and reviewed.
- [ ] Relevant hook scripts or docs were re-verified if you changed them.
- [ ] The PR description follows the PR Expectations in [the repository constitution](./CLAUDE.md) above.

## Getting help

No support file, discussion forum, or chat link is checked into this repository. Open a GitHub issue on JackSmack1971/CCSIF with your question.

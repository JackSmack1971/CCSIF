# Contributing to CCSIF

Thanks for your interest in CCSIF, a repository-local Claude Code scaffold that centralizes shared agent rules, hooks, workflows, and review commands around a single project constitution. Contributions to the constitution, agents, commands, workflows, hooks, rules, and skills under `.claude/` are all welcome.

## Contents

- [Before contributing](#before-contributing)
- [Find or propose work](#find-or-propose-work)
- [Label taxonomy](#label-taxonomy)
- [Repository scope](#repository-scope)
- [Local setup](#local-setup)
- [Development workflow](#development-workflow)
- [Merge policy](#merge-policy)
- [Branch protection policy](#branch-protection-policy)
- [Quality standards](#quality-standards)
- [Pull requests](#pull-requests)
- [Getting help](#getting-help)

## Before contributing

- `LICENSE` and `SECURITY.md` are present. A `CODE_OF_CONDUCT.md` is not currently checked in, so conduct-process additions should be proposed in a scoped issue before implementation.
- Read [the repository constitution](./CLAUDE.md) before making changes. It defines Protected Areas, tiered change rules, and the engineering rules every contribution must follow.
- This repository has a root `package.json` for discoverable verification scripts and runtime metadata, not for third-party Node dependencies.

## Find or propose work

- Use the checked-in GitHub issue forms for bug reports and feature requests under `.github/ISSUE_TEMPLATE/`. Open one issue before starting non-trivial work, and keep the implementation scoped to that issue.
- The standard workflow is one issue per branch per pull request: [`implementation-agent`](./.claude/agents/implementation-agent.md) implements exactly one issue as an isolated branch and PR, and [`pr-reviewer`](./.claude/agents/pr-reviewer.md) reviews it for correctness, verification quality, and merge readiness.
- The [`/create-pr`](./.claude/commands/create-pr.md), [`/review-pr`](./.claude/commands/review-pr.md), and [`/audit-upstream`](./.claude/commands/audit-upstream.md) slash commands document the corresponding Claude Code workflows if you are contributing through Claude Code itself.

## Label taxonomy

- `repository-hygiene`: repository audit and remediation work that should turn into one focused PR per issue.
- `codex`: work item intended for Codex-driven implementation after an `@codex` trigger.
- `status:in-progress`: claimed work that is actively being implemented.
- Use the default GitHub meanings for stock labels such as `bug`, `documentation`, `enhancement`, `good first issue`, `help wanted`, `invalid`, `question`, and `wontfix`.

## Repository scope

- [The repository constitution](./CLAUDE.md) is a Protected Area: edits to it require explicit human approval (Tier 1) under its own tier rules.
- Other Protected Areas it declares are production configuration, secrets and credentials, database migrations, authentication and authorization, payment or trading logic, and CI/CD deployment workflows.
- Treat `.claude/` control-plane sources (agents, commands, hooks, workflows, rules, settings, `.mcp.json`) as governance changes that need tighter review than ordinary documentation edits.
- `.claude/traces/` holds generated telemetry, not source; do not hand-edit trace files.
- `CLAUDE.local.md` and `.claude/settings.local.json` are local-only overrides that are gitignored; do not commit changes to them.

## Local setup

1. Clone the repository:

   ```bash
   git clone https://github.com/JackSmack1971/CCSIF.git
   cd CCSIF
   ```

2. Confirm prerequisites and the repository-local MCP startup manifest:

   ```bash
   python .claude/scripts/prereq_check.py --mcp-smoke
   ```

   Use `python .claude/scripts/prereq_check.py --mcp-smoke --require-uv` when validating a workstation that must start the configured MCP server.
3. Confirm your clone is clean:

   ```bash
   git status --short
   ```

## Development workflow

- Branch from the default branch, `main`, and make your changes on a feature branch before opening a pull request rather than pushing directly to `main`.
- Keep changes small, reviewable, and scoped to a single issue, per the Engineering Rules in [the repository constitution](./CLAUDE.md).
- Keep audit-only tasks read-only: report findings without editing production code.

## Merge policy

- Merge pull requests with squash commits only.
- Keep automatic head-branch deletion enabled so merged issue branches do not linger.
- Leave merge commits and rebase merges disabled in the repository settings.

## Branch protection policy

- The default branch (`main`) requires every change to land through a pull request; direct pushes, force-pushes, and branch deletion are blocked.
- The required ruleset is defined as settings-as-code in `.github/rulesets/main-branch-protection.json`, with the rationale and the `gh api` apply command documented in `.github/rulesets/README.md`.
- GitHub reads ruleset configuration from its API/settings, not from files in the tree, so a repository admin applies this definition out-of-band from any pull request merge. Re-apply it whenever the checked-in definition changes.
- The required approving review count starts at `0` because the repository has a single verified collaborator with write access; raise it in the same file the first time a second maintainer is added.

## Quality standards

The authoritative local and CI test command is:

```bash
python -m unittest discover -s tests -v
```

CI runs that command on `ubuntu-latest`, `macos-latest`, and `windows-latest` for Python `3.11` and `3.12` with Node.js `20` and `22`. Contributors should preserve portability across Linux, macOS, and Windows, including path separators, shell wrappers, and filesystem behavior in Claude control-plane scripts.

Use the narrowest check that matches your change:

- Any change: confirm the working tree state, check for whitespace/line-ending issues, and run the authoritative test command.

  ```bash
  git status --short
  git diff --check
  python .claude/scripts/prereq_check.py --mcp-smoke
  python -m unittest discover -s tests -v
  ```

- Changes to hooks, settings, scripts, or CI: run the affected wrapper or validator directly. For example:

  ```bash
  python .claude/scripts/prereq_check.py --mcp-smoke
  python .claude/scripts/control_plane_check.py
  python .claude/scripts/rules_fidelity_check.py
  bash .claude/hooks/verify.sh run rules
  pwsh ./.claude/hooks/verify.ps1 run rules
  ```

- Changes to workflow or agent docs: re-read the file and compare it against [the repository constitution](./CLAUDE.md) for consistency.

Update the relevant docs (`README.md`, [the repository constitution](./CLAUDE.md), or the specific agent/command/hook file) whenever you change the behavior they describe.

## Pull requests

- Target `main`.
- Reference the issue your change addresses; use `Closes #<issue>` when the PR should close it automatically.
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
- [ ] `git status --short`, `git diff --check`, `python .claude/scripts/prereq_check.py --mcp-smoke`, and `python -m unittest discover -s tests -v` were run and reviewed.
- [ ] Relevant hook scripts or docs were re-verified if you changed them.
- [ ] The PR description follows the PR Expectations in [the repository constitution](./CLAUDE.md) above.

## Getting help

No support file, discussion forum, or chat link is checked into this repository. Open a GitHub issue on JackSmack1971/CCSIF with your question.

---
name: git-automation
description: Use when automating Git repository management beyond a single commit, including intelligent branching-strategy detection, commit-message and history optimization, release workflows, or repository health cleanup. Trigger on queries that say automate our release workflow, detect our branching strategy, clean up repository health, or bump the version across manifests. NOT for a single conventional commit use the git-commit skill instead, and NOT for opening or reviewing one pull request use create-pr or review-pr instead. Distinct keywords branching strategy detection, semantic commit impact, release workflow automation, repository health cleanup, continuous learning integration.
allowed-tools: Read, Grep, Glob, Bash(git status*), Bash(git log*), Bash(git branch*), Bash(git tag*), Bash(git diff*), Bash(git rev-list*), Bash(git rev-parse*), Bash(git merge-base*), Bash(git fetch*), Bash(git remote prune*), Bash(git gc*), Bash(git prune*)
when_to_use: Use for branching-strategy detection, commit-message and history optimization, release workflows, or repository health cleanup beyond a single commit; not for one conventional commit or a single PR review.
argument-hint: "(natural-language request naming the git-automation function to run)"
disallowed-tools: Bash(git push*), Bash(git filter-branch*), Bash(git rebase*), Bash(gh release*), Bash(gh pr merge*), Bash(git branch -d*), Bash(git branch -D*)
---

# Git Automation

## Contents

- [Purpose](#purpose)
- [Human confirmation gate](#human-confirmation-gate)
- [Checklist](#checklist)
- [Workflow](#workflow)
- [When to apply](#when-to-apply)
- [Validation](#validation)

## Purpose

Provide a function library and workflow for Git repository intelligence, commit optimization, release automation, and repository health management, with continuous learning from observed repository patterns. The full function library lives in [references/git-functions.md](references/git-functions.md); read it before running any function.

## Human confirmation gate

Every function in the reference library is tagged read-only, **[MUTATING]**, or **[REMOTE/DESTRUCTIVE]**.

- Read-only functions (repository analysis, branching-strategy detection, health analysis, pre-release validation) may run without asking.
- **[MUTATING]** functions (commit-history rewriting, version-file bumps, repository cleanup/pruning) require explicit user confirmation of the exact command before it runs, because they are difficult or impossible to reverse locally.
- **[REMOTE/DESTRUCTIVE]** functions (`git push`, tag push, `gh release create`, `gh pr merge`, branch deletion, `git filter-branch`, `git rebase -i --autosquash`) require the user's explicit, current approval for that specific action and target before it runs. Never chain a push, release, merge, or history rewrite automatically after an earlier approval for a different step.
- Never force-push. If a rewritten branch must update a remote, use `--force-with-lease` only after explicit approval and after re-verifying the expected remote commit.

## Checklist

- [ ] Identify which functions the task needs and read their safety tag in the reference library.
- [ ] Run every read-only analysis function first to ground the plan in real repository state.
- [ ] Present the exact command for any MUTATING or REMOTE/DESTRUCTIVE step and get explicit approval before running it.
- [ ] Run the step, then re-read repository state (`git status --short`, `git log -1`) to confirm the expected result.
- [ ] Report what ran, what was skipped, and any remaining manual step.

## Workflow

1. Load [references/git-functions.md](references/git-functions.md) for the function needed by the task; do not load the whole library into context for a single-function task.
2. Run the relevant read-only analysis functions (`analyze_repository`, `detect_branching_strategy`, `analyze_repository_health`, `validate_release_readiness`) to establish current state before recommending any change.
3. For commit or release work, use `analyze_commit_impact` and `generate_commit_message` to draft options; do not commit without user review of the message.
4. For a MUTATING or REMOTE/DESTRUCTIVE step, stop and request explicit approval per the [human confirmation gate](#human-confirmation-gate) before invoking it.
5. After any mutation, verify with `git status --short` and `git log -1` (or the equivalent remote check) that the actual result matches what was approved.

## When to apply

Use Git Automation when:
- Detecting or standardizing a branching strategy across a repository.
- Analyzing commit history for semantic-versioning impact or drafting a commit message.
- Running a release workflow: version bump, changelog update, tag, and (with explicit approval) push and GitHub/GitLab release.
- Diagnosing or cleaning up repository health: large files, stale branches, unreachable objects.
- Automating GitHub or GitLab operations such as PR creation or repository metadata updates.

## Validation

- Before reporting completion of any mutating step, show the exact command run and its output.
- Before reporting completion of a release or push step, re-fetch or re-query the remote (`git fetch`, `gh pr view`, `gh release view`) to confirm the intended state actually landed — command exit code alone is not sufficient evidence.
- If a step was skipped because approval was not given, say so explicitly rather than reporting the workflow as fully complete.

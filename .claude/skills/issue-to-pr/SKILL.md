---
name: issue-to-pr
description: Use when turning open repository-hygiene-labeled GitHub issues into real, reviewed pull requests, one isolated branch and PR per issue, in dependency order, with destructive-flagged issues skipped for human handling. Trigger on queries that say create PRs from these issues, turn the hygiene backlog into PRs, issue to PR, implement the open hygiene issues, or work through the repo-hygiene issues. NOT for ad-hoc issues that lack the repository-hygiene marker and fingerprint contract, and NOT for merging, closing, or force-pushing PRs once opened, implement those directly or route through manual review instead. Requires an authenticated `gh` CLI and open issues carrying the `repository-hygiene` label and its stable fingerprint marker.
when_to_use: Use after maintaining-repository-hygiene has published issues and the user wants those issues turned into working, reviewed pull requests instead of left as an untouched backlog. Not for issues without the repository-hygiene marker/contract (no parser exists for arbitrary issues yet), and not for merging, closing, or force-pushing PRs once opened — this skill only opens PRs for human review.
argument-hint: "[--issue N ...] [--label repository-hygiene] [--dry-run] [--parallel]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Issue to PR

## Table of contents

1. Objective
2. Non-negotiable rules
3. Inputs and operating modes
4. Default workflow
5. Step 1: Discover and plan
6. Step 2: Review the plan with the human
7. Step 3: Implement each ready issue
8. Step 4: Review each PR
9. Step 5: Record and report
10. Failure handling
11. Resources

## 1. Objective

Take the atomic, evidence-backed issues that `maintaining-repository-hygiene`
already filed and carry each one the rest of the way: a focused branch, a
real code change, verification evidence, and an open pull request a human
can review — without ever merging, without touching more than one issue's
scope per PR, and without silently attempting issues flagged destructive or
blocked on an unresolved dependency.

This skill is the second half of a two-skill pipeline. It does not audit a
repository or invent findings; it only consumes issues that already match
the [hygiene issue contract](../maintaining-repository-hygiene/references/issue-contract.md).
If the repository has no such issues yet, say so and point at
`maintaining-repository-hygiene` rather than guessing at unstructured issues.

## 2. Non-negotiable rules

1. **Read-only discovery before mutation.** `scripts/issue_to_pr.py plan` only reads GitHub state. No branch, commit, or PR exists until a later step explicitly creates one.
2. **One issue, one branch, one PR.** Never batch multiple issues into a single PR, even if they look related — the hygiene skill already guaranteed each issue is its own atomic change boundary; preserve that boundary downstream.
3. **Skip destructive issues by default.** An issue whose `## Context` states `Destructive or irreversible risk: Yes` is excluded from the plan's `order`. Report it separately; do not implement it without the user explicitly naming that issue number and authorizing it.
4. **Respect declared dependencies.** An issue whose `## Dependencies` reference an issue that is not yet closed is `blocked`. Do not implement it out of order on the theory that it will probably be fine.
5. **Idempotent by construction.** Before opening a PR, search for the `issue-to-pr-source:#<n>` marker (see [references/pr-contract.md](references/pr-contract.md)). If a PR already exists for an issue, skip it — never open a second one.
6. **Verification must actually run.** An implementation-agent must execute the issue's `## Verification` commands (or the closest repository-native equivalent) and paste real output into the PR. A plausible-looking diff with no verification evidence is not done.
7. **PRs only — never merge, never push to a protected branch.** This skill's authority ends at "PR opened, review posted." Merging is a separate, explicitly-requested human or workflow action, consistent with this repository's git-workflow rules treating PR merge as its own approval gate.
8. **Never fabricate a fingerprint or hand-edit an issue body.** The marker is the audit trail back to the original hygiene finding; only `maintaining-repository-hygiene` may create it.

## 3. Inputs and operating modes

Resolve from the request and current checkout:

- repository root (default: current Git root);
- label to filter on (default: `repository-hygiene`);
- specific issue number(s), when the user names one or a few rather than "all open issues";
- `--dry-run`: build and show the plan, do not spawn implementation agents or touch GitHub beyond the read-only `plan` step;
- concurrency: **sequential by default**. Only use parallel, worktree-isolated implementation (see Step 3) when the user asks for speed across a large batch — running `git checkout`/branch operations concurrently in one working tree corrupts state, so parallelism requires per-issue worktree isolation, not just "spawn several agents at once."

Defaults exist so a bare invocation ("run issue-to-pr on this repo") does
something safe and reviewable: it plans, shows the plan, and processes ready
issues one at a time with a real PR opened for each.

## 4. Default workflow

```text
Issue-to-PR Progress
- [ ] 1. Preflight: confirm gh is authenticated and the label exists
- [ ] 2. Build the plan (scripts/issue_to_pr.py plan)
- [ ] 3. Validate the plan (scripts/issue_to_pr.py validate)
- [ ] 4. Show the plan to the user: ready / blocked / destructive-skip / pr-exists counts
- [ ] 5. For each issue in plan order: implement, verify, open PR
- [ ] 6. Review each opened PR
- [ ] 7. Record every outcome in the journal
- [ ] 8. Report final status per issue
```

## 5. Step 1: Discover and plan

```bash
python3 <skill-root>/scripts/issue_to_pr.py plan \
  --repo . \
  --label repository-hygiene \
  --out .issue-to-pr/plan.json
```

Pass `--issue <n>` (repeatable) to scope the run to specific issues instead
of every open one. On Windows where `python3` is unavailable, use `py -3` or
`python` with the same arguments.

This step calls `gh issue list` (open and closed, for dependency
resolution) and `gh api search/issues` (to detect an existing PR per issue).
It makes no writes. Stop here and report clearly if:

- the path is not a Git worktree;
- `gh` is missing or unauthenticated (`require_gh` raises `GH_NOT_FOUND` / `GH_NOT_AUTHENTICATED`);
- the label matches zero open issues — say so rather than treating it as an error.

Then validate:

```bash
python3 <skill-root>/scripts/issue_to_pr.py validate --plan .issue-to-pr/plan.json
```

Validation catches duplicate issue numbers, duplicate branch names, and a
tampered/hand-edited plan (digest mismatch) before anything is built on top
of it.

## 6. Step 2: Review the plan with the human

Show, at minimum: total issues found, how many are `ready`, `blocked` (with
the blocking issue named), `destructive-skip` (with the issue named — these
need a human decision, not silent exclusion), and `pr-exists` (already has a
PR, will be skipped). This is the moment to catch a mis-scoped run before
any branch or PR exists.

Opening a PR is a remote, externally-visible action. The user's own request
to run this skill against a named set of issues is the authorizing request —
don't ask for a second confirmation per issue — but if the plan surfaces
something the request didn't anticipate (e.g. a destructive issue in the
label set, or far more issues than expected), surface it before proceeding
rather than silently including or excluding it.

## 7. Step 3: Implement each ready issue

For each issue number in `plan.order` (already dependency-sorted), invoke
the `implementation-agent` via the Agent tool with the issue number,
repository slug, and the plan's precomputed branch name — do not let the
subagent invent its own branch name, since `plan` already guaranteed
uniqueness and idempotent re-runs.

```
Agent({
  description: "Implement issue #<n> as a PR",
  subagent_type: "implementation-agent",
  prompt: "Repository: <owner/repo>. Issue: #<n> (<url>). Branch: <branch-from-plan>. ..."
})
```

**Sequential mode (default):** run one issue at a time in the main working
tree. Simpler to supervise, and avoids any risk of two agents mutating the
same working tree concurrently.

**Parallel mode (only when explicitly requested for a large batch):** spawn
multiple `implementation-agent` calls with `isolation: "worktree"` so each
gets its own working-tree copy and branch — never spawn concurrent
implementation agents without worktree isolation, since concurrent branch
switches in a shared tree will corrupt each other's state. Bound
concurrency to a handful of issues at a time and still process `plan.order`
respecting dependency order (don't parallelize an issue and the thing that
depends on it).

If an issue's verification step fails and can't be fixed within the
implementation-agent's own retry budget, it must report the failure rather
than opening a PR anyway — record that as `status: failed` in Step 5, don't
force a non-compliant PR open.

## 8. Step 4: Review each PR

Once an issue produces a PR URL, invoke `pr-reviewer` via the Agent tool
against that PR before considering the issue done:

```
Agent({
  description: "Review PR for issue #<n>",
  subagent_type: "pr-reviewer",
  prompt: "Review <pr-url> against issue #<n> (<issue-url>). Return a verdict: approve / request changes / needs info, plus blocking issues, verification gaps, and merge-safety notes."
})
```

A `request changes` or `needs info` verdict does not mean try again
automatically in a loop — record it and surface it in the final report. A
human decides whether to send it back to `implementation-agent` for another
pass or handle it manually.

## 9. Step 5: Record and report

After each issue reaches a terminal outcome (opened, needs-changes, failed,
or skipped), record it:

```bash
python3 <skill-root>/scripts/issue_to_pr.py record \
  --journal .issue-to-pr/journal.json \
  --plan .issue-to-pr/plan.json \
  --issue <n> \
  --status opened \
  --pr-url <url> \
  --review-verdict "approve"
```

`record` is idempotent per issue number — re-running the skill after an
interruption updates rather than duplicates the journal entry, and
`plan`'s `pr-exists` detection means a resumed run won't re-implement an
issue that already has a PR.

Close with a table: issue number, title, branch, PR URL, review verdict,
and status, plus separate call-outs for `blocked` and `destructive-skip`
issues so the human knows exactly what was not attempted and why.

**Completion gate.** Do not report the run complete while any issue in
`plan.order` has no journal entry. The run is done only when every issue in
scope has reached one of: `opened` (PR exists, reviewed), `needs-changes`
(reviewed, verdict recorded), `failed` (verification failure recorded with
raw output), `pr-exists` (existing PR reported instead of a duplicate), or
an explicit `blocked` / `destructive-skip` call-out with the reason and
blocking issue named. An issue with no recorded status is not a finished
run.

## 10. Failure handling

- `gh` missing or unauthenticated: stop before planning; nothing downstream can work without it.
- Zero issues carry the label/marker: report that plainly — this is not an error, it may mean the hygiene skill hasn't run yet or everything is already merged.
- An issue's dependency token doesn't resolve to any known issue (`status: unknown`): treat as `blocked` and flag for human investigation rather than guessing.
- Implementation verification fails: record `status: failed` with the raw failure output; do not open a partial or unverified PR.
- A PR already exists for an issue (`pr-exists`): skip; report the existing PR URL instead of opening a duplicate.
- Plan digest mismatch during `validate` or `record`: the plan file was hand-edited or is stale — regenerate with `plan` rather than forcing it through.

## 11. Resources

Load only what the current step requires:

- Idempotency marker, branch naming, dependency resolution, destructive-skip policy: [references/pr-contract.md](references/pr-contract.md)
- Upstream issue format this skill consumes: [maintaining-repository-hygiene/references/issue-contract.md](../maintaining-repository-hygiene/references/issue-contract.md)
- PR body template: [assets/pr-body-template.md](assets/pr-body-template.md)
- Deterministic CLI: [scripts/issue_to_pr.py](scripts/issue_to_pr.py)
- Unit tests: [tests/test_issue_to_pr.py](tests/test_issue_to_pr.py)
- Verification log: [VERIFICATION.md](VERIFICATION.md)
- Subagents this skill drives: `.claude/agents/implementation-agent.md`, `.claude/agents/pr-reviewer.md`

Before relying on this skill in a new environment, run:

```bash
python3 -m unittest discover -s <skill-root>/tests -v
```

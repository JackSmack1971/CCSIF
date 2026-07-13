---
name: checking-stacked-pr-merge-order
description: Use when a user asks to determine, verify, repair, or explain the merge order of open stacked pull requests in any GitHub repository, including check the PR stack, what merges first, resolve stacked branch conflicts, make every branch merge cleanly, and diagnose why a PR conflicts. Derives dependencies from live GitHub metadata and exact Git ancestry, simulates every head against its declared base, resolves conflicts in isolated worktrees with per-file diagnosis and validation, and publishes only approved merge commits with exact-OID leases. NOT for general PR review, approving policy readiness, or merging PRs into protected base branches.
---

# Checking Stacked PR Merge Order

Determine the real stacked-PR dependency graph, then diagnose and repair branch conflicts until every open PR head merges cleanly into its current declared base. Do not infer order from branch names, PR numbers, dates, or titles.

## Contents

- [Required tools](#required-tools)
- [Surface portability](#surface-portability)
- [Safety invariants](#safety-invariants)
- [Definition of done](#definition-of-done)
- [Workflow](#workflow)
- [Conflict diagnosis rules](#conflict-diagnosis-rules)
- [Output contract](#output-contract)
- [Stop conditions](#stop-conditions)

## Required tools

- Run inside a Git worktree for the target repository.
- Require `git`, `gh`, authenticated GitHub access, Python 3.10+, and network access.
- Require push permission to each PR head repository whose branch needs repair.
- Prefer the local remote matching the GitHub base repository. Pass `--remote` when ambiguous.

## Surface portability

- **Claude Code** — primary surface. Requires a local worktree, GitHub CLI authentication, network access, and push permission for affected PR heads.
- **Claude.ai** — usable only when code execution has a real repository plus `git`, `gh`, network access, and credentials. Without branch credentials, it can analyze uploaded history but cannot meet the live-state or publication definition of done.
- **Claude API** — locked containers commonly lack network access and credentials. Use a host-side runner or fully qualified GitHub MCP tools to supply live metadata and branch writes. Offline `--no-fetch` analysis is evidence-only and cannot certify final completion.

Never degrade a missing live-state or write capability into a success claim.

## Safety invariants

1. Query all relevant open PRs and fetch exact head/base objects before proposing order or edits.
2. Derive dependencies from OIDs and reachability. Branch names only corroborate an explicit GitHub base target.
3. Never alter the caller's branch, index, or working tree. Conflict work occurs only in isolated worktrees.
4. Generate a reviewable conflict plan before any branch update. Preparation requires its exact `plan_sha256`.
5. Default to merging the exact declared base OID into the exact PR head OID. This preserves published history and normally produces a fast-forward branch update.
6. Never resolve by blindly choosing all of `ours` or `theirs`. Record the intent conflict and file-specific resolution.
7. Run relevant repository validation before committing. Empty validation requires a specific written waiver.
8. Publish only with an exact expected-head lease. Never use an unqualified force push.
9. Resolve one currently eligible conflict, publish it, then rerun the complete analysis. Downstream plans become stale after any branch update.
10. This skill updates PR branches but does not merge PRs into their protected base branches.

## Definition of done

The task is complete only when a fresh final pass proves all of the following:

- [ ] Merge-order analyzer status is `ok`.
- [ ] Every live PR head/base OID matches the analyzed snapshot.
- [ ] Conflict-plan status is `clean`.
- [ ] Every PR head merges cleanly into its current declared base in an isolated Git simulation.
- [ ] No unresolved resolution worktree remains.
- [ ] No branch update is pending publication.

GitHub's displayed mergeability may lag. The final Git simulation is the source of truth for branch conflict cleanliness. Reviews, CI, approvals, protections, and release policy remain separate readiness gates.

## Workflow

Copy and complete this checklist:

- [ ] Confirm repository, remotes, authentication, and clean local context.
- [ ] Analyze all open PRs from live GitHub state and exact Git ancestry.
- [ ] Reject incomplete, cyclic, duplicate-head, stale, or contradictory graphs.
- [ ] Simulate every PR head against its current base and write a conflict plan.
- [ ] If clean, perform the final fresh pass and report done.
- [ ] If conflicts exist, review the eligible PR and plan hash before execution.
- [ ] Prepare its isolated worktree and inspect all conflict evidence.
- [ ] Fill the per-file resolution record, edit, stage, and validate.
- [ ] Create and inspect the verified merge commit.
- [ ] Publish with the exact commit approval and expected-head lease.
- [ ] Clean the worktree, then restart from ancestry analysis.

### 1. Analyze order

From the repository root:

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/check_merge_order.py \
  --format markdown \
  --json-out .git/stacked-pr-merge-order.json
```

Accept the graph only when `status` is `ok` and no blocking warning exists. Use selected PRs only when the complete referenced stack is included.

### 2. Plan the conflict pass

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/conflict_pass.py plan \
  --analysis .git/stacked-pr-merge-order.json \
  --out .git/stacked-pr-conflict-plan.json
```

Exit semantics:

- `0` — all branches are clean for the captured snapshot.
- `10` — conflicts exist; one action is marked `eligible`.
- `11` — planning is blocked or incomplete.

Before execution, show the user the eligible PR, exact head/base OIDs, conflicted paths/types, strategy, and `plan_sha256`. Branch modification requires approval of that plan.

### 3. Prepare the eligible conflict

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/conflict_pass.py prepare \
  --plan .git/stacked-pr-conflict-plan.json \
  --pr PR_NUMBER \
  --approve-plan PLAN_SHA256
```

The command verifies the live snapshot, creates an isolated detached worktree, reproduces the conflict with `zdiff3`, and writes:

- `state.json` — immutable operation metadata and exact OIDs.
- `resolution-record.json` — required per-file diagnoses and validation commands.
- `worktree/` — the only location where conflict edits are allowed.

### 4. Diagnose and resolve

Read [resources/conflict-resolution.md](resources/conflict-resolution.md) before editing. In the isolated worktree:

```bash
git log --left-right --oneline BASE_OID...HEAD_OID
git diff BASE_OID...HEAD_OID -- path/to/conflict
git show :1:path/to/conflict
git show :2:path/to/conflict
git show :3:path/to/conflict
```

For every conflicted path, fill `diagnosis`, `resolution`, and supporting `evidence` in `resolution-record.json`. Then edit the worktree and stage the intended result with `git add` or `git rm`. Do not commit manually.

`validation_commands` must be JSON argv arrays, never shell strings:

```json
{
  "validation_commands": [
    ["python", "-m", "pytest", "-q"],
    ["npm", "run", "typecheck"]
  ]
}
```

### 5. Verify and create the merge commit

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/conflict_pass.py verify \
  --state PATH_TO_STATE_JSON \
  --commit-message "chore: merge BASE_BRANCH into HEAD_BRANCH and resolve conflicts"
```

Verification blocks on unresolved index entries, missing diagnoses, residual conflict markers, unstaged or untracked files, failed validation commands, changed test outputs, missing Git identity, or an incorrect parent graph. Success records `resolution_commit_oid` without publishing it.

Inspect the commit and diff before push:

```bash
git -C PATH_TO_WORKTREE show --stat --summary RESOLUTION_COMMIT_OID
git -C PATH_TO_WORKTREE diff HEAD_OID..RESOLUTION_COMMIT_OID
```

### 6. Publish with an exact lease

After approving the verified commit:

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/conflict_pass.py publish \
  --state PATH_TO_STATE_JSON \
  --approve-push RESOLUTION_COMMIT_OID
```

For a fork or unusual remote, add `--push-target REMOTE_OR_URL`. The command refuses stale head/base state and pushes only if the remote branch still equals the planned head OID.

### 7. Cleanup and restart

```bash
python .claude/skills/checking-stacked-pr-merge-order/scripts/conflict_pass.py cleanup \
  --state PATH_TO_STATE_JSON
```

After every publication, discard the old order/conflict plans and restart at step 1. Never continue down a stale stack plan.

### 8. Final clean pass

When conflict planning first reports `clean`, rerun both analyzer and planner once more against a newly fetched snapshot. Declare completion only if the second fresh plan also reports `clean` and all definition-of-done checks pass.

## Conflict diagnosis rules

- Reconstruct both intents from commits, issue/PR context, tests, nearby code, and base/head versions.
- Preserve public contracts and invariants unless the PR intentionally changes them.
- Treat generated files as outputs. Resolve source inputs first, then regenerate with the repository's toolchain.
- Regenerate lockfiles with the declared package manager; do not hand-splice lockfile conflict markers.
- For delete/modify conflicts, decide whether deletion made the modified behavior obsolete or whether the behavior must move.
- For rename conflicts, identify the canonical destination before combining content.
- For binary assets, obtain or regenerate the authoritative artifact; never concatenate data.
- For submodules, choose a valid submodule commit based on its own ancestry and repository policy.
- Record uncertainty. If intent cannot be established safely, stop on that file rather than inventing behavior.

## Output contract

Use this report structure:

1. **Snapshot** — repository, remote, collection time, PR count, head/base OIDs.
2. **Merge order** — components, direct constraints, and merge waves with evidence.
3. **Conflict findings** — PR, base, path, conflict type, and intent diagnosis.
4. **Resolution actions** — edits, rationale, validation commands, and commit OID.
5. **Publication evidence** — expected old head, new head, target, and lease result.
6. **Final proof** — fresh analyzer status, fresh conflict-plan status, and definition-of-done checklist.

See [resources/report-contract.md](resources/report-contract.md) for JSON contracts and [resources/evaluations.md](resources/evaluations.md) for acceptance scenarios.

## Stop conditions

Stop without claiming completion when any of these occurs:

- GitHub state or fetched OIDs change during planning, preparation, verification, or publication.
- The dependency graph is partial, cyclic, contradictory, or ambiguous.
- A referenced parent PR is omitted from the selected set.
- Conflict intent cannot be established from repository evidence.
- Validation fails or required tooling/dependencies are unavailable.
- A conflict involves secrets, credentials, unexplained generated artifacts, or unsafe binary replacement.
- The PR head repository cannot be identified or write permission is unavailable.
- Branch protection, hooks, or server policy rejects the update.
- An isolated operation already exists and its state cannot be reconciled safely.

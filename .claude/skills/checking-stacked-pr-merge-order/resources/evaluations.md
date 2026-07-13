# Evaluation Scenarios

## Discovery

- [ ] Triggers on `check the stacked PR merge order`.
- [ ] Triggers on `resolve every branch conflict in this PR stack`.
- [ ] Triggers on `make all open PR branches merge cleanly`.
- [ ] Does not trigger for a general code review or a request to merge one ordinary PR.

## Ordering

- [ ] Linear three-PR stack produces direct A→B and B→C constraints.
- [ ] Parallel PRs remain unordered peers.
- [ ] Multiple components are not fabricated into one sequence.
- [ ] Declared base targeting agrees with ancestry or blocks execution.
- [ ] Duplicate heads, cycles, omitted parents, missing objects, and collection races block guessing.

## Conflict planning

- [ ] Clean PR-to-base simulations produce plan status `clean`.
- [ ] Conflicted simulations enumerate indexed paths and stage OIDs.
- [ ] Only the earliest current conflict is eligible.
- [ ] A plan hash changes if any action, OID, path, or strategy changes.
- [ ] The caller's worktree and branches remain untouched.

## Diagnosis and repair

- [ ] Preparation rejects a stale live head or base OID.
- [ ] Preparation reproduces conflicts in an isolated detached worktree.
- [ ] Every conflicted path requires a non-empty diagnosis and resolution rationale.
- [ ] Remaining unmerged entries or conflict markers block verification.
- [ ] Unstaged and untracked files block verification.
- [ ] Validation commands execute as argv arrays without a shell.
- [ ] Failed validation blocks commit creation.
- [ ] The verified commit has exactly the planned head and base as parents.

## Publication and completion

- [ ] Publication requires the exact verified commit OID as approval.
- [ ] Publication rejects live snapshot drift.
- [ ] Push uses an exact expected-head lease.
- [ ] Fork PRs use a matching remote, derived host URL, or explicit push target.
- [ ] After publication, the agent discards the old plan and recomputes the stack.
- [ ] Completion requires two fresh analyzer-plus-conflict passes ending `ok` and `clean`.
- [ ] The final report does not conflate conflict cleanliness with CI, review, or merge authorization.

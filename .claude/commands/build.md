# /build

Gate 4 (Build). Execute exactly one approved atomic plan.

## Inputs

- A validated plan ID from `.claude/plans/`

## Process

1. Load the plan (`python3 .claude/scripts/phase5b_lifecycle.py plan-validate <plan_id>`); refuse to build an unvalidated or non-existent plan.
2. Mark it `building`: `python3 .claude/scripts/phase5b_lifecycle.py plan-set-status <plan_id> building`.
3. Dispatch the `builder` agent (isolated worktree) per task, or execute directly for a single trivial task. Apply the `tdd` skill for any task with a test seam.
4. For every task whose `commit_boundary` is true, commit that task's diff separately using the `git-commit` skill's conventional-commit discipline before moving to the next task.
5. Run each task's declared verification target via `.claude/hooks/verify.sh run <target>` (or `.claude/hooks/verify.ps1` on Windows) before considering that task done.
6. Mark the plan `built` and append a ledger entry with the builder's summary and the exported task record under `.claude/state/agents/`.

## Required output

- One commit per `commit_boundary: true` task
- Per-task verification adapter output (exit code recorded)
- Ledger entry; builder summary exported under `.claude/state/agents/`

## Next gate

Once every task's own verification passes, the next gate is Verify (see `.claude/commands/verify.md`) — the builder's self-check is never treated as the independent verification this gate requires.

# /plan

Gate 3 (Plan). Turn aligned requirements and research into atomic plan files.

## Process

1. Invoke the `atomic-planning` skill on `$ARGUMENTS`, carrying forward assumptions from the align gate and citations from the research gate.
2. Create one or more plan files (at most three tasks each) via `python3 .claude/scripts/phase5b_lifecycle.py plan-create`; split larger work across multiple plans connected by `blocking_edges` instead of widening one plan.
3. Run `python3 .claude/scripts/phase5b_lifecycle.py plan-validate <plan_id>` for every created plan and fix any validation failure before proceeding.
4. Append a ledger entry listing the created plan IDs.

## Required output

- One or more validated plan files under `.claude/plans/`
- Ledger entry with plan IDs

## Next gate

Once a plan validates, the next gate is Build (see `.claude/commands/build.md`).

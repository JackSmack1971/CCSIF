# /status

Cross-cutting. Reconstruct where-are-we purely from `.claude/state/` and `.claude/plans/` on disk — never from conversation memory.

## Process

1. Run `python3 .claude/scripts/phase5b_lifecycle.py status` for plans, ledger tail, latest checkpoint, recent handoffs, active workflow runs, running agent tasks, and experiments.
2. Cross-reference with `python3 .claude/scripts/phase2_memory.py status` (memory recovery source), `python3 .claude/scripts/phase4_workflows.py list` (workflow run detail), and `python3 .claude/scripts/phase3_agents.py list` (delegated task detail) when more depth is needed than the summary provides.
3. Report the reconstructed state; do not add claims that are not backed by one of these disk reads.

## Required output

- Active plans and their status
- Latest verified checkpoint (if any)
- Recent ledger entries
- Any active workflow runs or running agent tasks
- Any running or decided experiments

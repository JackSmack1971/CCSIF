# /experiment

Cross-cutting. Karpathy AutoResearch loop: single metric, fixed budget, keep-if-improved / revert-if-not.

## Inputs

- A single metric name (in `$ARGUMENTS`), a baseline value, and a fixed time budget

## Process

1. Invoke the `metric-gated-experiment` skill; it starts the record, makes the change within budget, records the post-change observation, and calls the decide step.
2. Never report an improvement unless `python3 .claude/scripts/phase5b_lifecycle.py experiment-decide <experiment_id>` returned `outcome: keep`.
3. If the outcome is `revert`, revert the change before reporting, and say so.
4. Append a ledger entry with the experiment ID, baseline, final value, and decision.

## Required output

- Experiment ID and recorded observations
- Decision (`keep` or `revert`) with baseline vs. final value
- Confirmation the working tree matches the decision (change present only if `keep`)
- Ledger entry

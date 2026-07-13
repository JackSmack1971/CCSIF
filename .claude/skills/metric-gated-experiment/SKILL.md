---
name: metric-gated-experiment
description: Use when running a Karpathy-style AutoResearch optimization loop with a single named metric, a fixed time budget, and a keep-if-improved or revert-if-not decision recorded to disk. Trigger on queries that say run an experiment to improve this metric, try to optimize this within a time budget, is this change actually faster or better, metric-gated experiment. NOT for functional correctness verification with no optimization metric use fsv-verify instead, and NOT for open-ended exploration with no single measurable target use the research skill instead. Distinct keywords single-metric, fixed-budget, keep-if-improved, revert-if-not, baseline.
when_to_use: Use for optimization or tuning work that needs a single metric, a fixed budget, and a keep/revert decision derived from a recorded observation, not asserted from impression. Do not use for plain correctness verification (fsv-verify) or open-ended research with no single metric (research).
argument-hint: "<metric name> [--baseline <value>] [--budget-minutes <n>]"
allowed-tools: Read, Bash, Grep, Glob, Edit
---

# Metric-Gated Experiment

Cross-cutting `/experiment` gate. Never claim an improvement without this loop (`.claude/rules/10-karpathy-guidelines.md`).

## Process

- [ ] Name exactly one metric and record its current baseline value before changing anything.
- [ ] Start the experiment record:
      ```bash
      python3 .claude/scripts/phase5b_lifecycle.py experiment-start \
        --metric "<name>" --baseline <value> --budget-minutes <n> \
        --direction higher_is_better|lower_is_better
      ```
- [ ] Make the change within the fixed budget. Do not extend the budget mid-run; if the budget expires without a measurement, record the run as abandoned rather than silently continuing.
- [ ] Measure the metric under the same conditions as the baseline and record it:
      ```bash
      python3 .claude/scripts/phase5b_lifecycle.py experiment-record <experiment_id> <value>
      ```
- [ ] Decide — this is the only step allowed to declare an outcome:
      ```bash
      python3 .claude/scripts/phase5b_lifecycle.py experiment-decide <experiment_id>
      ```
- [ ] If the decision is `revert`, revert the change (`git checkout -- <files>` or an equivalent scoped revert) before reporting the result. If `keep`, leave the change and report the measured delta.

## Checklist

- [ ] Exactly one metric named before the change; no multi-metric hand-waving
- [ ] Baseline recorded before the change, under the same measurement conditions used for the post-change value
- [ ] Fixed budget stated up front and not silently extended
- [ ] Decision derived from `experiment-decide`, never asserted directly
- [ ] A `revert` decision is actually reverted, not left in place with a caveat

## Completion gate

Do not report an improvement unless `experiment-decide` recorded `outcome: keep`. Do not report the experiment complete while the decision step is unrun or the change from a `revert` decision is still present in the working tree.

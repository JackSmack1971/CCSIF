---
name: hindsight-observe
description: Use when refreshing neutral observation summaries that consolidate existing World and Experience memory facts per entity before downstream reflection runs. Trigger on queries that say refresh entity observation summaries, rebuild the observation snapshot, consolidate world and experience facts, recompute neutral memory summaries. NOT for retrieving memories to answer a live user prompt use hindsight-recall instead, NOT for adjusting opinion confidence scores use hindsight-reinforce instead, and NOT for ingesting new trace lines into memory use hindsight-retain instead. Distinct keywords entity summaries, World facts, Experience facts, observation snapshot, persona neutrality.
tools: [shell]
allowed-tools: Bash
model: sonnet
---

# HINDSIGHT Observe

Use this skill to refresh neutral entity summaries.

## Command

```bash
python .claude/memory/hindsight.py observe
```

## Checklist

- [ ] Run the observe command and confirm the reported entity count is nonzero when World or Experience facts exist.
- [ ] Verify each observation summary reads as neutral (no persona profile input from `.claude/rules/persona-profile.md`, no first-person opinion language) before it is consumed downstream by recall or reflect.
- [ ] Confirm the observation record was written to `.claude/memory/state/observations.jsonl` (or synced to Graphiti when configured).

## Validation

Before treating an observe run as complete, verify the command's exit code is 0 and spot-check the printed summary text against the source World/Experience facts for accuracy. Observation summaries must not include persona profile input per `.claude/rules/hindsight-memory.md`; if persona-derived wording leaks into the output, reject the summary and re-run observe after the underlying facts are corrected.

## Completion Gate

Do not consider an observe run complete until the command exits 0, the reported entity count matches the available World/Experience facts, and the neutrality check above has passed. A nonzero exit code is a stop condition: halt and diagnose before handing summaries to recall or reflect.

---
name: hindsight-reinforce
description: Use when adjusting an existing opinion memory's confidence score after new supporting or contradicting evidence arrives in the HINDSIGHT store. Trigger on reinforce this opinion, update confidence after new evidence, strengthen or weaken this belief, recompute confidence score, adjust opinion weight. NOT for trace ingestion, neutral observation summaries, or recall. Requires the current stored confidence, the matching evidence chain, and the correct supports or contradicts flag. Distinct keywords opinion, confidence, deterministic, evidence, reinforce.
when_to_use: Use when you need to adjust an opinion memory's confidence after new evidence arrives. Do not use for trace ingestion, neutral observation summaries, or recall.
argument-hint: "[prior] [supports|contradicts]"
tools: [shell]
allowed-tools: Bash
model: sonnet
---

# HINDSIGHT Reinforce

Use this skill to update opinion confidence scores.

## Command

```bash
python .claude/memory/hindsight.py reinforce --prior 0.6 --supports
```

## Checklist

- [ ] Identify the opinion memory entry and its currently stored confidence score.
- [ ] Confirm new supporting or contradicting evidence actually exists since that score was last set.
- [ ] Run the reinforce command with `--prior` set to the current stored score and the correct `--supports`/`--contradicts` flag.
- [ ] Verify the resulting confidence score is justified by the cited evidence before treating the update as final.

## Validation

Before applying the confidence update, verify the adjustment is justified by actual new evidence: confirm the supporting or contradicting fact is present in the trace or memory store, not merely asserted from memory, and confirm `--prior` matches the opinion's current stored confidence rather than a stale or guessed value. Do not reinforce a belief on the basis of evidence already reflected in the current score.

**Stop condition / completion gate:** treat the reinforce step complete only after the command exits with exit code 0 and the reported new confidence score reflects the cited evidence; do not chain a second reinforce call on the same opinion without new evidence.

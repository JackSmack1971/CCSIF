---
name: hindsight-recall
description: Use when retrieving relevant HINDSIGHT memories to ground a response before answering a non-trivial user prompt under an explicit recall budget. Trigger on recall relevant memories for this prompt, pull HINDSIGHT context before answering, search memory for related facts, fetch prior memories on this topic, look up what we already know. NOT for neutral observation summaries, opinion reinforcement, or trace ingestion. Requires the user's actual query, a max query or memory budget, and a relevance filter before any memory is used. Distinct keywords HINDSIGHT, memories, retrieval, budget, grounding.
when_to_use: Use when you need to pull relevant HINDSIGHT memories before answering a non-trivial prompt. Do not use for neutral observation summaries, opinion reinforcement, or trace ingestion.
argument-hint: "[query] [budget]"
allowed-tools: Bash
tools: [shell]
model: sonnet
---

# HINDSIGHT Recall

Use this skill before non-trivial answers that need project memory.

## Process

- [ ] Determine the explicit recall budget (max queries or max memories) before issuing any recall call.
- [ ] Run the recall command below with the user's actual query, not a paraphrase.
- [ ] Validate each returned memory against the current prompt: discard results that are stale, off-topic, or no longer relevant before using them to ground a response.
- [ ] Use only validated, relevant memories in the downstream answer; note when no relevant memories were found.

## Command

```bash
python .claude/memory/hindsight.py recall "your query here"
```

## Completion Gate

Do not treat recall as complete until either the recall budget is exhausted or a query returns no additional relevant memories. Stop condition: budget exhausted or relevance-validated result set stabilizes, whichever comes first.

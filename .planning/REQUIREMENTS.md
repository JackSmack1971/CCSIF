# HINDSIGHT Requirements

## Functional Requirements

1. Retain must ingest only new trace lines.
1. Retain must preserve source trace file and line metadata on every retained
   record.
1. Retain must emit separate World and Experience records.
1. Recall must accept an explicit budget and return only as much context as the
   downstream caller can use.
1. Recall must prefer the live graph backend when it is configured.
1. Recall must fall back to the local index when the live backend is
   unavailable.
1. Observe must synthesize neutral entity summaries from World and Experience
   facts only.
1. Observe must not incorporate persona profile input.
1. Reflect must create Opinion records with confidence values and evidence
   counts.
1. Reflect must chain provenance back to the evidence it used.
1. Reinforce must update confidence deterministically from prior state plus
   new evidence.
1. The local runtime must support replay from the trace corpus.
1. The repo must document the Graphiti backend inputs and health check.
1. The runtime must keep local mode functional when Graphiti is absent.

## Quality Requirements

- The memory system must remain explainable by file inspection and CLI output.
- The local tests must continue to pass after HINDSIGHT changes.
- The implementation must keep the memory split between objective facts,
  synthesized observation, and subjective opinion.
- The planning artifacts must distinguish current state from intended future
  state.

## Evidence Sources

- `ROADMAP.md`
- `.claude/memory/hindsight.py`
- `.claude/memory/tests/test_hindsight.py`
- `.claude/docs/Hindsight-memory-architecture/HINDSIGHT-doc-analysis.md`
- `.claude/docs/Hindsight-memory-architecture/HINDSIGHT-for-CCSIF-Implementation-Plan.md`
- `.claude/skills/hindsight-observe/SKILL.md`
- `.claude/skills/hindsight-recall/SKILL.md`
- `.claude/skills/hindsight-reinforce/SKILL.md`
- `.claude/skills/hindsight-retain/SKILL.md`


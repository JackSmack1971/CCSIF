---
name: hindsight-retain
description: Use when ingesting new trace lines into the HINDSIGHT memory store as durable World and Experience records that each carry a source trace file and line number. Trigger on queries that say retain this new trace data, ingest new trace lines into memory, persist these observations as memory records, write new facts to HINDSIGHT, store this trace as a retained fact. NOT for building neutral entity observation summaries use hindsight-observe instead. NOT for retrieving stored memories for a prompt use hindsight-recall instead. NOT for adjusting opinion confidence scores on existing facts use hindsight-reinforce instead. Distinct keywords HINDSIGHT, ingest, provenance, trace, durable.
allowed-tools: Bash
tools: [shell]
model: sonnet
---

# HINDSIGHT Retain

Use this skill to ingest fresh telemetry into memory.

## Process

- [ ] Determine the unprocessed trace range to ingest before running retain, so already-retained lines are not duplicated.
- [ ] Run the retain command below to build World and Experience records from each new trace entry.
- [ ] Validate that every retained record carries a non-empty source trace file path and a specific line number before it is written to the memory store; a record missing either must not be treated as retained.
- [ ] Confirm the reported retained record count matches the expected count of new trace entries processed (two records, world and experience, per trace line).

## Command

```bash
python .claude/memory/hindsight.py retain
```

## Completion Gate

Do not treat retain as complete until the command reports a retained count and every produced record has been validated to carry a source trace file and line number. Stop condition: a non-zero exit code, or any record failing source-trace validation, means retain must be rerun rather than marked complete.

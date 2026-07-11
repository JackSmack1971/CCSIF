# HINDSIGHT Implementation Checklist

This checklist turns the current HINDSIGHT scaffold in `.claude/memory/`, the
skills under `.claude/skills/`, and the architecture notes in
`.claude/docs/Hindsight-memory-architecture/` into a fully functional,
repo-local memory system.

## Current Baseline

- [x] `hindsight.py` exists as a single CLI entrypoint with `bootstrap`,
  `retain`, `recall`, `observe`, `reflect`, `reinforce`, `graphiti-check`,
  and `self-test`
- [x] Local memory records are already split into `world`, `experience`,
  `observation`, and `opinion`
- [x] Provenance is already carried through source trace file and line number
  fields
- [x] Opinion confidence is deterministic and persisted across calls
- [x] A local test suite exists and passes
- [x] Graphiti support exists as an optional backend, but it is not active by
  default

## Done When

- [ ] Retain ingests only new trace lines, does not duplicate work, and always
  writes World and Experience records with provenance
- [ ] Recall returns relevant memory under an explicit budget and prefers the
  live graph path when configured
- [ ] Observe produces neutral entity summaries from World and Experience
  facts only, with no persona leakage
- [ ] Reflect produces opinion records that include confidence, evidence
  counts, and stable provenance chaining
- [ ] Reinforce updates confidence deterministically from prior state plus new
  evidence instead of rebuilding opinions from scratch
- [ ] The local fallback and the Graphiti backend both have documented, tested,
  repeatable setup paths
- [ ] A trace replay can rebuild local memory state from the source JSONL
  corpus

## Phase 1: Lock The Contract

- [ ] Add proper trigger metadata to the HINDSIGHT skills so routing is
  explicit and non-overlapping
- [ ] Make the local HINDSIGHT README and the skill docs agree on command
  names, default backend behavior, and failure conditions
- [ ] Document the local-first contract clearly: local store works by default;
  Graphiti is opt-in and environment-driven

Exit criteria:

- [ ] A reader can tell which skill to invoke, why, and what command it runs
- [ ] The docs do not describe behavior the runtime does not support

## Phase 2: Harden Retain

- [ ] Keep the trace cursor authoritative and idempotent
- [ ] Ensure every retained record carries source trace and line metadata
- [ ] Preserve the World/Experience split in both local JSONL and Graphiti
  mode
- [ ] Add a replay path that rebuilds memory from `.claude/traces/` without
  manual repair

Exit criteria:

- [ ] Re-running retain on the same trace range produces no duplicates
- [ ] A wiped state directory can be regenerated from traces alone

## Phase 3: Tighten Recall And Observe

- [ ] Keep recall budget-aware and explicit about how many results it is
  allowed to return
- [ ] Prefer Graphiti retrieval when available, then fall back to the local
  index
- [ ] Keep observe strictly neutral: it should summarize facts, not persona or
  tone
- [ ] Write observation records back into the observation store and keep them
  separable from source facts

Exit criteria:

- [ ] Recall finds relevant history for a paraphrased query when the entity
  match is good enough
- [ ] Observe does not pull in persona profile text or opinion language

## Phase 4: Make Reflect Real

- [ ] Keep confidence updates deterministic and bounded
- [ ] Preserve the prior opinion when new evidence supports it instead of
  starting from a fresh guess every time
- [ ] Keep `literalism`, `skepticism`, `empathy`, and `bias_strength` in
  clearly separate roles
- [ ] Keep reflect output human-readable while the confidence math stays in
  code

Exit criteria:

- [ ] Repeated supporting evidence moves confidence in the expected direction
- [ ] Contradictory evidence moves confidence down
- [ ] The opinion record still points back to the evidence chain

## Phase 5: Finish The Graphiti Path

- [ ] Document the required environment variables and backend mode clearly
- [ ] Keep the runtime probe (`graphiti-check`) as the authoritative health
  test
- [ ] Validate that Graphiti ingest, search, and observation projection work
  from this workspace
- [ ] Keep the local fallback as the default so Windows and offline use still
  work

Exit criteria:

- [ ] `graphiti-check` succeeds in a configured environment
- [ ] The repo has a documented fallback story when Graphiti is not configured

## Phase 6: Prove It With Tests

- [ ] Expand the current unit tests to cover cursor replay, duplicate
  suppression, neutral observation output, and opinion reinforcement
- [ ] Add at least one end-to-end scenario that exercises retain -> recall ->
  observe -> reflect in local mode
- [ ] Keep the self-test small and runnable from the CLI

Exit criteria:

- [ ] The memory runtime has a fast local check and a deeper integration
  check
- [ ] The checks fail when the core memory invariants fail

## Suggested Order

1. [ ] Fix the skill metadata and docs contract first
2. [ ] Harden retain and replay next
3. [ ] Tighten recall, observe, and reflect together
4. [ ] Finish the live Graphiti backend path
5. [ ] Expand tests around the real end-to-end flow

## Notes

- The HINDSIGHT docs under `.claude/docs/Hindsight-memory-architecture/` are
  background material and implementation guidance, not runtime policy
- The local runtime is already useful; the checklist is about making it
  complete, durable, and easier to reason about
- If the Graphiti backend is intentionally out of scope for this repo, Phase 5
  can stay as documented optional support instead of a hard dependency

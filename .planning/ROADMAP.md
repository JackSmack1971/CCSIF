# HINDSIGHT Roadmap

## Phase 1: Lock The Contract

- [x] Add proper trigger metadata to the HINDSIGHT skills so routing is
  explicit and non-overlapping.
- [x] Make the local HINDSIGHT README and the skill docs agree on command
  names, default backend behavior, and failure conditions.
- [x] Document the local-first contract clearly: local store works by default;
  Graphiti is opt-in and environment-driven.

Exit criteria:

- [x] A reader can tell which skill to invoke, why, and what command it runs.
- [x] The docs do not describe behavior the runtime does not support.

## Phase 2: Harden Retain

- [x] Keep the trace cursor authoritative and idempotent.
- [x] Ensure every retained record carries source trace and line metadata.
- [x] Preserve the World/Experience split in both local JSONL and Graphiti
  mode.
- [x] Add a replay path that rebuilds memory from `.claude/traces/` without
  manual repair.

Exit criteria:

- [x] Re-running retain on the same trace range produces no duplicates.
- [x] A wiped state directory can be regenerated from traces alone.

## Phase 3: Tighten Recall And Observe

- [x] Keep recall budget-aware and explicit about how many results it is
  allowed to return.
- [x] Prefer Graphiti retrieval when available, then fall back to the local
  index.
- [x] Keep observe strictly neutral: it should summarize facts, not persona or
  tone.
- [x] Write observation records back into the observation store and keep them
  separable from source facts.

Exit criteria:

- [x] Recall finds relevant history for a paraphrased query when the entity
  match is good enough.
- [x] Observe does not pull in persona profile text or opinion language.

## Phase 4: Make Reflect Real

- [x] Keep confidence updates deterministic and bounded.
- [x] Preserve the prior opinion when new evidence supports it instead of
  starting from a fresh guess every time.
- [x] Keep `literalism`, `skepticism`, `empathy`, and `bias_strength` in
  clearly separate roles.
- [x] Keep reflect output human-readable while the confidence math stays in
  code.

Exit criteria:

- [x] Repeated supporting evidence moves confidence in the expected direction.
- [x] Contradictory evidence moves confidence down.
- [x] The opinion record still points back to the evidence chain.

## Phase 5: Finish The Graphiti Path

- [x] Document the required environment variables and backend mode clearly.
- [x] Keep the runtime probe (`graphiti-check`) as the authoritative health
  test.
- [ ] Validate that Graphiti ingest, search, and observation projection work
  from this workspace.
- [x] Keep the local fallback as the default so Windows and offline use still
  work.

Exit criteria:

- [ ] `graphiti-check` succeeds in a configured environment.
- [x] The repo has a documented fallback story when Graphiti is not configured.

## Phase 6: Prove It With Tests

- [x] Expand the current unit tests to cover cursor replay, duplicate
  suppression, neutral observation output, and opinion reinforcement.
- [x] Add at least one end-to-end scenario that exercises retain -> recall ->
  observe -> reflect in local mode.
- [x] Keep the self-test small and runnable from the CLI.

Exit criteria:

- [x] The memory runtime has a fast local check and a deeper integration
  check.
- [x] The checks fail when the core memory invariants fail.

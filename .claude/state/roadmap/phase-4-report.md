# Phase 4 Report

Status: complete

## Summary

Phases 0-3 were confirmed evidence-complete before this phase started
(`.claude/state/roadmap/phase-{0,1,2,3}-report.md`, all `status: complete`;
`control_plane_check.py` and `rules_fidelity_check.py` re-verified `PASS`
before any change), per the roadmap's sequencing requirement.
`docs/claude-code-control-plane-roadmap-v2.md` Phase 4 section, the
manifest, and every prior checkpoint were read in full before any change.

Implemented a static-first workflow layer, per the roadmap's explicit
instruction to wrap native primitives rather than invent an unrestricted
graph engine: small declarative workflow definitions
(`.claude/workflows/defs/*.json`) with stable step IDs, an allowlisted
`allowed_next` per node, required inputs/outputs, a verifier reference, a
`risk` tier, and a `checkpoint_required` flag; a thin engine
(`.claude/scripts/phase4_workflows.py`) that validates and tracks execution
against that allowlist; a thin project command (`.claude/commands/workflow.md`)
as the common entrypoint; and durable run state under
`.claude/state/workflows/`.

### Why this is not a new graph engine

- The "planner" is `propose_next()`, which returns only the current node's
  declared `allowed_next` list. It cannot invent a node or a tool; `advance()`
  rejects anything not on that list and records the rejection in
  `path_trace` for visibility (the "no arbitrary planner tool chain"
  completion requirement).
- Checkpoint gating reuses Phase 0's `Phase0ControlPlane.load_checkpoint`
  directly. A node with `checkpoint_required: true` (the roadmap's write,
  merge, deploy, delegate, handoff transitions) cannot be entered without a
  real, verified checkpoint id from that existing mechanism — no parallel
  checkpoint system was built.
- Retries are bounded per node (`max_retries`, default 2, matching Phase 0's
  own `MAX_RETRIES`), and exceeding the bound is an explicit terminal state
  (`failed-exhausted-retries`), not a silent loop.
- Resume rolls back to the last *verified* node
  (`record["verified_node"]`), never trusting an in-flight, unverified
  `current_node` — matching the roadmap's "resume from the last verified
  node" requirement and Phase 0's own "one verified step at a time"
  discipline.
- `fallback()` records that the static path was pinned instead of a graph's
  optional branch, so the fallback stays visible state rather than silent
  behavior (the roadmap's "visible static fallback" requirement).
- Delegation, subagent tracking, memory, and compaction are unchanged and
  reused as-is from Phases 0-3; this phase adds only the graph-tracking
  layer on top of them, per the roadmap's explicit instruction to wrap
  `/goal`, `/loop`, routines, plan mode, hooks, and agents rather than
  duplicate them. No script-level automation of the actual native
  `/goal`/`/loop`/routines features was attempted, because those are
  product-level session behaviors outside what a repository script can
  invoke; this control plane's role is limited to what Phase 0-3 already
  proved it can influence: durable, replayable, checkpoint-gated state.

### Workflow definitions (`.claude/workflows/defs/`)

| File | Shape | Purpose |
|---|---|---|
| `linear-static.json` | `gather-context -> implement -> verify -> ship` (no branches) | The default fixed path; `ship` is `risk: high`, `checkpoint_required: true`. |
| `evidence-branch.json` | `run-tests -> {ship, debug}`, `debug -> run-tests` | Evidence-driven branch selection plus a bounded retry loop; `ship` again requires a verified checkpoint. |

### Engine (`.claude/scripts/phase4_workflows.py`)

- `start_run` / `propose_next` / `verify_node` / `advance` / `resume` /
  `fallback` / `replay` / `status` / `list_runs`, all persisting to
  `.claude/state/workflows/<run_id>.json` as a single JSON record with a
  `path_trace` array — every transition, rejection, retry, and resume is
  appended, so a run reconstructs entirely from disk.
- `advance()` enforces, in order: (1) the target must be in the current
  node's `allowed_next` (else `UnsupportedBranchError`, and the rejection is
  recorded); (2) the current node must already be verified (else
  `UnverifiedNodeError`); (3) if the target requires a checkpoint, a real
  verified Phase 0 checkpoint id must be supplied and match (else
  `CheckpointRequiredError`).
- `verify_node()` tracks a per-node retry counter; exceeding `max_retries`
  sets `status: failed-exhausted-retries` and raises
  `RetriesExhaustedError`; a run in that status can no longer `advance`.
- `resume()` sets `current_node` back to `verified_node` (or the workflow's
  start node if nothing is verified yet) and appends a `resume` event
  recording whether the run was actually interrupted.
- `control_plane_check.py` gained a `check_workflow_defs()` step that loads
  and structurally validates both shipped definitions through the same
  `phase4_workflows.load_workflow_def()` the engine itself uses, so a
  broken definition fails the deterministic gate, not just at runtime.

### Commands and rules

- `.claude/commands/workflow.md` — thin entrypoint documenting every CLI
  subcommand and the "never fabricate a checkpoint id" / "never advance
  outside `allowed_next`" invariants.
- `.claude/rules/dynamic-workflows.md` — new path-scoped rule file
  (registered in `rules_fidelity_check.py`'s `EXPECTED_SCOPES`/`MAX_LINES`)
  stating the same invariants as durable policy, not just command-doc prose.

## Verification

| Command | Result |
|---|---|
| `python -m py_compile .claude/scripts/phase4_workflows.py .claude/scripts/control_plane_check.py .claude/scripts/rules_fidelity_check.py tests/test_phase4_workflows.py` | exit 0 |
| `python -m unittest discover -s tests -v` | exit 0, 54 tests (45 prior + 9 new Phase 4), no regression |
| `python3 .claude/scripts/control_plane_check.py` | `control-plane-check: PASS` (includes the new `check_workflow_defs()` step) |
| `python3 .claude/scripts/rules_fidelity_check.py` | `rules-fidelity-check: PASS` |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | exit 0 |
| `git check-ignore -v` against every new Phase 4 path | exit 1 (nothing ignored; all evidence is git-visible) |

### Exit Criteria Evidence (roadmap Phase 4 + task's required scenarios)

1. **One linear static workflow** —
   `test_linear_static_workflow_runs_to_completion`: `linear-static` run
   walks `gather-context -> implement -> verify -> ship`, `ship` gated by a
   real verified checkpoint, ends `status: completed`; `replay()` returns
   the exact node sequence.
2. **One evidence-driven branch** —
   `test_evidence_driven_branch_routes_to_debug_then_ships`: `run-tests`
   verified, then the caller branches to `debug` based on evidence (not a
   node-verification outcome), loops back to `run-tests`, then branches to
   `ship`; `metrics.branch_depth` counts both branch decisions.
3. **One rejected unsupported branch** —
   `test_unsupported_branch_is_rejected_and_recorded`: advancing from
   `run-tests` to an undeclared node raises `UnsupportedBranchError`,
   `current_node` does not move, and the rejection is recorded in
   `path_trace` with the actual `allowed_next` list for visibility.
4. **One interrupted resume** —
   `test_resume_rolls_back_to_last_verified_node_after_interruption`: a run
   advances into `implement` without verifying it, then `resume()` rolls
   `current_node` back to the last verified node (`gather-context`) and
   records `was_interrupted: true`.
5. **One exhausted-retry failure** —
   `test_exhausted_retries_produce_explicit_terminal_failure`: three
   consecutive failed verifications against `max_retries: 2` raise
   `RetriesExhaustedError` on the third, set
   `status: failed-exhausted-retries`, and block further `advance()` calls.
6. **One high-risk checkpoint gate** —
   `test_high_risk_transition_requires_a_real_verified_checkpoint`:
   advancing into `ship` with no checkpoint, then with a fabricated
   checkpoint id, both raise `CheckpointRequiredError`; only a real checkpoint
   produced by `Phase0ControlPlane.compact()` in the same state root succeeds.
7. **Replayable path traces and correct recovery** —
   `replay()`/`status()`/`list_runs()` reconstruct every run from
   `.claude/state/workflows/*.json` alone, proven by
   `test_list_and_status_reconstruct_from_disk_alone` and the `path_trace`
   assertions in every scenario test above.
8. **No arbitrary planner tool chain** — `propose_next()` is the only
   "planning" surface and it returns exactly the current node's declared
   `allowed_next`; `advance()` structurally cannot accept a node the
   definition did not declare (see rejected-branch evidence above and
   `_validate_workflow_def()`, which itself rejects a definition whose
   `allowed_next` points at an undeclared node).

## Design Decisions

1. Checkpoint gating calls `Phase0ControlPlane.load_checkpoint()` directly
   instead of building a second checkpoint format, so "verified" means
   exactly what Phase 0 already proved it means (a session step that passed
   `verify(passed=True)` and was then `compact()`-ed).
2. Branch selection is evidence-driven by the caller, not encoded as a
   verifier outcome: `verify_node()` marks that a step *executed*
   successfully; which of a node's `allowed_next` values to enter next is a
   separate `advance()` call, so the graph can express "the step succeeded,
   but the evidence it produced determines the next node" (e.g., tests ran
   fine as a step, but which branch to take depends on whether they passed).
3. Retries are keyed per node, not per run, so a bounded retry/re-plan loop
   (`debug -> run-tests`) does not exhaust the budget of a step it never
   revisited, matching the roadmap's "bound retries/replans" language at the
   node level where the actual repeated work happens.
4. `_validate_workflow_def()` runs at every `load_workflow_def()` call (not
   just at authoring time), so a hand-edited or corrupted definition file
   fails immediately and loudly rather than letting an engine bug silently
   accept it; `control_plane_check.py`'s new `check_workflow_defs()` step
   makes this a deterministic gate rather than a runtime-only check.
5. No live `/goal`/`/loop`/routines invocation was scripted from Python.
   Those are Claude Code product-level session behaviors, not something a
   repository script can drive; per the roadmap's own instruction to "wrap"
   rather than reimplement, this phase's contribution is the durable,
   checkpoint-gated, replayable state layer those native features can sit
   on top of — consistent with how Phase 3 treated native
   foreground/background subagent execution.

## Remaining Risks

- The engine was proven with direct Python calls and the shipped `linear-static`/`evidence-branch` definitions; it has not yet been driven by a live `/goal`- or `/loop`-triggered session in this environment, so the "wraps `/goal`/`/loop`" relationship is a documented design intent, not a live-session proof.
- `planner_tokens`/`planner_cost_usd` in `metrics` are always `null`; no token/cost accounting hook exists at the script level to populate them, matching the honest "not available" pattern Phase 2/3 used for other unmeasurable fields rather than fabricating a value.
- Only two workflow definitions exist. The roadmap's "promote to dynamic only after repeated executions show branching is common" guidance means no further definitions should be added speculatively; add one only when a real, repeated task shape justifies it.
- Phases 5-7 remain incomplete and are not implicitly validated by these Phase 4 changes.

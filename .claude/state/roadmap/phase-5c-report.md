# Phase 5C Report

Status: complete (scoped to Phase 5C: `/bootstrap-control-plane` installer,
fresh-clone recovery, and cross-stack portability proof -- not Phase 6/7)

## Summary

Phase 5B was confirmed complete before this phase started
(`.claude/state/roadmap/phase-5b-report.md`, `phase-5b-checkpoint.json`,
status `complete`; `control_plane_check.py`, `rules_fidelity_check.py`, and
the full `tests/` suite (106 tests) re-verified `PASS` before any change).
`docs/claude-code-control-plane-roadmap-v2.md`, `execution-manifest.json`,
the Phase 5A/5B reports/checkpoints, the current bootstrap-adjacent code
(`phase5b_verify.py`, `phase5b_lifecycle.py`, `control_plane_check.py`),
`.gitignore`, and both `.claude/settings.json` / `.claude/settings.local.json`
were read in full before any change. No prior `/bootstrap-control-plane`
command or installer script existed (confirmed via
`.claude/state/completion-matrix.md`'s Phase 5C section, which recorded all
three criteria as `missing`).

This phase does not depend on any user-global (`~/.claude/*`) file: the
installer, its templates, and its proof scripts are entirely repo-local and
were verified to run correctly with `HOME`/`USERPROFILE` pointed at a
nonexistent directory (see Portability Proof below).

## What was added

| Artifact | Purpose | New/extended |
|---|---|---|
| `.claude/scripts/bootstrap_control_plane.py` | The installer itself: stack scan/interview, additive-only idempotent tree scaffold, `CLAUDE.md` facts-block merge, gitignored `autoMemoryDirectory` write, `.gitignore` append, generic `control_plane_check`/`taxonomy`-equivalent validation, and a trivial five-gate smoke workflow | New |
| `.claude/commands/bootstrap-control-plane.md` | Thin orchestrator entrypoint delegating entirely to the script above (two-axis taxonomy) | New |
| `.claude/scripts/phase5c_portability_proof.py` | Builds two fresh, throwaway fixture repos (one Python code stack, one docs-only non-code pipeline), bootstraps each from a fresh copy, restarts every step as an independent subprocess, reconstructs `/status`, and proves no `~/.claude/*` dependency via a hostile `HOME`/`USERPROFILE` environment | New |
| `.claude/scripts/phase5c_context_pressure.py` | Documented, reproducible main-thread context-pressure proxy: reuses the existing always-loaded-instruction-budget measurement and adds a 10-plan dispatcher-load-vs-naive-inline proxy | New |
| `tests/test_bootstrap_control_plane.py` | 18 tests: idempotence, migration/preservation of pre-existing customizations, Windows/POSIX path handling, rollback-safe (resumable) failure, validate/smoke, stack detection | New |
| `tests/test_phase5c_portability.py` | 1 integration test driving the full two-workload portability proof and asserting every sub-result | New |
| `tests/test_phase5c_context_pressure.py` | 2 tests asserting the dispatcher-load proxy stays under the roadmap's 50% target and the always-loaded budget stays measured against real repo files | New |
| `.claude/scripts/control_plane_check.py` | Registered the five new required paths | Extended |
| `.claude/state/roadmap/phase-5c-portability-evidence.json` | Persisted evidence from the two-workload portability proof | New (generated) |
| `.claude/state/roadmap/phase-5c-context-pressure-evidence.json` | Persisted evidence from the context-pressure proxy | New (generated) |

## Why a fresh, generic payload instead of copying this repo's own Phase 0-5B scripts

`phase0_control_plane.py`, `phase5b_verify.py`, `phase5b_lifecycle.py`, etc.
are CCSIF's own historical harness -- built incrementally across Phases 0-5B
and carrying this repo's own naming, SQLite session-tracking, and hook
wiring. Copying them verbatim into an unrelated target repo (a fresh
Node.js app, a docs-only research pipeline) would embed CCSIF-specific
assumptions and phase-numbered names that mean nothing there. The installer
instead generates a **new, stack-agnostic minimal payload**
(`verify_adapter.py`, `lifecycle.py`, `common.py`, generic rule/command/
skill stubs) whose only two stack-specific surfaces are exactly the two the
roadmap names in Phase 5.4: the generated `CLAUDE.md` facts block and the
verify adapter's parsed targets. The verify adapter and lifecycle script
are line-for-line functional ports of this repo's own `phase5b_verify.py` /
`phase5b_lifecycle.py` logic (same parsing rules, same exit-code contract,
same plan-validation rules), renamed and stripped of CCSIF-specific
dependencies (no import of `phase0_control_plane.py`; a small embedded
`common.py` replaces it).

## Idempotence

`scaffold_tree()` is additive-only: `_write_if_missing()` never overwrites
a path that already exists, whether it was created by a prior bootstrap run
or is a hand-authored project customization. `merge_claude_md()` refuses to
touch `CLAUDE.md` at all once a `## Source-of-Truth Commands` section
already exists (any section, not just a bootstrap-generated one).
`bootstrap_local_settings()` mirrors `phase2_memory.bootstrap_local_settings`'s
documented contract: unchanged if `autoMemoryDirectory` already matches,
updated in place (every other key preserved) if it doesn't, and a hard
refusal (no overwrite) if the existing file is not valid JSON.
`update_gitignore()` only appends entries that are not already present.

Measured empirically (`tests/test_bootstrap_control_plane.py::IdempotenceTests`
plus a manual two-run comparison against a scratch temp directory): run 1
created 35 tree paths + `CLAUDE.md` + `settings.json` + `settings.local.json`
+ 2 `.gitignore` lines; run 2 against the same target created 0 new paths
(35/35 preserved), left `CLAUDE.md`/`settings.json` untouched (`"preserved"`
status), reported `autoMemoryDirectory` `"unchanged"`, and added 0 new
`.gitignore` lines.

## Migration behavior for pre-existing `.claude/`

`MigrationPreservesCustomizationTests` proves, against real fixture state
rather than by inspection:

- A pre-existing `.claude/rules/00-operating-doctrine.md` with custom
  content is never overwritten; it is reported as `preserved`, byte-for-byte
  unchanged.
- A pre-existing `CLAUDE.md` that already has *any* `## Source-of-Truth
  Commands` section (not necessarily bootstrap's own) is left untouched;
  the merge is refused wholesale rather than attempting a partial patch
  that could corrupt a hand-authored block.
- A pre-existing `.claude/settings.local.json` with unrelated keys (e.g.
  `env`) keeps those keys; only `autoMemoryDirectory` is added/updated.
- A pre-existing `.claude/settings.local.json` that is not valid JSON is
  left byte-for-byte unmodified and the operation raises rather than
  silently replacing it (fail-closed, matching `phase2_memory`'s own
  documented behavior).

## Windows/POSIX path handling

`autoMemoryDirectory` is always written as `Path(...).resolve()`, which
normalizes to a native absolute path on either platform (verified: this
session's real run produced `C:\Users\...\...` on Windows).
`.claude/hooks/verify.sh` and `.claude/hooks/verify.ps1` are both generated
so either platform has a native entrypoint into the same
`verify_adapter.py`. `.gitignore` appends use explicit `newline="\n"` so a
mixed-newline file is never produced. `PathHandlingTests` asserts the
written `autoMemoryDirectory` is absolute and that a second `.gitignore`
append is a byte-identical no-op.

## Rollback-safe failure behavior

Because every write is additive-only (`_write_if_missing`, the
`bootstrap_local_settings` unchanged/updated/created triad, and
`update_gitignore`'s append-only diff), an interrupted run has no unsafe
state to roll back from: whatever was written is already correct and final,
and whatever was not written is simply picked up by re-running the same
command. `RollbackSafetyTests::test_interrupted_scaffold_can_be_resumed_by_rerunning`
simulates an interruption after only one file was written and proves a
re-run completes the rest without touching the already-written file.
`--dry-run` (`scaffold_tree(..., dry_run=True)`) additionally lets a caller
preview the exact create/preserve split with zero filesystem writes before
committing to a real run.

## Portability proof (two unrelated workloads)

`phase5c_portability_proof.py` builds two throwaway fixture repos per run
(never touching this repo's own `.claude/`):

1. **Code stack**: a Python project (`pyproject.toml`, `tests/test_smoke.py`,
   `src.py`). Stack detection assigns `test_command: "python -m pytest -q"`,
   `lint_command: "python -m ruff check ."`.
2. **Non-code pipeline**: a docs-only research-report workload (`README.md`,
   `report.md` with a cited claim, no manifest of any kind). Stack detection
   assigns `test_command: null`, `lint_command: null` -- the installer never
   fabricates a shell command where none exists; `CLAUDE.md`'s generated
   Source-of-Truth block instead gets a `# rubric` placeholder pointing at
   the adapter's non-code verifier protocol.

For each workload this run drives, as independent fresh subprocesses
(simulating "fresh clone -> new session -> restart"):

`facts` (scan) -> `run` (bootstrap) -> `validate` (fresh subprocess) ->
`smoke` (fresh subprocess, all five gates) -> `lifecycle.py status` (fresh
subprocess, disk-only reconstruction) -- every step after `run` executed
with `HOME`/`USERPROFILE` pointed at
`%TEMP%\does-not-exist-control-plane-home`, a directory that does not
exist. Every step passed for both workloads
(`.claude/state/roadmap/phase-5c-portability-evidence.json`,
`both_passed: true`); `hostile_home_exists: false` for both, proving
correctness never depended on the real machine's home directory existing.
`only_facts_and_verify_targets_differ: true` confirms the two workloads'
generated facts (test/lint commands) diverged while every other generated
file (rules, commands, skills, hooks, scripts) is the identical bootstrap
payload for both.

## Context-pressure measurement (documented proxy)

Live token metering is unavailable in this environment (no Agent SDK
instrumentation hook exposes it here), so per the roadmap's explicit
allowance this phase uses a documented, reproducible proxy
(`phase5c_context_pressure.py`):

1. **Always-loaded instruction budget** (reused from Phase 5A's own
   measurement, re-run live this phase): `CLAUDE.md` (74 lines) +
   `paths: ["**/*"]` rules (`failure-escalation.md`=27,
   `hindsight-memory.md`=12, `persona-profile.md`=11,
   `surgical-density.md`=16) = 140/400 lines, **35%** of budget.
2. **Multi-plan dispatcher-load proxy**: 10 atomic plans (2 tasks each,
   realistic assumption/description text) built in a throwaway fixture.
   The main thread's actual cost is what `/status`
   (`reconstruct_status()`) returns -- plan_id/title/status/task-count only
   -- measured at 1,399 characters (~350 estimated tokens at 4
   chars/token). The naive alternative -- inlining every plan's full
   task/assumption/verification detail into the main thread instead of
   dispatching each `/build` to a fresh subagent context per
   `builder.md`'s `isolation: worktree` -- would cost 8,780 characters
   (~2,195 estimated tokens). Dispatcher load is **15.9%** of the naive
   inline cost, well under the roadmap's ~50% target
   (`within_target: true`).

Both numbers are persisted at
`.claude/state/roadmap/phase-5c-context-pressure-evidence.json` and are
reproducible by re-running `python3 .claude/scripts/phase5c_context_pressure.py`.

## Verification

| Command | Result |
|---|---|
| `python -m py_compile .claude/scripts/bootstrap_control_plane.py .claude/scripts/phase5c_portability_proof.py .claude/scripts/phase5c_context_pressure.py .claude/scripts/control_plane_check.py tests/test_bootstrap_control_plane.py tests/test_phase5c_portability.py tests/test_phase5c_context_pressure.py` | exit 0 |
| `python -m unittest discover -s tests -v` | exit 0, 127 tests (106 prior + 21 new), no regression |
| `python3 .claude/scripts/control_plane_check.py` | `control-plane-check: PASS` (5 new required paths registered) |
| `python3 .claude/scripts/rules_fidelity_check.py` | `rules-fidelity-check: PASS` |
| `python3 .claude/scripts/taxonomy_check.py` | `taxonomy-check: PASS` |
| `python3 .claude/scripts/phase5c_portability_proof.py` | exit 0, `both_passed: true` for both workloads |
| `python3 .claude/scripts/phase5c_context_pressure.py` | exit 0, `within_target: true` (15.9% vs 50% target) |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | exit 0 |
| `git status --short` (post-change) | only intended new/modified paths; pre-existing untracked files (roadmap docs, `.scratch/`, prior-session state dirs) left untouched |

## Exit Criteria Evidence (Phase 5C scope only)

1. **`/bootstrap-control-plane` reproduces the full framework with zero
   reliance on `~/.claude/`** -- `.claude/commands/bootstrap-control-plane.md`
   + `.claude/scripts/bootstrap_control_plane.py`; hostile-`HOME` proof in
   `phase5c_portability_proof.py` (both workloads: `hostile_home_exists:
   false`).
2. **Re-running produces no unintended diff** -- `IdempotenceTests`
   (18 tests, incl. `test_second_run_creates_nothing_new`,
   `test_full_run_command_is_idempotent_end_to_end`); manual two-run
   comparison in this session (35 created -> 0 created, 35 preserved).
3. **The same framework runs unmodified against at least two unrelated
   stacks, only `CLAUDE.md` facts and the verify adapter differing** --
   `phase5c_portability_proof.py`, `both_passed: true`,
   `only_facts_and_verify_targets_differ: true`.
4. **Fresh-clone recovery: bootstrap, restart, reconstruct `/status` from
   disk alone** -- every post-bootstrap step in the proof runs as an
   independent fresh subprocess; `status_reconstruction.result.source ==
   "disk-only"` for both workloads.
5. **Bootstrap tests, migration behavior for pre-existing `.claude/`,
   Windows/POSIX path handling, rollback-safe failure** --
   `tests/test_bootstrap_control_plane.py` (18 tests across
   `IdempotenceTests`, `MigrationPreservesCustomizationTests`,
   `PathHandlingTests`, `RollbackSafetyTests`, `ValidateAndSmokeTests`,
   `StackDetectionTests`).
6. **Main-thread context stays within the roadmap's ~50% target on
   multi-plan work, or an evidenced limitation is reported** --
   `phase5c_context_pressure.py`: 15.9% (dispatcher load vs. naive inline)
   and 35% (always-loaded instruction budget), both under 50%;
   `within_target: true`. No limitation to report for this measurement
   method, but see Remaining Risks for the proxy's own limits.
7. **Report and checkpoint written; matrix, manifest, and ledger updated**
   -- this report; `phase-5c-checkpoint.json`; `completion-matrix.md`
   Phase 5C section; `execution-manifest.json` `phase_5c_completion`
   block; ledger entry.

## Remaining Risks

- **Context-pressure proxy is a proxy, not live metering.** No
  Agent-SDK-level token instrumentation is available in this environment.
  The 15.9%/35% figures are reproducible and grounded in real repo/fixture
  state, but they measure *bytes of durable-state JSON and instruction
  files*, not actual model-context tokens consumed during a live multi-plan
  session with real subagent dispatch. A future phase with token-level
  telemetry (Phase 6's "Measurement" section) should replace this proxy
  with a live measurement rather than assume the proxy's ratio transfers
  exactly.
- **The portability proof's "fresh clone" is a fresh temp-directory copy,
  not a real `git clone` of a pushed remote.** No network operation was
  performed (per the Security and Tool Boundaries scope limits and because
  no remote was designated for this task); the proof exercises every
  file-system-level guarantee a real clone would also exercise (no
  pre-existing state, fresh working directory, restart via independent
  subprocesses), but does not prove `git`-specific behavior (e.g. `.git`
  object integrity across a real clone).
- **Bootstrap's generated framework is a deliberately minimal payload**,
  not a copy of this repo's own mature 61-skill/16-agent/16-rule corpus.
  A target repo bootstrapped today gets the 11 lifecycle commands, 4 new
  discipline skills, the verify adapter, and 4 rule files -- functionally
  complete for the five-gate lifecycle, but it does not receive this
  repo's accumulated Phase 0-5B tooling (session harness, subagent
  tracking, dynamic workflow engine), which remain CCSIF-specific and are
  explicitly Phase 7's "package the stable core as a versioned plugin"
  concern, not Phase 5C's.
- **`smoke` target auto-injection assumes a `\`\`\`bash` fence exists** in
  `CLAUDE.md`'s Source-of-Truth block (`add_smoke_target_to_claude_md`);
  this always holds for bootstrap-generated `CLAUDE.md` files (the template
  always includes the fence) but would silently no-op against a
  pre-existing customized `CLAUDE.md` that used a different fence style --
  in that case `smoke` runs would report `exit_code: 2` (unavailable),
  which is the adapter's correct deterministic behavior for a missing
  target, not a crash.
- Phases 6 and 7 remain unimplemented and are not implicitly validated by
  these Phase 5C changes.

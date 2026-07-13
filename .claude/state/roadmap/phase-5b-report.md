# Phase 5B Report

Status: complete (scoped to Phase 5B: task-agnostic lifecycle commands,
discipline skills, adapters, and durable artifacts — not Phase 5C or
Phase 6)

## Summary

Phase 5A was confirmed complete before this phase started
(`.claude/state/roadmap/phase-5a-report.md`, `phase-5a-checkpoint.json`,
status `complete`; `control_plane_check.py`, `rules_fidelity_check.py`, and
the full `tests/` suite (65 tests) re-verified `PASS` before any change).
`docs/claude-code-control-plane-roadmap-v2.md`, the execution manifest, the
Phase 5A report/checkpoint, the lifecycle contract
(`.claude/rules/20-lifecycle-gates.md`), the skill taxonomy rule
(`.claude/rules/30-skill-taxonomy.md`), the taxonomy linter and its tests,
and current repo facts (`.claude/commands/`, `.claude/skills/`,
`.claude/agents/`, `CLAUDE.md`) were read in full before any change.

Phase 5A left the five-gate lifecycle contract as documentation only, with
no gate commands and no verify adapter. This phase implements both, plus
the four cross-cutting gates, while reusing the existing 57-skill corpus
wherever it already covers a discipline (research, TDD, independent
verification, debugging, commit hygiene) instead of duplicating it.

## What was added

| Artifact | Purpose | New or reused |
|---|---|---|
| `.claude/commands/{brainstorm,grill,research,plan,build,verify,ship,handoff,status,debug,experiment}.md` | Thin orchestrator entrypoints for all 5 gates + 4 cross-cutting flows | New (11 files) |
| `.claude/skills/alignment-interview/SKILL.md` | Gate 1 (open-ended and interrogative alignment interviewing) | New |
| `.claude/skills/atomic-planning/SKILL.md` | Gate 3 (≤3-task plans, assumptions, verification targets, commit boundaries, blocking edges) | New |
| `.claude/skills/session-takeover/SKILL.md` | Durable, repo-committed cold-start handoff (distinct from the pre-existing OS-temp-directory `handoff` skill) | New |
| `.claude/skills/metric-gated-experiment/SKILL.md` | Karpathy AutoResearch loop for `/experiment` | New |
| `research`, `tdd`, `fsv-verify`, `diagnosing-bugs`, `git-automation`, `grill-with-docs` skills | Research citations, TDD, independent verification, debugging, commit hygiene, doc-grounded interrogation | Reused unmodified |
| `.claude/scripts/phase5b_verify.py` | Verify-adapter core: parses `CLAUDE.md`'s own Source-of-Truth Commands block into named targets; runs `full`/`lint`/`test`/`<slug>` with deterministic exit codes (0 pass, 1 fail, 2 unavailable); `rubric`/`citation`/`factcheck` non-code targets return 2 with a protocol pointer | New |
| `.claude/hooks/verify.sh`, `.claude/hooks/verify.ps1` | Platform-appropriate thin entrypoints delegating to `phase5b_verify.py` | New |
| `.claude/scripts/phase5b_lifecycle.py` | Atomic plan create/validate/list, disk-only status reconstruction, cold-start handoff creation, metric-gated experiment start/record/decide | New |
| `tests/test_phase5b_verify.py` | 21 tests: parsing, target resolution, pass/fail/unavailable exit codes, non-code verifier guidance, real-repo integration (including the bash hook wrapper) | New |
| `tests/test_phase5b_lifecycle.py` | 20 tests: plan sizing/validation (9), status reconstruction (4), handoff cold-start (4), experiment keep/revert (7 minus overlap) | New |
| `.claude/rules/20-lifecycle-gates.md` | Updated to point at the now-real command implementations and the verify adapter, replacing a now-stale "command implementations remain future work" sentence | Extended (2 lines net, 39/40 budget) |
| `.claude/scripts/control_plane_check.py` | Registered every new required path; added `check_verify_adapter()` | Extended |

## Why the existing corpus was reused, not duplicated

Per `.claude/rules/30-skill-taxonomy.md`, every new skill's description was
checked against the full existing 57-skill corpus before being written.
Five disciplines the task named already had a fitting project skill:

- **Research citations** — `research` (background agent, primary-source
  citations, single Markdown file under `.claude/state/research/`).
- **TDD** — `tdd` (red-green-refactor, seams, anti-patterns).
- **Independent verification** — `fsv-verify` (PRE/ACT/POST/DIFF protocol);
  the pre-existing `verifier` agent (Phase 3) already implements "never
  trust the builder's narrative" at the agent level.
- **Debugging** — `diagnosing-bugs` (reproduce/isolate/hypothesize/
  instrument/fix/regression-guard, six phases).
- **Commit hygiene** — `git-automation` and `git-commit` (conventional
  commits, human-confirmation gate on mutating/destructive steps).

Four genuinely new disciplines had no existing skill:

- **Alignment interviewing** — the closest existing skill (`grill-with-docs`)
  requires an already-written design and existing documentation to cite
  against; it cannot run a from-scratch open-ended or interrogative
  requirements interview. `alignment-interview` fills that gap and is used
  in two modes by `/brainstorm` and `/grill`.
- **Atomic planning** — `to-spec` produces a long-form PRD published to an
  issue tracker, not a disk-persisted, three-task-capped, machine-validated
  plan file. `atomic-planning` fills that gap.
- **Durable session handoff** — the existing `handoff` skill explicitly
  writes to the OS temp directory for a casual context-transfer note. The
  lifecycle contract (`20-lifecycle-gates.md`) requires a durable,
  repo-committed artifact under `.claude/state/handoffs/`. Rather than
  changing the existing skill's documented behavior (which callers may rely
  on), `session-takeover` was added as a distinct skill for the distinct
  requirement.
- **Metric-gated experiments** — no skill implemented Karpathy's
  AutoResearch loop (single metric, fixed budget, keep-if-improved/
  revert-if-not); `metric-gated-experiment` fills that gap.

## Verify adapter design

The adapter never hardcodes a language or toolchain. It parses this repo's
own `CLAUDE.md` "## Source-of-Truth Commands" fenced block (`# label`
comment lines above each command) into named targets:

- `full` — every parsed command.
- `lint` — commands whose label matches `lint|rule|format` (this repo's
  `rules` fidelity check is its lint-equivalent; there is no separate
  linter, so the adapter reports exactly what exists rather than
  fabricating a per-file lint step).
- `test` — commands whose label matches `test`; supports `--pattern`,
  appended as `-k <pattern>` to any command containing `unittest discover`,
  for focused runs.
- `<slug>` — any individual parsed command, addressable directly
  (`control-plane`, `rules`, `memory-tests`, `issue-to-pr-tests`).
- `rubric`/`citation`/`factcheck` — non-code verifiers. No shell check can
  judge these; the adapter deterministically returns exit 2 with a pointer
  to the relevant model-invoked protocol (`fsv-verify`'s checklist for
  rubric review, `research`'s completion gate for citation/fact-check)
  rather than fabricating a pass/fail signal.

Exit codes are always one of `0` (pass), `1` (fail), `2` (unavailable —
target not found, non-code verifier, or unparseable `CLAUDE.md`).

A recursion hazard was found and fixed during implementation:
`control_plane_check.py`'s new `check_verify_adapter()` step originally
called the `control-plane` target, which itself shells out to
`control_plane_check.py` — infinite self-recursion. Caught before any test
run completed (two orphaned `python.exe` processes, not a runaway fork
bomb) and fixed by pointing the self-check at the non-recursive `rules`
target instead. The same hazard was independently found and fixed in the
`test_phase5b_verify.py` fixture, whose synthetic "unit tests" command
originally read `python3 -m unittest discover -s tests -v` against the real
repo `tests/` directory — which would re-run the very test invoking it. It
was repointed at a nonexistent `fixture_tests` directory (asserted to fail
fast, not hang).

## Atomic plan validation

`phase5b_lifecycle.create_plan`/`validate_plan_dict` enforce, at creation
time and on re-validation:

- 1-3 tasks per plan (roadmap's GSD-derived sizing evidence); more work
  must become a second plan file connected via `blocking_edges`, never a
  widened single plan.
- At least one explicit assumption (an unstated assumption is a defect per
  `.claude/rules/10-karpathy-guidelines.md`).
- Every task: non-empty `description`, a named `verification.target`, and
  an explicit `commit_boundary` boolean — no implicit defaults.
- `blocking_edges` must reference plan files that already exist on disk.

## Status reconstruction and handoff

`reconstruct_status()` reads only `.claude/plans/*.json` and
`.claude/state/{ledger.md,checkpoints,handoffs,workflows,agents,
experiments}` — no transcript, no in-memory session state — matching the
Phase 2/3/4 "reconstruct from disk" convention this repo already
established. `create_handoff()` mirrors Phase 3's `handoff` pattern:
verification evidence (`{command, exit_code}` pairs) or an explicit
`summary_only` flag is required; a summary is never silently treated as
proof. The written document's `## Verified State` section is either a real
evidence table or an explicit `UNVERIFIED — summary only` marker.

## Metric-gated experiments

`start_experiment`/`record_observation`/`decide_experiment` implement
Karpathy's AutoResearch loop as three separate, ordered steps: a fixed
budget and direction (`higher_is_better`/`lower_is_better`) are declared
before any change; the decision is derived from the latest recorded
observation vs. the baseline, never asserted; a decided experiment cannot
be re-decided (`ExperimentError` on a second `decide` call), and
`.claude/skills/metric-gated-experiment/SKILL.md` requires reverting the
change when the outcome is `revert`.

## Verification

| Command | Result |
|---|---|
| `python -m py_compile .claude/scripts/phase5b_lifecycle.py .claude/scripts/phase5b_verify.py .claude/scripts/control_plane_check.py tests/test_phase5b_lifecycle.py tests/test_phase5b_verify.py` | exit 0 |
| `python -m unittest discover -s tests -v` | exit 0, 106 tests (65 prior + 41 new), no regression |
| `python3 .claude/scripts/control_plane_check.py` | `control-plane-check: PASS` (includes new `check_verify_adapter()` step) |
| `python3 .claude/scripts/rules_fidelity_check.py` | `rules-fidelity-check: PASS` (`20-lifecycle-gates.md` re-validated at 39/40 lines after its edit) |
| `python3 .claude/scripts/taxonomy_check.py` | `taxonomy-check: PASS` (0 cross-invocation violations across 16 commands; 0 duplicate descriptions across 61 skills + 16 commands) |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | exit 0 |
| `git check-ignore -v` against every new Phase 5B path | exit 1 (nothing ignored; all evidence is git-visible) |
| `bash .claude/hooks/verify.sh run control-plane` | exit 0 |
| `bash .claude/hooks/verify.sh run rubric` | exit 2 (deterministic non-code-verifier signal) |
| `bash .claude/hooks/verify.sh run does-not-exist` | exit 2 (deterministic unavailable-target signal) |

## Exit Criteria Evidence (Phase 5B scope only)

1. **Thin project commands for all 11 lifecycle entrypoints, never invoking
   each other** — `.claude/commands/{brainstorm,grill,research,plan,build,
   verify,ship,handoff,status,debug,experiment}.md`; 0 cross-invocation
   violations (`taxonomy_check.py`).
2. **Small reusable skills for the 9 named disciplines** — 4 new
   (`alignment-interview`, `atomic-planning`, `session-takeover`,
   `metric-gated-experiment`) plus 5 reused unmodified (`research`, `tdd`,
   `fsv-verify`, `diagnosing-bugs`, `git-automation`); 0 duplicate
   descriptions.
3. **Main-thread output bounded; substantive artifacts in `.claude/state/`
   or `.claude/plans/`** — every command delegates execution detail to a
   skill/agent/script and writes its durable output to one of those two
   trees; no command inlines a large artifact into its own body.
4. **One code-agnostic verification adapter, platform-appropriate
   entrypoints, stable targets, deterministic exit codes, non-code
   verifiers** — `.claude/hooks/verify.sh` / `.ps1` +
   `.claude/scripts/phase5b_verify.py`; 21 passing tests.
5. **Atomic plan files (≤3 tasks), explicit assumptions, blocking edges,
   per-task verification, commit boundaries** —
   `.claude/scripts/phase5b_lifecycle.py` plan functions; 9 passing tests.
6. **`/status` reconstructs from disk alone** —
   `reconstruct_status()`; 4 passing tests.
7. **`/handoff` produces a cold-start takeover document** —
   `create_handoff()` + `session-takeover` skill; 4 passing tests.
8. **Every command contract, taxonomy rule, adapter failure propagation,
   plan sizing, artifact creation, status reconstruction, handoff cold
   start, and experiment keep/revert behavior tested** — 41 new tests
   (21 verify-adapter, 20 lifecycle), 106 total, 0 regressions.
9. **Report and checkpoint written; matrix, manifest, and ledger
   updated** — this report; `phase-5b-checkpoint.json`;
   `completion-matrix.md` Phase 5B section; `execution-manifest.json`
   `phase_5b_completion` block; ledger entry.

## Remaining Risks

- Phase 5C (`/bootstrap-control-plane` installer, cross-stack proof against
  two unrelated stacks, main-thread context measurement on multi-plan
  work) and Phase 6/7 remain unimplemented; this report does not claim
  them.
- The verify adapter's `lint` target maps to this repo's `rules` fidelity
  check because no separate per-file linter exists here; a repository with
  a real linter would get a more precise `lint` mapping automatically once
  its `CLAUDE.md` names that command with a `lint`/`format`-matching label
  — no adapter code change would be needed, but this repo itself cannot
  demonstrate that precision since it has no such linter.
  `--files`-scoped invocation is accepted by the CLI but has no effect
  beyond running the full matched command, since this repo's commands take
  no file arguments; this is stated in the adapter's behavior, not silently
  assumed to work.
- Two commands (`/build`, `/ship`) describe dispatching to agents
  (`builder`, `pr-reviewer`) and skills (`tdd`, `git-automation`) that were
  not live-invoked end-to-end in this session; their contracts were
  verified statically (frontmatter, taxonomy) rather than by a real
  delegated run, matching the residual-risk pattern Phase 3 already
  recorded for its own agent files.
- The `/experiment` gate's revert step is a documented instruction inside
  `metric-gated-experiment`'s `SKILL.md`, not a script-enforced git action;
  `decide_experiment()` records the decision deterministically, but nothing
  in this phase mechanically verifies that a `revert` decision was actually
  reverted in the working tree.
- Phases 5C, 6, and 7 remain incomplete and are not implicitly validated by
  these Phase 5B changes.

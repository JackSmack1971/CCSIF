# ADR 0001: Phase 5A portable-layout decisions

- Status: accepted
- Date: 2026-07-12

## Context

`docs/claude-code-control-plane-roadmap-v2.md` Phase 5.1 specifies a
canonical `.claude/` layout with numbered operating rules
(`00-operating-doctrine.md`, `10-karpathy-guidelines.md`), a five-gate
lifecycle contract, a two-axis skill taxonomy, and a taxonomy linter. This
repo already had a mature `.claude/rules/` corpus (16 files) and a 57-skill
corpus before Phase 5A started; the task's own instruction was to audit and
consolidate rather than duplicate.

## Decision

1. Keep `.claude/rules/00-core-workflow.md` as the operating-doctrine file
   instead of adding a competing `00-operating-doctrine.md`; it already held
   that role and renaming risked churn with no behavior change. Extended it
   with a Scope Doctrine pointer and a loop-discipline cross-reference
   instead.
2. Add `.claude/rules/10-karpathy-guidelines.md` as new content only for the
   delta not already covered by `surgical-density.md` (assumption-
   surfacing, verify-before-done, metric-gated experiment loops), rather
   than duplicating that file's smallest-change/solution-ladder content.
3. Add `.claude/rules/20-lifecycle-gates.md` documenting the five-gate
   contract (inputs/outputs/artifacts/verification owner) without
   implementing `/brainstorm`, `/plan`, `/build`, etc. as command files —
   per the task's explicit "without yet implementing every command"
   instruction.
4. Add `.claude/rules/30-skill-taxonomy.md` encoding the two-axis rule as
   this repo's existing skills actually use it (skills may carry
   `user-invocable: true` and still be model-invoked discipline modules;
   commands stay pure orchestrators).
5. Build `.claude/scripts/taxonomy_check.py` as a fifth deterministic gate
   (wired into `control_plane_check.py`) instead of a prose-only rule,
   because taxonomy drift is exactly the kind of always-true invariant this
   repo's `failure-escalation.md`/`00-core-workflow.md` convention already
   treats as script-enforced, not review-enforced.
6. Keep `.claude/docs/decision-log.md` (existing, append-only, free-form) as
   the running audit trail and use `docs/adr/` only for structured,
   one-decision-per-file records, per the roadmap's distinct `docs/adr/`
   directory. The two are not duplicates: the decision log is chronological
   narrative, an ADR is a scoped, supersedable record.

## Alternatives considered

- Rename `surgical-density.md` to `10-karpathy-guidelines.md` — rejected;
  that file's response-density content is not Karpathy-guideline content,
  and renaming would have required touching every reference to it for a
  cosmetic gain.
- Skip the linter and rely on the new rule files alone — rejected; this
  repo's own convention (`failure-escalation.md`, `dynamic-workflows.md`)
  already treats must-hold invariants as script-enforced (determinism
  ladder rung 4+), and a taxonomy violation is exactly that kind of
  invariant.

## Consequences

- Adding a command or skill that violates the two-axis rule, duplicates a
  description, or grows always-loaded context past budget now fails
  `control_plane_check.py` immediately instead of surfacing in review.
- The always-loaded budget (400 lines) and root-guidance budget (200 lines)
  are now measured, not assumed; current usage is documented in
  `.claude/state/roadmap/phase-5a-report.md`.
- Phase 5B/5C (bootstrap skill, command implementations for the five gates)
  remain open; this ADR does not claim they are done.

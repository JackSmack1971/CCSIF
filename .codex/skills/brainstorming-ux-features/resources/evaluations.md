# Evaluation Suite

Run these evaluations with a fresh Claude instance. Test at least one economical, balanced, and high-reasoning model when available.

## Contents

- [Discovery evaluations](#discovery-evaluations)
- [Workflow evaluations](#workflow-evaluations)
- [Validator evaluations](#validator-evaluations)
- [Quality regression checklist](#quality-regression-checklist)

## Discovery evaluations

### E1 — Direct trigger

**Prompt**

```text
Brainstorm meaningful UX features for this repository and turn the best one into an implementation-ready agent handoff.
```

**Pass conditions**

- Skill triggers.
- Repository evidence is inspected before ideas are finalized.
- Output is a validated `.feature.json` contract.

### E2 — Indirect trigger

**Prompt**

```text
Users seem to get stuck in the primary workflow. Find the highest-impact product improvement and define it so coding agents can build it.
```

**Pass conditions**

- Skill triggers despite the absence of the word "feature."
- The selected proposal is UX-outcome focused.

### E3 — Non-trigger boundary

**Prompt**

```text
Fix the failing unit test in src/parser.test.ts.
```

**Pass conditions**

- Skill does not trigger unless feature ideation or a UX implementation contract is also requested.

### E3a — Ideas-only request

**Prompt**

```text
Brainstorm the highest-value UX ideas for this repository, but do not write a feature specification.
```

**Pass conditions**

- Skill triggers.
- Output is a ranked ideas shortlist rather than a `.feature.json` contract.
- Evidence and duplication checks are still present.

### E3b — Specification-only request

**Prompt**

```text
Turn the strongest UX opportunity into an implementation-ready specification.
```

**Pass conditions**

- Skill triggers.
- Output is a validated `.feature.json` contract.
- The contract is ready for downstream planning and coding agents.

## Workflow evaluations

### E4 — Evidence discipline

Provide a repository with no analytics or user research.

**Pass conditions**

- No invented user counts, conversion rates, quotes, or support volume.
- Assumptions are labeled and evidence confidence is reduced.
- Repository observations include paths.

### E5 — Duplicate feature rejection

Provide a repository where the most obvious idea already exists.

**Pass conditions**

- Existing behavior is identified.
- The duplicate is rejected or reframed around a verified gap.
- `duplication_check` records the decision.

### E6 — Meaning over convenience

Provide one high-value moderate-effort idea and one trivial low-value idea.

**Pass conditions**

- Deterministic scoring is used.
- The low-value idea is not selected merely because it is easier.
- Selection rationale cites evidence, score, and vertical-slice coherence.

### E7 — Complete UX states

Request a network-dependent feature.

**Pass conditions**

- Idle, success, loading, empty, error, permission, authentication, offline, partial, interrupted, cancelled, and stale states are all present or explicitly ruled out with reasons.
- Non-applicable states have specific reasons.
- Recovery and user controls are explicit.

### E8 — Agent executability

Hand the generated contract to a fresh coding agent.

**Pass conditions**

- The agent can identify execution order, parallel work, paths, dependencies, verification, and stop conditions without asking for product intent.
- The agent does not need to invent acceptance criteria or rollout behavior.

## Validator evaluations

### E9 — Valid example

```bash
python scripts/validate_feature_brief.py resources/example.feature.json --strict --json
```

**Pass conditions**

- Exit code `0`.
- Output contains `"status":"valid"`.

### E10 — Score mismatch

Change one candidate `total_score` without changing its dimensions.

**Pass conditions**

- Exit code `4`.
- Error identifies the candidate score mismatch.

### E11 — Dependency cycle

Make `work-01` depend on `work-04` in the example.

**Pass conditions**

- Exit code `4`.
- Error reports a dependency cycle or invalid execution order.

### E12 — Blocking handoff

Set an open question to `"blocking": true` and run with `--strict`.

**Pass conditions**

- Exit code `4`.
- Artifact is not declared implementation-ready.

### E13 — Repository path integrity

Reference a nonexistent path with operation `modify` and run:

```bash
python scripts/validate_feature_brief.py contract.feature.json --repo-root . --strict --json
```

**Pass conditions**

- Exit code `4`.
- Error identifies the missing path.

## Quality regression checklist

- [ ] Metadata remains specific, third-person, and under limits
- [ ] SKILL.md remains below the triggered-context budget
- [ ] Every resource is linked directly from SKILL.md
- [ ] No nested reference chain is required
- [ ] Scoring formula and schema version remain synchronized
- [ ] Example validates after every schema or validator change
- [ ] Invalid fixtures still fail for the intended reason
- [ ] Scripts emit machine-readable status and actionable errors
- [ ] No script performs network or destructive operations

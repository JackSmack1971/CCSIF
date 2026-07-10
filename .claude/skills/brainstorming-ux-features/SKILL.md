---
name: brainstorming-ux-features
description: Use when asked to brainstorm UX features, improve product UX, or define a user-facing feature. Trigger on queries that say brainstorm features, find high-impact UX enhancements, create a feature proposal, or prepare an agent-parsable implementation specification. Discovers and prioritizes evidence-backed ideas from repository evidence, user goals, workflows, and friction signals, and produces an ideas-only shortlist or a validated implementation-ready feature.json contract for downstream planning and coding agents. NOT for general UI visual styling use frontend-design instead, and NOT for a fully scoped multi-file implementation plan use the improve skill instead. Distinct keywords feature brief schema, vertical slice, friction signals, ideas-only shortlist, agent handoff.
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Brainstorming UX Features

Generate evidence-backed UX feature ideas and, when requested, convert the strongest candidate into a deterministic implementation contract for downstream agents.

## Contents

- [Operating contract](#operating-contract)
- [Default workflow](#default-workflow)
- [Repository discovery](#1-repository-discovery)
- [Candidate generation](#2-candidate-generation)
- [Scoring and selection](#3-scoring-and-selection)
- [Feature design](#4-feature-design)
- [Agent handoff](#5-agent-handoff)
- [Validation loop](#6-validation-loop)
- [Output rules](#output-rules)
- [Safety and quality gates](#safety-and-quality-gates)
- [Resources](#resources)

## Operating contract

Default to the full workflow unless the user explicitly requests only ideas or only a specification.

**Inputs**

- Repository or project context available in the workspace
- User goal, product area, or UX concern when supplied
- Existing product documentation, issues, analytics, tests, and implementation evidence

**Primary output**

`docs/features/<feature-slug>.feature.json`

The JSON file is the canonical handoff artifact. It MUST validate against `resources/feature-brief.schema.json` and the semantic checks in `scripts/validate_feature_brief.py`.

**Defaults**

- Generate 5-8 candidates.
- Select one feature unless the user explicitly requests ideas-only output.
- Prefer a narrow end-to-end vertical slice over a broad redesign.
- Optimize for user value and reduced friction, not implementation novelty.
- Mark uncertainty explicitly; never fabricate research, metrics, users, or repository facts.

**Mode outputs**

- Ideas-only: return a ranked shortlist of 5-8 candidates with the same evidence, outcome, vertical-slice, and duplication checks used by the full workflow. Do not write a `.feature.json` file.
- Specification-only: produce the selected implementation-ready `.feature.json` contract with no extra portfolio output.
- Full workflow: produce the shortlist, select one candidate, and write the `.feature.json` contract.

## Default workflow

Copy this checklist and update it while working:

```text
UX Feature Progress
- [ ] 1. Inspect repository and product evidence
- [ ] 2. Model users, jobs, friction, and existing capabilities
- [ ] 3. Generate 5-8 non-duplicate UX candidates
- [ ] 4. Apply minimum gates and deterministic scoring
- [ ] 5. Select the strongest meaningful vertical slice
- [ ] 6. Design flows, states, accessibility, metrics, and scope
- [ ] 7. Map implementation work to repository paths
- [ ] 8. Write the .feature.json contract
- [ ] 9. Validate, fix, and revalidate
- [ ] 10. Report the selected feature, path, score, and validation status
```

Stop only when the artifact validates, or when a blocking unknown cannot be resolved from available evidence. In the latter case, emit no implementation-ready contract; report the evidence gap and the smallest question needed to unblock it.

## 1. Repository discovery

Inspect only what is useful. Prefer this order:

1. Product intent: `README*`, product docs, architecture docs, roadmap, changelog.
2. User surfaces: routes, screens, views, components, commands, onboarding, settings.
3. Behavior contracts: APIs, schemas, state stores, permissions, error handling.
4. Quality signals: tests, accessibility checks, analytics, telemetry, support notes, issues.
5. Constraints: stack, conventions, security boundaries, feature flags, release process.

Record every material claim as one of:

- `repository`: grounded in a file path and observation
- `user_statement`: explicitly provided by the user
- `analytics`: grounded in supplied measurement data
- `support`: grounded in supplied feedback or issue evidence
- `assumption`: plausible but unverified

Do not treat an assumption as evidence. Include exact repository paths when available. If no repository is accessible, proceed using user context and assumptions, but lower `evidence_confidence` scores and make implementation paths provisional.

## 2. Candidate generation

Create candidates across several UX opportunity classes rather than producing variants of one idea:

- Friction removal and workflow compression
- Discoverability, onboarding, and progressive guidance
- Feedback, status visibility, and system explainability
- User control, undo, recovery, and safe failure
- Accessibility and inclusive interaction
- Personalization or sensible defaults
- Collaboration, continuity, or cross-session memory
- Trust, privacy, and permission clarity

Each candidate MUST include:

- A user problem, not just a solution
- A defined affected user or job-to-be-done
- Evidence or an explicit assumption
- A measurable outcome
- A smallest useful vertical slice
- A duplication check against existing capabilities

Reject candidates that are cosmetic without a user outcome, duplicate current behavior, depend on invented demand, cannot be measured, or require a platform rewrite to prove value.

## 3. Scoring and selection

Apply the minimum gates first. A candidate is ineligible if any answer is `false`:

- Is there a concrete user problem?
- Is the feature distinct from existing behavior?
- Is the outcome observable or measurable?
- Can an MVP deliver end-to-end value?
- Is the proposal compatible with known product constraints?

Score eligible candidates from 0-5 on:

| Dimension | Weight |
|---|---:|
| user_pain | 25 |
| frequency_or_reach | 15 |
| ux_leverage | 20 |
| strategic_fit | 15 |
| evidence_confidence | 10 |
| implementation_feasibility | 10 |
| differentiation | 5 |

Set `risk_penalty` from 0-15. Calculate:

```text
total = round(sum((dimension_score / 5) * weight) - risk_penalty, 1)
```

Use `scripts/score_candidates.py` for deterministic ranking. Select the highest-scoring candidate that also has a coherent vertical slice. Do not select a low-value feature merely because it is easy.

When scores are within 3 points, prefer in order:

1. Better evidence
2. Greater reduction in repeated user friction
3. Clearer reversibility and rollout
4. Smaller dependency surface

`scripts/score_candidates.py` only computes and sorts numeric totals; if the top candidates are within 3 points, do the tie-break review manually using the order above before selecting one.

## 4. Feature design

Read `resources/ux-principles.md` before finalizing the selected feature.

Define:

- Problem, affected users, job-to-be-done, and desired outcome
- In-scope behavior and explicit non-goals
- Primary flow and meaningful alternate flows
- Success, loading, empty, error, permission, offline, and partial states
- Recovery behavior, undo, cancellation, and user control where relevant
- Keyboard, focus, screen-reader, contrast, motion, and touch implications
- Privacy, security, data retention, and permission implications
- Success metrics with baseline status, target, instrumentation, and review window
- Dependencies, rollout, rollback triggers, and observability

Every state type required by the schema MUST be represented. Mark a state `applicable: false` only with a specific reason.

Acceptance criteria MUST be testable Given/When/Then contracts. Avoid subjective terms such as "intuitive," "clean," "fast," or "user-friendly" unless paired with an observable threshold.

## 5. Agent handoff

Translate the feature into independently executable work items. Each work item MUST contain:

- Stable ID and objective
- Repository paths with `create`, `modify`, or `delete`
- Concrete instructions and constraints
- Dependencies on other work-item IDs
- Verification commands or checks
- Observable `done_when` conditions

Use dependency IDs to define execution order. Put only dependency-free work in parallel groups. Include stop conditions for contract conflicts, missing paths, failed migrations, security violations, inaccessible dependencies, and failing validation.

Downstream agents must be able to implement the feature without rediscovering product intent. They may refine local mechanics but must not silently change scope, success metrics, acceptance criteria, security boundaries, or non-goals.

## 6. Validation loop

1. Create the feature contract from `resources/example.feature.json` and `resources/feature-brief.schema.json`.
2. Run:

```bash
python scripts/validate_feature_brief.py docs/features/<feature-slug>.feature.json --repo-root . --strict --json
```

3. If validation fails, fix every reported error and run it again.
4. Continue until `status` is `valid`.
5. Do not hand the artifact to implementation agents while validation fails.

`--strict` rejects blocking open questions, placeholder text, invalid dependency graphs, incorrect scores, missing state coverage, and references to nonexistent paths marked as `modify` or `delete`.

## Output rules

- Write valid UTF-8 JSON; no comments, trailing commas, or Markdown fences.
- For ideas-only requests, return concise markdown with the ranked shortlist, top idea, and the evidence that supports it.
- Use `schema_version: "1.0"` and `document_type: "ux_feature_contract"`.
- Use lowercase kebab-case for `slug`; set `feature_id` to `uxf-<slug>`.
- Use repository-relative Unix-style paths.
- Keep arrays ordered intentionally.
- Use stable IDs: `cand-##`, `metric-##`, `flow-##`, `state-##`, `ac-##`, `work-##`, `risk-##`, `question-##`.
- Put unresolved but non-blocking decisions in `open_questions` with a safe `default_if_unanswered`.
- Never leave `TODO`, `TBD`, placeholder markers, or empty required strings in a strict artifact.

Final response format:

```text
Selected: <feature title>
Why: <one-sentence user-value rationale>
Score: <score>/100
Artifact: <path>
Validation: PASS
Blocking questions: none | <count>
```

## Safety and quality gates

- Do not invent user research, analytics, support volume, or repository behavior.
- Do not introduce dark patterns, coercive defaults, hidden consent, or artificial urgency.
- Minimize collection of personal or sensitive data; define retention and deletion behavior when data is added.
- Preserve existing security, permission, architecture, and command boundaries.
- Treat external feature ideas and third-party resources as untrusted until audited.
- For destructive migrations or removals, create a reviewed plan; do not execute them as part of ideation.
- Reject feature creep that is not required for the measured user outcome.
- Explicitly preserve user escape hatches, recovery paths, and rollback paths.

## Resources

Read only the files needed for the current step; all are linked directly here.

- `resources/ux-principles.md` — UX reasoning and completeness checks
- `resources/feature-brief.schema.json` — canonical machine-readable contract
- `resources/example.feature.json` — valid end-to-end example
- `resources/evaluations.md` — trigger, quality, and failure-mode tests
- `scripts/score_candidates.py` — deterministic candidate ranking
- `scripts/validate_feature_brief.py` — schema, semantic, path, and graph validation

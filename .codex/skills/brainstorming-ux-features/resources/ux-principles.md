---
title: UX Feature Design Principles
version: 2.0
status: active
owner: repository maintainers
last_updated: 2026-07-05
audience:
  - product managers
  - product designers
  - UX researchers
  - content designers
  - engineers
  - reviewers
applies_to:
  - new user-facing features
  - major workflow changes
  - high-risk experiments
  - AI-assisted experiences
  - changes to permissions, personal data, or retention
  - changes to success, failure, or recovery behavior
standards_baseline:
  - WCAG 2.2 AA
  - NIST AI Risk Management Framework
---

# UX Feature Design Principles

Use this standard to scope, write, review, implement, and approve user-facing feature proposals. A proposal is ready only when it defines a real user problem, an end-to-end solution, measurable outcomes, explicit risks, testable accessibility behavior, implementation evidence, and a safe rollout and rollback plan.

## Contents

- [When to use this standard](#when-to-use-this-standard)
- [Normative language](#normative-language)
- [Required feature proposal contract](#required-feature-proposal-contract)
- [Evidence labels and traceability](#evidence-labels-and-traceability)
- [Problem framing](#problem-framing)
- [MVP and scope boundaries](#mvp-and-scope-boundaries)
- [Complete interaction design](#complete-interaction-design)
- [Required state coverage](#required-state-coverage)
- [User control and reversibility](#user-control-and-reversibility)
- [Accessibility requirements](#accessibility-requirements)
- [Trust, privacy, security, and AI-assisted behavior](#trust-privacy-security-and-ai-assisted-behavior)
- [Outcome measurement](#outcome-measurement)
- [Implementation evidence](#implementation-evidence)
- [Rollout, stop conditions, and rollback](#rollout-stop-conditions-and-rollback)
- [Definition of done](#definition-of-done)
- [Feature review cover block](#feature-review-cover-block)
- [Review checklist](#review-checklist)
- [Maintenance and revision history](#maintenance-and-revision-history)

## When to use this standard

Use this standard for:

- A new user-facing feature
- A major change to an existing workflow
- A high-risk or difficult-to-reverse experiment
- An AI-assisted or probabilistic experience
- A feature that collects personal data, expands retention, or requests a new permission
- A change to task completion, system status, failure, recovery, cancellation, or saved progress

A lightweight review may be sufficient for minor visual polish that does not change user decisions, system behavior, permissions, data use, accessibility, or task completion. Document why the full standard does not apply.

## Normative language

- **Must** indicates a release-blocking requirement.
- **Should** indicates the preferred approach. Deviations require a written rationale.
- **May** indicates an optional practice.

## Required feature proposal contract

Every proposal must contain the following sections. Use `not applicable` only with a specific explanation.

1. Feature identity and owner
2. Target audience and primary job to be done
3. Problem statement and evidence
4. Proposed MVP and explicit non-goals
5. Primary, alternate, and failure flows
6. State coverage
7. Accessibility acceptance criteria
8. Trust, privacy, security, and AI behavior
9. Outcome, diagnostic, and guardrail metrics
10. Implementation seams and dependencies
11. Risks, rollout, stop conditions, and rollback
12. Completion evidence and open questions

## Evidence labels and traceability

Separate claims into:

- **Fact:** grounded in repository evidence, supplied research, analytics, policy, direct observation, or an attributable user statement
- **Inference:** a reasoned conclusion drawn from one or more facts
- **Assumption:** unverified and explicitly marked for validation

Do not turn an assumption into a metric, frequency claim, user quote, or statement of user intent.

Every material fact must include an evidence note or stable link. Every inference must identify the facts that support it. Every assumption must include an owner and validation plan when it can materially affect scope, risk, or success criteria.

Use this format:

```yaml
claim: "<claim being used to make a product decision>"
classification: fact | inference | assumption
source: "<document, repository path, analytics view, interview, or policy>"
source_date: "YYYY-MM-DD or unknown"
owner: "<person, team, or role>"
confidence: high | medium | low
decision_impact: "<what changes if this claim is wrong>"
validation_plan: "<required for material assumptions>"
```

## Problem framing

A meaningful feature changes an observable user outcome. Frame the problem as:

```text
When <context>, <user> struggles to <job> because <friction>, causing <observable cost>.
```

The problem statement must identify:

- The target user or audience segment
- The context in which the problem occurs
- The job the user is trying to complete
- The observed friction or failure
- The observable user or business cost
- The evidence supporting the claim
- What remains unknown

Do not begin with a preferred solution. Describe the problem in terms that allow more than one credible solution to be considered.

## MVP and scope boundaries

The MVP must let one target user complete one valuable job end to end. It must include the smallest interface, behavior, content, state handling, instrumentation, and verification needed to learn whether the user outcome improved.

An MVP must define:

- The single primary audience
- The single primary job
- The entry point and completion point
- The minimum useful behavior
- Required instrumentation
- Acceptance criteria
- Explicit non-goals
- Deferred capabilities and the reason for deferral

Reject infrastructure-only MVPs unless the infrastructure itself creates an observable user benefit. Internal capability is an implementation milestone, not a user outcome.

## Complete interaction design

For each primary user action, specify:

- Trigger and entry point
- Information shown before commitment
- User action and system response
- Progress, latency, and background-activity feedback
- Success confirmation
- Failure explanation and recovery
- Cancellation, undo, correction, or reversal where reasonable
- Persistence and cross-session behavior
- Return-after-time-away behavior
- Authentication or permission barriers
- Help and escalation paths

Include at least:

- One primary success flow
- One alternate flow
- One recoverable failure flow
- One unrecoverable or blocked flow when applicable

A flow is incomplete if a downstream implementer must invent product behavior to finish it.

## Required state coverage

For this skill package, the validation scope is the full state set below. Use the state section to record the trigger, experience, and recovery for each applicable state; capture the detailed actions, persistence, analytics, and verification in the surrounding proposal sections rather than repeating them in every state entry:

- `idle`
- `loading`
- `success`
- `empty`
- `error`
- `permission`
- `authentication`
- `offline`
- `partial`
- `interrupted`
- `cancelled`
- `stale`

For each non-applicable state, explain why it cannot occur or why separate handling is unnecessary.

Use a state matrix:

| State | Trigger | What the user sees | Available actions | Persistence | Instrumentation | Verification |
|---|---|---|---|---|---|---|
| `<state>` |  |  |  |  |  |  |

## User control and reversibility

Prefer defaults that are visible, understandable, and reversible.

Avoid:

- Forced opt-ins
- Hidden consequences
- Irreversible actions without confirmation
- Ambiguous system status
- Surprise background activity
- Preselected consent for optional data use
- Blocking users from exporting, undoing, cancelling, correcting, or deleting their work without necessity
- Designs that make refusal materially harder than acceptance

The proposal must state:

- Which actions are reversible
- Which actions are irreversible and why
- What confirmation is required
- How cancellation behaves
- What happens to partial work
- How users revoke permissions or consent
- How users export, correct, or delete relevant data

## Accessibility requirements

Accessibility is part of scope, design, implementation, testing, and completion evidence. Align the feature with the current WCAG 2.2 AA baseline and any stricter repository or platform requirements.

Acceptance criteria must describe observable behavior rather than claim generic compliance.

Review at minimum:

- Full keyboard access without a keyboard trap
- Logical focus order
- Visible focus indicators
- Focus that is not fully obscured by sticky or overlapping content
- Focus restoration after dialogs, menus, route changes, errors, and asynchronous updates
- Semantic names, roles, values, states, and relationships
- Accessible status messages and announcements
- Headings, labels, and instructions that describe purpose
- Label text that matches or contains the visible control name
- Contrast and non-color cues
- Text resizing, zoom, orientation, and responsive reflow
- Reduced-motion and animation alternatives
- Pointer alternatives and target sizes that meet the applicable WCAG 2.2 requirement
- Error identification, correction guidance, and prevention for consequential actions
- Time limits, interruptions, session expiry, and saved progress
- Consistent placement of repeated help mechanisms
- Avoidance of redundant re-entry within the same process unless required for security or validity
- Authentication paths that do not rely unnecessarily on memory, transcription, puzzles, or cognitive tests
- Screen reader and assistive-technology behavior for critical flows

Accessibility acceptance criteria must identify the expected behavior, test method, supported platforms, and evidence location.

## Trust, privacy, security, and AI-assisted behavior

Users must be able to understand:

- What the system is doing
- Why it needs data, access, or permission
- What data is collected or generated
- Where data goes
- How long data remains
- Who or what can access it
- What can fail, be incomplete, or be wrong
- How to review, correct, revoke, delete, retry, or exit

Require privacy or security review when a feature:

- Collects new personal, sensitive, or regulated data
- Expands data retention or sharing
- Requests a new permission or broader scope
- Changes authentication or authorization behavior
- Automates a meaningful decision or action
- Sends data to a new service or provider
- Generates user-visible output from probabilistic or untrusted inputs
- Can cause financial, legal, safety, reputation, or account-access harm

For AI-assisted behavior, specify:

- The model or capability boundary, when known
- What input context is sent and where
- How uncertainty or limitations are communicated
- Whether sources or provenance can be shown
- Where human review is required
- How users correct or reject output
- What happens when the AI is unavailable or refuses
- A non-AI fallback when the user could otherwise be blocked
- Evaluation, monitoring, and incident-escalation expectations
- Prohibited or unsupported uses

Do not use human-like language or interface cues that conceal automation, overstate certainty, or imply capabilities the system does not have.

## Outcome measurement

Use one primary outcome metric and a small set of diagnostic and guardrail metrics.

Every metric must define:

- Name and purpose
- Exact event, formula, or calculation
- Unit and population
- Inclusion and exclusion rules
- Current baseline or `unknown`
- Target direction or threshold
- Instrumentation location
- Review window
- Data-quality assumptions
- Guardrail against harmful optimization
- Owner and decision rule

Use this format:

```yaml
metric_name: "<name>"
metric_type: primary | diagnostic | guardrail
user_job: "<job represented by the metric>"
definition: "<exact event, formula, or calculation>"
unit: "<unit>"
population: "<included users, sessions, or tasks>"
exclusions: "<exclusion rules>"
baseline: "<value or unknown>"
target: "<direction or threshold>"
instrumentation: "<event names and code or analytics location>"
review_window: "<time period>"
guardrail: "<harm the team must not optimize through>"
owner: "<person, team, or role>"
decision_rule: "<continue, revise, stop, or roll back condition>"
```

Avoid vanity metrics unless they directly represent the intended user job. A metric is invalid if it can improve while the user outcome becomes worse.

## Implementation evidence

Map the proposal to observed repository seams. Prefer existing patterns, components, stores, services, permissions, content surfaces, events, tests, and deployment controls.

The implementation section must identify:

- Components and user-interface surfaces
- Routes, commands, or entry points
- Services, APIs, or providers
- State stores and persistence
- Permissions and capabilities
- Analytics events
- Feature flags or exposure controls
- Tests and verification commands
- Documentation that must change
- Dependencies and migration requirements
- Security, privacy, and accessibility review points

Mark paths as `provisional` when repository access or verification is unavailable. Do not present an inferred path as confirmed.

Do not require downstream agents to infer:

- Scope boundaries
- Product decisions
- State behavior
- Acceptance criteria
- Rollout or rollback behavior
- Security and privacy expectations
- Required tests
- Completion evidence

## Rollout, stop conditions, and rollback

Every proposal must define:

- Launch strategy
- Exposure controls or feature flags
- Eligible and excluded populations
- Monitoring owner
- Success threshold
- Guardrail threshold
- Stop conditions
- Rollback trigger
- Rollback procedure
- User communication requirements
- Data cleanup or migration reversal requirements

If the feature can fail silently or partially, describe how the team will detect the condition and protect affected users.

A rollout plan is incomplete when it says only “monitor after launch.” It must state what will be monitored, by whom, for how long, and what decision follows each threshold.

## Definition of done

A feature proposal is ready for implementation only when:

- The audience and job are explicit
- The problem is user-centered and evidence-labeled
- Material facts are traceable
- Material assumptions have validation plans
- The MVP delivers end-to-end value
- Non-goals prevent scope expansion
- Primary, alternate, and failure flows are complete
- Required states are covered or explicitly ruled out
- User control, recovery, and reversibility are explicit
- Accessibility behavior is observable and testable
- Trust, privacy, security, and AI notes are complete
- Metrics and decision rules are defined
- Repository seams and dependencies are concrete
- Rollout, stop conditions, and rollback are executable
- Completion evidence is named
- Downstream work can proceed without product rediscovery

## Feature review cover block

Use this block at the beginning of a proposal:

```yaml
feature_name: "<name>"
owner: "<person, team, or role>"
status: draft | in_review | approved | superseded
last_updated: "YYYY-MM-DD"
target_audience: "<primary audience>"
job_to_be_done: "<primary job>"
primary_metric: "<metric name>"
release_risk: low | medium | high | critical
accessibility_review_required: true | false
privacy_review_required: true | false
security_review_required: true | false
ai_assisted_behavior: true | false
repository_evidence_available: true | false
```

## Review checklist

### Purpose and evidence

- [ ] Audience and primary job are explicit
- [ ] Problem is user-centered and evidence-labeled
- [ ] Material facts include source notes
- [ ] Material inferences cite their supporting facts
- [ ] Material assumptions include owners and validation plans
- [ ] The feature is not a duplicate of an existing capability

### Scope and interaction

- [ ] MVP delivers one valuable job end to end
- [ ] Non-goals and deferred work prevent scope expansion
- [ ] Primary, alternate, and failure flows are explicit
- [ ] Required states are covered or specifically ruled out
- [ ] Latency, background activity, and system status are legible
- [ ] Recovery, cancellation, correction, and reversal are explicit
- [ ] Persistence and return-after-time-away behavior are defined

### Accessibility and trust

- [ ] Accessibility behavior is observable and testable
- [ ] WCAG 2.2 AA considerations are addressed
- [ ] Repeated help, redundant entry, focus visibility, target size, and accessible authentication are reviewed
- [ ] Data use, permissions, retention, and revocation are legible
- [ ] Required privacy and security reviews are identified
- [ ] AI uncertainty, provenance, review, correction, and fallback behavior are explicit

### Measurement and delivery

- [ ] Primary metric represents the intended user outcome
- [ ] Diagnostic and guardrail metrics are defined
- [ ] Instrumentation and decision rules are concrete
- [ ] Repository paths, dependencies, and verification commands are concrete or marked provisional
- [ ] Risks, rollout, stop conditions, rollback, and ownership are present
- [ ] Completion evidence is named
- [ ] Downstream work can execute without product rediscovery

## Maintenance and revision history

The document owner must review this standard when any referenced baseline changes materially, including accessibility standards, privacy or security requirements, AI governance expectations, or repository delivery practices.

Record substantive changes below:

| Version | Date | Change | Rationale | Owner |
|---|---|---|---|---|
| 2.0 | 2026-07-05 | Added operating scope, evidence traceability, proposal contract, expanded WCAG 2.2 coverage, trust and AI review triggers, rollout controls, templates, and governance metadata | Convert the principles into an executable and reviewable internal standard | Repository maintainers |

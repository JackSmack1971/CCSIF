# Repository Hygiene Issue Contract

Every implementation-plan step maps to one issue and contains the following sections.

## Required title

`[Hygiene] <imperative, atomic outcome>`

The title must describe an outcome, not an audit observation.

## Required body

```markdown
<!-- repository-hygiene-step:<stable-fingerprint> -->

## Objective
<one outcome>

## Context
- Detected stack: ...
- Audit rule(s): ...
- Severity: ...
- Confidence: ...

## Evidence
| Source | Evidence |
|---|---|
| `path:line` or command | deterministic observation |

## Implementation checklist
- [ ] ...

## Acceptance criteria
- [ ] ...

## Verification
```text
<commands or deterministic checks>
```

## Dependencies
- None, or issue-step fingerprints/titles

## Risk and rollback
- Risk: ...
- Rollback: ...

## Non-goals
- ...
```

## Atomicity rules

Group findings only when they:

1. modify the same policy surface or tightly coupled files;
2. share the same rollback boundary; and
3. can be verified by the same completion evidence.

Split findings when they have different owners, permissions, risk tiers, or verification commands.

## Idempotency

The stable HTML marker is the deduplication key. Before creating an issue, search open and closed issues for the exact marker. Never create a duplicate. Closed issues remain authoritative unless the underlying fingerprint changes.

## Quality gates

- Every actionable finding appears in exactly one step.
- Every step has at least one acceptance criterion and one verification check.
- Titles are under GitHub's limit and bodies remain below the API limit.
- Evidence contains no secret values.
- Destructive work is explicitly identified.
- Low-confidence findings require an investigation checkbox before implementation.

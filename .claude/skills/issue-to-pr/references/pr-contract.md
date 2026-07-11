# Issue-to-PR Contract

This is the consumer-side counterpart to `maintaining-repository-hygiene`'s
[issue-contract.md](../../maintaining-repository-hygiene/references/issue-contract.md).
It only applies to issues that carry that skill's stable marker:

```
<!-- repository-hygiene-step:<fingerprint> -->
```

An issue without this marker is out of scope for `scripts/issue_to_pr.py plan`
— it will not appear in the generated plan. Do not hand-edit an issue body to
add a marker; a fabricated fingerprint breaks the audit trail back to the
original finding.

## Branch naming

`hygiene/<fingerprint-prefix-12>-<slugified-title-40>`, e.g.
`hygiene/f9f5c0f38d2b-choose-and-add-an-explicit-repository-license`.
Deterministic from `(fingerprint, title)` alone, so re-running `plan` never
proposes a different branch for the same issue.

## PR idempotency marker

Every PR body opens with:

```
<!-- issue-to-pr-source:#<issue-number> -->
```

Before creating a PR for an issue, search for this marker
(`gh api search/issues -f 'q=repo:<slug> "issue-to-pr-source:#<n>" in:body'`).
If found, the issue already has a PR — record `status: skipped` in the
journal and move on. Never open a second PR for the same issue.

## Destructive issues are skipped, not blocked

The hygiene issue's `## Context` section states:
`Destructive or irreversible risk: Yes — ...` or `No destructive operation is
expected.` When it states `Yes`, `plan` marks the item `destructive-skip` and
excludes it from `order`. This mirrors the constitution's Tier 1 rule that
Protected Areas and destructive/irreversible changes require explicit human
approval before apply — an automated agent should not decide on its own that
a destructive remediation is safe to implement. Surface these items in the
final report so a human can decide whether to implement them by hand or
re-run `plan --issue <n>` after explicitly authorizing that one issue.

## Dependency resolution

The hygiene issue's `## Dependencies` section lists `None` or one token per
line — either a fingerprint or a title fragment of another hygiene issue.
`plan` resolves each token against the full set of open and closed issues
carrying the same label:

- token matches a **closed** issue → dependency satisfied.
- token matches an **open** issue → dependency unsatisfied; item is `blocked`
  with the blocking issue number named in `block_reason`.
- token matches nothing → `blocked` with `status: unknown` so a human can
  investigate rather than silently skipping work.

`order` (the sequence handed to implementation) contains only `ready` items,
sorted so items with fewer unresolved dependencies come first. Re-run `plan`
after merging a PR to unblock anything that depended on it.

## Verification before PR

An issue's `## Verification` section is the acceptance bar. The
implementation-agent must run those exact commands (or the closest
repository-native equivalent when the issue's commands are illustrative) and
paste the real output into the PR body's `## Verification` section. A PR
opened without evidence that verification ran is not compliant with this
contract, regardless of whether the diff looks correct.

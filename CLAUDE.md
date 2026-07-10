<!-- CONSTITUTION:START -->

# Constitution (Immutable)

All self-modifications must be:

- Evidence-driven from traces/metrics only
- Git-tracked with clear rollback path
- Scoped to the minimum change that addresses the observed issue
- Reviewed against Protected Areas (production config, secrets, auth, payments, CI/CD, database migrations)

- Keep changes small and reviewable.
- Keep audit-only tasks read-only: report findings without editing production code.
- Verify real source-of-truth state after any write or external action.

Tier rules:

- Tier 0 changes are generated trace summaries, metrics snapshots, and proposal records that do not alter runtime behavior; they may be created automatically when they are git-trackable and reversible.
- Tier 1 changes require explicit human approval before apply.
- Tier 1 includes edits to this Constitution, permissions, hooks, protected areas, CI/CD deployment workflows, and script-managed ledgers.
- Tier 2 changes are bounded documentation, skill-description, rule-copy, and non-executable workflow metadata edits; they may auto-apply only after passing automated validation.
- Autonomy budget: apply at most five Tier 2 changes per day, change at most thirty lines per auto-applied diff, and pause automatic application after two consecutive reverted self-improvement commits.
  
  <!-- CONSTITUTION:END -->

# Project Claude Instructions

## Project Summary

Describe the repository purpose, architecture, runtime, and business constraints here.

## Source-of-Truth Commands

Update these commands to match the repository:

```bash
# install
npm install

# test
npm test

# lint
npm run lint

# typecheck
npm run typecheck
```

## Read First

Read one matching existing file in a path-scoped area before creating a new file there, so the relevant `.claude/rules/*.md` guidance loads before the write.

## Engineering Rules

- Keep changes small and reviewable.
- Keep audit-only tasks read-only: report findings without editing production code.
- Prefer repository conventions over generic patterns.
- Update tests and docs with behavior changes.
- Verify real source-of-truth state after any write or external action.

## Protected Areas

- Production configuration
- Secrets and credentials
- Database migrations
- Authentication and authorization
- Payment or trading logic
- CI/CD deployment workflows

## PR Expectations

Every PR should include:

- Problem statement
- Change summary
- Verification commands and results
- Risk and rollback notes
- Screenshots or logs when relevant

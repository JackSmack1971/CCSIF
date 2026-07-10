<!-- CONSTITUTION:START -->

# Constitution (Immutable)

All self-modifications must be:

- Evidence-driven from traces/metrics only
- Git-tracked with clear rollback path
- Scoped to the minimum change that addresses the observed issue
- Reviewed against Protected Areas (production config, secrets, auth, payments, CI/CD, database migrations)

Keep changes small and reviewable.  
Do not mutate production code during audit-only tasks.  
Verify real source-of-truth state after any write or external action.

Tier rules:

- Tier 1 changes require explicit human approval before apply.
- Tier 2 changes may auto-apply only after passing automated validation.
  
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

## Engineering Rules

- Keep changes small and reviewable.
- Do not mutate production code during audit-only tasks.
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

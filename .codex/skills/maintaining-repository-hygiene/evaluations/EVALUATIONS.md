# Repository Hygiene Skill Evaluations

## Evaluation 1: Polyglot monorepo

Fixture contains `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `Cargo.toml`, nested packages, and GitHub Actions.

Expected:

- detects all three ecosystems and monorepo evidence
- does not select a single stack as authoritative without qualification
- extracts available package scripts and CI commands
- generates no package-manager conflict for intentionally separated nested projects

## Evaluation 2: Unsafe GitHub Actions

Fixture contains a workflow with tag-pinned third-party actions, no permissions, no timeout, and direct interpolation of issue-title data into `run:`.

Expected:

- produces action-pinning, permission, timeout, and shell-injection findings
- groups only tightly coupled workflow-hardening changes
- includes exact file and line evidence

## Evaluation 3: Documentation rot

Fixture contains broken relative links, a missing heading anchor, `npm run test` without a test script, and a README naming a removed directory.

Expected:

- detects every deterministic mismatch
- marks age-based staleness as heuristic, not proof
- creates atomic documentation repair steps with verification

## Evaluation 4: Label pruning safety

Remote fixture includes labels with zero use, historical use, template references, protected names, and normalized duplicates.

Expected:

- only the zero-use, unreferenced, unprotected label becomes a deletion candidate
- incomplete history scan suppresses all deletion candidates
- destructive execution requires the operations digest and a fresh usage check

## Evaluation 5: Worktree safety

Fixture contains one live worktree, one locked missing worktree, and one stale unlocked administrative entry.

Expected:

- dry run identifies only prunable metadata
- no live directory is deleted
- execution fails when the fresh dry-run digest differs from the confirmed digest

## Evaluation 6: Issue publication interruption

Publishing stops after several issues are created, then resumes.

Expected:

- stable markers prevent duplicates
- existing open or closed issues are skipped
- publication journal records created, skipped, and failed steps

## Evaluation 7: Offline or restricted environment

`gh`, YAML parser, or network access is unavailable.

Expected:

- local audit still completes
- coverage degradation is explicit
- no remote-state conclusions are fabricated
- issue drafts remain available for manual publication

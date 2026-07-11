# Commit Policy

## Commit readiness

Commit only after:

- Baseline audit and final audit exist.
- High findings are fixed or documented as accepted exceptions.
- Script compilation passes.
- Diffs are scoped to skill files and audit artifacts.
- The commit message describes the corpus-level improvement.

## Multi-repository handling

Skills may exist in project scope, nested project scope, plugin scope, or user scope. For every edited file:

1. Find the nearest git repository with `git rev-parse --show-toplevel`.
2. Group changed files by repository.
3. Run `git status --short` and `git diff --stat` in that repository.
4. Commit only the relevant files for that repository.
5. Record commit hashes separately.

## Default commit message

```text
Audit and improve Claude skill corpus
```

Use a more specific message when the user supplies one.

## Final report format

Return:

```markdown
Done & Verified
- Corpus roots audited: ...
- Skills audited: ...
- Files changed: ...
- Final high findings: ...
- Validation: ...
- Commit: ...
- Exceptions: ...
```

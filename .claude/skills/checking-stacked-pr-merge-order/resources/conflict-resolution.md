# Conflict Resolution SOP

Use this only inside the isolated worktree created by `conflict_pass.py prepare`.

## Evidence sequence

For each conflicted path:

1. Read the PR title/body and linked issue when available.
2. Inspect commits unique to the base and head.
3. Inspect the common-ancestor, head, and base index stages.
4. Read callers, tests, schemas, generated sources, and nearby documentation.
5. State both intents before choosing a result.
6. Record the resolution and evidence in `resolution-record.json`.
7. Edit, stage, validate, and inspect the resulting merge commit.

Useful commands:

```bash
git log --left-right --oneline BASE_OID...HEAD_OID
git diff BASE_OID...HEAD_OID -- path
git show :1:path   # common ancestor
git show :2:path   # PR head, current worktree side
git show :3:path   # declared base being merged into the PR head
git diff --cc -- path
git ls-files -u -- path
```

## Resolution record requirements

Every original conflict path needs:

- `diagnosis` — what each side intended and why Git could not combine them.
- `resolution` — the chosen behavior and why it preserves or intentionally supersedes each intent.
- `evidence` — relevant commits, tests, callers, issue text, schemas, or commands.

Do not write vague entries such as `fixed conflict`, `kept both`, or `used ours`.

## Conflict-type guidance

### Content or mode

Reconstruct behavior rather than mechanically combining lines. Verify APIs, error paths, types, and tests. Preserve executable-bit changes only when intentional.

### Add/add

Determine whether both files represent the same concept. Combine into one canonical file only when imports, build configuration, and ownership agree. Otherwise rename or retain both deliberately.

### Modify/delete

Determine whether deletion intentionally retired the behavior. If the behavior remains required, move it to the replacement path or architecture rather than restoring obsolete structure.

### Rename and directory conflicts

Identify the canonical destination from current imports, manifests, build files, and follow-up commits. Apply content changes at that destination and remove obsolete duplicates.

### Generated files and lockfiles

Resolve the source of truth, then run the repository's pinned generator or package manager. Do not hand-merge generated bundles, dependency graphs, or lockfile internals unless the repository explicitly requires it.

### Binary files

Do not splice or concatenate. Select or regenerate the authoritative asset, verify format integrity, and record provenance.

### Submodules

Inspect the submodule repository's commit ancestry. Select a commit containing the intended changes or stop for an owner decision. Never edit a gitlink as text.

### Configuration and migrations

Preserve ordering, uniqueness, backward compatibility, and rollback expectations. Run parsers, schema checks, and migration tests when available.

## Validation selection

Choose the narrowest commands that prove the resolution and the broadest commands reasonably available before publication:

- focused tests for conflicted behavior;
- typecheck or compile for affected packages;
- lint or formatting where enforced;
- generated-file or schema consistency checks;
- broader test suite when the blast radius is shared or unclear.

Encode commands as arrays so no shell interpolation occurs:

```json
{
  "validation_commands": [
    ["python", "-m", "pytest", "tests/test_feature.py", "-q"],
    ["cargo", "test", "-p", "affected-crate"]
  ]
}
```

Use `validation_waiver` only when no executable validation exists. State what was inspected, why no command is available, and the residual risk.

## Prohibited shortcuts

- Whole-tree `ours` or `theirs` selection.
- Deleting tests merely to obtain a pass.
- Disabling hooks, protections, or checks without explicit repository policy.
- Editing the user's original worktree.
- Continuing to downstream branches after a push without rerunning ancestry and conflict planning.
- Claiming completion from GitHub mergeability alone.

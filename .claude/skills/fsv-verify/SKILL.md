---
name: fsv-verify
description: Use when performing any write, mutation, external side effect, GitHub issue update, PR creation, label edit, or deployment action, to run the project-local Full State Verification protocol before and after the change. Trigger on queries that say verify this mutation, confirm the deploy took effect, check the PR state after merging, or run full state verification. Reads authoritative state before acting, performs exactly one intended operation, reads authoritative state again, diffs the expected delta, and halts on mismatch. NOT for read-only inspection with no mutation use plain Read or status commands instead. Distinct keywords authoritative state, expected delta, source of truth, mismatch halt, single intended operation.
when_to_use: Use immediately before and after any write, mutation, or external side effect to prove the expected delta occurred, not for plain read-only inspection.
argument-hint: "(no arguments; wraps the mutation you are about to perform)"
allowed-tools: Read, Bash, Grep, Glob
---

# FSV Verify

Use for every write, mutation, external side effect, GitHub issue update, PR creation, label edit, or deployment action.

## Protocol

1. PRE: read authoritative state.
2. ACT: perform exactly one intended operation.
3. POST: read authoritative state again.
4. DIFF: verify the exact expected delta.
5. HALT: stop on mismatch.

## Checklist

- [ ] PRE: read authoritative state before acting.
- [ ] ACT: perform exactly one intended operation.
- [ ] POST: read authoritative state again.
- [ ] DIFF: verify the exact expected delta.
- [ ] HALT: stop and report on any mismatch.

**Stop condition:** halt immediately when POST state does not match the expected DIFF; do not proceed to a second operation until the mismatch is resolved or explicitly accepted.

Read [references/fsv-checklist.md](references/fsv-checklist.md) for the full pre/post-mutation checklist.

## Project Source-of-Truth Examples

- Files: read file contents from disk.
- Git: `git status --short`, `git diff`, `git rev-parse HEAD`.
- Tests: test output plus file-level evidence.
- GitHub: issue or PR state fetched after mutation.

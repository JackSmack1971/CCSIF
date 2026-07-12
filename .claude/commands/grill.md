# /grill

Gate 1 (Align), interrogative mode. Interrogate a plan or idea until no material ambiguity remains.

## Process

1. Invoke the `alignment-interview` skill in interrogative mode on `$ARGUMENTS`.
2. If a design or plan document already exists and needs doc-grounded stress-testing with citations, layer in the `grill-with-docs` skill.
3. Record every settled decision as an ADR and every new term in `docs/CONTEXT.md` as the session proceeds.
4. Append a ledger entry summarizing resolved and explicitly deferred questions.

## Required output

- Every open question resolved or explicitly deferred with a stated reason
- ADRs for settled architectural decisions
- Ledger entry

## Next gate

Once alignment is settled, the next gate is Research (see `.claude/commands/research.md`) or Plan (see `.claude/commands/plan.md`).

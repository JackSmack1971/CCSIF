# /brainstorm

Gate 1 (Align), open-ended mode. Explore what to build before anything is built.

## Process

1. Invoke the `alignment-interview` skill in open mode on the topic in `$ARGUMENTS`.
2. Propose concrete directions with trade-offs; let the user narrow or blend them.
3. Record settled requirements, assumptions, and success criteria as they crystallize; update `docs/CONTEXT.md` and draft ADRs for decisions that would be expensive to reverse.
4. Append a ledger entry (`.claude/state/ledger.md`) summarizing the outcome.

## Required output

- Requirements, assumptions, and constraints stated explicitly
- Observable success criteria
- Any new `docs/CONTEXT.md` glossary entries or ADR drafts
- Ledger entry

## Next gate

Once alignment is settled, the next gate is Research (see `.claude/commands/research.md`) or, if requirements are already well understood, Plan (see `.claude/commands/plan.md`).

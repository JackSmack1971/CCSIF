# /research

Gate 2 (Research). Investigate a question against primary sources and capture cited findings — never a raw dump.

## Process

1. Invoke the `research` skill on the question in `$ARGUMENTS`; it dispatches a background agent to read primary sources and write a single cited Markdown file.
2. Confirm the findings landed under `.claude/state/research/` with a citation for every claim.
3. Append a ledger entry pointing at the research file.

## Required output

- `.claude/state/research/<topic>.md` with every claim cited to its primary source
- Ledger entry

## Next gate

Once research is captured, the next gate is Plan (see `.claude/commands/plan.md`).

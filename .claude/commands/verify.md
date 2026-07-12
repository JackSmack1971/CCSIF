# /verify

Gate 5a (Verify). Independently re-derive pass/fail from the plan's stated success criteria and the actual diff — never the builder's narrative.

## Inputs

- A plan ID that has completed the Build gate

## Process

1. Dispatch the `verifier` agent with the plan's success criteria and the diff, not the builder's summary.
2. Apply the `fsv-verify` skill's PRE/ACT/POST/DIFF protocol for every mutation the plan claims to have made.
3. Run the plan's declared verification targets directly via `.claude/hooks/verify.sh run <target>` (or `.ps1` on Windows) and record the exact exit codes.
4. For non-code work, use the adapter's `rubric`, `citation`, or `factcheck` targets as a pointer to the corresponding model-judged checklist instead of expecting a shell pass/fail.
5. Mark the plan `verified` only if every declared target passed; otherwise mark it `needs-attention` and report the specific failing target.

## Required output

- Exact commands run and their exit codes
- Verdict: verified / needs-attention, with the specific failing criterion if not verified
- Ledger entry

## Next gate

Once verified, the next gate is Ship (see `.claude/commands/ship.md`).

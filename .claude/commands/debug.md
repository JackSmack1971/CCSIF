# /debug

Cross-cutting. Systematic root-cause protocol: reproduce, isolate, hypothesize, test, fix, regression-guard.

## Process

1. Invoke the `diagnosing-bugs` skill on `$ARGUMENTS`; follow its phases in order (feedback loop, reproduce + minimize, hypothesize, instrument, fix + regression test, cleanup + post-mortem).
2. Do not skip Phase 1 (build a tight, red-capable feedback loop) — jumping to a hypothesis first is the exact failure that skill exists to prevent.
3. Once fixed, run the relevant verification target via `.claude/hooks/verify.sh run <target>` to confirm the regression test is green and the original repro no longer reproduces.
4. Append a ledger entry naming the confirmed root cause.

## Required output

- The tight reproduction command that went red before the fix
- The regression test (or a documented reason no test seam exists)
- Verification adapter result after the fix
- Ledger entry with root cause

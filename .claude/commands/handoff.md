# /handoff

Cross-cutting. Compact the current session into a durable, repo-committed cold-start takeover document.

## Process

1. Invoke the `session-takeover` skill (not the OS-temp-directory `handoff` skill — this gate's artifact must be durable and repo-committed).
2. Gather real verification-command evidence from this session; if none exists, pass the explicit unverified path instead of fabricating evidence.
3. Write the document via `python3 .claude/scripts/phase5b_lifecycle.py handoff-create`.
4. Report the saved path back to the user.

## Required output

- `.claude/state/handoffs/<timestamp>-<id>.md` with session context, verified state (or an explicit unverified marker), next steps, open risks, and pointers to the relevant plan/ledger/checkpoint

## Note

`/handoff` never invokes another command; if the next session should resume a specific gate, name that gate in the "What's Next" section as text, not as a command call.

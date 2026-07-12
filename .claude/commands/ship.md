# /ship

Gate 5b (Verify & Ship). Move a verified plan to a reviewed PR and a recorded checkpoint.

## Inputs

- A plan ID marked `verified`

## Process

1. Refuse to proceed if the plan is not `verified` — Ship never runs ahead of Verify.
2. Use the `git-automation` skill for branch/commit-history hygiene and, with explicit user approval, the push and PR creation steps (these are REMOTE/DESTRUCTIVE per that skill's gate).
3. Dispatch the `pr-reviewer` agent as the adversarial review lens before requesting merge; report blocking issues, non-blocking suggestions, and verification gaps.
4. Once verification and review both pass, record a Phase 0 checkpoint: `python3 .claude/scripts/phase0_control_plane.py compact <session_id> --reason "ship: <plan_id>"`.
5. Mark the plan `shipped` and append a ledger entry with the PR URL and checkpoint ID.

## Required output

- PR URL
- `pr-reviewer` verdict and any blocking issues resolved
- Recorded checkpoint ID
- Ledger entry

## Cross-cutting

Use the session-takeover skill (see `.claude/commands/handoff.md`) if the session ends before shipping completes.

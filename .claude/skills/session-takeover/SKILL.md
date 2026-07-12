---
name: session-takeover
description: Use when compacting the current session into a durable, repo-committed cold-start takeover document under .claude/state/handoffs/ so any fresh agent can reconstruct progress from disk alone, with real verification evidence or an explicit unverified flag. Trigger on queries that say write the lifecycle handoff, hand this off to the next session durably, produce a cold-start takeover doc, close out this session for the control plane. NOT for an ad hoc context-transfer note saved to the OS temp directory for casual continuation use the handoff skill instead. Distinct keywords cold-start, durable, disk-only, verification-evidence, repo-committed.
when_to_use: Use for the lifecycle's cross-cutting /handoff gate, which must write a durable, repo-committed, evidence-backed cold-start document under .claude/state/handoffs/. Do not use for a casual temp-directory context-transfer note; use the handoff skill for that.
argument-hint: "[what the next session should focus on]"
allowed-tools: Read, Bash, Write
---

# Session Takeover

Cross-cutting lifecycle artifact, distinct from the `handoff` skill: that skill writes a casual context-transfer note to the OS temp directory; this skill writes the lifecycle-mandated **durable, repo-committed** cold-start document to `.claude/state/handoffs/`, per `.claude/rules/20-lifecycle-gates.md`.

## Process

- [ ] Gather real verification evidence for this session's work: exact commands run and their exit codes. If none exist, you must pass `summary_only` explicitly — a summary is never silently treated as proof.
- [ ] Call the lifecycle script rather than hand-writing the document, so the required sections and evidence table are structurally enforced:
      ```bash
      python3 .claude/scripts/phase5b_lifecycle.py handoff-create \
        --summary "<session context>" \
        --next-steps "<what the next session should do>" \
        --verification-evidence '[{"command": "...", "exit_code": 0}]' \
        --plan-id <plan_id if applicable> \
        --open-risks "<risks or omit>"
      ```
- [ ] If there is genuinely no verification evidence, use `--summary-only` instead of `--verification-evidence`, and say so in the summary text too.
- [ ] Reference existing plans, ledger entries, and checkpoints by path instead of duplicating their content into the handoff body.

## Checklist

- [ ] Verification evidence is real command/exit-code pairs, or `--summary-only` was passed explicitly
- [ ] The written document lives under `.claude/state/handoffs/`, not the OS temp directory
- [ ] Referenced plan, ledger, and checkpoint paths actually exist
- [ ] No secrets, tokens, or personally identifiable information appear in the document

## Completion gate

Do not consider the handoff complete until the document exists on disk under `.claude/state/handoffs/`, its verification section is either a real evidence table or an explicit `UNVERIFIED — summary only` marker, and its path has been reported back to the user.

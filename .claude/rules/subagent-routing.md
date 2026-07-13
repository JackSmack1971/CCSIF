---
paths:
  - ".claude/agents/**"
  - ".claude/commands/**"
  - ".claude/skills/**"
  - ".claude/workflows/**"
  - ".claude/hooks/**"
  - "CLAUDE.md"
---
# Subagent Routing Rules

- Keep subagent descriptions high-signal: mention target files, task shape, and trigger phrases users are likely to type.
- Prefer narrower descriptions over role slogans; overlapping agent descriptions reduce routing accuracy.
- Scope read-only reviewer agents to advisory findings only, with no implementation authority.
- Writer agents must state their expected prerequisites, such as an existing plan, explicit target paths, or failing-test evidence.
- Writers must be conflict-safe: use `isolation: worktree` in frontmatter (`builder`), or an equally isolating convention documented in the agent's own file (`implementation-agent`'s branch-per-issue). Never let two writer subagents share one working tree unisolated.
- A subagent's own summary is never proof of completion. Before treating delegated work as done, run `python3 .claude/scripts/phase3_agents.py handoff --parent-session-id <id> --agent-id <id> --verification-command "<cmd>" --verification-exit-code <n>`; a summary-only handoff must pass `--summary-only` explicitly and is recorded unverified.
- Use `python3 .claude/scripts/phase3_agents.py list` to reconstruct active/completed delegated work and `sweep` to flag interrupted (stale) workers, instead of opening subagent transcripts.

---
paths:
  - ".claude/agents/**"
  - ".codex/agents/**"
  - ".claude/commands/**"
  - ".codex/commands/**"
  - ".claude/skills/**"
  - ".codex/skills/**"
  - "CLAUDE.md"
---
# Subagent Routing Rules

- Keep subagent descriptions high-signal: mention target files, task shape, and trigger phrases users are likely to type.
- Prefer narrower descriptions over role slogans; overlapping agent descriptions reduce routing accuracy.
- Scope read-only reviewer agents to advisory findings only, with no implementation authority.
- Writer agents must state their expected prerequisites, such as an existing plan, explicit target paths, or failing-test evidence.

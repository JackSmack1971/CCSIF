# Agents

## Purpose
Project-local subagent definitions. This subtree owns the repo's reusable specialized agents.

## Entry Points
- `implementation-agent.md` - isolated issue implementation.
- `pr-reviewer.md` - merge-readiness review.
- `upstream-auditor.md` - audit-only issue discovery.
- `reflect-agent.md` - HINDSIGHT opinion synthesis.

## Contracts & Invariants
- Keep each agent narrowly scoped to one role.
- Keep agent prompts small enough to stay readable and reviewable.
- Keep tool access minimal and role-appropriate.
- Keep implementation agents, review agents, and audit agents separate unless a role merge is explicitly justified.

## Patterns
- Read the agent file before changing it.
- Preserve the current frontmatter conventions and tool lists.
- Keep any supporting context in nearby docs or skills, not inside the agent prompt itself.

## Anti-patterns
- Do not turn an agent into a general-purpose workflow script.
- Do not duplicate long-lived repo policy that belongs in `CLAUDE.md` or `.claude/rules/`.
- Do not widen tools without a specific reason tied to the role.

## Related Context
- Parent node: `../AGENTS.md`
- Directory map: `../README.md`
- Agent docs: `*.md`
- Subagents docs: `../docs/claude-code-docs-2026-07-12-00-15-46/docs/code-claude-com-docs-en-sub-agents-ceb0b8dc.md`

# Agents

## Purpose
Project-local subagent definitions. This subtree owns the repo's reusable specialized agents.

## Entry Points
- `implementation-agent.md` - isolated issue implementation (branch-per-issue, GitHub flow).
- `pr-reviewer.md` - merge-readiness review of a finished GitHub PR.
- `upstream-auditor.md` - audit-only issue discovery.
- `reflect-agent.md` - HINDSIGHT opinion synthesis.
- `scout.md` - read-only research/discovery (Phase 3 catalog).
- `planner.md` - bounded atomic plan proposal (Phase 3 catalog).
- `builder.md` - scoped executor, worktree-isolated (Phase 3 catalog).
- `verifier.md` - independent verifier of a builder/implementation-agent handoff (Phase 3 catalog).

## Roles Not Modeled as Files
- Supervisor/dispatcher: the main Claude Code session itself coordinates subtasks and merges
  results — this is native behavior, not a subagent definition. `.claude/scripts/phase3_agents.py`
  and `.claude/rules/subagent-routing.md` govern how the main session routes and tracks that work.
- Additional reviewer lenses (security/architecture/maintainer): not added. This repo's actual
  content (governance scripts, hooks, docs) has no evidenced recurring need beyond `pr-reviewer`'s
  correctness/merge-readiness lens and the new generic `verifier`; add one only when a real,
  repeated need shows up, per the roadmap's "only lenses justified by the repo" guidance.
- Collaborative agent teams: not used. No task in this repo has shown a genuine need for
  workers to exchange state mid-task; the supervisor + one-way-delegation pattern covers every
  observed case so far.

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

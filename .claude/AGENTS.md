# .claude Control Plane

## Purpose
Repository-local control-plane scaffolding for CCSIF. This subtree defines how agents, rules, hooks, memory, commands, skills, docs, and workflows fit together. It is the first stop for any edit under `.claude/`.

## Entry Points
- `README.md` - directory map for the `.claude` subtree.
- `rules/` - path-scoped behavior rules and control-plane policy.
- `hooks/` - executable gates, guards, and notifications.
- `memory/` - durable HINDSIGHT state and CLI entrypoint.
- `docs/` - reference material and architecture notes.
- `skills/` - reusable workflows and skill definitions.
- `agents/`, `commands/`, `output-styles/`, `workflows/` - agent prompts, slash commands, response styles, and deterministic orchestration.

## Contracts & Invariants
- `CLAUDE.md` remains the only root-level context file; keep any `AGENTS.md` files below the repository root.
- Read the nearest node before changing a child subtree. For example, read `rules/AGENTS.md` before editing rule files and `skills/AGENTS.md` before adding or changing a skill.
- Treat `.claude/rules/`, `.claude/hooks/`, and `.claude/memory/` as live control surfaces, not passive documentation.
- Keep edits narrow and preserve behavior within the live `.claude/` control plane.

## Patterns
- For control-plane changes, update the closest node first, then run the repo's validation for that area.
- For new `.claude/` subtrees, add a child `AGENTS.md` when the subtree owns behavior, hidden invariants, or more than one distinct concern.

## Anti-patterns
- Don't spread identical guidance across multiple nodes when one ancestor can carry it.
- Don't edit rule, hook, or memory behavior without checking the existing README and the nearest path-scoped instruction file.

## Related Context
- Root constitution and Tier rules: `../CLAUDE.md`
- Reference docs node: `docs/AGENTS.md`
- Skills node: `skills/AGENTS.md`

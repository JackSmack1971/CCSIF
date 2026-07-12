# Skills

## Purpose
Reusable task-specific skills and packaged workflows under `.claude/skills/`.

## Entry Points
- `*/SKILL.md` - skill definitions and instructions.

## Contracts & Invariants
- Keep each skill focused on one reusable workflow or domain.
- Read the target `SKILL.md` and any referenced docs before editing a skill.
- Prefer skill-local instructions over repeating the same guidance in parent nodes.
- Keep skill changes aligned with the docs corpus and the repo's control-plane contract.

## Patterns
- Update a skill in place when the behavior changes.
- Add a new skill directory only when the task is reusable and distinct.
- Verify skill changes against the repo's control-plane check and any skill-local self-tests.

## Anti-patterns
- Do not duplicate broad repo policy inside every skill.
- Do not split one workflow across multiple near-identical skills.
- Do not add a new skill when a script or command already covers the behavior.

## Related Context
- Parent node: `../AGENTS.md`

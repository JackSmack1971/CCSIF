---
paths:
  - ".claude/commands/**"
  - ".claude/skills/**"
  - "CLAUDE.md"
---

# Skill Taxonomy (Two-Axis Rule)

- User-invoked commands (`.claude/commands/*.md`) are orchestrators. A
  command may call skills, agents, or scripts; it must never invoke another
  command. Composition across commands happens in the main thread, not by
  one command's body referencing another command.
- Model-invoked skills (`.claude/skills/<name>/SKILL.md`) hold reusable,
  single-purpose discipline. A skill's `description` states one job and one
  explicit non-goal (`NOT for X; use Y instead`), per this repo's existing
  convention. A skill may carry `user-invocable: true` to also be callable
  directly; that does not make it an orchestrator.
- Before adding a skill or command, grep `.claude/skills/*/SKILL.md`
  descriptions and `.claude/commands/*.md` for the same job; extend or
  reference the existing one instead of duplicating it.
- `python3 .claude/scripts/taxonomy_check.py` enforces the no-cross-
  invocation and no-duplicate-description parts of this rule mechanically;
  do not rely on review alone.

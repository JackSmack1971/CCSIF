# Rules

## Purpose
Path-scoped behavior rules for the `.claude/` and `.codex/` control planes. These files define how agents should behave in this repo and which areas are protected.

## Entry Points
- `README.md` - quick index for the rule set.
- `00-core-workflow.md` - first read for general repo workflow.
- `control-plane.md` - live governance for control-plane changes.
- `hindsight-memory.md` - memory-specific operating rules.
- `security.md`, `testing.md`, `subagent-routing.md`, `failure-escalation.md` - domain rules for common edge cases.

## Contracts & Invariants
- Keep each rule file path-scoped with accurate `paths:` frontmatter.
- Prefer one rule file for one concern; don't duplicate the same directive in multiple places.
- Treat rule edits as control-plane changes and verify them with the existing fidelity checks after writing.
- Preserve the distinction between policy, procedure, and reference. Rules are enforceable guidance, not background notes.

## Patterns
- Read the nearest rule file before editing a matching area.
- When adding a rule, put it in the narrowest file whose `paths:` matches the scope.
- Update verification commands whenever the rule set changes behavior.

## Anti-patterns
- Don't broaden a `paths:` selector just to avoid adding a more specific rule.
- Don't encode runtime state or history in rule files.

## Related Context
- Parent node: `../AGENTS.md`
- Root constitution: `../../CLAUDE.md`

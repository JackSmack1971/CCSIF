---
paths:
  - ".claude/rules/**"
---

# Rules

## Purpose
Path-scoped behavior rules for the live `.claude/` control plane. These files define how agents should behave in this repo and which areas are protected.

## Entry Points
- `00-core-workflow.md` - first read for general repo workflow.
- `control-plane.md` - live governance for control-plane changes.
- `hindsight-memory.md` - memory-specific operating rules.
- `security.md`, `testing.md`, `subagent-routing.md`, `failure-escalation.md` - domain rules for common edge cases.

## Contracts & Invariants
- Keep each rule file path-scoped with accurate `paths:` frontmatter.
- Keep one rule file per concern, and duplicate a directive only when a distinct scope needs different guidance.
- Treat rule edits as control-plane changes and verify them with the existing fidelity checks after writing.
- Preserve the distinction between policy, procedure, and reference. Rules are enforceable guidance, not background notes.

## Patterns
- Read the nearest rule file before editing a matching area.
- When adding a rule, put it in the narrowest file whose `paths:` matches the scope.
- Update verification commands whenever the rule set changes behavior.

## Anti-patterns
- Broaden a `paths:` selector only when the broader scope genuinely matches the instruction.
- Keep runtime state and history out of rule files.

## Related Context
- Parent node: `../AGENTS.md`
- Root constitution: `../../CLAUDE.md`

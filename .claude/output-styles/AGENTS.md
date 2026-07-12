# Output Styles

## Purpose
Response-formatting assets for Claude Code. This subtree exists to hold custom output styles that alter how responses are framed, not what the repository does.

## Entry Points
- `*.md` output style files - project or global response-formatting instructions.

## Contracts & Invariants
- Keep output styles narrow and purpose-built.
- Use output styles only for response formatting, tone, or presentation changes.
- Keep repository conventions, commands, and behavioral rules in `CLAUDE.md`, `.claude/rules/`, or workflow/skill/agent files instead.
- Prefer styles that can be selected or removed without changing repository behavior.

## Patterns
- Read the relevant output style file before editing it.
- Keep style instructions short and easy to reason about.
- If a style needs project-specific behavior, keep the behavior in the proper control-plane file and let the style format the response.

## Anti-patterns
- Do not move project policy, commands, or hidden invariants into an output style.
- Do not use output styles as a substitute for rules, hooks, or skills.
- Do not create a style that duplicates the root constitution.

## Related Context
- Parent node: `../AGENTS.md`
- Directory map: `../README.md`
- Output style docs: `../docs/claude-code-docs-2026-07-12-00-15-46/docs/code-claude-com-docs-en-output-styles*.md`

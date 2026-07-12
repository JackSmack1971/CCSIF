# Commands

## Purpose
Single-file slash commands that package focused, user-invoked workflows. This subtree owns the repo's command entrypoints.

## Entry Points
- `create-pr.md` - turn one issue into one PR.
- `review-pr.md` - review one PR for merge readiness.
- `audit-upstream.md` - audit-only issue discovery.
- `control-plane-check.md` - deterministic control-plane validation.

## Contracts & Invariants
- Keep each command narrow, explicit, and readable as a standalone prompt.
- Prefer commands for one-off workflows; move repeatable or multi-file behavior into skills when that reduces drift.
- Keep commands aligned with the live repo surface they describe.
- Avoid hidden side effects, broad automation, or cross-subtree edits in command docs.

## Patterns
- Read the command file before changing it.
- Keep the required input and output sections crisp and machine-readable where possible.
- Use command docs to point at the authoritative file paths and verification commands.

## Anti-patterns
- Do not turn a command into a mini spec for unrelated behaviors.
- Do not duplicate long-lived policy that belongs in `CLAUDE.md` or `.claude/rules/`.
- Do not add implementation logic to command markdown.

## Related Context
- Parent node: `../AGENTS.md`
- Directory map: `../README.md`
- Command docs: `*.md`
- Skills guidance: `../docs/claude-code-docs-2026-07-12-00-15-46/docs/code-claude-com-docs-en-skills-1151358d.md`

# Claude Code Architecture Improvement Playbook

## Default Repair Order

1. Stabilize safety first: settings, permissions, hooks, MCP allowlists.
2. Restore context discipline: root manifest budget, imports, scoped rules.
3. Improve routing: path globs, Read First protocol, rule names.
4. Improve language: affirmative imperatives and measurable criteria.
5. Preserve learning: decision log and promoted memory rules.
6. Validate: deterministic audit plus repository-native checks.

## Root Manifest Pattern

Target root `CLAUDE.md` or `.claude/CLAUDE.md` structure:

```markdown
# Project Claude Operating Guide

## Immutable Boundaries
- Use approved package manager commands listed below.
- Route database access through the repository data layer.
- Request approval before migrations, production configuration changes, or credential handling.

## Read First Protocol
Before creating a new file under a scoped directory, read one nearby existing file in the same directory or matching pattern so path-scoped rules load before writing.

## Rule Index
- Frontend rules: `.claude/rules/frontend.md`
- Backend rules: `.claude/rules/backend.md`
- Testing rules: `.claude/rules/testing.md`

## Verification
Run the smallest reliable check after each change and the full check before final response.
```

Keep detailed coding standards in path-scoped rule files or human docs referenced on demand.

## Path-Scoped Rule Pattern

Use one domain per file:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "packages/server/**/*.ts"
---
# API Rules

- Route persistence through `src/db/query-builder.ts`.
- Validate request payloads at the route boundary.
- Add tests for success, validation failure, and authorization failure paths.
```

Repair rules:

- Add `paths` frontmatter for local domains.
- Quote wildcard globs.
- Split files above 50 lines when domains separate cleanly.
- Keep global rule files rare and explicitly labeled.

## Affirmative Rewrite Pattern

Convert weak prohibitions into target behavior:

| Source pattern | Rewrite target |
| --- | --- |
| Do not use direct SQL in UI | Route database calls through the server data-access layer |
| Never skip tests | Run the named verification command and resolve failures before final response |
| Avoid large CLAUDE.md files | Keep root manifest under 120 lines and extract domain rules |
| Do not edit generated files | Change the source generator and regenerate outputs |

## Hook Hardening Pattern

Use hooks when failure would be expensive. Represent these as examples, then adapt to the repository.

### PreToolUse Destructive Command Gate

Create a script such as `.claude/hooks/prevent_destructive_commands.sh` that reads hook JSON from stdin, detects unsafe Bash command patterns, prints a JSON denial, and exits with status 2.

### Stop Verification Gate

Create a script such as `.claude/hooks/verify_before_stop.sh` that runs the repository's selected verification commands. On failure, print a JSON block with `decision` set to `block` and include the failing command plus concise stderr.

Hook adoption checklist:

```markdown
- [ ] Script exists in `.claude/hooks/` or equivalent committed path.
- [ ] Script has a narrow purpose and deterministic output.
- [ ] Settings reference the script through project settings.
- [ ] Failure mode is clear to the agent.
- [ ] Manual bypass path is documented for maintainers.
```

## MCP Governance Pattern

- Keep allowed MCP servers explicit.
- Use managed-only settings where organization policy requires it.
- Reference MCP tools with fully qualified names such as `Server:tool_name`.
- Keep high-volume tool schemas deferred where possible.
- Record why each server is authorized.

## Memory Promotion Pattern

Promote stable findings from local auto-memory into committed files:

```markdown
.claude/docs/decision-log.md
.claude/rules/memory-api.md
.claude/rules/memory-testing.md
```

Promotion checklist:

```markdown
- [ ] Finding is stable across sessions.
- [ ] Finding applies to future contributors.
- [ ] Finding is phrased as an operational rule or decision record.
- [ ] Transient or personal details remain local.
- [ ] The committed version is shorter than the source memory note.
```

## Improvement Plan Template

```markdown
# Claude Code Architecture Improvement Plan

## Goal
[One sentence]

## Proposed Edits
| File | Change | Axis | Risk | Stop condition |
| --- | --- | --- | --- | --- |

## Approval Needed
- [ ] Hook or permission changes
- [ ] Deleting or moving files
- [ ] Broad rule rewrites
- [ ] MCP access changes

## Validation
- [ ] Run audit script
- [ ] Run repository-native verification
- [ ] Compare before and after findings
```

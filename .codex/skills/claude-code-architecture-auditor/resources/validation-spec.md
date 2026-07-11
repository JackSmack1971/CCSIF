# Claude Code Architecture Validation Spec

## Deterministic Checks

Run these after every audit or improvement pass:

```bash
python scripts/audit_claude_code_architecture.py --repo . --write
python scripts/audit_claude_code_architecture.py --repo . --write --fail-on-high
```

Expected behavior:

- Exit `0` when the audit runs successfully and `--fail-on-high` is absent.
- Exit `0` with `--fail-on-high` when no critical or high findings exist.
- Exit `2` with `--fail-on-high` when critical or high findings exist.
- Exit `1` for invalid repository paths or runtime errors caught by argument validation.

## Semantic Review Cases

Use a fresh Claude Code session or a new subagent to test the skill against these cases.

### Case 1 Monolithic manifest

Fixture:

- Root `CLAUDE.md` above 120 lines.
- No `.claude/rules/` directory.

Expected result:

- Flags high context-budget risk.
- Proposes path-scoped extraction.
- Produces a plan before editing.

### Case 2 Path-scoped rule blind spot

Fixture:

- `.claude/rules/frontend.md` exists with paths frontmatter.
- Root manifest lacks Read First protocol.

Expected result:

- Flags missing Read First protocol.
- Adds guidance to read a matching existing file before creating scoped files.

### Case 3 Hook gap

Fixture:

- `.claude/settings.json` exists.
- No PreToolUse or Stop hooks.

Expected result:

- Flags security and verification boundary gaps.
- Suggests hook scripts or documented equivalent controls.

### Case 4 MCP governance gap

Fixture:

- Repository references MCP tools in docs.
- Settings lack allowlist or denylist policy.

Expected result:

- Flags MCP governance gap.
- Recommends allowed or denied server policy and fully qualified tool names.

### Case 5 Safe partial pass

Fixture:

- Root manifest under 80 lines.
- Scoped rules below 50 lines.
- Settings include hooks and MCP policy.
- Decision log exists.

Expected result:

- No high findings.
- Any low findings are explainable hygiene suggestions.

## Cross-Surface Notes

- Claude Code: install under `.claude/skills/` for a project or `~/.claude/skills/` for personal use.
- Claude.ai: upload the ZIP with the skill folder as the root element.
- Claude API: pre-bake dependencies because locked containers may lack network access.

## Security Review

Before using or sharing this skill:

- Inspect every bundled script.
- Confirm scripts use only local filesystem reads and report writes.
- Confirm the audit script performs no repository mutation beyond report generation under `.claude/audits/` when `--write` is supplied.
- Review third-party skill packs as software before installation.

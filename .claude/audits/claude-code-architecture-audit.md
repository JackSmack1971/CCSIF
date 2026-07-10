# Claude Code Architecture Audit Report

Repository: `C:\workspaces\CCSIF`
Generated: `2026-07-09T23:03:02`
Status: **PARTIAL**

## Summary

| Severity | Count |
| --- | ---: |
| critical | 0 |
| high | 0 |
| medium | 3 |
| low | 2 |
| info | 0 |

## Findings

| ID | Severity | Axis | File | Evidence | Recommendation | Stop condition |
| --- | --- | --- | --- | --- | --- | --- |
| CCA-001 | medium | context budget | `.claude/rules/constitutional-agent-engineering-rules.md` | 73 lines | Trim or split this rule file to keep path-injected context lean. | Rule file is at or below 50 lines or documented as intentionally global. |
| CCA-002 | medium | context budget | `.claude/rules/surgical-density.md` | 55 lines | Trim or split this rule file to keep path-injected context lean. | Rule file is at or below 50 lines or documented as intentionally global. |
| CCA-003 | medium | MCP governance | `.claude/settings.json` | No allowedMcpServers, deniedMcpServers, or allowManagedMcpServersOnly key found. | Add explicit MCP server governance when external tools are used. | Settings define MCP access policy or document that the project uses no MCP servers. |
| CCA-004 | low | security boundaries | `.claude/settings.json` | disableSkillShellExecution is not true. | Set disableSkillShellExecution true in managed or project settings when inline shell in skills is outside policy. | Policy is explicit in settings or documented as intentionally permissive. |
| CCA-005 | low | memory hygiene | `.gitignore` | No .claude/projects or .claude/memory ignore pattern found. | Exclude accidental local Claude memory paths if this repository stores any local memory artifacts. | Gitignore covers local memory artifacts or repository confirms none are created inside project root. |

## Suggested Validation Loop

```bash
python scripts/audit_claude_code_architecture.py --repo . --write --fail-on-high
# then run repository-native build, test, typecheck, and lint commands
```

# Claude Code Architecture Audit Report

Repository: `C:\workspaces\CCSIF`
Generated: `2026-07-11T21:48:28`
Status: **PARTIAL**

## Summary

| Severity | Count |
| --- | ---: |
| critical | 0 |
| high | 0 |
| medium | 7 |
| low | 1 |
| info | 0 |

## Findings

| ID | Severity | Axis | File | Evidence | Recommendation | Stop condition |
| --- | --- | --- | --- | --- | --- | --- |
| CCA-001 | medium | context budget | `CLAUDE.md` | 85 lines | Review for extraction candidates before the file reaches the hard budget. | Root manifest is at or below 80 lines or documented as intentionally dense. |
| CCA-002 | medium | context budget | `.` | .claude/worktrees/rules-fidelity-check/CLAUDE.md | Use claudeMdExcludes or consolidate nested manifests where inheritance creates bloat or conflict. | Nested manifests are intentionally included or excluded by settings. |
| CCA-003 | medium | path-scoped rules | `.claude/rules/AGENTS.md:1` | No paths key detected in YAML frontmatter. | Add precise paths frontmatter unless this is an intentionally global habit file. | Rule file has paths frontmatter or a clear global label. |
| CCA-005 | medium | context budget | `.claude/settings.json` | Nested CLAUDE.md files exist and settings lack claudeMdExcludes. | Add claudeMdExcludes for irrelevant inherited manifests in complex repositories. | Exclusion policy exists or nested manifests are confirmed relevant. |
| CCA-006 | medium | linguistic architecture | `CLAUDE.md:18` | - Tier 0 changes are generated trace summaries, metrics snapshots, and proposal records that do not alter runtime behavior; they may be created automatically when they are git-trackable and reversible. | Rewrite as an affirmative imperative with a measurable target behavior. | The replacement line states the desired action and includes a verification condition where applicable. |
| CCA-007 | medium | linguistic architecture | `.claude/rules/AGENTS.md:15` | - Prefer one rule file for one concern; don't duplicate the same directive in multiple places. | Rewrite as an affirmative imperative with a measurable target behavior. | The replacement line states the desired action and includes a verification condition where applicable. |
| CCA-008 | medium | linguistic architecture | `.claude/rules/hindsight-memory.md:10` | - Never write to opinion memory without a confidence score. | Rewrite as an affirmative imperative with a measurable target behavior. | The replacement line states the desired action and includes a verification condition where applicable. |
| CCA-004 | low | security boundaries | `.claude/settings.json` | disableSkillShellExecution is not true. | Set disableSkillShellExecution true in managed or project settings when inline shell in skills is outside policy. | Policy is explicit in settings or documented as intentionally permissive. |

## Suggested Validation Loop

```bash
python scripts/audit_claude_code_architecture.py --repo . --write --fail-on-high
# then run repository-native build, test, typecheck, and lint commands
```

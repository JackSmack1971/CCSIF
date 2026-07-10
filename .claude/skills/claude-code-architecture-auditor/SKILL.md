---
name: auditing-ai-agent-config-architecture
description: Use when auditing or improving a repository Claude Code architecture including CLAUDE.md, .claude/rules, settings, hooks, MCP governance, auto-memory hygiene, context budget, path scoped rules, and Read First routing. Trigger on audit Claude Code architecture, refactor .claude, improve CLAUDE.md, optimize Claude Code rules, validate hooks settings. NOT for general code review, app architecture, or ordinary repository hygiene. Requires citing exact file paths under .claude, hooks, or settings before recommending a change.
when_to_use: Use when auditing or improving a repository's Claude Code operating architecture (CLAUDE.md, .claude/rules, settings, hooks, MCP governance, memory hygiene) rather than application code or general repository hygiene.
argument-hint: "[repository root path] [audit-only|improve-in-place|migrate|validate]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Auditing Claude Code Architecture

## Contents

- [Purpose](#purpose)
- [Inputs](#inputs)
- [Fast Path](#fast-path)
- [Audit Axes](#audit-axes)
- [Required Workflow](#required-workflow)
- [Improvement Rules](#improvement-rules)
- [Validation Loop](#validation-loop)
- [References](#references)
- [Output Contract](#output-contract)

## Purpose

Audit and improve a repository's Claude Code operating architecture as source-controlled infrastructure. Focus on context efficiency, deterministic guardrails, path-scoped rule injection, hook verification, MCP governance, memory hygiene, and empirical self-improvement loops.

Use the bundled script for deterministic measurement before proposing edits. Treat generated changes as an improvement plan first, then execute only after the user approves the plan.

## Inputs

Accept any of these inputs:

- Repository root path, default current working directory.
- Existing `.claude/` tree, `CLAUDE.md`, `.claude/settings.json`, `.claude/rules/*.md`, hooks, MCP config, or memory notes.
- User goal such as audit only, improve in place, migrate monolithic CLAUDE.md, validate settings, or create GitHub issues.

If the repository path is unclear, inspect the current directory first. If no Claude Code files exist, produce a bootstrap architecture plan.

## Fast Path

1. Read `resources/audit-sop.md`.
2. Run the deterministic audit:

```bash
python scripts/audit_claude_code_architecture.py --repo . --write --fail-on-high
```

3. Read the generated JSON and Markdown reports from `.claude/audits/`.
4. Rank liabilities by severity, context cost, and routing collision risk.
5. Write `.claude/audits/claude-code-improvement-plan.md` before editing.
6. Ask the user to approve the plan when edits are broad, destructive, security-sensitive, or cross-cutting.
7. Apply approved changes using the playbook in `resources/improvement-playbook.md`.
8. Re-run the audit until high-severity findings are resolved or explicitly deferred.
9. Produce a final verification log using `resources/report-template.md`.

## Audit Axes

Evaluate these axes in order:

1. **Discovery and routing**: root manifest clarity, rule names, file placement, and path-scoped activation.
2. **Context budget**: `CLAUDE.md` below 120 lines, warning above 80 lines, rule files preferably 10 to 50 lines, imports kept globally relevant.
3. **Progressive disclosure**: root manifest as router, one-level references, scoped rules for local domains, minimal unconditional loading.
4. **Path-scoped rules**: YAML frontmatter with quoted path globs, local rules activated by Read operations, explicit Read First protocol.
5. **Settings hierarchy**: project settings committed, local settings ignored, managed and runtime overrides treated as higher precedence, scalar overrides separated from merged permissions.
6. **Security boundaries**: high-risk operations enforced by PreToolUse hooks, not markdown-only policy.
7. **Verification boundaries**: Stop hooks or equivalent scripts run build, tests, typecheck, lint, or project-specific proof before success.
8. **MCP governance**: allowed servers, denied servers, managed-only policy, and fully qualified MCP tool naming when referenced.
9. **Memory hygiene**: durable findings promoted from local auto-memory into committed rules or decision logs, transient local files excluded from git.
10. **Metacognitive improvement**: rank-based A/B comparison of alternatives, decision logging, validate-fix-repeat loops.

## Required Workflow

Copy this checklist into the working notes and check off items as they complete:

```markdown
Task Progress:
- [ ] Locate repository root and Claude Code architecture files.
- [ ] Run deterministic audit script and save JSON plus Markdown outputs.
- [ ] Review every high and medium finding against actual repository intent.
- [ ] Draft an improvement plan with file-by-file edits and stop conditions.
- [ ] Get user approval before broad rewrites, hook changes, permission changes, or deleting files.
- [ ] Apply approved changes in small commits or staged patches.
- [ ] Re-run audit and project verification commands.
- [ ] Record final decisions in `.claude/docs/decision-log.md` or equivalent.
- [ ] Report resolved, deferred, and remaining risks.
```

## Improvement Rules

- Convert bloated root instructions into path-scoped `.claude/rules/<topic>.md` files.
- Keep root `CLAUDE.md` as an operational router, not a manual.
- Put immutable project boundaries and security posture at the top of root context.
- Place immediate verification criteria near the end of task plans and final prompts.
- Encode destructive-operation constraints as hooks or scripts.
- Phrase operational rules as affirmative imperatives with measurable completion criteria.
- Preserve `.claude/settings.local.json` for individual overrides and keep it out of git.
- Use `@import` for globally relevant content only.
- Add Read First guidance before any workflow that creates new files in a path-scoped area.
- Use rank-order comparisons instead of numeric confidence scores for self-audits.

## Validation Loop

After changes:

1. Run the audit script again.
2. Run repository-native checks, selecting the smallest reliable command set first.
3. Compare before and after reports.
4. Confirm that high-severity findings are fixed, intentionally deferred, or converted into tracked issues.
5. Summarize the exact evidence used for completion.

Stop when one of these conditions is true:

- Audit passes with no high-severity findings and user-defined verification passes.
- Remaining high-severity findings require policy decisions outside repository scope.
- User explicitly asks for audit-only output.

## References

Load these only as needed:

- `resources/audit-sop.md` for the full audit checklist.
- `resources/improvement-playbook.md` for migration and repair patterns.
- `resources/report-template.md` for final findings and verification format.
- `resources/validation-spec.md` for deterministic and semantic test cases.
- `scripts/audit_claude_code_architecture.py` for deterministic architecture measurement.

## Output Contract

Return:

1. Executive summary with pass, partial, or fail status.
2. Ranked findings table with severity, axis, file, evidence, and fix.
3. Improvement plan or patch summary.
4. Validation log with commands run and results.
5. Deferred risks and suggested next actions.

# Claude Code Architecture Audit SOP

## Scope

Use this SOP to audit a repository's Claude Code configuration and improvement readiness. The audit covers `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md`, `.claude/settings.json`, `.claude/settings.local.json`, hook scripts, MCP settings, gitignore hygiene, and decision logs.

## Checklist

```markdown
Audit Progress:
- [ ] Confirm repository root and git status.
- [ ] Inventory all Claude Code files.
- [ ] Measure root manifest line count and classify context budget risk.
- [ ] Find unconditional imports and assess whether they are globally relevant.
- [ ] Inspect `.claude/rules/*.md` for YAML frontmatter and path scoping.
- [ ] Confirm Read First guidance exists for file creation under path-scoped rules.
- [ ] Scan instructions for negative phrasing and rewrite candidates.
- [ ] Parse `.claude/settings.json` and `.claude/settings.local.json`.
- [ ] Confirm local settings are ignored by git.
- [ ] Confirm destructive actions are protected by PreToolUse hooks or equivalent policy scripts.
- [ ] Confirm success claims are protected by Stop hooks or equivalent verification scripts.
- [ ] Review MCP allowlists, denylists, and managed-only settings.
- [ ] Inspect memory and decision-log promotion paths.
- [ ] Rank findings by severity, context liability, and collision risk.
- [ ] Draft a plan file before editing.
- [ ] Re-run the audit after changes.
```

## Severity Rules

Assign severity using the highest matching condition.

### Critical

- A committed setting enables broad permission bypass or disables safety controls for the team.
- Hook configuration runs unknown, missing, or clearly destructive scripts.
- MCP configuration exposes sensitive systems without an allowlist or managed-only guardrail.

### High

- Root `CLAUDE.md` exceeds 120 lines.
- `.claude/rules` is absent in a large or multi-domain repository with a bloated root manifest.
- Path-scoped file creation workflows lack Read First guidance.
- Destructive-operation policy exists only as markdown prose.
- Stop verification is absent for repositories where tests, typecheck, or build commands exist.
- `.claude/settings.local.json` appears tracked or absent from `.gitignore` when local settings exist.

### Medium

- Root `CLAUDE.md` exceeds 80 lines.
- Rule files exceed 50 lines or contain multiple unrelated domains.
- Rule files under `.claude/rules` lack `paths` frontmatter without a clear global reason.
- `@import` loads detailed docs that are not globally relevant.
- Negative phrasing appears in operational rules.
- Decision logging or memory promotion path is missing.

### Low

- Naming, formatting, or report structure reduces maintainability but does not affect safety or context routing.
- Optional settings such as `skillListingBudgetFraction` are missing and no evidence of skill bloat exists.

## Evidence Requirements

Every finding needs:

- File path.
- Line number when applicable.
- Evidence snippet or computed metric.
- Why it matters in Claude Code operation.
- Concrete fix.
- Stop condition that proves the fix worked.

## Stop Conditions

Finish the audit only when:

- All high and critical findings are listed with evidence.
- Each proposed edit maps to one audit axis.
- Every security-sensitive change is isolated for user approval.
- The final report states which checks were deterministic and which were semantic review.

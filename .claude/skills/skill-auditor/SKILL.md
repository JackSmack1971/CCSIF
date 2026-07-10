---
name: skill-auditor
description: Use when auditing and improving a local Claude Code skill corpus under .claude/skills or ~/.claude/skills. Trigger on queries that say audit all skills, improve skill corpus, fix SKILL.md metadata, validate skill descriptions, commit skill updates. NOT for reviewing application code or PR diffs use code review or repository hygiene skills instead. Distinct keywords skill corpus, frontmatter, progressive disclosure, evals.json, overtriggering, undertriggering.
when_to_use: Trigger when the user asks to audit, lint, repair, modernize, optimize, validate, benchmark, or commit changes across local Claude Code Agent Skills.
argument-hint: "[--root PATH] [--include-user] [--fix] [--commit] [--message TEXT]"
arguments:
  - options
model: opusplan
effort: high
allowed-tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Grep
  - Glob
  - Bash(python *)
  - Bash(python3 *)
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(git rev-parse *)
  - Bash(git ls-files *)
  - Bash(find *)
  - Bash(mkdir *)
  - Bash(cat *)
  - Bash(ls *)
disallowed-tools:
  - Bash(git push *)
  - Bash(rm -rf *)
  - Bash(curl *)
  - Bash(wget *)
  - WebFetch
  - WebSearch
compatibility: "Claude Code project and user scope skills. Requires Python 3.9+ and git for commits. Uses only Python standard library."
---

# Skill Auditor

## Purpose

Audit the full local Claude Code skill corpus, improve every measurable skill-authoring defect, validate the result, and commit the changes. Optimize for discovery precision, progressive disclosure, deterministic validation, security boundaries, and honest verification.

## Contents

- [Purpose](#purpose)
- [Operating rules](#operating-rules)
- [Default corpus](#default-corpus)
- [Core workflow](#core-workflow)
- [References](#references)
- [Completion gate](#completion-gate)

## Operating rules

- Treat every `SKILL.md`, script, hook, and reference file as executable or instruction-bearing software.
- Preserve domain intent. Never make a generic rewrite that reduces trigger specificity, negative space, safety boundaries, or provenance.
- Use deterministic scripts for inventory, scoring, and validation; use reasoning only for semantic repairs that scripts cannot safely infer.
- Commit only after re-audit shows no high-severity findings introduced by the edits.
- Do not push. Do not delete skill files unless the user explicitly requested pruning.
- If multiple git repositories contain skills, create one commit per repository.

## Default corpus

Scan these roots unless the user narrows scope with `$options`:

1. `${CLAUDE_PROJECT_DIR}/.claude/skills`
2. Any nested `.claude/skills` directories under `${CLAUDE_PROJECT_DIR}`, excluding `.git`, `node_modules`, `.venv`, `venv`, `dist`, `build`, and cache directories
3. `$HOME/.claude/skills` when the request says local, global, user scope, all skills, or includes `--include-user`

If a discovered root is outside any git repository, audit it but do not mutate or commit it unless the user explicitly accepts uncommitted file changes.

## Core workflow

Copy this checklist into the working notes and mark each item done only after the artifact exists and has been inspected.

```markdown
Skill Corpus Audit Progress:
- [ ] Resolve corpus roots and git repositories
- [ ] Run deterministic baseline audit and inspect `skill-audit-report.md`
- [ ] Create `skill-audit-fix-plan.json` for all findings
- [ ] Apply safe mechanical fixes with scripts
- [ ] Manually repair semantic findings that require judgment
- [ ] Re-run audit until high-severity findings are gone or explicitly documented
- [ ] Validate scripts, references, metadata, and generated artifacts
- [ ] Review `git diff --stat` and representative diffs
- [ ] Commit all audited changes with a clear message
- [ ] Report final score, changed files, unresolved limitations, and commit hash
```

### 1. Baseline audit

Run from the repository root:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/audit_skill_corpus.py" --root "${CLAUDE_PROJECT_DIR}" --include-user --output skill-audit-report.json --markdown skill-audit-report.md
```

Open `skill-audit-report.md`. Prioritize findings in this order:

1. Invalid or weak discovery metadata
2. Missing or unsafe frontmatter controls
3. Bloated `SKILL.md` bodies and deep reference chains
4. Missing workflows, checklists, stop conditions, or validation loops
5. Script safety, missing I/O contracts, missing exit codes, or dependency ambiguity
6. Missing evals, verification logs, portability notes, or security notes

### 2. Fix plan

Generate a plan before editing:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/apply_skill_fixes.py" --audit skill-audit-report.json --plan skill-audit-fix-plan.json --dry-run
```

Inspect `skill-audit-fix-plan.json`. Apply only fixes that preserve meaning. For semantic fixes, edit the skill directly using the rubric in `references/audit-rubric.md`.

### 3. Safe mechanical fixes

Apply safe repairs only after the plan is reviewed:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/apply_skill_fixes.py" --audit skill-audit-report.json --plan skill-audit-fix-plan.json --apply
```

Mechanical fixes may add a missing normalized `name`, normalize simple one-line frontmatter, add missing verification placeholders, or create audit artifact directories. They must not invent domain-specific trigger patterns.

### 4. Semantic repair loop

For each skill with medium or high findings:

- Read its `SKILL.md` and only the directly linked reference needed for the finding.
- Rewrite descriptions to lead with activation conditions, include 3 to 5 user-sayable trigger patterns, name negative-space routes, and embed distinctive domain keywords.
- Move bulky edge-case detail from `SKILL.md` into one-level `references/` files.
- Add a concrete checklist with artifact-producing steps and explicit stop conditions.
- Add validation commands or eval specs for fragile behavior.
- Add security and portability notes where scripts, MCP tools, network calls, hooks, or commits are involved.

Use `references/fix-policy.md` before changing behavior or moving content.

### 5. Re-audit and validate

Repeat until clean enough to commit:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/audit_skill_corpus.py" --root "${CLAUDE_PROJECT_DIR}" --include-user --output skill-audit-report.json --markdown skill-audit-report.md
python "${CLAUDE_SKILL_DIR}/scripts/validate_audit_artifacts.py" --audit skill-audit-report.json --max-high 0 --require-markdown skill-audit-report.md
python -m py_compile "${CLAUDE_SKILL_DIR}/scripts/audit_skill_corpus.py" "${CLAUDE_SKILL_DIR}/scripts/apply_skill_fixes.py" "${CLAUDE_SKILL_DIR}/scripts/validate_audit_artifacts.py"
```

If high findings remain because they are intentional, document each in the final response with file path, reason, and risk.

### 6. Commit protocol

Before committing:

```bash
git status --short
git diff --stat
git diff -- .claude/skills
```

Commit only relevant skill-corpus and audit artifacts. Use this default message unless the user supplied `--message`:

```bash
git add .claude/skills skill-audit-report.json skill-audit-report.md skill-audit-fix-plan.json
git commit -m "Audit and improve Claude skill corpus"
```

For user-scope or nested repositories, run the same status diff validation inside each owning repository and commit there separately.

## References

- Rubric and measurable gates: [references/audit-rubric.md](references/audit-rubric.md)
- Fix policy and stop conditions: [references/fix-policy.md](references/fix-policy.md)
- Commit policy and final report format: [references/commit-policy.md](references/commit-policy.md)

## Completion gate

Do not call the task complete until all true statements are supported by artifacts:

- `skill-audit-report.json` exists and parses.
- `skill-audit-report.md` summarizes corpus counts, scores, and findings.
- All high findings are fixed or explicitly documented as accepted exceptions.
- Python scripts compile.
- `git diff --stat` has been inspected.
- A git commit was created for every edited git-tracked skill repository, or the reason no commit could be made is stated.

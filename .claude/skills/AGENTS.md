# Skills Library

## Purpose
Holds all Claude Code Agent Skills for this control-plane repo: one subdirectory per skill (audits, doc generation, hygiene, security review, release/CI workflows, etc.), each invoked via the `Skill` tool or a `/slash-command`. This directory does not contain application code — every skill governs how Claude Code behaves in *other* repositories or in this one; it does not implement product features.

## Entry Points
- `<skill-name>/SKILL.md` - the skill definition: YAML frontmatter (`name`, `description`, `when_to_use`, `allowed-tools`, `arguments`) plus the instructions body. This is the only file Claude Code loads to decide whether/how to trigger the skill.
- `<skill-name>/scripts/` - executable helpers a skill shells out to (e.g. `7axes-audit/scripts/7axes`).
- `<skill-name>/evals/evals.json` - trigger-accuracy and behavior test cases for that skill, used by `skill-auditor` and `skill-creator`.
- `<skill-name>/VERIFICATION.md` - evidence log for skills that make verification claims (e.g. `7axes-audit`).

## Contracts & Invariants
- `description` in frontmatter is the *only* signal Claude Code uses for routing — it must state what the skill does, concrete trigger phrases, an explicit NOT-for exclusion, and required arguments/preconditions (see `disambiguating-skill-descriptions`).
- Skills must not duplicate another skill's triggering conditions; overlapping descriptions reduce routing accuracy (`.claude/rules/subagent-routing.md` applies the same principle to agents).
- A skill that files GitHub issues, writes ledgers, or otherwise mutates shared state must be idempotent and deduplicate against its own ledger (see `7axes-audit`, `maintaining-repository-hygiene`).
- Read-only audit/review skills (`repo-audit`, `dependency-audit`, `observability-audit`, etc.) report findings only — they must not edit the code they are auditing.

## Patterns
To add a new skill:
1. Create `.claude/skills/<kebab-name>/SKILL.md` with frontmatter (`name`, `description`, `when_to_use`, `allowed-tools`).
2. Write a `description` with trigger phrases and an explicit NOT-for boundary against the closest existing skill (grep this directory first — many skills already cover adjacent ground, e.g. `ci-cd-audit` vs `cicd-workflow-audit`, `7axes-audit` vs `7axes-reference`).
3. Add `evals/evals.json` test cases before considering the skill complete (see `skill-creator`, `skill-auditor`).
4. Validate with the `skill-auditor` skill, which lints frontmatter and evals across the whole corpus.

## Anti-patterns
- Don't write a new skill that re-implements a workflow another skill already owns; extend or parameterize the existing one instead.
- Don't give a skill an `allowed-tools` list broader than what its instructions actually use.
- Don't let a skill mutate control-plane files (agents, hooks, rules, settings) without routing through the Tier 0/1/2 approval rules in the root `CLAUDE.md` Constitution.

## Related Context
- Root constitution and Tier rules: `../../CLAUDE.md`
- Ecosystem conventions (rules vs skills vs hooks vs output styles): `../rules/claude-code-ecosystem.md`
- Architecture background: `../docs/AGENTS.md`

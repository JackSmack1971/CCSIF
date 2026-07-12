# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Added the initial `.claude/` control-plane scaffold: agent, command, hook, output-style, rule, skill, and workflow definitions for repository-shared Claude Code behavior
- Added a self-improvement framework: the `CLAUDE.md` project constitution, the `self-improve` skill, expanded constitutional rules, `.claude/settings.json`, and `trace-writer.js` session telemetry
- Added a repository README covering quickstart, architecture, and the agent/command/hook/skill map
- Added the local Claude Code skill corpus (21 project skills) — including a safety-gated `git-automation` reference that requires explicit human confirmation for push, rebase, filter-branch, and release operations — and the `skill-auditor` tooling for auditing and repairing skill-authoring defects
- Added a `/control-plane-check` command and `control_plane_check.py` script, plus `pre-tool-use-guard.js` enforcement, as part of a self-improvement control-plane roadmap for validating proposed self-modifications
- Added 16 further skills to the corpus: release-readiness, CI/CD workflow audit, test strategy, incident response, migration safety, documentation drift, dependency-upgrade planning, API contract review, CI/CD audit, release notes, observability audit, database migration review, API contract docs, contributor onboarding, ADR authoring, and accessibility review

### Changed

- Replaced placeholder no-op `PreToolUse`/`Stop` hooks with real enforcement (Protected Area guard, git hygiene verification)
- Improved documentation and discoverability metadata across the local skill corpus (`when_to_use`/`argument-hint` frontmatter, linked references, tables of contents, script CLI/exit-code documentation), raising the skill-auditor score from 77.62 to 97.33 with zero high or low findings
- Refined the test-strategy and incident-response skill guides based on review feedback
- Rewrote `SKILL.md` router descriptions across 36 skills to a consistent disambiguation standard (literal `Use when`/`Trigger on`/negative-space/`Requires` structure), clearing 48 lint errors and 37 warnings down to zero, and added explicit routing boundaries between the near-duplicate ci-cd-audit/cicd-workflow-audit and database-migration-review/migration-safety skill pairs
- Fixed a false-positive trigger-pattern regex in the skill-corpus auditor and backfilled missing `VERIFICATION.md`/`evals.json`, tables of contents, and completion checklists across 16 skills, raising the corpus audit score from 82.16 to 96.18 with zero high findings

### Fixed

- Fixed `trace-writer.js` misclassifying successful `Read` calls as tool failures when file content merely discussed the words error/exception/traceback, by scoping the keyword scan to `Bash` output only
- Fixed a Mermaid rendering error in the README architecture diagram caused by unquoted special characters in flowchart node labels
- Fixed `architecture.md`/`security.md`/`testing.md` path-scoped rules never activating, because they used a `globs:` key the rule loader doesn't read

### Security

- Removed an untracked rule file that loaded unconditionally on every turn and instructed autonomous self-modification of `.claude/`, relocating its reusable reference content to `.claude/docs` with the operational directives stripped
- Declared an explicit empty MCP server allowlist in `.claude/settings.json` and added `.claude/memory/` and `.claude/projects/` to `.gitignore` as preventive hygiene, closing the two remaining findings from the architecture audit (5 findings down to 3, no high or critical at any point)

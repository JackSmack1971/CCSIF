---
name: release-notes
description: Use when asked to generate release notes, update changelog entries, or draft upgrade and migration notes from repository evidence. Trigger on generate release notes, update the changelog, summarize this release, draft upgrade notes. NOT for assessing whether the repository is actually ready to release; use release-readiness instead. Requires grounding every entry in commits, PR titles, labels, or diffs without overstating unsupported changes.
when_to_use: Use when a release, tag, or merged range needs user-facing release notes or maintainer changelog entries drafted from commits, PR metadata, and diffs, not for judging whether the repository is ready to ship.
argument-hint: "[RANGE|TAG|MILESTONE] [--changelog-path PATH]"
allowed-tools: "Read Grep Glob Bash(git log:*) Bash(git diff:*) Bash(git show:*) Bash(git tag:*) Bash(git describe:*) Bash(gh pr list:*) Bash(gh pr view:*) Bash(gh release view:*) Edit Write"
---

# Release Notes

## Contents

- [Workflow](#workflow)
- [Checklist](#checklist)
- [Evidence Checklist](#evidence-checklist)
- [Breaking-Change Heuristics](#breaking-change-heuristics)
- [Output Guidance](#output-guidance)
- [Rollback and Upgrade Guidance](#rollback-and-upgrade-guidance)
- [Accuracy Rules](#accuracy-rules)

## Workflow

1. **Define the release scope.** Identify the comparison range, tags, branch, PR, milestone, or commit list. If the range is missing, infer the safest available range from local git context and clearly state the assumption.
2. **Collect evidence.** Inspect commits, PR titles, PR labels, changed files, and diffs. Prefer direct diff evidence over commit-message claims. Use hosting metadata when available, but do not invent missing context.
3. **Classify changes.** Group supported changes into these sections, omitting empty sections unless the requested format requires them:
   - Added
   - Changed
   - Fixed
   - Deprecated
   - Removed
   - Security
   - Migration Notes
4. **Detect breaking changes.** Look specifically for API, configuration, schema, CLI, dependency, and behavior changes that could require user action.
5. **Draft outputs.** Produce both user-facing release notes and maintainer-facing changelog entries when requested or useful.
6. **Add operational guidance.** Include upgrade and rollback guidance when the diff indicates migrations, config changes, deployment steps, dependency upgrades, or risky behavior changes.
7. **Calibrate claims.** Avoid overstating changes not supported by diff evidence. Use cautious language for inferred impact and call out uncertainty.

## Checklist

- [ ] Define the release scope (range, tags, branch, PR, or milestone), stating any inferred assumption.
- [ ] Collect evidence from commits, PR metadata, and diffs.
- [ ] Classify changes into Added, Changed, Fixed, Deprecated, Removed, Security, and Migration Notes.
- [ ] Detect breaking changes using the Breaking-Change Heuristics.
- [ ] Draft user-facing release notes and maintainer-facing changelog entries as requested.
- [ ] Add upgrade and rollback guidance when the diff indicates migrations, config, or dependency changes.
- [ ] Calibrate claims against diff evidence before returning output.

## Evidence Checklist

Inspect as many of these as are available in the environment:

- `git log --oneline --decorate <range>` for commit subjects and release boundaries.
- `git diff --stat <range>` for changed-file scope.
- `git diff <range>` for implementation evidence.
- PR titles, labels, descriptions, and linked issues for intent and audience impact.
- Changed docs, examples, migrations, config files, schemas, API definitions, CLI definitions, package manifests, lockfiles, and tests.

When evidence conflicts, prioritize the actual diff and note the discrepancy only if it affects release-note accuracy.

## Breaking-Change Heuristics

Flag a change as breaking or potentially breaking when evidence shows any of the following:

- **API:** Removed or renamed exported symbols, endpoints, methods, fields, request/response shapes, status codes, authentication requirements, or default values.
- **Config:** Renamed, removed, newly required, or semantically changed configuration keys, environment variables, feature flags, or defaults.
- **Schema:** Database migrations, data model changes, required fields, type changes, index or constraint changes, serialization format changes, or irreversible migrations.
- **CLI:** Removed or renamed commands, flags, arguments, output formats, exit codes, prompts, or default behavior.
- **Dependencies:** Major-version upgrades, runtime or platform requirement changes, removed integrations, license-sensitive swaps, or lockfile changes that alter transitive behavior.
- **Behavior:** Changes to validation, permissions, error handling, sorting, pagination, caching, retries, timing, side effects, or compatibility promises.

Use labels such as **Breaking**, **Potentially breaking**, or **Migration required** only when supported by evidence. If unsure, write a short verification note instead of presenting it as fact.

## Output Guidance

### User-facing release notes

Write for users deciding whether and how to upgrade:

- Start with a concise summary of the release impact.
- Group changes by Added, Changed, Fixed, Deprecated, Removed, Security, and Migration Notes.
- Emphasize user-visible behavior, compatibility, and required action.
- Include upgrade steps for migrations, config changes, or manual actions.
- Include rollback guidance when deployment risk exists, such as database migrations, persistent data changes, config rollout, or dependency/runtime changes.
- Avoid internal implementation detail unless it explains user impact.

### Maintainer-facing changelog entries

Write for maintainers auditing what changed:

- Include concise bullets with commit or PR references when available.
- Mention changed files or components when useful.
- Preserve uncertainty and verification needs.
- Separate confirmed breaking changes from candidates needing review.
- Note test, docs, migration, and dependency-only changes when relevant.

## Rollback and Upgrade Guidance

Add this guidance only when applicable and supported by evidence:

- **Upgrade:** list required versions, commands, migrations, config edits, sequencing, feature-flag steps, or compatibility checks.
- **Rollback:** list safe rollback order, data-backup requirements, reversible/irreversible migration warnings, config reverts, dependency pinning, cache invalidation, and monitoring checks.
- **Validation:** suggest smoke tests, health checks, CLI commands, API probes, or data checks that confirm success.

If no special action appears necessary, say that no required migration or rollback steps were identified from the inspected evidence.

## Accuracy Rules

- Do not claim a feature, fix, security impact, or breaking change solely from a vague commit title.
- Do not turn refactors, tests, formatting, or dependency bumps into user-facing changes unless the diff shows user impact.
- Use “appears to,” “likely,” or “needs maintainer confirmation” for inferences.
- Preserve source traceability with commit hashes, PR numbers, file paths, or labels when available.
- Omit empty categories unless a template requires every category.

# Repository Hygiene Audit Rubric

## Table of contents

1. Operating principles
2. Stack and topology discovery
3. Local Git hygiene
4. GitHub label hygiene
5. `.github/` governance and automation
6. Documentation integrity
7. Repository contents and size
8. Remote repository settings
9. Dependency and release hygiene
10. Severity and confidence
11. Official reference basis

## 1. Operating principles

- Treat repository evidence as authoritative; never infer a stack from file extensions alone when manifests, lockfiles, CI, or build files provide stronger evidence.
- Separate observation, recommendation, and execution.
- Never delete labels, worktrees, branches, files, or remote configuration during the audit phase.
- Require a validated plan and a matching digest before any write or destructive command.
- Recheck every destructive precondition immediately before execution.
- Convert each atomic remediation step into exactly one GitHub issue. Group only findings that must be implemented and verified together.
- Preserve uncertainty. A low-confidence heuristic becomes an investigation task, not a factual claim.

## 2. Stack and topology discovery

Collect evidence from:

- package manifests and lockfiles
- workspace and monorepo configuration
- build, test, lint, formatting, type-check, packaging, and documentation configuration
- container, infrastructure-as-code, deployment, and release files
- CI workflow commands
- repository layout and executable entry points

Record:

- languages and ecosystems
- frameworks and runtimes
- package managers and lockfiles
- monorepo/workspace boundaries
- canonical install, build, test, lint, type-check, docs, and release commands
- deployment targets and generated-output directories
- confidence and evidence for every conclusion

Conflicting package managers or lockfiles are findings unless the repository structure clearly justifies them.

## 3. Local Git hygiene

Audit:

- repository root and current worktree state
- linked worktrees and stale administrative metadata
- locked worktrees
- local branches whose upstream is gone
- merged and stale local/remote branches as advisory evidence
- accidental nested repositories
- tracked generated files and ignored-output alignment

Use `git worktree prune --dry-run --verbose --expire now` for discovery. Pruning removes stale administrative records for missing worktrees; it must not be confused with deleting live worktree directories.

## 4. GitHub label hygiene

Inventory all repository labels and historical issue/pull-request usage. A deletion candidate requires all of the following:

- complete history scan within the configured limit
- zero issue and pull-request associations
- no reference in issue forms, workflows, automation, documentation, or policy files
- no protected policy name or prefix
- sufficient age when creation time is available
- a fresh zero-use recheck immediately before deletion

Also detect:

- case-insensitive or punctuation-normalized duplicates
- labels without descriptions
- inconsistent taxonomy prefixes
- labels referenced by templates but missing remotely

Deletion is never part of the audit. It is a separately confirmed operation.

## 5. `.github/` governance and automation

Audit supported locations and content for:

- README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, FUNDING, CITATION
- CODEOWNERS
- pull-request templates
- issue templates and issue forms
- Dependabot configuration for detected ecosystems
- release configuration and changelog automation
- GitHub Actions workflows

Workflow checks include:

- YAML parseability when a parser is available
- explicit least-privilege `permissions`
- full commit-SHA pinning for third-party actions when policy requires it
- job timeouts
- risky `pull_request_target` usage
- untrusted event data interpolated directly into shell commands
- broad write permissions
- missing concurrency controls on deployment/release workflows
- stale action versions only as advisory evidence; do not invent upgrades without verification

Do not require every community file for every private or internal repository. Apply public-project expectations only when visibility and collaboration model justify them.

## 6. Documentation integrity

Audit Markdown and recognized documentation files for:

- broken relative links and images
- missing local anchors
- references to removed paths
- README commands that contradict detected package managers or scripts
- documented scripts or make targets that do not exist
- stale architecture/setup statements compared with the current tree
- docs substantially older than relevant code changes, reported as a review signal rather than proof of rot
- missing owner, maintenance, support, or security routes where applicable

External URL checking is optional and must be identified as degraded when network access is unavailable.

## 7. Repository contents and size

Audit tracked files for:

- generated, cache, virtual-environment, dependency, and build-output directories
- sensitive filenames such as `.env`, private keys, and credential exports
- large binaries and archives
- missing or contradictory `.gitignore` entries
- duplicate lockfiles
- root-directory clutter
- committed editor/OS artifacts
- executable files with suspicious or missing intent

Never print secret contents. Report only path, size, and rule evidence.

## 8. Remote repository settings

When authenticated GitHub access exists, inspect:

- default branch
- issues availability
- branch protection or rulesets
- required reviews and status checks where visible
- merge-method configuration
- automatic head-branch deletion
- repository description, homepage, topics, visibility, archival state, and license metadata
- security-and-analysis features when permissions expose them

A permission-denied response is coverage degradation, not proof that a feature is disabled.

## 9. Dependency and release hygiene

Map detected package ecosystems to Dependabot coverage. Check for:

- update automation coverage for every active manifest directory
- lockfile alignment
- changelog/release notes conventions
- release workflow and tag consistency
- version declarations that disagree across canonical files

Do not run package-manager installation or arbitrary project scripts during a hygiene audit unless the user explicitly expands scope.

## 10. Severity and confidence

Severity:

- `critical`: immediate credential exposure or a repository control likely to permit direct compromise
- `high`: material supply-chain, governance, or destructive-maintenance risk
- `medium`: professional-practice gap likely to cause reliability, maintenance, or contributor friction
- `low`: bounded cleanup, consistency, or documentation debt
- `info`: context or evidence with no implementation step

Confidence:

- `high`: direct, deterministic evidence
- `medium`: strong heuristic with a plausible exception
- `low`: investigation is required before changing anything

## 11. Official reference basis

- GitHub repository best practices: https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories
- Community health files: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions
- CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Security policy: https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository
- Issue forms: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
- Dependabot configuration: https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference
- Secure GitHub Actions use: https://docs.github.com/en/actions/reference/security/secure-use
- Protected branches and rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- Labels: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels
- Large files: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- Git worktrees: https://git-scm.com/docs/git-worktree

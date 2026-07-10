---
name: contributor-onboarding
description: Use when the user asks to onboard contributors, document first-time setup, create or audit a new developer guide, improve developer onboarding, or verify that repository onboarding material is complete. Guides agents to build or audit evidence-backed onboarding material covering repository purpose, architecture, setup, workflows, ownership discovery, safe first issues, tools, environment variables, services, troubleshooting, and fallback paths. Distinct trigger phrases: onboard contributors, first-time setup, new developer guide, developer onboarding.
compatibility: Requires Git and repository read access; documentation updates require repository write access.
disable-model-invocation: true
context: fork
agent: general-purpose
when_to_use: Use to create, improve, or audit contributor onboarding and first-time setup material for a repository.
argument-hint: "[optional target file, audience, or audit-only scope]"
allowed-tools: Read Grep Glob Write Edit Bash(git status) Bash(git status *) Bash(git rev-parse *) Bash(git diff *) Bash(git ls-files *) Bash(find *) Bash(python3 *) Bash(python *)
disallowed-tools: WebSearch WebFetch
---

# Contributor Onboarding

## Contents

- [Purpose](#purpose)
- [Output modes](#output-modes)
- [Procedure](#procedure)
- [Onboarding coverage checklist](#onboarding-coverage-checklist)
- [Evidence rules](#evidence-rules)
- [Safety](#safety)
- [Validation](#validation)
- [Completion report](#completion-report)
- [Troubleshooting](#troubleshooting)
- [Worked examples](#worked-examples)

## Purpose

Build or audit repository onboarding material that lets a first-time contributor move from a clean clone to a successful verification command without guessing. The material must be specific to the repository, grounded in checked-in evidence, and explicit about what to do when setup fails.

Use this skill when requests include phrases such as **"onboard contributors"**, **"first-time setup"**, **"new developer guide"**, or **"developer onboarding"**.

Treat `$ARGUMENTS` as optional plain-language context only. Never interpolate it directly into shell commands, paths, links, or generated content.

## Output modes

Choose the smallest output that satisfies the request:

1. **Audit mode:** If the user asks to review existing onboarding material, produce a findings report in the response unless they request a persistent file.
2. **Update mode:** If an onboarding document already exists and the user asks to improve it, update that document in place.
3. **Create mode:** If no target is specified, create or update the most appropriate contributor-facing document, preferring existing repository conventions in this order:
   - `CONTRIBUTING.md`
   - `docs/CONTRIBUTING.md`
   - `docs/development.md`, `docs/onboarding.md`, or equivalent existing developer guide
   - `README.md` only when it is already the repository's documented setup entry point
4. **Requested-path mode:** If the user names a path, write only that path unless doing so would overwrite unrelated content without explicit permission.

Do not create multiple new onboarding documents unless the user explicitly asks for a documentation set.

## Procedure

### 1. Establish repository boundaries

1. Resolve the repository root:

   ```bash
   git rev-parse --show-toplevel
   ```

2. Run `git status --short` and record pre-existing changes.
3. Identify the target onboarding document according to [Output modes](#output-modes).
4. Read any existing target document fully before editing.
5. Do not stage, discard, or rewrite unrelated user changes.

### 2. Inventory authoritative sources

Use targeted file discovery and reads. Prioritize:

- `README*`, `CONTRIBUTING*`, `docs/**`, `CLAUDE.md`, `AGENTS.md`, and repository-specific rule files.
- Package manifests, workspace manifests, lockfiles, runtime-version files, task runners, Makefiles, justfiles, scripts, devcontainer files, Docker Compose files, and bootstrap scripts.
- CI workflows, test configuration, lint/format/type-check configuration, release workflows, and deployment configuration.
- `CODEOWNERS`, maintainers files, issue templates, pull-request templates, security policy, support policy, and ownership documentation.
- `.env.example`, sample configuration, local service manifests, seed data scripts, migration tooling, and emulator configuration.
- Representative source and test files only when higher-level configuration does not reveal conventions.

Prefer `git ls-files`, `Glob`, and targeted `Grep` searches over broad recursive scans.

### 3. Reconstruct the clean-clone path

Document the shortest supported path from a clean clone to the first successful verification command:

1. Required runtime versions and package managers.
2. Dependency installation command.
3. Required environment files and variables, using examples or placeholders only.
4. Required local services, containers, databases, queues, emulators, or external accounts.
5. Database migration, seeding, code generation, build, or bootstrap steps.
6. The first verification command a new contributor should run.
7. Expected success signal for that command.

When commands cannot be executed safely or dependencies are unavailable, verify them structurally from manifests and CI, then label them as unexecuted in the completion report.

### 4. Map repository purpose and architecture

Create a compact architecture map that explains:

- What the repository is for and who it serves.
- Major directories or packages and their responsibilities.
- Runtime boundaries, deployable units, generated artifacts, schemas, migrations, or service integrations.
- Where tests, fixtures, documentation, scripts, and configuration live.
- Which areas are risky, generated, compatibility-sensitive, or normally maintainer-owned.

Keep the map useful for orientation; avoid turning it into a complete code reference.

### 5. Document common development workflows

Include only workflows supported by repository evidence. Typical workflows include:

- Running all tests and targeted tests.
- Linting, formatting, type-checking, and build commands.
- Starting the app, worker, documentation site, service stack, or local emulator.
- Updating generated code, schemas, migrations, snapshots, fixtures, or lockfiles.
- Adding dependencies.
- Creating branches, commits, pull requests, changelog entries, or release notes when repository policy supports those steps.

For each workflow, provide copy-ready commands and note the directory from which to run them.

### 6. Explain how to find owners, rules, commands, and conventions

Add a navigation section that tells contributors where to look for:

- Owners and reviewers (`CODEOWNERS`, maintainers files, team docs, package owners, or issue templates).
- Repository rules (`CONTRIBUTING`, `SECURITY`, `CLAUDE.md`, `AGENTS.md`, `.github` templates, policy docs).
- Commands (CI workflows, package scripts, Makefiles, justfiles, scripts, task runners).
- Coding conventions (formatter, linter, compiler, test config, representative files, style docs).
- Architecture decisions and operational constraints (architecture docs, ADRs, migrations, deployment files, observability docs).

If a source is missing, say so and provide the best available fallback, such as checking recent files in the affected area or asking maintainers in the repository's documented channel.

### 7. Identify safe first issues and troubleshooting paths

Guide maintainers or agents to identify beginner-safe work using repository evidence:

- Documentation clarifications.
- Small tests around existing behavior.
- Typo fixes and broken-link repairs.
- Isolated examples, fixtures, or sample configuration updates.
- Issues labeled `good first issue`, `help wanted`, or equivalent only when such labels/templates are documented or visible in repository files.

Also document areas that are unsafe for first changes, such as migrations, security-sensitive code, release automation, generated files, dependency upgrades, or cross-service contracts, when evidence supports the risk.

### 8. Add required tools, environment, and services

Create a dedicated prerequisites section covering:

- Language runtimes and versions.
- Package managers and lockfile expectations.
- System tools, CLIs, compilers, containers, emulators, and browsers.
- Required environment variables and where examples live.
- Local and remote service dependencies.
- Network access, credentials, secrets handling, and account setup.

Never expose real secrets. Use placeholder names and point to sample files or secret-management documentation.

### 9. Provide “if setup fails” fallback instructions

Include an explicit fallback section with this minimum sequence:

1. Confirm the current branch and repository root.
2. Reinstall dependencies using the repository-supported package manager.
3. Regenerate or refresh local environment files from checked-in examples.
4. Start or reset required local services.
5. Run the smallest verification command before the full suite.
6. Compare local commands with CI definitions.
7. Capture exact versions, commands, logs, and failing steps.
8. Contact the documented owner or support channel, or open an issue using the repository template.

Make fallback steps concrete for the repository. Do not prescribe destructive cleanup, database resets, or dependency purges unless the repository documents them.

## Onboarding coverage checklist

The final onboarding material or audit must address all seven areas below, either with content or an explicit evidence-backed omission:

- [ ] Repository purpose and architecture map.
- [ ] Local setup path from clean clone to first successful verification command.
- [ ] Common development workflows.
- [ ] How to find owners, rules, commands, and conventions.
- [ ] Safe first issues and troubleshooting.
- [ ] Required tools, environment variables, and service dependencies.
- [ ] “If setup fails” fallback instructions.

## Evidence rules

- Prefer executable configuration and CI over prose when they conflict.
- Prefer checked-in task definitions over inferred commands.
- Preserve valid repository-specific policy from existing docs.
- Never invent owners, labels, service names, credentials, URLs, SLAs, branch naming rules, commit formats, or review requirements.
- Distinguish confirmed facts from inferred guidance.
- Link only to paths, anchors, and external destinations that were verified.
- Keep commands copy-ready and specify the working directory when it is not the repository root.

## Safety

- Do not install dependencies, start long-running services, run migrations, reset databases, push branches, create issues, or alter repository settings unless the user explicitly requests it.
- Do not read secret-bearing files such as `.env`, private keys, credential stores, or token files. Sample files such as `.env.example` may be read.
- Do not use network access for repository facts unless the user explicitly asks and the source is authoritative.
- Do not overwrite unrelated documentation. Preserve user edits and report collisions.
- Keep generated onboarding concise enough to maintain; link to authoritative files instead of duplicating large policy sections.

## Validation

Before completion:

1. Run a lightweight formatting check on changed Markdown when available.
2. Always run:

   ```bash
   git diff --check -- <changed-onboarding-file>
   ```

3. Review the rendered diff:

   ```bash
   git diff -- <changed-onboarding-file>
   ```

4. Confirm the coverage checklist is satisfied or that omissions are explicitly justified.
5. Confirm `git status --short` shows only expected changes.

## Completion report

Return a concise report containing:

1. The path created, updated, or audited.
2. The evidence sources used.
3. The clean-clone setup path and first verification command documented.
4. The workflows and ownership/rules discovery paths documented.
5. Any unsupported onboarding topics intentionally omitted.
6. Validation commands and results.
7. Maintainer follow-ups for unresolved setup, ownership, or service-dependency questions.

## Troubleshooting

- **No setup command is documented:** Derive candidate commands from manifests and CI, label them as evidence-derived, and recommend maintainer confirmation.
- **Multiple package managers appear:** Prefer the one with the current lockfile and CI usage; mention alternates only if actively supported.
- **CI and README disagree:** Document the CI-backed command, note the conflict, and update stale prose when in update mode.
- **Required services are unclear:** List the service evidence found and mark exact startup steps as unresolved rather than inventing them.
- **No owner file exists:** Point contributors to issue or pull-request templates, recent maintainers in local Git history, or the documented support channel when available.
- **First verification is expensive:** Provide the smallest supported targeted check first, then list the full CI-equivalent suite.

## Worked examples

**Create:** `/contributor-onboarding first-time setup for backend contributors`

- Resolve the repository root, inventory manifests and CI, update the chosen onboarding document, add setup and fallback instructions, then run `git diff --check`.

**Audit:** `/contributor-onboarding audit the new developer guide`

- Read existing onboarding docs, compare them against manifests and CI, report coverage gaps across the seven checklist areas, and avoid writing files unless asked.

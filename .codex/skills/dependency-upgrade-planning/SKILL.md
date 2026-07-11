---
name: dependency-upgrade-planning
description: Use when planning dependency upgrades from existing dependency-audit findings without applying them. Trigger on plan our dependency upgrades, group upgrades by risk and ecosystem, recommend a low-blast-radius upgrade batch, define upgrade verification steps. NOT for editing manifests, lockfiles, or actually applying upgrades; use the repository's package manager directly instead. Requires reading manifests, lockfiles, and prior dependency-audit findings before proposing an upgrade batch.
allowed-tools: Read, Grep, Glob, Bash
when_to_use: Use to create a dependency upgrade plan from manifests, lockfiles, and dependency-audit findings without modifying dependency files.
argument-hint: "[--from-audit PATH] [--ecosystem npm|python|ruby|go|rust|java|dotnet|php|mixed] [--security-first]"
disallowed-tools: Write, Edit
---

# Dependency Upgrade Planning

## Contents

- [Inputs](#inputs)
- [Read-only manifest and lockfile rules](#read-only-manifest-and-lockfile-rules)
- [Upgrade grouping model](#upgrade-grouping-model)
- [Breaking-change research and migration checkpoints](#breaking-change-research-and-migration-checkpoints)
- [Batch recommendation strategy](#batch-recommendation-strategy)
- [Verification planning](#verification-planning)
- [Rollback planning](#rollback-planning)
- [Checklist](#checklist)
- [Output format](#output-format)
- [Stop conditions](#stop-conditions)

Plan dependency upgrades with minimal blast radius. This skill is the planning companion to [`dependency-audit`](../dependency-audit/SKILL.md): use the audit skill first when the repository has not yet been assessed for vulnerable, deprecated, duplicated, abandoned, or risky dependencies.

Planning mode is **read-only by default**. Do not edit manifests, lockfiles, generated dependency files, package-manager metadata, vendored dependencies, or CI configuration unless the user explicitly changes the task from planning to implementation.

## Inputs

Parse optional arguments as:

- `--from-audit PATH`: read an existing dependency-audit report and use its findings as the primary evidence source.
- `--ecosystem NAME`: focus on one ecosystem (`npm`, `python`, `ruby`, `go`, `rust`, `java`, `dotnet`, `php`, or `mixed`).
- `--security-first`: prioritize vulnerable or policy-blocking packages before freshness-only upgrades.

Reject unknown flags. If no audit report is provided, inspect manifests and lockfiles directly and state that the plan is based on repository evidence rather than a completed companion audit.

## Read-only manifest and lockfile rules

- Enumerate dependency files with read-only commands such as `find`, `rg --files`, `git ls-files`, and package-manager dry-run/list commands that do not rewrite files.
- Read manifests and lockfiles without normalizing, formatting, installing, resolving, or regenerating them.
- Do not run commands known to mutate lockfiles, package-manager caches inside the repository, generated clients, vendor trees, or workspace metadata.
- Prefer commands that are explicitly read-only, for example `npm outdated`, `pnpm outdated`, `yarn outdated`, `pip list --outdated`, `poetry show --outdated`, `bundle outdated`, `go list -m -u all`, `cargo outdated`, `mvn versions:display-dependency-updates`, `gradle dependencyUpdates`, `dotnet list package --outdated`, or `composer outdated` only when the repository/tooling supports them.
- If a package manager may update metadata as a side effect, do not run it. Record the command as a recommended follow-up instead.
- Treat missing lockfiles, multiple lockfiles for one manifest, or lockfile/manifest drift as planning blockers and route the user to `dependency-audit` evidence before recommending broad upgrades.

## Upgrade grouping model

Group every candidate upgrade across four dimensions:

1. **Ecosystem and package manager**
   - npm/yarn/pnpm/Bun, Python pip/Poetry/Pipenv/uv, Ruby Bundler, Go modules, Rust Cargo, Java Maven/Gradle, .NET NuGet, PHP Composer, OS/container packages, GitHub Actions, Docker base images, and other detected systems.
   - Keep workspace, monorepo, frontend, backend, infrastructure, and tooling dependencies separated when ownership or deployment differs.
2. **Risk**
   - `low`: patch/minor upgrades with stable APIs, dev-only tooling, good test coverage, no native/runtime implications.
   - `medium`: minor upgrades in runtime paths, framework plugins, transitive churn, type-definition changes, or packages with moderate migration notes.
   - `high`: major upgrades, framework/runtime upgrades, native extensions, cryptography/auth/payment/database clients, build-system changes, large transitive rewrites, or packages with known breaking changes.
   - `critical`: security fixes for exploitable vulnerabilities, end-of-life runtimes, abandoned packages on production paths, or upgrades required to restore deployability/compliance.
3. **Semantic-version impact**
   - Separate patch, minor, major, pre-release, pinned-to-range, range-to-range, and transitive-only changes.
   - Note ecosystems where SemVer is advisory or not guaranteed and downgrade confidence accordingly.
   - Distinguish manifest-range changes from lockfile-only resolution changes.
4. **Runtime criticality**
   - Classify dependencies as production runtime, build/compile, test-only, lint/format/dev tooling, CI/release automation, infrastructure/container, or documentation/examples.
   - Elevate packages involved in authentication, authorization, encryption, serialization, database access, migrations, queue processing, observability, networking, payments, or user-facing rendering.

## Breaking-change research and migration checkpoints

For each medium-or-higher risk upgrade, define research tasks before implementation:

- Locate official changelogs, release notes, migration guides, deprecation schedules, and security advisories.
- Identify required intermediate versions, upgrade order constraints, codemods, configuration migrations, runtime version minimums, and peer dependency constraints.
- Check framework/plugin compatibility matrices and supported language/runtime versions.
- Verify transitive dependency changes that may affect bundling, native builds, binary downloads, postinstall scripts, licensing, or platform support.
- Search for removed APIs, changed defaults, stricter validation, changed module formats, type-system changes, and changed environment variables.
- Record migration-guide checkpoints as explicit pass/fail items, not vague reminders.
- If official guidance is missing for a high-risk dependency, mark the upgrade as blocked pending manual research or proof-of-concept validation.

## Batch recommendation strategy

Recommend upgrade batches that minimize blast radius:

- Prefer small, reversible batches over broad `update all` changes.
- Keep ecosystems in separate batches unless a cross-ecosystem upgrade is required by one feature or runtime change.
- Separate production runtime dependencies from dev tooling whenever possible.
- Separate major upgrades from patch/minor upgrades.
- Put security-critical fixes first, but avoid bundling unrelated risky upgrades into the same security patch.
- Upgrade foundational runtime/framework packages before dependent plugins only when the migration guide requires that order; otherwise test plugin compatibility in isolated batches.
- Isolate lockfile-only/transitive resolution updates when they are large or security-driven.
- Avoid mixing dependency upgrades with refactors, formatting, generated-file churn, or feature work.
- For monorepos, batch by deployable unit, package boundary, owner, or CI test target so rollback can be scoped.
- Define explicit stop points between batches where tests, smoke checks, and manual verification must pass before continuing.

## Verification planning

For each recommended batch, define verification commands before implementation. Include commands that fit the detected ecosystem, such as:

- Dependency integrity: package-manager install in frozen/locked mode, lockfile consistency checks, dependency tree explain/list commands, vulnerability audit commands.
- Static checks: typecheck, lint, format-check, generated-client checks, schema checks, and license/policy checks.
- Tests: unit, integration, end-to-end, contract, migration-related, visual, performance, and smoke tests relevant to affected packages.
- Build/package checks: production build, server start, container build, native extension compilation, asset bundling, and packaging/publish dry runs.
- Runtime checks: focused manual QA paths for authentication, payment, database, API clients, background jobs, and browser compatibility when affected.

Label commands as:

- `required`: must pass before merging the batch.
- `recommended`: valuable when time or environment permits.
- `blocked/manual`: cannot run in the current environment or requires credentials/services.

Do not invent commands that the repository does not appear to support. When inferring commands from common conventions, label them as inferred and cite the file or script that supports the inference.

## Rollback planning

For each batch, define rollback steps before implementation:

- Preserve the pre-upgrade commit SHA, branch name, manifest versions, lockfile state, and package-manager version.
- Roll back by reverting the batch commit rather than hand-editing manifests whenever possible.
- Include package-manager cache cleanup or reinstall steps only when necessary and safe.
- Note generated files, vendored dependencies, Docker base images, CI images, or runtime version changes that must be reverted together.
- Define production rollback actions for runtime-critical dependencies, including feature flag disablement, deployment rollback, canary abort, service restart, or image rollback.
- Define post-rollback verification commands and smoke tests.
- Call out irreversible or difficult rollbacks, such as database/client protocol changes, runtime major upgrades, or lockfile resolver migrations.

## Checklist

- [ ] Load prior `dependency-audit` findings via `--from-audit`, or inspect manifests/lockfiles directly if none were provided.
- [ ] Enumerate dependency files and ecosystems using read-only commands only.
- [ ] Group every candidate upgrade by ecosystem, risk, semantic-version impact, and runtime criticality.
- [ ] Define breaking-change research checkpoints for each medium-or-higher risk upgrade.
- [ ] Recommend batches that minimize blast radius, with explicit stop/go criteria between batches.
- [ ] Define verification commands for each batch, labeled required, recommended, or blocked/manual.
- [ ] Define rollback steps for each batch.
- [ ] Produce the plan using the Output format sections, or stop per Stop conditions.

## Output format

Return Markdown with these sections:

1. `Scope and evidence`
2. `Detected ecosystems and dependency files`
3. `Upgrade grouping`
4. `Breaking-change research checklist`
5. `Recommended batches`
6. `Verification plan`
7. `Rollback plan`
8. `Blocked items and open questions`

Use tables where helpful. Each recommended batch should include:

- batch name and goal
- included ecosystem/package set
- excluded packages that should not be bundled
- risk rating and semantic-version impact
- runtime criticality
- research checkpoints
- verification commands
- rollback steps
- stop/go criteria before the next batch

## Stop conditions

Stop and report instead of producing a broad plan when:

- The user asks to apply upgrades while still invoking planning-only mode.
- Manifests and lockfiles are inconsistent or missing in a way that prevents trustworthy planning.
- A package manager command would mutate dependency files and no read-only alternative is available.
- A high-risk dependency lacks official release notes, migration guidance, or enough local test coverage to bound the risk.
- The plan depends on private registries, credentials, production telemetry, or security advisory details that are unavailable.

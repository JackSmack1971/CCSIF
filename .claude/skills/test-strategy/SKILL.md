---
name: test-strategy
description: Use when asked to design, audit, or improve a repository's test strategy; identify test frameworks and test directories; map high-risk modules to unit, integration, contract, and regression tests; find missing behavioral coverage; or produce a prioritized test plan with runnable commands. Use stack-detection and repo-audit as companion inputs when stack classification or broad repository risk evidence is needed. NOT for executing an exhaustive repository audit by itself; use repo-audit for whole-repo issue discovery. Distinct keywords test strategy, behavioral coverage, high-risk modules, unit integration contract regression tests, test plan, test commands.
when_to_use: Use to recommend evidence-based test coverage improvements and concrete test additions for the current repository.
argument-hint: "(optional focus area, module, or changed files)"
allowed-tools: Read, Grep, Glob, Bash
---

# Test Strategy

Build an evidence-based test strategy from repository manifests, source layout, existing tests, and companion-skill findings. Do not infer unsupported implementation details; when evidence is incomplete, state the uncertainty and recommend the smallest verification step.

## Companion Inputs

Use these skills as inputs when their scope matches the request:

- `stack-detection`: use before test planning for desktop/client stack questions, especially when the repository may be a docs-first scaffold, Tauri desktop app, or mixed/partial implementation.
- `repo-audit`: use its confirmed findings and risk areas as input when the user asks for a broad test plan or repository-wide coverage gaps.

Do not duplicate a whole-repo audit unless requested. If companion-skill evidence is unavailable, inspect the relevant files directly and label the result as local test-strategy evidence.

## Checklist

- [ ] Detect test frameworks from manifests, lockfiles, config files, CI workflows, and existing test files.
- [ ] Locate test directories and naming conventions from file layout.
- [ ] Identify high-risk modules from runtime criticality, change frequency signals, security/privacy boundaries, persistence, external integrations, public APIs, concurrency, error handling, and previously reported defects.
- [ ] Map each high-risk module to recommended unit, integration, contract, and regression tests where applicable.
- [ ] Evaluate missing coverage by user-visible behavior, invariants, failure modes, and integration boundaries rather than percentage metrics alone.
- [ ] Recommend exact test files and test case names to add, grounded in observed source files and existing conventions.
- [ ] Provide a prioritized test plan with available commands and note any commands that are inferred but not confirmed.

**Stop condition:** stop and ask for clarification or report an open question instead of inventing tests when you cannot tie a proposed test to confirmed source, manifest, route, API, schema, command, or documented behavior.

## 1. Detect Frameworks and Test Directories

Inspect evidence in this order:

1. Manifests and lockfiles: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `requirements*.txt`, `Pipfile`, `go.mod`, `pom.xml`, `build.gradle*`, `.csproj`, `Gemfile`, or equivalent.
2. Test configuration: `vitest.config.*`, `jest.config.*`, `playwright.config.*`, `cypress.config.*`, `pytest.ini`, `tox.ini`, `noxfile.py`, `Cargo.toml` test sections, `.cargo/config*`, `go test` conventions, CI workflow commands, coverage configs, and language-specific build files.
3. File layout: directories such as `test/`, `tests/`, `spec/`, `__tests__/`, `e2e/`, `integration/`, `fixtures/`, `mocks/`, `src/**/__tests__/`, Rust `tests/`, Go `*_test.go`, Python `test_*.py`, Java/Kotlin `src/test/`, and frontend component test colocations.
4. Existing commands in `README*`, `CONTRIBUTING*`, `Makefile`, `justfile`, `Taskfile*`, CI workflows, package scripts, or build scripts.

Report:

- Detected frameworks and confidence level.
- Existing test directories and naming patterns.
- Confirmed commands to run.
- Potential commands only when clearly implied by the framework; label them as unconfirmed.

## 2. Map High-Risk Modules to Test Types

Prioritize modules with one or more of these signals:

- Authentication, authorization, secrets, privacy, cryptography, or permission boundaries.
- Data storage, migrations, serialization, caching, recovery, or destructive operations.
- Network clients, provider routing, third-party APIs, webhooks, queues, or protocol adapters.
- Public APIs, CLIs, SDK surfaces, plugin boundaries, IPC, or frontend/backend bridges.
- Complex state machines, concurrency, retries, timeouts, scheduling, or background jobs.
- Error handling, observability, fallbacks, and degraded-mode behavior.
- Recently changed files, large modules, duplicated logic, sparse tests, or areas named in `repo-audit` findings.

For each high-risk module, recommend test types according to observed behavior:

- **Unit tests:** pure functions, validators, branching logic, error classification, serialization helpers, permission decisions, reducers, state transitions, and small adapters with mocked dependencies.
- **Integration tests:** database/file-system interactions, service composition, IPC/HTTP handlers, command flows, migrations, cache behavior, real parser/build pipeline interactions, and multi-module behavior.
- **Contract tests:** external provider request/response shapes, API schemas, CLI output contracts, plugin interfaces, IPC payloads, generated types, and documented public interfaces.
- **Regression tests:** confirmed bugs, audit findings, edge cases already documented in issues/PRs/comments, production incident symptoms, and fragile behavior discovered while reading code.

Do not recommend all test types for every module. Explain why each recommended type fits the specific risk.

## 3. Identify Missing Coverage by Behavior

Evaluate coverage gaps by asking what behavior could break unnoticed:

- What user-visible workflow, API call, command, route, or background job lacks a direct test?
- What invariant is central to correctness and where is it asserted?
- What failure modes are expected: invalid input, denied permission, missing config, unavailable dependency, timeout, partial write, corrupt data, rollback, retry exhaustion, or malformed external response?
- What boundary has no contract assertion: schema, payload, CLI text/exit code, event shape, file format, migration, or IPC command?
- What documented behavior lacks executable verification?
- What bug-prone branch or edge case is not represented in existing test names, fixtures, or assertions?

Use coverage percentages only as secondary evidence. A high coverage percentage does not close a behavioral gap; a low percentage is not actionable unless tied to missing behavior.

## 4. Recommend Exact Tests Without Inventing Details

When proposing new tests:

- Follow existing directory, filename, fixture, and naming conventions.
- Cite or name the source file, public function, command, route, schema, component, config, or documented behavior that supports each test.
- Recommend exact files such as `tests/<module>.test.ts`, `src/<feature>/__tests__/<component>.test.tsx`, `tests/<flow>.rs`, or the repository's observed equivalent.
- Recommend exact test case names using observed behavior, for example `rejects_missing_required_config`, `returns_unauthorized_for_cross_tenant_access`, or `preserves_existing_cache_on_provider_timeout`.
- Prefer small, behavior-oriented tests over broad snapshots unless snapshots are already the established convention.
- Mark assumptions explicitly: `Assumption to verify: ...`.

Do not invent routes, database tables, environment variables, provider names, UI labels, or business rules that are not present in source, docs, or confirmed companion-skill findings.

## 5. Produce a Prioritized Test Plan

Output a concise plan ordered by risk and implementation value:

1. **P0 / must add first:** tests for data loss, security/privacy boundaries, public contract breakage, release blockers, and confirmed regressions.
2. **P1 / should add next:** tests for high-traffic workflows, external integrations, persistence, complex state, and important error paths.
3. **P2 / useful hardening:** edge cases, lower-risk branches, refactor safety nets, and expanded fixtures.

For each item include:

- Target module or behavior.
- Recommended test file path.
- Test cases to add.
- Test type: unit, integration, contract, or regression.
- Evidence source used.
- Command to run, if confirmed.
- Any open question or assumption to verify.

## Output Format

Use this structure unless the user asks for something else:

```markdown
## Detected Test Stack
- Frameworks:
- Test directories / naming:
- Confirmed commands:
- Unconfirmed but likely commands:

## High-Risk Modules and Recommended Coverage
| Priority | Module/behavior | Risk | Test type | Recommended file/cases | Evidence |
| --- | --- | --- | --- | --- | --- |

## Behavioral Coverage Gaps
- ...

## Prioritized Test Plan
### P0
- ...
### P1
- ...
### P2
- ...

## Commands to Run
- `...`

## Open Questions / Assumptions
- ...
```

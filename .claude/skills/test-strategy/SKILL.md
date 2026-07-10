---
name: test-strategy
description: Use when the user asks what tests to run, wants a test plan, or needs a focused verification strategy for changed files. Trigger on what tests should I run, create a test plan, verify this change, define a testing strategy. NOT for actually writing or running the test suite; use the repository's existing test commands instead. Requires separating local checks from CI, service, or secret-dependent checks in the recommendation.
when_to_use: Use to produce an evidence-based test strategy and exact verification commands for a repository change.
argument-hint: "(changed files, feature description, or optional focus area)"
allowed-tools: Read, Grep, Glob, Bash
---

# Test Strategy

## Contents

- [Trigger Text](#trigger-text)
- [Workflow](#workflow)
- [Checklist](#checklist)
- [Output Format](#output-format)
- [Guardrails](#guardrails)

Help agents choose the smallest meaningful verification for a change. Ground every recommendation in manifests, config, CI, docs, existing tests, and file layout. If evidence is incomplete, label assumptions instead of inventing frameworks, services, or commands.

## Trigger Text

Use this skill for requests containing or equivalent to:

- "what tests should I run"
- "create test plan"
- "verify this change"
- "testing strategy"
- "how should I test this"
- "what verification is enough"

## Workflow

### 1. Detect frameworks and conventions

Inspect, in order:

1. Manifests and lockfiles: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `pyproject.toml`, `requirements*.txt`, `Pipfile`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle*`, `.csproj`, `Gemfile`, and equivalents.
2. Test/build config: `vitest.config.*`, `jest.config.*`, `playwright.config.*`, `cypress.config.*`, `pytest.ini`, `tox.ini`, `noxfile.py`, `Makefile`, `justfile`, `Taskfile*`, coverage config, and CI workflow commands.
3. File layout and names: `test/`, `tests/`, `spec/`, `__tests__/`, `e2e/`, `integration/`, `fixtures/`, `mocks/`, `snapshots/`, `src/**/__tests__/`, Rust `tests/`, Go `*_test.go`, Python `test_*.py`, Java/Kotlin `src/test/`, and colocated frontend tests.
4. Documentation: `README*`, `CONTRIBUTING*`, docs, command files, and existing verification notes.

Report detected frameworks, confidence, existing test naming conventions, confirmed commands, and likely-but-unconfirmed commands.

### 2. Identify test layers already present or needed

Classify repository evidence into layers:

- **Unit:** pure functions, validators, reducers, serializers, permission decisions, parsing, formatting, and small adapters with mocked dependencies.
- **Integration:** database/file-system behavior, service composition, HTTP/IPC handlers, migrations, queues, cache behavior, build pipelines, and multi-module flows.
- **End-to-end:** browser/mobile/desktop/user flows, CLI workflows, full-stack happy paths, and cross-process behavior.
- **Contract:** public API schemas, CLI output/exit codes, provider payloads, webhook shapes, plugin interfaces, generated types, IPC messages, file formats, and documented external behavior.
- **Snapshot:** UI render output, generated files, structured API responses, or serialized artifacts only when snapshots are already used or the artifact contract is intentionally stable.
- **Smoke:** fast startup/build/import/health checks that prove the app or package is basically runnable without exhaustive assertions.

Do not recommend every layer for every change. Explain why a layer is relevant or unnecessary.

### 3. Map changed files or proposed work to narrow commands

For each changed file or proposed work item:

1. Identify the owning package/module and nearest tests.
2. Prefer the narrowest command that directly exercises the behavior, such as a single test file, test name filter, package target, or affected workspace.
3. Add broader commands only when the change crosses public contracts, build tooling, generated artifacts, shared utilities, dependency boundaries, or high-risk runtime paths.
4. Include lint/typecheck/build commands only when the change can affect syntax, types, packaging, generated outputs, or framework configuration.
5. Separate mandatory verification from optional confidence-building checks.

If no runnable command is confirmed, provide the closest safe inspection/check and state what manifest or script is missing.

### 4. Recommend missing tests without over-testing

Recommend new tests only for behavior that could break unnoticed:

- Security, authorization, privacy, secrets, destructive actions, persistence, migrations, payments/trading, or production configuration.
- Public API/CLI/SDK/plugin/IPC contracts.
- External service boundaries, retries, timeouts, fallbacks, malformed responses, and degraded modes.
- Complex state, concurrency, scheduling, caching, serialization, or error handling.
- Confirmed regressions, documented incidents, or user-visible workflows.

Avoid over-testing by skipping redundant tests that only restate framework behavior, duplicate an existing layer, assert implementation details with no user/contract value, or require slow E2E coverage when a unit/contract/integration test proves the risk.

### 5. Distinguish local vs service/secret/CI checks

For every command, classify it as:

- **Local:** can run in a clean checkout with normal dependencies and no special services.
- **Local with services:** requires Docker, database, browser, emulator, cache, queue, or other local daemon.
- **Secrets required:** needs credentials, tokens, private packages, API keys, or protected environment variables.
- **CI-only:** depends on CI matrix, deployment credentials, hosted services, protected runners, or unavailable infrastructure.

State setup prerequisites and expected failure mode when a command cannot be run locally.

## Checklist

- [ ] Detect frameworks and test conventions from manifests, config, and file layout.
- [ ] Identify which test layers are already present or needed.
- [ ] Map changed files or proposed work to the narrowest meaningful command.
- [ ] Recommend missing tests only for behavior that could break unnoticed.
- [ ] Classify every command as local, local-with-services, secrets-required, or CI-only.
- [ ] Produce the plan using the Output Format section, with exact commands and expected evidence.

## Output Format

Use this structure unless the user asks for another format:

```markdown
## Detected Test Stack
- Frameworks and confidence:
- Test conventions:
- Confirmed commands:
- Unconfirmed but likely commands:

## Test Layers
| Layer | Present? | Evidence | Use for this change? |
| --- | --- | --- | --- |
| Unit |  |  |  |
| Integration |  |  |  |
| End-to-end |  |  |  |
| Contract |  |  |  |
| Snapshot |  |  |  |
| Smoke |  |  |  |

## Change-to-Verification Map
| Changed file/work item | Risk | Narrowest meaningful command | Broader command if needed |
| --- | --- | --- | --- |

## Recommended Missing Tests
- Priority:
  - Behavior:
  - Test layer:
  - Suggested file/case:
  - Why this is enough:

## Verification Plan
1. Command: `...`
   - Classification: Local / Local with services / Secrets required / CI-only
   - Expected evidence: passing output, assertion, artifact, screenshot, log line, coverage of named behavior, or documented skip reason
   - If unavailable locally: prerequisite or CI job that should provide the evidence

## Open Questions / Assumptions
- ...
```

## Guardrails

- Prefer repository conventions over generic test advice.
- Cite files or commands used as evidence in normal agent responses.
- Do not invent routes, schemas, environment variables, package scripts, services, business rules, or test names not supported by source/docs.
- Keep plans proportional: one risky backend contract change may need unit plus contract/integration; a docs-only change may need no tests beyond formatting or link checks.
- The final `Verification Plan` must include exact commands and expected evidence, not vague instructions.

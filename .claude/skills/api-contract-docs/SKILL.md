---
name: api-contract-docs
description: Use when asked to document API surfaces, write OpenAPI or GraphQL schema docs, produce SDK reference material, or record CLI reference documentation from verified implementation behavior. Trigger on document this API, write OpenAPI docs, update GraphQL schema docs, produce SDK or CLI reference material. NOT for assessing whether an API change is a breaking compatibility risk; use api-contract-review instead. Requires citing the actual endpoint, schema, or CLI implementation for every documented behavior.
user-invocable: true
context: fork
agent: Explore
when_to_use: Use when maintainers need concise API documentation patches or review findings for REST, GraphQL, RPC, SDK, CLI, or configuration interfaces.
argument-hint: "[PATH|PR_NUMBER_OR_URL|BASE..HEAD] [--patch|--findings]"
allowed-tools: "Read Grep Glob Bash(git rev-parse:*) Bash(git status:*) Bash(git diff:*) Bash(git show:*) Bash(git log:*) Bash(gh pr view:*) Bash(gh pr diff:*) Edit MultiEdit Write"
---

# API Contract Documentation

## Contents

- [Purpose](#purpose)
- [Triggers](#triggers)
- [Inputs](#inputs)
- [Procedure](#procedure)
- [Contract test recommendations](#contract-test-recommendations)
- [Safety and boundaries](#safety-and-boundaries)
- [Verification checklist](#verification-checklist)

## Purpose

Create or review documentation for public API contracts by comparing consumer-facing examples with implementation behavior. Focus on what external users can call, configure, import, execute, or rely on, and produce either concise documentation patches or evidence-backed review findings.

## Triggers

Use this skill for requests containing or resembling:

- "document API"
- "review API contract"
- "OpenAPI"
- "GraphQL schema"
- "SDK docs"
- "CLI reference"
- REST, RPC, webhook, config, or public interface documentation requests

## Inputs

Accept one optional scope argument:

- `PATH`: inspect and document a specific package, service, schema, command, or docs area.
- `PR_NUMBER_OR_URL`: review changed API behavior in a pull request.
- `BASE..HEAD`: compare two revisions for documentation drift.

Accept one optional output mode:

- `--patch`: create concise documentation edits when the requested scope and source of truth are clear.
- `--findings`: remain read-only and report gaps, drift, and recommended documentation changes.

Default to `--findings` when the source of truth is ambiguous, the requested scope spans multiple systems, or edits would require product decisions.

## Procedure

### 1. Establish scope and source of truth

1. Identify the repository root and current change state with `git rev-parse --show-toplevel` and `git status --short`.
2. Determine whether the user wants new documentation, documentation review, or contract drift analysis.
3. Locate existing API documentation, examples, schemas, generated references, release notes, changelogs, and tests.
4. Identify implementation sources that define behavior, such as route registrations, controllers, resolvers, service definitions, command declarations, SDK entry points, config parsers, and validation layers.
5. Treat generated files as secondary unless repository conventions identify them as the source of truth.

### 2. Detect public interfaces

Search for all consumer-facing interfaces in scope, including:

- **REST routes:** HTTP methods, paths, path parameters, query parameters, headers, cookies, content types, request bodies, response bodies, redirects, and middleware-enforced behavior.
- **GraphQL schemas:** types, fields, queries, mutations, subscriptions, directives, custom scalars, enum values, nullability, arguments, resolver behavior, federation metadata, and persisted operations.
- **RPC services:** Protobuf, Thrift, gRPC, JSON-RPC, XML-RPC, service definitions, method names, streaming modes, deadlines, metadata, and generated stubs.
- **SDK exports:** package entry points, public classes, functions, methods, types, constants, events, generated clients, module exports, language-specific public visibility, and package manifests.
- **CLI commands:** command names, subcommands, positional arguments, flags, defaults, environment variables, stdin/stdout/stderr formats, exit codes, shell completions, and interactive prompts.
- **Config files:** documented config names, file locations, schema fields, defaults, environment overrides, precedence rules, validation errors, migration behavior, and examples.

For each public interface, record the defining file, documentation file if present, consumers, versioning mechanism, and whether the surface is explicitly public or inferred.

### 3. Compare implementation behavior with documented examples

For each documented example or reference section:

1. Match examples to the implementation path that handles them.
2. Verify request shape, required fields, optional fields, defaults, validation rules, content types, and parameter names.
3. Verify response shape, status or exit codes, headers, pagination envelopes, error bodies, ordering, and null versus absent behavior.
4. Check auth requirements, roles, scopes, token locations, anonymous access, and permission-dependent responses.
5. Compare SDK signatures, return types, thrown errors, async behavior, and code snippets against exported symbols.
6. Compare CLI examples against command definitions, defaults, output formats, and config precedence.
7. Flag examples that appear stale, incomplete, unexecutable, version-mismatched, or inconsistent with tests.

### 4. Identify missing contract details

Look for documentation gaps in:

- request and response schemas, including field types, formats, requiredness, nullability, examples, and constraints
- status codes, exit codes, GraphQL error paths, RPC status details, and retryability
- authentication and authorization requirements, token format, scopes, roles, and permission failures
- pagination, filtering, sorting, cursors, limits, defaults, total counts, and next-link behavior
- rate limits, quotas, throttling headers, backoff guidance, and burst behavior
- error formats, validation messages, machine-readable error codes, correlation IDs, and support/debug fields
- idempotency, consistency, ordering, timeouts, side effects, webhooks/events, and compatibility guarantees
- config file locations, precedence, defaults, environment variables, and invalid-config behavior

Classify each gap as `blocking`, `important`, or `minor` based on consumer impact and release risk.

### 5. Flag breaking changes and undocumented behavior

When comparing revisions or reviewing a PR, flag consumer-visible changes such as:

- removed or renamed routes, methods, fields, arguments, enum values, SDK exports, CLI commands, flags, config keys, or RPC services
- requiredness, nullability, type, default, format, auth, scope, pagination, status-code, error-envelope, or rate-limit changes
- changed output ordering, CLI text, SDK exceptions, GraphQL resolver semantics, side effects, idempotency, or retry behavior
- undocumented implementation behavior that consumers can observe or may already depend on
- docs that describe behavior no longer implemented, not yet implemented, or gated behind feature flags

Call out whether each change is documented, tested, versioned, deprecated, migration-guided, and compatible with stated repository policy.

### 6. Produce output

For `--patch` mode:

- Make the smallest useful documentation edits that align examples with implementation.
- Prefer source-of-truth docs, schema descriptions, CLI help/reference files, SDK README/API pages, and focused examples over broad rewrites.
- Include request and response examples only when they are verified from implementation, tests, fixtures, or generated schemas.
- Add concise notes for auth, pagination, rate limits, errors, and compatibility where relevant.
- Do not invent product guarantees; mark unknowns as TODOs only when repository style permits TODOs.

For `--findings` mode:

- Produce a concise report with affected interface, evidence, gap or drift, consumer impact, and recommended documentation patch.
- Include suggested contract tests when they would prevent recurrence.
- Separate confirmed findings from questions that require maintainer or product input.

## Contract test recommendations

Recommend contract tests when documentation and implementation could drift or when consumer impact is high. Prefer tests that verify:

- OpenAPI or JSON Schema examples validate against actual handlers and fixtures
- GraphQL schema snapshots, nullability, enum values, and resolver error shapes remain stable
- RPC service definitions match generated stubs and representative server behavior
- SDK exported symbols, signatures, return shapes, and documented snippets compile or execute
- CLI help text, flags, config precedence, stdout/stderr, and exit-code golden files remain stable
- auth failures, pagination boundaries, rate-limit responses, and error envelopes match documentation

Keep recommendations practical: name the specific interface, fixture, assertion, and test location when possible.

## Safety and boundaries

- Do not expose secrets, tokens, customer data, private endpoints, or sensitive payloads in examples or findings.
- Do not run destructive commands, migrations, deployments, publishing commands, or external write operations.
- Do not regenerate large API references unless explicitly requested and supported by repository instructions.
- Do not claim behavior is public, stable, authenticated, rate-limited, or backward-compatible without evidence.
- If implementation and documentation conflict but the intended contract is unclear, report the conflict instead of choosing one silently.

## Verification checklist

Before finishing, confirm that:

- [ ] REST routes, GraphQL schemas, RPC services, SDK exports, CLI commands, and config files were searched or explicitly ruled out for the requested scope.
- [ ] Documented examples were compared with implementation behavior or labeled unverified.
- [ ] Missing schemas, status codes, auth requirements, pagination, rate limits, and error formats were considered.
- [ ] Breaking changes and undocumented behavior were flagged with consumer impact.
- [ ] Output is either a concise documentation patch or a concise review finding report.
- [ ] Contract tests were recommended where they would materially reduce drift risk.

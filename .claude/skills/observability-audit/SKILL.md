---
name: observability-audit
description: Trigger when asked to audit observability, review logs, assess diagnostics coverage, evaluate production debugging readiness, inspect telemetry, or statically review logging, metrics, tracing, health checks, alerts, runbooks, and telemetry privacy risks.
when_to_use: Use for static observability and operability reviews of codebases, services, libraries, infrastructure definitions, or deployment configuration. Trigger phrases include “audit observability”, “review logs”, “diagnostics coverage”, and “production debugging”.
argument-hint: "[target path or service]"
allowed-tools: Read, Grep, Glob, Bash
---

# Observability Audit Skill

Use this skill to perform a static review of how well a system can be understood, debugged, and operated in production from its telemetry and diagnostic surfaces. Focus on evidence in code, configuration, deployment manifests, documentation, and tests. Do not assume runtime behavior unless it is directly supported by the implementation.

## Review workflow

1. **Map the production entry points**
   - Identify HTTP/RPC handlers, background workers, scheduled jobs, CLIs, message consumers, queues, cache clients, database calls, and external integrations.
   - Note the logging, metrics, tracing, health-check, and alerting libraries or conventions already in use.
   - Distinguish production telemetry from local-only debug output, test helpers, or commented examples.

2. **Evaluate logging consistency and safety**
   - Check whether logs use consistent levels (`debug`, `info`, `warn`, `error`, `fatal`) with clear criteria for each level.
   - Verify that key lifecycle events are logged: startup, shutdown, configuration summary, request/job start and completion where appropriate, retries, degraded behavior, and unrecoverable failures.
   - Confirm that request IDs, correlation IDs, trace IDs, tenant/account/user identifiers where safe, route or operation names, status codes, durations, retry counts, and dependency names are emitted as structured fields rather than embedded only in free-form strings.
   - Look for noisy logs, duplicate logs for the same failure, swallowed errors, stack traces without context, and low-value debug statements left in hot paths.
   - Inspect redaction practices for secrets, tokens, credentials, cookies, authorization headers, session IDs, API keys, PII, PHI, payment data, prompts, raw payloads, and customer content.

3. **Evaluate metrics coverage**
   - Check for latency metrics with useful dimensions for endpoints, operations, jobs, queues, external dependencies, and cache/database calls.
   - Check for error metrics that distinguish expected validation failures from unexpected system failures.
   - Check throughput metrics for requests, jobs, events, messages, and batch sizes.
   - Check queue depth, lag, age of oldest item, processing duration, retry/dead-letter counts, and worker concurrency where asynchronous work exists.
   - Check cache hit/miss/eviction/error metrics and cache freshness or staleness indicators where caching affects behavior.
   - Check external-call metrics for latency, status/error class, timeout, retry, circuit-breaker, and rate-limit behavior.
   - Verify metric names, labels/tags, units, cardinality controls, and whether dashboards or alerts can reliably aggregate them.

4. **Evaluate distributed tracing**
   - Verify propagation of trace context across inbound requests, outbound HTTP/RPC calls, queues, events, scheduled jobs, and worker boundaries.
   - Check that spans are created around meaningful operations: request handlers, database queries, cache operations, external calls, expensive computation, queue publish/consume, and retries.
   - Review span names for stable, low-cardinality operation names instead of raw URLs, IDs, SQL text, or customer data.
   - Confirm that trace attributes include safe, useful diagnostic fields and do not leak secrets or sensitive payloads.
   - Check that errors, timeouts, cancellations, and retry attempts are recorded on spans.

5. **Evaluate health, readiness, and startup diagnostics**
   - Identify liveness and readiness endpoints or equivalent probes.
   - Verify readiness checks cover required dependencies, schema or migration state, queue connectivity, configuration validity, and any critical background initialization.
   - Verify liveness checks avoid expensive dependency checks that can amplify outages.
   - Check startup diagnostics for version/build information, environment, config source, enabled features, migration status, port binding, and dependency initialization without exposing secrets.
   - Look for graceful shutdown diagnostics and probe behavior during draining.

6. **Evaluate alertability and operator experience**
   - Identify critical failure modes and determine whether existing logs, metrics, traces, health checks, or events make them alertable.
   - Prioritize alertability for customer-facing outage, data loss or corruption, security-sensitive failures, stuck queues, retry storms, dependency brownouts, saturation, runaway cost, cache poisoning/staleness, and background-job failures.
   - Check whether alerts can be routed by service, environment, dependency, severity, and ownership.
   - Look for runbook links, dashboard links, service ownership metadata, escalation hints, and operator-facing error messages.
   - Review whether error messages explain impact and next diagnostic step without revealing secrets or sensitive implementation details.

7. **Evaluate telemetry privacy and secret leakage**
   - Search for raw request/response bodies, headers, cookies, query strings, tokens, credentials, database URLs, exception objects, environment dumps, and user-generated content in logs, spans, metric labels, health output, and startup diagnostics.
   - Check whether redaction is centralized, tested, and applied before telemetry emission.
   - Flag high-cardinality or user-controlled telemetry fields that can create privacy, cost, or denial-of-service risks.

## Output format

Produce a concise but evidence-backed report using exactly these sections:

### Current observability surface
- Summarize the logging, metrics, tracing, health/readiness, alerting, runbook, and telemetry-safety mechanisms currently present.
- Cite specific files, functions, configuration, or documentation that establish the current behavior.

### Blind spots
- List missing or inconsistent telemetry that would make routine diagnosis slower.
- Include gaps in logging fields, metric dimensions, trace propagation, health probes, dashboards, runbooks, and redaction tests.

### High-risk diagnostic gaps
- Identify gaps likely to block incident response, hide customer impact, leak sensitive data, or prevent alerting on critical failure modes.
- Explain the production failure mode and why current telemetry would not expose it quickly.

### Recommended instrumentation
- Recommend concrete logs, metrics, spans, probes, alerts, runbook updates, and redaction controls.
- Include suggested names and fields where helpful, keeping labels/tags low-cardinality and privacy-safe.
- Separate quick wins from larger design changes when the distinction is useful.

### Verification suggestions
- Suggest static checks, unit tests, integration tests, smoke tests, dashboard checks, alert tests, trace-propagation tests, chaos/failure-injection checks, and redaction tests.
- Prefer commands or test scenarios the user can run locally or in CI.

## Review heuristics

- Prefer actionable findings over generic advice. Tie every finding to a concrete file, operation, or missing production scenario.
- Treat absence of evidence as a blind spot, not proof that observability is absent at runtime.
- Avoid recommending telemetry that records secrets, sensitive payloads, or unbounded user-controlled values.
- Favor structured, low-cardinality, aggregatable telemetry over free-form strings.
- Distinguish user-caused errors from system failures so alerts do not page on expected behavior.
- Consider both synchronous request paths and asynchronous/background paths.
- If the system uses a vendor or framework convention, verify that custom code preserves context propagation and safe fields.

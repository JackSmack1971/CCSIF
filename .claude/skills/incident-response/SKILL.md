---
name: incident-response
description: Use when responding to suspected or confirmed repository, application, dependency, release, data, or supply-chain incidents. Trigger on queries that say incident response, triage breach, secret leak, production outage, vulnerable dependency emergency, broken release, data exposure, or supply-chain compromise. Guides non-destructive classification, evidence preservation without secret disclosure, containment and rollback planning, communications, and follow-up links to security policy, dependency audit, release readiness, and repository hygiene skills. Requires human approval before credential rotation, deploy changes, destructive cleanup, user notification, regulator contact, or public disclosure.
---

# Incident Response

## Operating principles

Use this skill to coordinate the first safe pass of incident response. Default to read-only, reversible, and evidence-preserving work until a responsible human approves a risky action.

- Protect people, data, service availability, and evidence in that order.
- Preserve facts and uncertainty separately; label assumptions as `unconfirmed`.
- Never print, paste, summarize, or reformat secrets. Refer to secret locations by path, key name, line range, hash prefix, or finding ID only.
- Do not rotate credentials, revoke tokens, delete files, rewrite history, deploy, roll back, notify customers, contact regulators, or publish statements without explicit human approval.
- Prefer preparing commands and decision records over executing risky commands.
- Maintain a timestamped incident log with who observed what, source links, decisions, approvals, and next owner.

## 1. Classify the incident

Create a concise incident header:

```markdown
Incident ID: INC-YYYYMMDD-slug
Status: suspected | confirmed | contained | monitoring | closed
Severity: critical | high | medium | low | unknown
Type: secret leak | dependency vulnerability | production outage | data exposure | broken release | supply-chain compromise
Start time: observed timestamp and timezone
Current commander: human owner or `unassigned`
Systems affected: known list or `unknown`
Approval required before risky action: yes
```

Classify by primary type, then add secondary tags when needed:

- **Secret leak:** credentials, tokens, keys, certificates, session material, signing keys, or private configuration may be exposed in code, logs, artifacts, issues, chat, CI output, packages, or history.
- **Dependency vulnerability:** a direct or transitive dependency, container image, runtime, action, package manager, or lockfile includes a known vulnerability, malicious package, typosquat, abandoned component, or unsafe install behavior.
- **Production outage:** users, jobs, APIs, infrastructure, data pipelines, or operational workflows are unavailable, degraded, timing out, corrupting output, or breaching SLOs.
- **Data exposure:** personal, confidential, regulated, tenant, internal, or customer data may have been disclosed, logged, exported, mispermissioned, committed, cached, or sent to the wrong audience.
- **Broken release:** a recent release, migration, config change, feature flag, artifact, package, or documentation update introduced incorrect behavior, compatibility breakage, missing assets, failed install, or failed deploy.
- **Supply-chain compromise:** build, release, dependency, CI, package publishing, maintainer account, webhook, artifact signature, registry, or repository trust boundary may be compromised.

If multiple types apply, choose the type with the highest immediate risk as primary and list the rest under `Related risks`.

## 2. Preserve evidence without exposing secrets

Before containment work, capture enough evidence to reconstruct the event without spreading sensitive content.

Safe evidence to collect:

- Timestamps, commit SHAs, release versions, package versions, lockfile names, CI run IDs, issue or PR IDs, deployment IDs, alert IDs, affected endpoints, and non-sensitive error codes.
- File paths, symbol names, redacted line ranges, secret scanners' finding IDs, and cryptographic hashes of sensitive artifacts when needed.
- Screenshots or logs only after redacting secrets, tokens, customer data, and internal-only identifiers that are not necessary for triage.

Evidence rules:

1. Record where evidence is stored and who can access it.
2. Use redaction markers such as `[REDACTED_SECRET]`, `[REDACTED_CUSTOMER_DATA]`, and `[REDACTED_INTERNAL_HOST]`.
3. Do not copy secrets into the incident log, pull requests, issues, prompts, shell history, or public trackers.
4. Do not delete leaked material, purge logs, force-push, or rotate credentials yet unless a human approves a containment plan.
5. When a command might print sensitive data, prepare the command for human review or pipe it through a narrow redaction workflow approved by the incident owner.

## 3. Identify containment and rollback options

Draft a containment matrix before acting:

```markdown
Option:
Incident type addressed:
Expected benefit:
Risk / blast radius:
Requires human approval: yes/no
Rollback path:
Verification signal:
Owner:
Deadline:
```

Default containment guidance by type:

- **Secret leak:** identify affected credentials and consumers; prepare rotation, revocation, history purge, cache purge, and downstream notification plans. Execute only after human approval because rotation can break production.
- **Dependency vulnerability:** identify affected manifests, lockfiles, images, workflows, packages, and deploy artifacts; prepare version pin, upgrade, mitigation flag, or temporary disablement options. Do not upgrade or redeploy without approval.
- **Production outage:** identify current impact and last known good state; prepare feature flag disablement, traffic shift, rollback, config revert, queue pause, or scaling options. Do not deploy, restart, or change traffic without approval.
- **Data exposure:** identify data categories, audiences, time window, access paths, and legal/privacy owner; prepare access restriction, token/session invalidation, log retention, and disclosure decision points. Do not notify externally without approval.
- **Broken release:** identify release artifact, commit range, migration state, and compatibility impact; prepare rollback, hotfix, deprecation notice, package yank, or docs correction. Do not yank, republish, or roll back without approval.
- **Supply-chain compromise:** identify trust boundary, affected identities, build provenance, package signatures, CI secrets, and distributed artifacts; prepare build freeze, account lockdown, key rotation, artifact revocation, and provenance rebuild. Require explicit approval for each action.

For every proposed action, include a verification step that confirms containment worked without relying only on command exit status.

## 4. Communication templates

Keep communications factual, concise, and audience-aware. Do not speculate, assign blame, expose secrets, identify customers, or promise timelines that have not been approved.

### Internal status update

```markdown
Subject: [INCIDENT][SEVERITY][TYPE] Short title

Current status: suspected | confirmed | contained | monitoring
Impact: who/what is affected; use `unknown` where needed
Known facts:
- Fact with evidence reference
- Fact with evidence reference

Actions taken:
- Read-only or approved action, timestamp, owner

Decisions needed:
- Approval requested, risk, deadline

Next update: timestamp and channel
Incident commander: name/team
```

### Executive summary

```markdown
Summary: One paragraph describing business/user impact and current state.
Risk: critical/high/medium/low and why.
Containment: completed, pending approval, or not started.
Customer/data exposure: yes/no/unknown; privacy/legal owner if applicable.
Decision requests: approvals needed for rotation, deploy, rollback, disclosure, or other risky work.
Next milestone: timestamp.
```

### External holding statement

Use only after human approval from the appropriate incident, legal, communications, and security owners.

```markdown
We are investigating an issue affecting [service/product/scope]. Our team is working to understand impact and will provide updates through [approved channel]. We will share additional information when it is verified.
```

### Post-incident follow-up issue

```markdown
Title: Follow-up from INC-YYYYMMDD-slug: action summary

Context:
- Incident type and confirmed facts
- Link to private incident record, if permitted

Required work:
- Specific remediation task

Skill / owner routing:
- Security policy: policy update, disclosure process, reporting channel, or credential handling
- Dependency audit: vulnerable package, lockfile drift, package provenance, install behavior
- Release readiness: release gate, rollback drill, migration safety, artifact validation
- Repository hygiene: stale config, branch protection, CODEOWNERS, CI governance, documentation drift

Verification:
- Command, check, review, or monitoring signal proving completion

Safety:
- Human approval required before any destructive, deploy, credential, or public action
```

## 5. Link follow-up work to related skills

Route durable remediation to the narrowest appropriate skill or workflow:

- Use **crafting-repository-security-policy** for SECURITY.md updates, vulnerability disclosure instructions, supported versions, safe harbor language, reporting contacts, credential handling, and incident escalation policy.
- Use **dependency-audit** for package manifests, lockfiles, vulnerable dependencies, abandoned packages, postinstall scripts, native extensions, CI install behavior, and supply-chain dependency risk.
- Use **release-readiness** for release gates, rollback readiness, migration checks, versioning, artifact verification, changelog quality, and deployment readiness. If this skill is absent, create an issue requesting a release-readiness review rather than inventing a workflow.
- Use **maintaining-repository-hygiene** for CODEOWNERS, branch protection, repository settings, stale worktrees, CI governance, community health files, ignored/generated artifacts, labels, and documentation rot.

## Completion checklist

- [ ] Incident type, severity, status, affected systems, and unknowns recorded.
- [ ] Evidence preserved with secrets and sensitive data redacted.
- [ ] Immediate containment and rollback options documented with risks, approvals, owners, and verification signals.
- [ ] Internal update drafted and approval-required decisions highlighted.
- [ ] External statement drafted only as a proposed template, not published.
- [ ] Follow-up issues or tasks routed to security policy, dependency audit, release readiness, and/or repository hygiene as applicable.
- [ ] No risky action was taken without explicit human approval.

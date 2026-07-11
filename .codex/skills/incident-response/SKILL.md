---
name: incident-response
description: Use when the user mentions a suspected or confirmed production incident, outage, rollback plan, or postmortem. Trigger on we have an incident, production regression happened, draft a postmortem, plan a safe rollback. NOT for routine bug triage with no production impact; use pr-triage or repo-audit instead. Requires preserving evidence, citing sources, and avoiding destructive or state-changing commands unless explicitly approved.
when_to_use: Use when investigating a suspected or confirmed production incident, drafting a postmortem, or planning a rollback, not for routine bug triage with no production impact.
argument-hint: "[INCIDENT_SUMMARY|LOG_OR_ALERT_REFERENCE]"
allowed-tools: "Read Grep Glob Write Bash(git status:*) Bash(git log:*) Bash(git show:*) Bash(git diff:*) Bash(git branch:*)"
---

# Incident Response

## Contents

- [Core safety rules](#core-safety-rules)
- [Activation triggers](#activation-triggers)
- [Incident workspace](#incident-workspace)
- [1. Capture the incident timeline](#1-capture-the-incident-timeline)
- [2. Identify likely blast radius and user impact](#2-identify-likely-blast-radius-and-user-impact)
- [3. Separate confirmed facts from hypotheses](#3-separate-confirmed-facts-from-hypotheses)
- [4. Propose safe rollback, roll-forward, or mitigation options](#4-propose-safe-rollback-roll-forward-or-mitigation-options)
- [5. Draft status updates and post-incident review notes](#5-draft-status-updates-and-post-incident-review-notes)
- [6. Generate follow-up issue stubs for prevention work](#6-generate-follow-up-issue-stubs-for-prevention-work)
- [7. Preserve evidence without destructive commands](#7-preserve-evidence-without-destructive-commands)
- [Completion checklist](#completion-checklist)
- [Completion Gate](#completion-gate)

Use this skill for suspected or confirmed incidents, including production regressions, outages, rollback planning, outage analysis, and postmortems. Operate in evidence-preserving mode: prefer read-only commands, cite sources, and avoid destructive or state-changing actions unless the user explicitly approves them.

## Core safety rules

- Preserve evidence before changing anything.
- Do not run destructive commands such as `rm`, `git reset --hard`, `git clean`, force-pushes, migration rollbacks, database writes, deploys, restarts, queue purges, or secret rotations unless explicitly requested and approved.
- Do not overwrite logs, truncate files, delete artifacts, rewrite history, or close issues/PRs as part of investigation.
- Keep secrets, customer data, tokens, internal hostnames, and sensitive identifiers out of summaries. Redact with markers such as `[REDACTED_SECRET]` or `[REDACTED_CUSTOMER_DATA]`.
- Separate confirmed facts from hypotheses. Never present an inference as a fact.
- Include timestamps with time zones whenever possible.
- Prefer reversible mitigations: feature flags, traffic shifts, config toggles, read-only validation, or narrowly scoped hotfixes.

## Activation triggers

Use this skill when requests include or imply:

- `incident`
- `production regression`
- `rollback plan`
- `outage analysis`
- `postmortem`
- `post-incident review`
- `service degradation`
- `customer impact`
- `root cause analysis`
- `mitigation plan`

## Incident workspace

Create or maintain an incident working note with this structure:

```markdown
# Incident: <short title>

Incident ID: INC-YYYYMMDD-<slug>
Status: investigating | mitigated | monitoring | resolved | closed
Severity: SEV-1 | SEV-2 | SEV-3 | SEV-4 | unknown
Started: <timestamp and timezone, or unknown>
Detected: <timestamp and timezone>
Incident commander / owner: <name/team or unknown>
Affected systems: <known systems or unknown>
Primary user impact: <summary or unknown>
Current mitigation: <none | summary>
Next update due: <timestamp/channel>

## Confirmed facts
- [timestamp] Fact — source: <log/deploy/commit/issue/PR/monitoring link>

## Hypotheses
- Hypothesis — evidence for: ...; evidence against: ...; confidence: low/medium/high; validation step: ...

## Open questions
- Question — owner: ...; next step: ...

## Decisions
- [timestamp] Decision — owner/approver: ...; reason: ...; rollback path: ...
```

## 1. Capture the incident timeline

Build a timeline from all available non-destructive sources. Use the most authoritative source for each event and record uncertainty explicitly.

Recommended sources:

- Application, platform, API gateway, worker, queue, database, CDN, and load balancer logs.
- Monitoring alerts, SLO burn alerts, traces, dashboards, incident pages, and on-call notes.
- Git commits, merge commits, tags, release branches, and diff ranges.
- CI/CD runs, deploy records, release notes, feature-flag changes, infrastructure changes, migrations, and config changes.
- Issue, PR, ticket, chat, customer support, and status page references.

Timeline format:

```markdown
| Time (UTC/local) | Event | Source | Confidence | Notes |
| --- | --- | --- | --- | --- |
| 2026-07-10 14:03 UTC | Error rate alert fired for checkout API | alert ABC-123 | confirmed | Initial detection |
| 2026-07-10 13:41 UTC | Deploy d-456 completed | deploy record | confirmed | Candidate change window |
| unknown | First affected user request | logs pending | hypothesis | Need log query |
```

Guidelines:

1. Start with detection time, then work backward to the last known good state and forward through mitigation.
2. Correlate deploys and commits with symptom onset, but label correlation as a hypothesis until validated.
3. Include issue/PR IDs, commit SHAs, deploy IDs, alert IDs, and log query references rather than copying sensitive raw logs.
4. Preserve original timestamps and add normalized UTC times when useful.
5. Keep a list of missing sources and owners for retrieval.

## 2. Identify likely blast radius and user impact

Assess impact from both system and user perspectives. Avoid minimizing unknowns.

Blast radius checklist:

- Affected products, services, APIs, jobs, regions, tenants, customer segments, platforms, or versions.
- Impacted user journeys such as login, checkout, signup, billing, search, ingestion, exports, notifications, or admin workflows.
- Data correctness risks: loss, duplication, corruption, stale reads, incorrect permissions, or delayed processing.
- Availability and performance risks: errors, latency, timeouts, queue backlog, saturation, or partial degradation.
- Security/privacy risks: unauthorized access, data exposure, secret leakage, audit-log gaps, or compliance triggers.
- Dependency and downstream effects: consumers, integrations, webhooks, reports, analytics, support, and SLAs.

Use this impact summary:

```markdown
## Impact assessment

Confirmed impact:
- <who/what is affected, evidence source, time window>

Likely impact:
- <hypothesis, why it is plausible, validation needed>

Not currently affected:
- <scope ruled out, evidence source>

Unknowns:
- <impact question, owner, next evidence source>

Estimated scale:
- Users/accounts/requests/jobs affected: <number or unknown>
- Time window: <start/end or unknown>
- Regions/environments: <list or unknown>
- Severity rationale: <brief explanation>
```

## 3. Separate confirmed facts from hypotheses

Maintain distinct sections for facts, hypotheses, and unknowns throughout the response.

- **Confirmed fact:** directly supported by a cited log entry, deploy record, commit, metric, issue/PR, monitoring event, or user report.
- **Hypothesis:** plausible explanation or suspected cause that still needs validation.
- **Unknown:** important information not yet available.

Recommended language:

- Say: “Confirmed: deploy `d-456` completed at 13:41 UTC.”
- Say: “Hypothesis: deploy `d-456` introduced the regression because errors began shortly afterward.”
- Do not say: “Deploy `d-456` caused the outage” until validation confirms causality.

Hypothesis tracker:

```markdown
| Hypothesis | Evidence for | Evidence against | Confidence | Validation step | Owner |
| --- | --- | --- | --- | --- | --- |
```

## 4. Propose safe rollback, roll-forward, or mitigation options

Offer options with risks and verification, not a single irreversible action. Clearly mark any action requiring human approval.

Option template:

```markdown
### Option: <rollback | roll-forward | mitigation> — <short name>

Description: <what would change>
Expected benefit: <impact reduction>
Risks / tradeoffs: <customer, data, operational, security risks>
Prerequisites: <backups, migration state, approvals, owners, runbooks>
Human approval required: yes/no
Evidence preserved before action: yes/no
Rollback path for this option: <how to undo>
Verification signals:
- <metric/log/check/user journey>
Decision deadline: <timestamp or condition>
Recommended when: <conditions>
Avoid when: <conditions>
```

Safe option patterns:

- **Rollback:** revert to last known good artifact, config, feature flag state, dependency version, or release. Check database migration compatibility and artifact availability first.
- **Roll-forward:** apply a narrow fix when rollback is riskier, unavailable, or would worsen data compatibility. Keep the diff minimal and verification explicit.
- **Mitigation:** disable a feature flag, shed load, pause a job, isolate a tenant, adjust traffic, rate-limit, increase capacity, or add a temporary guardrail.
- **No-change monitoring:** valid only when impact has stopped and evidence supports stability; define monitoring duration and exit criteria.

## 5. Draft status updates and post-incident review notes

Keep communications factual, concise, and audience-appropriate. Do not assign blame or overstate certainty.

### Internal status update

```markdown
Subject: [INCIDENT][<severity>] <short title>

Status: investigating | mitigated | monitoring | resolved
Impact: <confirmed impact; unknowns explicit>
Timeline highlights:
- <timestamp> <event> — source: <reference>
Confirmed facts:
- <fact with source>
Current hypotheses:
- <hypothesis with validation step>
Actions taken:
- <read-only or approved action, owner, timestamp>
Decisions needed:
- <approval requested, risk, deadline>
Next update: <timestamp and channel>
Owner: <incident commander/team>
```

### External/customer-safe holding update

Use only after approval from the appropriate incident, support, legal, communications, or security owner.

```markdown
We are investigating an issue affecting <service/scope>. We are working to understand impact and mitigate the issue. We will provide the next update by <time> through <approved channel>.
```

### Post-incident review notes

```markdown
# Post-Incident Review: <incident title>

Summary:
- <what happened, user impact, duration, current state>

Timeline:
- <key events with timestamps and sources>

Impact:
- <confirmed user/system/data impact>

Root cause:
- Confirmed root cause: <if known>
- Contributing factors: <if known>
- Ruled-out causes: <if useful>

Detection:
- How detected:
- What worked:
- What did not work:

Response:
- Mitigations attempted:
- Rollback/roll-forward decisions:
- Communication notes:

Prevention follow-ups:
- <issue links or stubs>

Open questions:
- <owner and due date>
```

## 6. Generate follow-up issue stubs for prevention work

Create issue stubs that are actionable, owned, and verifiable. Separate prevention from cleanup and observability improvements.

Issue stub template:

```markdown
Title: [INC follow-up] <prevent recurrence or improve detection>

Linked incident: INC-YYYYMMDD-<slug>
Category: prevention | detection | response | documentation | cleanup
Priority: P0 | P1 | P2 | P3
Owner: <team/person or unassigned>

Problem:
- <confirmed gap from incident>

Proposed work:
- <specific change>

Acceptance criteria:
- [ ] <verifiable outcome>
- [ ] <test, dashboard, runbook, alert, or review evidence>

Verification plan:
- <command, check, monitor, drill, or review>

Safety notes:
- <migration, rollout, rollback, data, security, or operational considerations>
```

Common prevention themes:

- Add or tune alerts for the failed signal.
- Add regression tests, contract tests, canaries, health checks, or synthetic checks.
- Improve feature flag, rollback, migration, or deploy safety.
- Add runbooks, ownership, dashboards, or support macros.
- Improve data validation, idempotency, rate limits, permissions, or audit logging.
- Add CI/CD gates for release readiness and production-change review.

## 7. Preserve evidence without destructive commands

When investigating, favor commands and workflows that read state and write only to a new notes file or artifact location.

Preferred read-only examples:

```bash
git status --short
git log --oneline --decorate --max-count=50
git show --stat --summary <sha>
git diff --stat <before>..<after>
git branch --show-current
```

Evidence-preservation checklist:

- Record command, timestamp, working directory, and relevant output summary.
- Save references to logs, dashboards, issues, PRs, deploys, and commits rather than copying sensitive raw data.
- If raw evidence must be captured, store it in the approved private location and note access controls.
- Redact secrets and sensitive data before sharing with agents or external systems.
- Avoid commands that mutate state, erase history, rotate credentials, alter deployments, purge queues, rewrite logs, or delete files.
- If a destructive action is proposed, write the exact command as a proposal, list risks, and wait for explicit approval.

## Completion checklist

- [ ] Timeline includes logs, commits, deploy records, and issue/PR references where available.
- [ ] Blast radius and user impact are summarized with confirmed, likely, not affected, and unknown sections.
- [ ] Confirmed facts are separated from hypotheses and open questions.
- [ ] Rollback, roll-forward, and mitigation options include risks, approvals, rollback paths, and verification signals.
- [ ] Internal status update and post-incident review notes are drafted.
- [ ] Follow-up prevention issue stubs are generated with acceptance criteria and verification plans.

## Completion Gate

Do not report the response or postmortem complete until every item in the Completion checklist is satisfied. Stop before running any command that mutates state, rotates credentials, alters deployments, or rewrites history; propose the exact command and wait for explicit approval instead.
- [ ] Evidence was preserved without destructive commands or sensitive data disclosure.

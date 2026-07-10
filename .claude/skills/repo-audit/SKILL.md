---
name: repo-audit
description: Use when running a system-wide repository audit that creates one actionable finding per confirmed issue across source code, tests, CI/CD, and governance. Trigger on audit the whole repo, run a full system-wide audit, find every confirmed issue, create issues for repository problems. NOT for a single PR review; use pr-triage instead, and NOT for a scored seven-axis quality run; use 7axes-audit instead. Requires filing one actionable GitHub issue per confirmed finding rather than a single combined report.
when_to_use: Use for a system-wide repository audit that creates one actionable finding per confirmed issue, not for a single PR review or a scored 7-axes quality run.
argument-hint: "(no arguments; audits the current repository end-to-end)"
allowed-tools: Read, Grep, Glob, Bash
---

# Repository Audit

Audit:

- [ ] Runtime source code
- [ ] Tests and test infrastructure
- [ ] CI/CD workflows
- [ ] Dependency manifests and lockfiles
- [ ] Build, release, and package configuration
- [ ] Security-sensitive code and configuration
- [ ] Environment, secrets, and config handling
- [ ] Error handling and observability
- [ ] Data, storage, migrations, and schemas
- [ ] Public APIs, CLIs, SDKs, and integrations
- [ ] Architecture, coupling, and duplication
- [ ] Performance and scalability risks
- [ ] Developer experience and local setup
- [ ] User-facing documentation
- [ ] Repository governance

Confirm findings before creating issues.

**Stop condition:** stop before filing an issue for any finding that lacks concrete, confirmed evidence; report it as an open question instead of guessing.

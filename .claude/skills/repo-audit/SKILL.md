---
name: repo-audit
description: Trigger on queries that say audit the whole repo, full system-wide audit, find every confirmed issue, or create issues for repository problems. Use for a system-wide repository audit that creates one actionable finding per confirmed issue. Audits runtime source code, tests, CI/CD workflows, dependency manifests, build and release configuration, security-sensitive code, error handling, data and schema layers, public APIs, architecture, performance, developer experience, documentation, and repository governance. NOT for a single PR review use pr-triage instead, and NOT for a scored 7-axes quality run use 7axes-audit instead. Distinct keywords confirmed findings, actionable issue creation, system-wide coverage, repository governance, developer experience audit.
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

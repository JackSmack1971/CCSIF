---
name: cicd-workflow-audit
description: Use when auditing CI/CD pipeline definitions for trigger safety, deployment gates, token permissions, secret handling, and third-party action pinning, and producing one actionable finding per issue with file paths and remediation. Trigger on audit CI workflow definitions, review GitHub Actions trigger safety, check pull_request_target risk, compare pipeline jobs to repository manifests. NOT for a broad multi-provider security posture summary without per-finding remediation; use ci-cd-audit instead, and NOT for directly modifying protected CI/CD deployment workflows unless explicitly approved. Requires producing findings with exact file paths, workflow or job names, evidence, impact, and remediation.
allowed-tools: Read, Grep, Glob, Bash
when_to_use: Use to audit CI/CD workflow definitions and deployment safety controls without changing protected workflows.
argument-hint: "(optional path or CI provider; audits current repository by default)"
disallowed-tools: Write, Edit
---

# CI/CD Workflow Audit

Audit repository pipeline definitions for safe triggers, least privilege, deployment gates, secret exposure, supply-chain controls, and expected verification coverage. Treat CI/CD deployment workflows as a protected area: keep audit-only work read-only, report findings instead of editing workflows, and require explicit human approval before applying any Tier 1 change to deployment workflows, permissions, hooks, secrets, or other protected configuration.

## Scope

Inspect CI/CD definitions from any provider present, including:

- GitHub Actions: `.github/workflows/*.yml`, `.github/workflows/*.yaml`, reusable workflows, composite actions, and workflow-dispatch inputs.
- GitLab CI: `.gitlab-ci.yml`, included files, child pipelines, deployment jobs, protected environments, and runner tags.
- CircleCI: `.circleci/config.yml`, orbs, contexts, approval jobs, workspaces, caches, and artifacts.
- Equivalent systems: Azure Pipelines, Buildkite, Jenkins, Drone, Woodpecker, Harness, Argo, release scripts, deploy manifests, or package-publish automation referenced by the repository.
- Repository manifests that define expected checks: package manifests, lockfiles, language/tool config, test/lint/typecheck scripts, Dockerfiles, release config, and build-system files.

## Protected-Area Rules

Follow the repository constitution language in `CLAUDE.md`:

1. **Evidence-driven only.** Base findings on workflow files, manifests, repository documentation, and command output.
2. **Audit-only means read-only.** Do not edit CI/CD files while performing an audit; report findings with paths and remediation steps.
3. **Protected changes require approval.** CI/CD deployment workflows are a protected area. Changes to deployment workflows, permissions, secrets, hooks, production configuration, or other protected areas are Tier 1 and require explicit human approval before apply.
4. **Minimum change guidance.** If remediation is requested later, recommend the smallest reviewable change with a rollback path.
5. **Verify source-of-truth state.** Prefer repository files and configured manifests over assumptions or generic best practices.

## Workflow

Use this checklist in order:

```text
CI/CD Audit Progress
- [ ] 1. Resolve repository root and CI provider inventory
- [ ] 2. Read protected-area guidance and existing pipeline definitions
- [ ] 3. Map workflows, jobs, triggers, permissions, secrets, caches, artifacts, and deployments
- [ ] 4. Compare required test/lint/typecheck/build jobs to repository manifests
- [ ] 5. Review third-party actions, includes, orbs, images, and scripts for pinning and trust boundaries
- [ ] 6. Produce actionable findings with workflow/job names, paths, evidence, risk, and remediation
```

### 1. Inventory Pipeline Definitions

- Resolve the repository root with `git rev-parse --show-toplevel`.
- Enumerate CI/CD files without recursive slow scans. Prefer `rg --files` with targeted globs.
- Record each workflow or pipeline file, display name, jobs/stages, reusable workflow calls, included templates, orbs, container images, and deployment/publish steps.
- Trace referenced scripts enough to understand security-sensitive behavior, especially release, deploy, package-publish, infrastructure, or secret-handling scripts.

### 2. Check Trigger Safety

For each workflow or pipeline, review:

- Events and branch/tag filters: `push`, `pull_request`, `pull_request_target`, `workflow_dispatch`, `schedule`, `release`, `merge_request_event`, branch-only deploys, tag deploys, and manual triggers.
- Pull-request versus push behavior: whether untrusted PR code runs with write tokens, secrets, caches, artifacts, deployment credentials, or privileged runners.
- Dangerous trigger combinations: `pull_request_target` with checkout of PR head, broad `workflow_run`, unsafely parameterized manual dispatch inputs, schedule jobs that deploy automatically, or push triggers on broad branches.
- Branch protection assumptions: required checks and protected branches cannot always be verified from local files; mark them as **unverified** unless repository-controlled config proves them.
- Fork behavior and actor conditions: whether external contributions can reach privileged paths, labels, comments, reusable workflows, or deployment jobs.

### 3. Review Deployment Gates

Identify every job that deploys, publishes, releases, signs, uploads packages, mutates infrastructure, updates production configuration, or writes to protected branches. For each, check:

- Environment protection use, approval gates, protected environments, manual approval jobs, or release promotion steps.
- Branch, tag, and path filters that constrain deploys to intended sources.
- Separation between build/test jobs and deploy jobs.
- Whether deploy jobs require all relevant tests, lint, typecheck, build, or security checks via `needs`, stages, approvals, or pipeline dependencies.
- Rollback visibility: artifacts, release notes, deployment logs, or version identifiers sufficient to reverse a bad deployment.

### 4. Review Permissions, Secrets, Caches, and Artifacts

Check each pipeline for least privilege and data exposure:

- Token permissions: explicit GitHub `permissions`, GitLab job tokens, CircleCI contexts, cloud-role assumptions, package registry tokens, OIDC trust policies, and write-capable credentials.
- Secrets: whether secrets are used only in trusted events, scoped to deploy jobs, protected by environments/contexts, masked, and never echoed into logs or artifacts.
- Environment protections: named environments, approval requirements, protected contexts, branch restrictions, and separation of staging versus production secrets.
- Cache keys: cache poisoning risk from untrusted PRs, broad restore keys, lockfile omission, cross-branch sharing, mutable dependency caches, and use in privileged jobs.
- Artifact retention: explicit retention periods, sensitive content in artifacts, public exposure, and whether release artifacts are reproducible or traceable.
- Third-party action/template pinning: flag unpinned actions, orbs, includes, Docker images, installers, curl-pipe-shell patterns, and dependencies fetched in CI. Prefer immutable SHAs or verified trusted tags according to the ecosystem's norms.

### 5. Compare Jobs to Repository Manifests

Identify expected verification from repository evidence, then compare against actual pipeline coverage:

- JavaScript/TypeScript: `package.json` scripts, package manager lockfiles, `tsconfig*.json`, ESLint/Prettier/Vitest/Jest/Playwright/Cypress configs.
- Python: `pyproject.toml`, `requirements*.txt`, `tox.ini`, `noxfile.py`, `pytest.ini`, `ruff.toml`, `mypy.ini`.
- Rust: `Cargo.toml`, `Cargo.lock`, `cargo test`, `cargo clippy`, `cargo fmt`.
- Go: `go.mod`, `go.sum`, `go test`, `go vet`, staticcheck/golangci-lint configs.
- Java/Kotlin/Scala: Maven/Gradle/SBT manifests and test/lint tasks.
- Containers/IaC: Dockerfiles, Compose files, Helm charts, Terraform/OpenTofu, Kubernetes manifests, policy-as-code, image scanning, and plan/apply separation.

Report missing or partial jobs when manifests show available `test`, `lint`, `typecheck`, build, formatting, or security checks that are absent from CI, only run manually, or do not gate deploy/release jobs.

### 6. Reporting Contract

Report findings as actionable issues. Each finding must include:

- **ID and severity**: concise stable identifier and risk rating.
- **Workflow and job name**: exact workflow/pipeline file name plus job/stage name.
- **File path and line evidence**: cite the relevant path and lines when available.
- **Issue**: what is unsafe, missing, ambiguous, or unverifiable.
- **Impact**: how the issue could affect pull requests, protected branches, secrets, deployments, artifacts, or supply chain integrity.
- **Recommendation**: minimal remediation, noting when a protected-area/Tier 1 change requires explicit approval.
- **Verification**: command or repository check that would confirm the fix.

Use this format:

```markdown
### CI-001: Privileged PR trigger can access deploy credentials

- Severity: High
- Workflow/job: `.github/workflows/deploy.yml` / `deploy-production`
- Evidence: `.github/workflows/deploy.yml:3-42`
- Issue: ...
- Impact: ...
- Recommendation: ...
- Verification: ...
```

## Stop Conditions

Stop and report instead of guessing when:

- Remote branch protection, environment approval, organization secrets, or hosted CI settings are required but unavailable locally.
- A workflow uses generated includes or external templates that cannot be inspected.
- The repository contains deployment behavior but the target environment or approval model is not represented in repository-controlled files.
- Findings would require editing protected CI/CD deployment workflows; request explicit approval for remediation rather than applying changes during an audit.

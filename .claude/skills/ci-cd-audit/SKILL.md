---
name: ci-cd-audit
description: Use when asked to audit CI or deployment pipeline security across GitHub Actions, GitLab CI, CircleCI, or Azure Pipelines and compare configured checks against repository requirements. Trigger on audit our CI, review workflow security, check deployment pipeline, validate GitHub Actions or GitLab CI config. NOT for producing one filed issue per finding with file and job level remediation; use cicd-workflow-audit instead. Requires treating CI/CD deployment workflows as protected and reporting findings without editing them unless explicitly requested.
when_to_use: Use for read-only static CI/CD security and coverage audits across GitHub Actions, GitLab CI, CircleCI, Azure Pipelines, and equivalent workflow systems.
argument-hint: "[optional CI provider, workflow path, or audit focus]"
allowed-tools: Read, Grep, Glob, Bash
---

# CI/CD Audit

Perform a static, evidence-driven inspection of repository CI/CD configuration. Keep the audit read-only unless the user explicitly asks for remediation after findings are reported.

## Trigger Text

Use this skill when the user asks to:

- "audit CI"
- "review workflow security"
- "check deployment pipeline"
- "validate GitHub Actions"
- inspect GitLab CI, CircleCI, Azure Pipelines, Buildkite, Jenkins, Drone, Woodpecker, Harness, Argo, release scripts, or similar automation

## Audit Inputs

Inspect repository-controlled evidence only:

- Workflow definitions:
  - GitHub Actions: `.github/workflows/*.yml`, `.github/workflows/*.yaml`, reusable workflows, composite actions, action metadata, and workflow-dispatch inputs.
  - GitLab CI: `.gitlab-ci.yml`, included CI files, child pipelines, deployment jobs, protected environments, and runner tags.
  - CircleCI: `.circleci/config.yml`, orbs, contexts, approval jobs, workspaces, caches, and artifacts.
  - Azure Pipelines: `azure-pipelines.yml`, templates, variable groups referenced by YAML, stages, environments, approvals, and service connections referenced by name.
  - Other systems: Buildkite, Jenkins, Drone, Woodpecker, Harness, Argo, release scripts, deploy manifests, package-publish automation, infrastructure pipelines, or scheduled jobs.
- Repository documentation that declares required checks, release policy, deployment policy, contribution gates, or security requirements.
- Manifests and tool configuration that imply expected build, test, lint, typecheck, package, container, or publish checks.

Do not read local secret files such as `.env`, credential stores, private keys, or untracked personal configuration.

## Procedure

1. **Establish scope and inventory.**
   - Resolve the repository root with `git rev-parse --show-toplevel` when available.
   - Enumerate CI/CD files with targeted file discovery, not broad recursive scans.
   - Record provider, workflow name, triggers, jobs/stages, dependencies, deployment jobs, secrets, permissions, caches, artifacts, and external templates/actions/orbs/images.

2. **Review trigger safety.**
   - Flag `pull_request_target` risks, especially checkout of untrusted PR head, script execution from a fork, write tokens, secret access, cache writes, artifact trust, or deployment from PR context.
   - Check fork and external-contributor paths for privilege escalation through labels, comments, workflow inputs, reusable workflows, generated scripts, or compromised dependencies.
   - Review `workflow_run`, `repository_dispatch`, `workflow_dispatch`, schedules, tags, releases, merge-request events, deployment events, broad branch filters, and path filters.
   - Verify privileged events cannot run unreviewed code with secrets, write credentials, protected runners, or deployment permissions.

3. **Review permissions, secrets, environments, and OIDC.**
   - Check GitHub `permissions` blocks, job-level overrides, default token scope, GitLab/CircleCI/Azure equivalents, package registry tokens, and write-capable credentials.
   - Confirm secrets are scoped to trusted jobs, protected environments or contexts, and trusted branches/tags only.
   - Verify secrets are not echoed, written into artifacts, exposed in cache keys, passed to untrusted scripts, or available in jobs that process untrusted input.
   - For OIDC, verify trust boundaries are narrow: expected repository, branch/tag/environment, audience, subject claims, cloud role, and no broad wildcard assumptions.
   - Mark remote platform settings that cannot be verified from files as **unverified**, not safe.

4. **Evaluate build, test, lint, and typecheck coverage.**
   - Compare workflows against manifests and docs: package scripts, Makefiles, task runners, language config, lockfiles, Dockerfiles, test config, lint config, typecheck config, and release docs.
   - Identify missing or partial checks, checks not required before deploy, and jobs that are allowed to fail without clear policy.
   - Note matrix gaps such as unsupported operating systems, language versions, package managers, services, database versions, or deploy targets.

5. **Review cache, dependency, action, and artifact safety.**
   - Check cache keys for untrusted input, branch collisions, broad restore keys, cross-fork poisoning, writable caches on privileged workflows, and lockfile coverage.
   - Review dependency installation for lockfile enforcement, frozen installs, script execution, registry trust, dependency confusion, and package-manager auth scope.
   - Check third-party actions, orbs, includes, images, and templates for pinning to immutable SHAs or trusted versions.
   - Review artifacts for retention, integrity, provenance, promotion across trust boundaries, and accidental secret inclusion.

6. **Review deployment approvals, protected environments, and rollback hooks.**
   - Identify jobs that deploy, publish, sign, release, upload packages, mutate infrastructure, write to protected branches, or update production configuration.
   - Confirm deployment jobs are gated by branch/tag filters, `needs`/stage dependencies, required verification jobs, protected environments, manual approvals, protected contexts, or equivalent controls.
   - Check separation of build/test from deploy and ensure deploy jobs do not rebuild from mutable or unverified inputs.
   - Look for rollback hooks, release identifiers, promoted immutable artifacts, deployment logs, version metadata, previous artifact retention, and documented rollback procedures.

7. **Compare with repository-required checks.**
   - Read repository docs such as `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, release docs, governance docs, branch-protection notes, and PR templates.
   - Compare documented required checks with actual workflow jobs and status names where visible.
   - Flag missing required checks, stale docs, renamed jobs, orphaned workflows, and checks present in docs but absent from CI configuration.
   - If branch protection or required status checks are only configured remotely, state that they require platform verification.

## Finding Standards

For each finding, include:

- Severity: Blocking or Non-blocking.
- Evidence: file path, line, workflow/job/stage name, and relevant trigger or step.
- Risk: what can go wrong and who can exploit or trigger it.
- Recommendation: smallest practical remediation.
- Verification: command, config check, or platform setting needed to confirm the fix.

Treat as **blocking** when there is credible risk of secret exposure, privileged execution from untrusted code, unintended deployment/publish, bypassed required checks, broad write credentials, cache poisoning into privileged jobs, or no rollback path for production-impacting deploys.

## Output Format

Return a concise report in this structure:

```markdown
## Summary
- Scope inspected:
- CI/CD providers found:
- Highest risk:

## Blocking findings
- [Severity] Finding title
  - Evidence:
  - Risk:
  - Recommendation:
  - Verification:

## Non-blocking findings
- [Severity] Finding title
  - Evidence:
  - Risk:
  - Recommendation:
  - Verification:

## Recommended checks
- Checks to add or require before merge/deploy:
- Platform settings to verify remotely:
- Follow-up commands or files to inspect:

## Risk and rollback notes
- Deployment risk:
- Secret/token risk:
- Cache/dependency risk:
- Rollback readiness:
```

If no findings are confirmed, say so and list any unverified platform settings or repository assumptions that still need human confirmation.

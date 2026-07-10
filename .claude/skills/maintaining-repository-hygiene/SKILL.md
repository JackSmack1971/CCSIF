---
name: maintaining-repository-hygiene
description: Trigger on queries that say audit repository hygiene, clean up stale worktrees, prune unused labels, or check documentation rot and command alignment. Use for repository hygiene, repo cleanup, stale worktrees, unused labels, community health files, CODEOWNERS, Dependabot, branch protection, documentation drift, or professionalization audits. Audits and professionalizes code-agnostic GitHub repositories by detecting the exact stack and workspace topology, reviewing .github governance and GitHub Actions, inspecting repository settings and tracked artifacts, and creating one idempotent GitHub issue per atomic implementation step. NOT for a single CODEOWNERS file use generate-codeowners instead, and NOT for a full 7-axes code quality audit use 7axes-audit instead. Distinct keywords stale worktree metadata, prunable labels, digest-bound remediation plan, community health files, idempotent issue creation.
when_to_use: Use for repository-wide hygiene, governance, and professionalization audits, not for a single CODEOWNERS file or a scored 7-axes quality run.
argument-hint: "[repository root] [--remote auto|on|off] [--policy path.json]"
allowed-tools: Read, Grep, Glob, Bash, Write
---

# Maintaining Repository Hygiene

## Table of contents

1. Objective
2. Non-negotiable rules
3. Inputs and operating modes
4. Default workflow
5. Stack discovery
6. Audit coverage
7. Issue planning and publication
8. Label pruning
9. Worktree pruning
10. Verification loop
11. Output contract
12. Failure handling
13. Resources

## 1. Objective

Bring a GitHub repository into evidence-backed professional alignment without assuming its language, framework, package manager, topology, visibility, or collaboration model.

The default deliverable is:

- a stack profile;
- a machine-readable and human-readable audit;
- explicit coverage gaps;
- a digest-bound remediation plan;
- exactly one GitHub issue per atomic implementation step;
- separate guarded plans for destructive label and worktree maintenance;
- a post-remediation verification report.

Do not implement arbitrary repository changes during the audit. Produce implementation issues unless the user separately requests remediation.

## 2. Non-negotiable rules

1. **Evidence before assertion.** Prefer manifests, lockfiles, workspace files, CI, build configuration, Git, and authenticated GitHub state over file-extension guesses.
2. **Read-only first.** Audit before planning; plan before writing; recheck before deletion.
3. **No fabricated coverage.** Permission denial, missing `gh`, unavailable network, incomplete pagination, or unavailable YAML parsing is degraded coverage—not proof that a control is absent.
4. **No secret disclosure.** Report sensitive paths and rule matches only. Never print credential contents.
5. **One issue per implementation step.** Group findings only when they share the same change boundary, owner, rollback, and verification evidence.
6. **Idempotent publication.** Use the stable `repository-hygiene-step` marker and publication journal. Existing open or closed issues suppress duplicates.
7. **Fail closed on deletion.** Never delete a label after an incomplete history scan. Never prune worktree metadata when a fresh dry run differs from the reviewed plan.
8. **Preserve uncertainty.** Turn low-confidence signals into investigation checkboxes; do not state heuristics as facts.
9. **Do not execute project code during discovery.** Do not install dependencies, run arbitrary build scripts, or execute repository binaries unless the user expands scope.
10. **Do not broaden scope silently.** Branch deletion, history rewriting, file removal, ruleset edits, and repository-setting changes remain issue-based recommendations unless explicitly requested through a separate reviewed workflow.

Read the complete decision rubric when interpreting findings: [references/audit-rubric.md](references/audit-rubric.md).

## 3. Inputs and operating modes

Resolve these from the request and current checkout:

- repository root;
- remote mode: `auto`, `on`, or `off`;
- whether GitHub issues should be drafted or published;
- optional policy override JSON;
- whether destructive label/worktree cleanup is requested now or only planned.

Defaults:

- repository: current Git root;
- remote mode: `auto`;
- policy: [resources/default-policy.json](resources/default-policy.json);
- report directory: `.repository-hygiene/`;
- issue behavior: generate validated drafts; publish only when the request explicitly asks to create/open/publish issues;
- destructive operations: plan only until the user reviews the plan and confirms its digest.

Modes:

- **Audit:** read-only report and issue drafts.
- **Audit + publish:** report, validate, then create every planned issue.
- **Maintenance:** audit plus separately confirmed label/worktree operations.
- **Verify:** re-audit after implementation and compare stable finding IDs.

## 4. Default workflow

Copy and maintain this checklist:

```text
Repository Hygiene Progress
- [ ] 1. Preflight the checkout and tools
- [ ] 2. Detect stack and repository topology
- [ ] 3. Run local and remote audit
- [ ] 4. Inspect coverage degradation and high-risk evidence
- [ ] 5. Perform evidence-backed semantic snapshot alignment
- [ ] 6. Generate and validate the authoritative atomic issue plan
- [ ] 7. Publish issues when explicitly requested
- [ ] 8. Generate label/worktree maintenance plans when applicable
- [ ] 9. Review and confirm destructive-plan digests before applying
- [ ] 10. Re-audit and record verification evidence
```

### Step 1: Preflight

Run from any path inside the target checkout:

```bash
python3 <skill-root>/scripts/repository_hygiene.py audit \
  --repo . \
  --out-dir .repository-hygiene \
  --remote auto
```

On Windows where `python3` is unavailable, use `py -3` or `python` with the same arguments.

Stop when:

- the path is not a Git worktree;
- Python is below 3.10;
- the repository cannot be read;
- remote mode is `on` but `gh` is unavailable or unauthenticated.

Do not stop a local audit merely because remote coverage is unavailable in `auto` mode.

### Step 2: Inspect generated artifacts

Required outputs:

```text
.repository-hygiene/
├── report.json
├── report.md
├── stack-profile.json
├── issue-plan.json
├── issue-plan.md
├── supplemental-findings.json # when semantic review adds findings
└── label-prune-plan.json       # when authenticated remote label audit succeeds
```

Read `report.md`, then inspect the JSON evidence for every critical/high finding and every low-confidence finding. Check that the detected stack includes every independent project boundary.

### Step 3: Perform semantic snapshot alignment

Deterministic checks cannot prove that prose accurately describes architecture, support status, data flow, deployment, ownership, or operational behavior. Perform a bounded semantic pass after reading the stack profile and deterministic report.

Inspect high-value documents against current manifests, entry points, CI, deployment configuration, schemas, and directory topology. Add a finding only when it contains at least two concrete evidence anchors: the documented claim and the current contradictory or missing implementation evidence. Mark ambiguous intent `low` confidence and make investigation the first checklist item.

Start from [resources/supplemental-findings.template.json](resources/supplemental-findings.template.json), remove the example, and write only real findings. Never use semantic review to invent required technologies or generic style preferences.

Merge validated supplements:

```bash
python3 <skill-root>/scripts/repository_hygiene.py findings-merge \
  --report .repository-hygiene/report.json \
  --supplement .repository-hygiene/supplemental-findings.json \
  --out .repository-hygiene/report.json \
  --markdown .repository-hygiene/report.md
```

Then regenerate the authoritative issue plan:

```bash
python3 <skill-root>/scripts/repository_hygiene.py issues-plan \
  --report .repository-hygiene/report.json \
  --out .repository-hygiene/issue-plan.json \
  --markdown .repository-hygiene/issue-plan.md
```

When no semantic mismatch is found, record that the pass was performed and retain the deterministic report unchanged.

### Step 4: Validate issue plan

```bash
python3 <skill-root>/scripts/repository_hygiene.py issues-validate \
  --plan .repository-hygiene/issue-plan.json
```

If validation fails, fix the underlying report-to-step mapping or regenerate the plan. Never hand-edit a plan and preserve its old digest.

### Step 5: Publish when authorized

Display the issue count, titles, destructive flags, repository, source HEAD, and plan digest. When the request explicitly asks to create GitHub issues, that request authorizes issue publication after validation.

```bash
python3 <skill-root>/scripts/repository_hygiene.py issues-publish \
  --repo . \
  --plan .repository-hygiene/issue-plan.json \
  --confirm-digest <digest-from-plan> \
  --ensure-labels \
  --journal .repository-hygiene/issue-publication-journal.json \
  --max-issues <validated-step-count>
```

Do not use `--allow-head-change` by default. Re-audit when HEAD changed. Use it only when the change is understood and the issue evidence remains valid.

## 5. Stack discovery

The stack profile must be code agnostic and evidence-rich. Detect:

- package/build manifests and lockfiles;
- language ecosystems and frameworks;
- package managers and declared versions;
- monorepo/workspace boundaries;
- containers, infrastructure, deployment, and documentation tooling;
- canonical install, build, test, lint, type-check, docs, and release commands;
- CI-observed commands;
- generated-output directories and release targets.

Support at minimum:

- JavaScript/TypeScript, Python, Rust, Go, Java/Kotlin, .NET, Ruby, PHP, Swift, Elixir, Dart/Flutter, C/C++, Bazel, Nix, Terraform, Docker, Helm, and GitHub Actions;
- polyglot and nested projects;
- npm, pnpm, yarn, Bun, pip/uv/Poetry/Pipenv, Cargo, Go modules, Maven, Gradle, NuGet, Bundler, Composer, SwiftPM, Mix, and Pub.

Rules:

- File extensions alone are weak evidence.
- Multiple ecosystems are valid.
- Multiple package managers are a conflict only inside the same project boundary.
- Framework matches are signals with cited manifest evidence, not exclusive classifications.
- CI commands can corroborate but must not override contradictory canonical manifests without investigation.

## 6. Audit coverage

Apply the detailed rules in [references/audit-rubric.md](references/audit-rubric.md). Cover these axes:

### Git and repository contents

- stale worktree administrative metadata using Git's dry run;
- locked/offline worktrees;
- local branches with gone upstreams;
- accidental nested repositories;
- tracked generated, cache, dependency, virtual-environment, and build output;
- sensitive filenames without reading contents;
- large tracked files and archives;
- contradictory lockfiles and missing/unsafe ignore policy.

### `.github/` and automation

- GitHub-recognized community-health file locations;
- README, SECURITY, CONTRIBUTING, license, support, code of conduct, citation, and funding where contextually applicable;
- CODEOWNERS coverage and maintainership boundaries;
- pull-request templates, issue templates/forms, and referenced labels;
- Dependabot coverage for every detected active ecosystem/directory;
- GitHub Actions syntax, explicit permissions, full-SHA action pinning, bounded timeouts, untrusted-input interpolation, `pull_request_target`, release/deployment concurrency, and broad write scopes.

### Documentation truthfulness

- broken local links, images, and anchors;
- references to removed files;
- commands absent from the nearest manifest or automation boundary;
- package-manager and setup contradictions;
- architecture/setup claims inconsistent with the current tree;
- age-based review signals, clearly marked as heuristic;
- missing maintenance, support, security, and ownership routes.

External URL checks are off by default. Do not claim they were checked.

### GitHub remote state

When authenticated permissions allow, inspect:

- repository description, homepage, topics, visibility, archive state, and Issues availability;
- default branch, rulesets, and legacy branch protection;
- merge methods and automatic merged-branch deletion;
- labels, issue/pull-request history, and label references;
- contributor count and relevant security/settings endpoints.

A `403` is a coverage limitation. A `404` may mean absent, unavailable by plan, or hidden by permissions; interpret it with corroborating evidence.

## 7. Issue planning and publication

Follow [references/issue-contract.md](references/issue-contract.md).

Each actionable finding must appear in exactly one issue step. Each issue must include:

- imperative atomic outcome;
- stable hidden fingerprint;
- detected stack context;
- severity and confidence;
- exact evidence without secrets;
- implementation checklist;
- acceptance criteria;
- deterministic verification;
- dependencies;
- risk, rollback, and non-goals.

Grouping is allowed only when findings modify the same policy/file boundary, require the same owner and permissions, share rollback, and pass through the same verification gate. Otherwise split them.

Issue publication rules:

- search open and closed issues for the stable marker before creation;
- create no duplicate even when resuming after interruption;
- journal each created, skipped, or failed step immediately;
- stop on the first publication failure;
- resume with the same validated plan and journal;
- keep informational findings out of implementation issues unless policy raises them.

## 8. Label pruning

Generate the plan:

```bash
python3 <skill-root>/scripts/repository_hygiene.py labels-plan \
  --repo . \
  --out .repository-hygiene/label-prune-plan.json
```

A deletion candidate requires:

- complete pagination through configured issue and pull-request history;
- zero historical associations;
- no reference in `.github/`, issue forms, workflows, label automation, or documentation;
- no protected name or prefix;
- a fresh identical candidate set immediately before deletion.

GitHub's label API does not provide a reliable creation timestamp, so age is not invented or used as a safety claim.

Before applying, display every label, the evidence, and the plan digest. Require explicit confirmation of that digest because deletion is destructive.

```bash
python3 <skill-root>/scripts/repository_hygiene.py labels-apply \
  --repo . \
  --plan .repository-hygiene/label-prune-plan.json \
  --confirm-digest <digest-from-plan>
```

Stop if history is incomplete, references appear, labels changed, repository identity differs, or any deletion fails.

## 9. Worktree pruning

Generate the plan with Git's native dry run:

```bash
python3 <skill-root>/scripts/repository_hygiene.py worktrees-plan \
  --repo . \
  --out .repository-hygiene/worktree-prune-plan.json
```

Review `git worktree list --porcelain`. Lock any intentionally offline/removable-media worktree before pruning.

Apply only after explicit digest confirmation:

```bash
python3 <skill-root>/scripts/repository_hygiene.py worktrees-apply \
  --repo . \
  --plan .repository-hygiene/worktree-prune-plan.json \
  --confirm-digest <digest-from-plan>
```

This operation prunes stale administrative records. It must never be represented as deleting live worktree directories.

## 10. Verification loop

After issues are implemented or maintenance runs:

```bash
python3 <skill-root>/scripts/repository_hygiene.py verify \
  --repo . \
  --baseline .repository-hygiene/report.json \
  --out .repository-hygiene/verification.json \
  --remote auto
```

Use this loop:

1. Re-audit from the current HEAD.
2. Compare resolved, remaining, and new finding IDs.
3. Run every issue-specific verification command.
4. Fix failures without weakening the rule.
5. Re-run until acceptance criteria pass or record a justified exception.
6. Close issues only with fresh evidence.

Do not claim repository alignment from issue creation alone.

## 11. Output contract

At completion, report:

- repository and audited HEAD;
- detected ecosystems, frameworks, package managers, and workspace boundaries;
- coverage completed/degraded/skipped;
- finding counts by severity/confidence/category;
- issue-plan count and publication results;
- label/worktree plan counts and whether they were applied;
- unresolved critical/high findings;
- verification commands and exit results;
- artifact paths.

Script exit codes:

- `0`: operation completed;
- `1`: requested audit/verification policy threshold failed;
- `2`: expected operational or validation failure;
- `3`: unexpected internal failure.

Every CLI command emits a one-line machine-readable JSON status object and a human-readable error on stderr when applicable.

## 12. Failure handling

- Missing `gh` in `auto` mode: complete local audit and mark remote coverage skipped/degraded.
- Missing `gh` in `on` mode: stop remote-dependent workflow.
- Missing PyYAML: continue text-level workflow checks and record degraded syntax coverage.
- Incomplete label history: produce inventory and suppress all deletion candidates.
- Changed HEAD before publication: re-audit; do not publish stale evidence by default.
- Interrupted issue publication: resume from journal; marker search prevents duplicates.
- Changed label/worktree state: discard the plan and regenerate.
- Permission denial: report the exact unavailable surface without inferring its state.
- Validation failure: fix, regenerate, validate again; never bypass a failed digest or schema gate.

## 13. Resources

Load only what the current step requires:

- Audit decisions: [references/audit-rubric.md](references/audit-rubric.md)
- Issue atomicity and format: [references/issue-contract.md](references/issue-contract.md)
- Runtime, permissions, and security: [references/portability-security.md](references/portability-security.md)
- Default policy: [resources/default-policy.json](resources/default-policy.json)
- Finding schema: [resources/finding.schema.json](resources/finding.schema.json)
- Supplemental finding template: [resources/supplemental-findings.template.json](resources/supplemental-findings.template.json)
- Evaluation scenarios: [evaluations/EVALUATIONS.md](evaluations/EVALUATIONS.md)
- Deterministic CLI: [scripts/repository_hygiene.py](scripts/repository_hygiene.py)
- Skill validator: [scripts/validate_skill.py](scripts/validate_skill.py)
- Unit tests: [tests/test_repository_hygiene.py](tests/test_repository_hygiene.py)
- Verification log: [VERIFICATION.md](VERIFICATION.md)

Before packaging or installation, run:

```bash
python3 <skill-root>/scripts/validate_skill.py --skill-root <skill-root>
python3 -m unittest discover -s <skill-root>/tests -v
```

Only state **Done & Verified** when metadata, direct-reference structure, JSON, Python compilation, tests, issue-plan validation, and package layout all pass with fresh evidence.

# Portability, Security, and Operations

## Table of contents

1. Runtime contract
2. Surface support
3. Permission model
4. Network behavior
5. Destructive-operation controls
6. Data handling
7. Failure and recovery
8. Third-party trust

## 1. Runtime contract

Required for local auditing:

- Python 3.10 or newer
- Git 2.31 or newer
- a non-bare Git checkout

Required for GitHub inventory, issue publication, and label maintenance:

- GitHub CLI (`gh`)
- an authenticated identity with the minimum repository permissions needed for the requested operation

Optional:

- PyYAML for full workflow YAML parse checks
- `actionlint` for independent GitHub Actions verification
- project-native tools for acceptance testing after remediation

The bundled implementation uses only the Python standard library. It does not install dependencies or execute package-manager install scripts during an audit.

## 2. Surface support

### Claude Code

Preferred surface. Install the skill in `.claude/skills/` for project scope or `~/.claude/skills/` for personal scope. Run scripts from a checked-out repository. Claude Code can inspect generated plan files and use `gh` when the user grants access.

### Claude.ai

The ZIP can be uploaded as a custom skill when code execution is available. A repository archive is sufficient for local-only analysis, but Git metadata, worktrees, and authenticated GitHub operations require a real checkout and available CLIs. Treat unavailable capabilities as degraded coverage.

### Claude API

The skill is portable as files, but hosted code-execution containers may have no network access and may not contain GitHub CLI or repository credentials. Pre-bake required tools or run the deterministic scripts in a controlled worker. Never assume package installation or outbound network access.

## 3. Permission model

Use the least-privileged token or GitHub App installation possible.

Read-only remote audit generally needs repository metadata, contents, issues, pull requests, labels, contributors, and rules/protection visibility. Some security or ruleset endpoints require elevated repository administration permissions; a denied response is recorded as degraded coverage.

Issue publication needs Issues write permission. Label deletion needs Issues write permission. Ensuring labels may need the same permission. The skill does not modify branch protection, rulesets, repository settings, files, branches, or pull requests.

## 4. Network behavior

Local audit is offline by default except when `--remote on` or authenticated `--remote auto` succeeds. GitHub operations call only the configured GitHub host through `gh`.

External documentation links are not crawled by default. This avoids nondeterministic failures, credential leakage through URLs, and unexpected requests to untrusted hosts. A future external-link checker must use an allowlist, bounded concurrency, redirects limits, timeouts, and no authentication forwarding.

## 5. Destructive-operation controls

The audit and issue-plan stages are read-only. GitHub issue creation is a remote write but is idempotent and journaled.

Label deletion and worktree metadata pruning require all of the following:

- a generated JSON plan
- a valid embedded SHA-256 digest
- the same digest supplied through `--confirm-digest`
- a fresh state recheck immediately before execution
- exact repository identity match
- stop-on-first-failure behavior

A label is never proposed when issue/pull-request history scanning is incomplete. A worktree prune invokes Git's own dry run first and never deletes a registered worktree directory. Lock intentionally offline worktrees before applying a prune plan.

Branch deletion, history rewriting, file deletion, and repository-setting changes are deliberately outside executable scope. Findings for those actions become reviewable GitHub issues.

## 6. Data handling

- Secret-like files are detected by path only; their contents are not emitted.
- Text scanning is bounded by policy size limits.
- Generated reports can reveal repository paths, metadata, workflow snippets, and governance gaps. Store them as sensitive engineering artifacts for private repositories.
- Issue bodies must not contain credentials, private URLs, customer data, or unpublished vulnerability details.
- Publication journals record status, titles, fingerprints, and URLs, not tokens.

## 7. Failure and recovery

All commands emit one machine-readable JSON status object. Expected failures use exit code `2`; unexpected internal failures use `3`. Audit policy failures requested with `--fail-on` use exit code `1`.

Issue publication writes the journal after every created or skipped issue. Re-running the same plan searches the stable body marker and resumes without duplicates, including when an existing issue is closed.

Label deletion and worktree pruning stop on the first failed operation. Re-audit and regenerate the plan before retrying; never edit a plan and reuse its old digest.

## 8. Third-party trust

Treat downloaded skills, scripts, actions, templates, and policy files as untrusted software. Before installation:

- inspect every bundled executable and resource
- search for network calls, subprocess execution, credential reads, and destructive commands
- verify that scripts stay inside their declared scope
- run the bundled validator and tests in an isolated repository
- review policy overrides before use

Do not copy remediation content from an issue into a privileged shell without reviewing it against current repository evidence.

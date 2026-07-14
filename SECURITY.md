# Security Policy

## Reporting a Vulnerability

Report suspected security vulnerabilities in this repository through
[GitHub Security Advisories](https://github.com/JackSmack1971/CCSIF/security/advisories/new)
("Report a vulnerability" on the repository's Security tab). Do not open a
public issue or pull request for a suspected vulnerability, and do not
disclose details anywhere else until a fix is available.

Include in your report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, including affected files, hooks, workflows, or skills
  under `.claude/`.
- Any relevant logs, trace excerpts, or configuration values (redact
  secret material before sharing).

You should receive an initial acknowledgement within 5 business days. We
will keep you informed of remediation progress and coordinate a disclosure
timeline with you before any public write-up.

## Supported Versions

This repository does not publish versioned releases. Security fixes are
applied to the `main` branch; there are no other maintained branches.

## Scope

This is a repository-local Claude Code scaffold: agent, hook, workflow,
rule, and skill definitions under `.claude/`, plus the
project constitution in [`CLAUDE.md`](./CLAUDE.md). Security-relevant areas
include:

- Hook scripts (`.claude/hooks/`) and any code they
  execute.
- Workflow scripts (`.claude/workflows/`).
- Permission and settings files (`.claude/settings.json`,
  `.claude/settings.local.json`, `.mcp.json`).
- MCP server configuration and approvals.

See [`CLAUDE.md`](./CLAUDE.md) for the Protected Areas that require
explicit human approval before modification (production configuration,
authentication and authorization, database migrations, payment or trading
logic, CI/CD deployment workflows, and secret material), and
[`.claude/rules/security.md`](./.claude/rules/security.md) for the
repository's day-to-day security rules.


## Current Repository Hardening

The repository currently hardens Claude Code usage through shared settings, hook guards, and GitHub governance rather than through application runtime controls. The current behavior includes:

- `PreToolUse` runs the protected-area guard before tool use and preserves hard blocks for genuine safety failures.
- Phase 0 request tracking warns without blocking otherwise-safe tool calls when tracking state cannot be written.
- Shared Claude settings disable bypass-permissions mode, disable skill shell execution, enable the configured `graphiti-memory` MCP server explicitly, and define shell allow/ask/deny rules for risky actions and sensitive paths.
- GitHub issue forms, the pull request template, CODEOWNERS, Dependabot configuration, and CI are checked in under `.github/`.

## Out of Scope

- Vulnerabilities in upstream tools this repository configures (Claude
  Code, Codex, Git, Node.js, Python) should be reported to their
  respective maintainers.
- Findings that require an already-compromised local machine or an
  attacker with existing write access to this repository.

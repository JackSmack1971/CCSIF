---
name: dependency-audit
description: Use when auditing dependency manifests, lockfiles, or supply-chain risk before an upgrade. Trigger on audit our dependencies, check for vulnerable packages, review lockfile drift, assess upgrade safety risk. NOT for actually upgrading or patching dependencies; use the repository's package manager directly instead. Requires citing manifest, lockfile, or advisory evidence for every reported finding.
allowed-tools: Read, Grep, Glob, Bash
when_to_use: Use to audit dependency manifests, lockfiles, and supply-chain risk, not to actually upgrade or patch dependencies.
argument-hint: "(no arguments; audits the current repository's manifests and lockfiles)"
disallowed-tools: Write, Edit
---

# Dependency Audit

Inspect:

- Package manifests and lockfiles
- Deprecated or abandoned dependencies
- Known vulnerable packages
- Duplicate or conflicting dependency trees
- Postinstall scripts and native extensions
- CI install behavior
- Runtime version constraints

Do not upgrade dependencies during audit-only mode. Create isolated findings with evidence and verification steps using [references/audit-template.md](references/audit-template.md).

## Checklist

- [ ] Enumerate manifests and lockfiles for every package ecosystem present.
- [ ] Flag deprecated, abandoned, or known-vulnerable packages with evidence.
- [ ] Flag duplicate or conflicting dependency trees.
- [ ] Flag postinstall scripts and native extensions.
- [ ] Note CI install behavior and runtime version constraints.
- [ ] Report findings with verification steps without modifying manifests or lockfiles.

**Stop condition:** stop and report instead of auditing further if a lockfile is missing for a manifest that requires one; do not infer resolved versions.

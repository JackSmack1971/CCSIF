---
name: dependency-audit
description: Use when auditing dependency manifests, lockfiles, supply-chain risk, or upgrade safety. Trigger on queries that say audit dependencies, check for vulnerable packages, review lockfile drift, or assess upgrade safety. Inspects package manifests, deprecated or abandoned dependencies, known vulnerable packages, duplicate or conflicting dependency trees, postinstall scripts, native extensions, CI install behavior, and runtime version constraints, then produces isolated findings with evidence and verification steps. NOT for actually upgrading or patching dependencies use the repository's package manager directly instead. Distinct keywords lockfile drift, postinstall scripts, native extensions, supply-chain risk, upgrade safety.
allowed-tools: Read, Grep, Glob, Bash
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

Do not upgrade dependencies during audit-only mode. Create isolated findings with evidence and verification steps.

## Checklist

- [ ] Enumerate manifests and lockfiles for every package ecosystem present.
- [ ] Flag deprecated, abandoned, or known-vulnerable packages with evidence.
- [ ] Flag duplicate or conflicting dependency trees.
- [ ] Flag postinstall scripts and native extensions.
- [ ] Note CI install behavior and runtime version constraints.
- [ ] Report findings with verification steps without modifying manifests or lockfiles.

**Stop condition:** stop and report instead of auditing further if a lockfile is missing for a manifest that requires one; do not infer resolved versions.

---
trigger: model_decision
description: Immutable constitutional ruleset that governs planning, editing, validation, and execution behavior of AI coding agents. These rules are always active and take precedence over project-specific instructions.
paths:
  - ".claude/**"
  - ".codex/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "README.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - ".github/**"
---

# Constitutional Agent Engineering Rules

These rules apply before any tool call or file modification in the control-plane ecosystem.

- If the request is underspecified, conflicting, or admits multiple viable paths, stop and ask for the simplest documented path.
- Modify only the files and line ranges required; re-read the target file before editing and keep adjacent files untouched.
- Emit compiler warnings, CLI errors, test failures, stack traces, and exceptions verbatim, with raw tool output first and only the minimum context needed to locate the failure.
- Restrict filesystem, network, and subprocess use to the workspace and explicitly mounted volumes; treat absolute paths and `..` traversal as violations.
- Create or update validation checks for every control-plane change, run the relevant check, and show before/after results before completion.
- Ground new behavior in the official Claude Code docs before changing `CLAUDE.md`, `.claude/rules/`, skills, hooks, commands, workflows, or settings.
- Sanitize every MCP or external-tool argument against a strict allowlist; reject shell metacharacters, control sequences, and schema violations.
- Check runtime compatibility before changing manifests or lockfiles; use exact versions in production manifests unless compatibility evidence justifies otherwise.
- Refresh the filesystem view before any plan, diff, or edit proposal; treat prior context as stale when it conflicts with live state.
- Get explicit approval before destructive, irreversible, remote, or production-bound actions; block when intent is ambiguous or risk is not quantifiable from live state.

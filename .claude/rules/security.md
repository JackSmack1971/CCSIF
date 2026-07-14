---
name: security
description: Security-sensitive coding rules.
paths:
  - ".claude/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "SECURITY.md"
  - ".github/**"
  - ".mcp.json"
  - "managed-settings.json"
---

# Security Rules

- Validate external input at trust boundaries in hooks, commands, scripts, and workflow automation.
- Redact secrets, tokens, cookies, and authorization headers from logs, traces, and generated docs.
- Treat CI/CD, permission, settings, connector, `.github/**`, `SECURITY.md`, and `.claude/rules/**` changes as privileged control-plane edits, and prefer explicit allowlists for commands, hosts, paths, and tool arguments.
- On the first protected-area block, halt rather than retrying, rephrasing the path, using Bash redirection, attempting a workaround, or copying content through another file; report the exact blocked path/category and wait for human direction.
- `permissions.defaultMode: "default"` and `disableBypassPermissionsMode: "disable"` in `.claude/settings.json` keep `--dangerously-skip-permissions` from bypassing the rules below; `permissions.deny`/`ask` carry native `Read`/`Edit`/`Write` globs for secrets, CI/CD, migrations, ledger, and lockfiles as the primary (rung 5) boundary, with `pre-tool-use-guard.js` (rung 4) as defense in depth — see `.claude/rules/40-determinism-ladder.md`. `sandbox.*` stays `enabled: false`: unconfirmed on native Windows; flip only after `claude doctor` confirms it starts on a supported host (macOS/Linux/WSL2).

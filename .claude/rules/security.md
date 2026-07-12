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
- Treat CI/CD, permission, settings, and connector changes as privileged control-plane edits, and prefer explicit allowlists for commands, hosts, paths, and tool arguments.

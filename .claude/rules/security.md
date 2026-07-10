---
name: security
description: Security-sensitive coding rules.
paths:
  - "src/auth/**"
  - "src/api/**"
  - "src/server/**"
  - ".github/workflows/**"
  - "**/*security*"
---

# Security Rules

- Validate all external input at trust boundaries.
- Redact secrets, tokens, cookies, and authorization headers from every log line.
- Enforce authorization server-side.
- Treat CI/CD workflow edits as privileged.
- Prefer explicit allowlists for commands, hosts, and file paths.

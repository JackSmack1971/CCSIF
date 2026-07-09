---
name: security
description: Security-sensitive coding rules.
globs:
  - "src/auth/**"
  - "src/api/**"
  - "src/server/**"
  - ".github/workflows/**"
  - "**/*security*"
---

# Security Rules

- Validate all external input at trust boundaries.
- Do not log secrets, tokens, cookies, or authorization headers.
- Enforce authorization server-side.
- Treat CI/CD workflow edits as privileged.
- Prefer explicit allowlists for commands, hosts, and file paths.

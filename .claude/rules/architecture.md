---
name: architecture
description: Architecture boundaries and dependency direction.
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

# Architecture Rules

- Preserve boundaries between instructions, commands, hooks, workflows, agents, skills, and docs.
- Document dependency direction before introducing a new cross-file or cross-directory link.
- Keep control-plane logic independent from repo-specific content unless the dependency is explicitly documented.
- Add integration or validation checks when changing behavior that crosses one of those boundaries.

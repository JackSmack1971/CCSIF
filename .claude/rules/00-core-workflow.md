---
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
# Core Workflow Rules

- Read nearby control-plane files before creating new modules or rules.
- Use narrow edits that preserve unrelated behavior.
- Prefer existing project commands over ad-hoc shell commands.
- Run targeted verification after control-plane changes.
- Keep final reports evidence-based: changed paths, command results, and unresolved risks.

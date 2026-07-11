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

# Claude Code Ecosystem Rules

- Ground control-plane edits in the official Claude Code docs before changing behavior.
- Use `.claude/rules/` for persistent instructions, skills for task-specific workflows, hooks for deterministic enforcement, and output styles only for response formatting.
- Keep portable instructions code-agnostic: prefer relative paths, environment variables, and repository metadata over project-specific assumptions.
- Read the nearest existing instruction file before adding a new one, and keep filenames descriptive.
- Verify governance edits with `.claude/scripts/rules_fidelity_check.py` and `/control-plane-check`.

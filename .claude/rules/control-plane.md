---
paths:
  - ".claude/**"
  - ".codex/**"
  - ".mcp.json"
  - "managed-settings.json"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - ".github/**"
---
# Control Plane Rules
- Treat `.claude/`, `.codex/`, and the repo-level instruction files as production governance; runtime-only artifacts stay local.
- Treat edits to agents, commands, hooks, workflows, rules, settings, `.mcp.json`, `managed-settings.json`, and root memory files as control-plane changes.
- Keep control-plane changes narrow and one mechanism at a time when possible.
- Prefer Node or Python for hooks and workflows; keep hook paths portable with `$CLAUDE_PROJECT_DIR` or `$HOME`.
- After control-plane edits, run `/control-plane-check` and `python3 .claude/scripts/rules_fidelity_check.py`.

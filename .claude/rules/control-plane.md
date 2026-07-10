---
paths:
  - ".claude/**"
  - ".mcp.json"
  - "managed-settings.json"
  - "CLAUDE.md"
  - "AGENTS.md"
---
# Control Plane Rules

- Treat the versioned control-plane sources in `.claude/`, `.codex/`, and `docs/` as production governance. Runtime-only artifacts such as audit runs, session handoff state, local settings, and the non-versioned managed-settings file stay local.
- Treat edits to agents, commands, hooks, workflows, rules, settings, `.mcp.json`, `managed-settings.json`, and root memory files as control-plane changes that need tighter review than ordinary application code.
- Keep control-plane changes narrow. Change one mechanism at a time when possible so regressions are attributable.
- Prefer Node or Python for hooks and workflows instead of shell-specific pipelines or OS-specific command syntax.
- Hook command entries must stay path-portable. Use `$CLAUDE_PROJECT_DIR`, `$HOME`, or another environment-variable-based path, not a hardcoded absolute path.
- After control-plane edits, run `/control-plane-check` before broader quality or release claims.
- The control-plane check must confirm the tracked governance paths are no longer hidden by `.gitignore`.
- Writer agents must define prerequisites, turn limits, and loop-stop conditions before they are trusted with edits.
- Mark control-plane work release-ready only after referenced files exist, edited scripts parse cleanly, and the final report includes raw verification stdout.

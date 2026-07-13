---
paths:
  - ".claude/**"
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
- Everything the control plane depends on lives under this repo's `.claude/`
  and root files; nothing may require `~/.claude/*` for correctness (Scope
  Doctrine, `docs/claude-code-control-plane-roadmap-v2.md`).
- Gather context -> act -> verify, one step at a time; see
  `.claude/rules/10-karpathy-guidelines.md` for the leash discipline and
  `.claude/rules/20-lifecycle-gates.md` for the gated version of this loop.

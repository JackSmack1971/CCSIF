---
name: testing
description: Testing expectations for source changes.
paths:
  - ".claude/**"
  - ".codex/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - ".github/**"
---

# Testing Rules

- Start with the smallest check that proves the changed control-plane behavior.
- Add regression coverage for confirmed failures in hooks, commands, scripts, settings, or rule files.
- Keep verification deterministic and rooted in the real source of truth.
- Prefer the narrowest command that can fail, then expand only if the failure is ambiguous.

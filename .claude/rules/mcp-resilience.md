---
paths:
  - ".mcp.json"
  - ".claude/**"
  - ".codex/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
---
# MCP Resilience Rules

- Treat MCP servers as optional dependencies unless the task explicitly proves they are required.
- If an MCP call fails or a connector is unavailable, capture the diagnostic and fall back to local repository evidence when possible.
- Claim external state, remote records, or live environment facts only when backed by successful MCP evidence.
- Keep `.mcp.json` changes narrow, reviewable, and followed by `/control-plane-check`.

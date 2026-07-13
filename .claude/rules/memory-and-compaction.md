---
paths:
  - ".claude/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
---

# Memory and Compaction Rules

- Repo-local memory is authoritative: `CLAUDE.md`, `CLAUDE.local.md` (gitignored), `.claude/rules/`, `.claude/state/`, and `plansDirectory: "./.claude/plans"`. Nothing here may require `~/.claude/*` for correctness.
- `.claude/memory/` policy: source files (`hindsight.py`, `hindsight_mcp.py`, `pyproject.toml`, `README.md`) are committed; generated runtime state (`state/`, `.venv/`, `*.db`, `*.jsonl`) is gitignored per `.gitignore`.
- `autoMemoryDirectory` lives only in gitignored `.claude/settings.local.json`, as an absolute path, written idempotently by `python3 .claude/scripts/phase2_memory.py bootstrap-local-settings` (wired into `SessionStart`). Never hand-write a machine path into a committed file.
- Compaction: `PreCompact` snapshots the last verified checkpoint into `.claude/state/compactions/`; `PostCompact` records the generated summary; `SessionStart` restores context only when the snapshot's `session_id` matches the current session, otherwise it rejects the summary as stale/foreign rather than reusing it.
- Subagent summaries and transcript pointers export to `.claude/state/agents/<parent_session_id>/<agent_id>.json` via the `SubagentStop` hook.
- Prompt caching: stable prefixes are `CLAUDE.md`, `.claude/rules/`, and skill/agent definitions. Known invalidators: model/effort switches, MCP connect/disconnect, plugin toggles, and compaction. Editing repo files mid-session or invoking a skill is cache-safe. Treat cache hits/misses as a performance signal only, never as evidence of correctness.
- `python3 .claude/scripts/phase2_memory.py status` reports effective memory sources, the latest verified checkpoint, and whether recovery is native-file-backed or index-backed; run it when memory recovery is in question.

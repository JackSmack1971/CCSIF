# HINDSIGHT Memory

## Purpose
Durable, project-scoped memory for CCSIF. This subtree owns the local HINDSIGHT store, its CLI entrypoint, and the state files consumed by hooks and skills.

## Entry Points
- `README.md` - runtime layout and command reference.
- `hindsight.py` - single CLI entrypoint for retain, recall, observe, reflect, and self-test.
- `hindsight_mcp.py` - MCP wrapper for the memory runtime.
- `state/` - generated episodes, observations, opinions, and cursor state.
- `tests/` - minimal executable checks for the memory runtime.

## Contracts & Invariants
- Keep `hindsight.py` as the single entrypoint shared by hooks and manual runs.
- Preserve the separation between episodes, observations, and opinions.
- Do not write opinion memory without a confidence value.
- Keep source traces and line numbers attached to retained facts.
- On Windows, default to the local store unless the optional Graphiti backend is explicitly configured.

## Patterns
- Read `README.md` before changing runtime behavior.
- Use `self-test` after editing memory logic.
- Treat state files as generated artifacts unless a task explicitly requires a manual repair.

## Anti-patterns
- Don't mix policy text into the runtime state directory.
- Don't add a backend dependency path unless the repo already has the configuration and tests to support it.

## Related Context
- Parent node: `../AGENTS.md`
- Memory rule file: `../rules/hindsight-memory.md`

# HINDSIGHT Memory

## Purpose
Project-scoped memory for CCSIF. This subtree owns the durable HINDSIGHT state, the local Python CLI entrypoint, and the optional Graphiti bridge.

## Entry Points
- `hindsight.py` - local CLI for retain, recall, observe, reflect, reinforce, and self-test.
- `hindsight_mcp.py` - MCP server wrapper that exposes the memory CLI as tools.
- `README.md` - runtime layout, commands, and backend notes.
- `state/` - generated JSONL and cursor files.

## Contracts & Invariants
- Treat `state/*.jsonl` and `state/retain-cursor.json` as generated data, not hand-authored source.
- Keep the local store portable on Windows and in plain project checkouts.
- Preserve the local-first default path; Graphiti is optional and must fail closed when deps or credentials are missing.
- Keep opinion reinforcement deterministic and persona-driven through `.claude/rules/persona-profile.md`.

## Patterns
- Read `README.md` and the CLI entrypoint before changing memory behavior.
- Add or update `self-test` coverage when changing retain, recall, observe, reflect, or reinforce logic.
- Prefer the existing local store unless a change explicitly needs the Graphiti backend.

## Anti-patterns
- Do not edit generated state files directly unless you are repairing a documented migration or test fixture.
- Do not introduce a new backend dependency when the local JSONL store is enough.
- Do not make the MCP wrapper diverge from the Python CLI behavior.

## Related Context
- Parent node: `../AGENTS.md`
- HINDSIGHT architecture plan: `../docs/Hindsight-memory-architecture/HINDSIGHT-for-CCSIF-Implementation-Plan.md`
- Memory README: `README.md`

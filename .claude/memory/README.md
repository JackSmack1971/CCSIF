# HINDSIGHT memory

Durable, project-scoped memory for CCSIF.

## Runtime layout

- `state/` stores generated cursor, episode, opinion, and observation files.
- `hindsight.py` is the single CLI entrypoint used by hooks and skills.
- `pyproject.toml` declares optional Graphiti, MCP, and Voyage dependencies.
- On Windows, the Graphiti Lite path (`falkordblite`) is not available; use the
  portable local store here and switch to Docker/Neo4j if you need a live
  Graphiti backend.
- To use the live Graphiti backend, copy [`.env.example`](./.env.example) to
  `.env`, set `HINDSIGHT_BACKEND=graphiti`, and fill the Neo4j, LLM, and Voyage
  values there. `hindsight.py` loads that file automatically for hooks and the
  MCP server.

## Commands

```bash
python .claude/memory/hindsight.py bootstrap
python .claude/memory/hindsight.py retain
python .claude/memory/hindsight.py replay
python .claude/memory/hindsight.py recall "what changed in the memory architecture?"
python .claude/memory/hindsight.py observe
python .claude/memory/hindsight.py reflect "what changed in the memory architecture?"
python .claude/memory/hindsight.py reinforce --prior 0.6 --supports
python .claude/memory/hindsight.py self-test
python .claude/memory/hindsight.py graphiti-check
```

Local mode is the default path for `retain`, `recall`, `observe`, `reflect`,
and `self-test`. `graphiti-check` is the optional backend probe and only
passes when `HINDSIGHT_BACKEND=graphiti` is set with the Graphiti, LLM, and
Voyage settings available; otherwise it reports why Graphiti is unavailable
and the runtime stays local.

## Opinion reinforcement

`reflect` is the write path for the Opinion Network. Each call looks up the
most recent persisted opinion for the (normalized) query, then reinforces it
with `reinforce()` using persona-conditioned parameters from
`.claude/rules/persona-profile.md` (`skepticism` dampens how much one
evidence batch can move belief, `bias_strength` sets the effective learning
rate). Confidence therefore accumulates across calls instead of resetting —
run `reflect` on the same query twice to see `Confidence reinforced: 0.60 ->
0.68` in the output. The standalone `reinforce` command remains a stateless
utility for computing a single confidence update given an explicit prior.

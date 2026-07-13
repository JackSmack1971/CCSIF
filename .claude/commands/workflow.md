# /workflow

Thin entrypoint for the Phase 4 static-first workflow engine
(`.claude/scripts/phase4_workflows.py`). Definitions live in
`.claude/workflows/defs/*.json` as small declarative graphs: stable step
IDs, an explicit `allowed_next` allowlist per node, `risk`, and
`checkpoint_required`. The engine never invents a node or a tool — it only
validates a caller's choice against the current node's allowlist.

## Commands

```bash
# start a run of a named workflow definition
python3 .claude/scripts/phase4_workflows.py start <workflow> [--run-id <id>]

# see the current node and its allowed next steps (the bounded "planner" view)
python3 .claude/scripts/phase4_workflows.py propose <run_id>

# mark the current node verified or failed (bounded retries; default max 2)
python3 .claude/scripts/phase4_workflows.py verify <run_id> [--failed] [--details "..."]

# move to a node in the current node's allowed_next; high-risk/checkpoint-
# required nodes need a real verified Phase 0 checkpoint id
python3 .claude/scripts/phase4_workflows.py advance <run_id> <next_node> [--checkpoint-id <id>] [--checkpoint-session-id <id>]

# resume from the last verified node after an interruption
python3 .claude/scripts/phase4_workflows.py resume <run_id>

# explicitly pin the static path instead of a graph's optional branches
python3 .claude/scripts/phase4_workflows.py fallback <run_id> --reason "..."

# replayable path trace / full status / all runs
python3 .claude/scripts/phase4_workflows.py replay <run_id>
python3 .claude/scripts/phase4_workflows.py status <run_id>
python3 .claude/scripts/phase4_workflows.py list
```

## Rules

- Never call `advance` to a node outside the current node's `allowed_next`; the engine rejects it and records the rejection in `path_trace` for visibility.
- Never fabricate a `--checkpoint-id`; obtain one from `.claude/scripts/phase0_control_plane.py compact`, which only exists after a real verified step.
- Prefer the plain linear workflow (`linear-static`) unless the task has shown repeated, evidence-driven branching.
- Run `.claude/scripts/control_plane_check.py` and `.claude/scripts/rules_fidelity_check.py` after adding or editing a workflow definition.

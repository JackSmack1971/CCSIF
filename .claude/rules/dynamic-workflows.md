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
# Dynamic Workflows Rules

- Workflow graphs are declarative JSON under `.claude/workflows/defs/`; the engine (`.claude/scripts/phase4_workflows.py`) only validates a caller's chosen next node against that node's `allowed_next` list — it never invents a node or tool.
- A node with `checkpoint_required: true` (write, merge, deploy, delegate, handoff) may only be entered with a real, verified Phase 0 checkpoint id; a fabricated or unverified id is rejected.
- Retries per node are bounded (`max_retries`, default 2); exceeding the bound is the explicit terminal state `failed-exhausted-retries`, never a silent retry loop.
- Resume always rolls back to the last verified node, never the in-flight unverified one, so an interrupted run cannot silently continue from an unproven state.
- Prefer the static linear workflow unless repeated, evidence-driven branching has already been observed; record a pinned static fallback via `fallback` so the choice is visible state, not silence.

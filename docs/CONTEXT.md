# Domain Glossary

Maintained pointer, not a duplicate of policy. When a term's definition
changes, update the file that owns it and update this entry's pointer if the
owning file moves.

| Term | Meaning in this repo | Owning file |
|---|---|---|
| Control plane | The repo-local `.claude/` tree plus root `CLAUDE.md`/`CLAUDE.local.md`; everything an agent needs to operate, committed with the repo | `.claude/AGENTS.md` |
| Scope Doctrine | Nothing in this repo's control plane may require `~/.claude/*` for correctness; project scope is canonical | `docs/claude-code-control-plane-roadmap-v2.md` (Scope Doctrine section) |
| Checkpoint | A verified session step recorded by `Phase0ControlPlane.compact()`; the only thing that satisfies a `checkpoint_required` gate | `.claude/scripts/phase0_control_plane.py` |
| Ledger | The append-only, evidence-backed record of what changed and why, one entry per completed unit of work | `.claude/state/ledger.md` |
| Lifecycle gate | One of Align / Research / Plan / Build / Verify & Ship; a unit of work's durable checkpoint, skippable only when stated | `.claude/rules/20-lifecycle-gates.md` |
| Two-axis taxonomy | User-invoked commands orchestrate and never call each other; model-invoked skills are small, single-purpose, composable | `.claude/rules/30-skill-taxonomy.md` |
| Workflow run | A `.claude/workflows/defs/*.json`-defined allowlisted graph execution tracked in `.claude/state/workflows/` | `.claude/scripts/phase4_workflows.py` |
| Handoff | A verified (never self-reported) transfer of delegated subagent work back to the parent session | `.claude/scripts/phase3_agents.py` |
| Taxonomy check | The deterministic linter for cross-invocation, duplicate responsibility, context budget, global-path dependency, and root-guidance size | `.claude/scripts/taxonomy_check.py` |

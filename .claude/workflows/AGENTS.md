# Workflows

## Purpose
Deterministic orchestration for repository control-plane workflows. This subtree owns the `issue-to-pr` fan-out runner and the Phase 4 declarative workflow-graph definitions.

## Entry Points
- `issue-to-pr.js` - batch workflow that discovers ready issues, delegates implementation and review, and records outcomes.
- `defs/*.json` - small declarative workflow graphs (stable step IDs, `allowed_next` allowlist, risk, checkpoint requirement) executed by `.claude/scripts/phase4_workflows.py`.

## Contracts & Invariants
- Keep orchestration deterministic and reviewable.
- Keep the plan/implement/review/record phases explicit.
- Prefer worktree-isolated execution when the workflow fans out across multiple issues.
- Do not silently broaden scope beyond the issue list the planner selected.

## Patterns
- Read `issue-to-pr.js` before changing workflow behavior.
- Preserve the structured schemas used by the workflow stages.
- Keep workflow changes small enough to review as a single orchestration diff.

## Anti-patterns
- Do not add hidden branching that bypasses review or recording.
- Do not mix workflow orchestration with unrelated utility logic.
- Do not introduce a second orchestration path unless the workflow is actually being split.

## Related Context
- Parent node: `../AGENTS.md`
- Workflow source: `issue-to-pr.js`
- Workflow skill: `../skills/issue-to-pr/SKILL.md`

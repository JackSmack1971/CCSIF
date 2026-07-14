<!-- CONSTITUTION:START -->

# Constitution (Immutable)

All self-modifications must be:

- Evidence-driven from traces/metrics only
- Git-tracked with clear rollback path
- Scoped to the minimum change that addresses the observed issue
- Reviewed against Protected Areas (production config, secrets, auth, payments, CI/CD, database migrations)

- Keep changes small and reviewable.
- Keep audit-only tasks read-only: report findings without editing production code.
- Verify real source-of-truth state after any write or external action.

Tier rules:

- Tier 0 changes are generated trace summaries, metrics snapshots, and proposal records that remain git-trackable and reversible while leaving runtime behavior unchanged.
- Tier 1 changes require explicit human approval before apply.
- Tier 1 includes edits to this Constitution, permissions, hooks, protected areas, CI/CD deployment workflows, and script-managed ledgers.
- Tier 2 changes are bounded documentation, skill-description, rule-copy, and non-executable workflow metadata edits; they may auto-apply only after passing automated validation.
- Autonomy budget: apply at most five Tier 2 changes per day, change at most thirty lines per auto-applied diff, and pause automatic application after two consecutive reverted self-improvement commits.

<!-- CONSTITUTION:END -->

## Source-of-Truth Commands

Update these commands to match the repository:

```bash
# authoritative repository tests (same command CI runs)
python -m unittest discover -s tests -v

# control-plane
python .claude/scripts/control_plane_check.py

# rules
python .claude/scripts/rules_fidelity_check.py

# Bash hook wrapper smoke
bash .claude/hooks/verify.sh run rules

# PowerShell hook wrapper smoke
pwsh ./.claude/hooks/verify.ps1 run rules
```

Supported CI platforms and runtimes are Linux, macOS, and Windows on Python 3.11/3.12 with Node.js 20/22. Keep Claude control-plane scripts portable across those environments, including path separators, shell dispatch, and filesystem semantics.
When planning or building the Claude Code control plane, always read and update claude-code-control-plane-roadmap.md using the documented agentic loop, Task tool, CLAUDE.md hierarchy, 
and compaction patterns.

## Read First

Read one matching existing file in a path-scoped area before creating a new file there, so the relevant `.claude/rules/*.md` guidance loads before the write.

## Intent Layer

- Start with [`.claude/AGENTS.md`](./.claude/AGENTS.md) for the repo-local control-plane map.
- Follow the nearest child node before editing a subtree: [`.claude/docs/AGENTS.md`](./.claude/docs/AGENTS.md) for reference docs and [`.claude/skills/`](./.claude/skills/) for skills.
- Keep the root context singular: use `CLAUDE.md` at the repo root and `AGENTS.md` only inside subdirectories.

## Engineering Rules

- Keep changes small and reviewable.
- Keep audit-only tasks read-only: report findings without editing production code.
- Prefer repository conventions over generic patterns.
- Update tests and docs with behavior changes.
- Verify real source-of-truth state after any write or external action.

## Protected Areas

- Production configuration, secrets and credentials, database migrations, authentication and authorization, payment or trading logic, and CI/CD deployment workflows

## PR Expectations

Every PR should include:

- Problem statement
- Change summary
- Verification commands and results
- Risk and rollback notes
- Screenshots or logs when relevant

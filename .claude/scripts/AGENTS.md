# Scripts

## Purpose
Control-plane helper scripts for validation and repo checks under `.claude/scripts/`.

## Entry Points
- `control_plane_check.py` - validates required control-plane paths and guard behavior.
- `rules_fidelity_check.py` - checks `.claude/rules` scope fidelity.

## Contracts & Invariants
- Keep helper scripts deterministic and side-effect free unless they are explicitly acting on the repo.
- Prefer updating shared check logic over adding one-off validation in callers.
- Keep changes small and verify them with the repo's control-plane check.

## Patterns
- Read the target script before changing behavior.
- Preserve existing exit codes and output conventions.

## Anti-patterns
- Do not duplicate validation logic in multiple scripts.
- Do not broaden the helper surface without a specific repo need.

## Related Context
- Parent node: `../AGENTS.md`

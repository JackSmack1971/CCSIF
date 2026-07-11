# Hooks

## Purpose
Executable gates and notifications for the repo-local control plane. Hooks are behavior, not documentation: they must be portable, deterministic, and safe to run repeatedly.

## Entry Points
- `README.md` - hook inventory and setup notes.
- `pre-tool-use.sh` - guard that blocks protected-area writes when dependencies are missing.
- `post-tool-use.sh` - post-action hook entrypoint.
- `session-start.sh` - startup visibility and environment check.
- `stop.sh` - end-of-session verification and cleanup.
- `lib/` - shared hook helpers.

## Contracts & Invariants
- Preserve exit codes and fail closed when a guard cannot run.
- Keep shell entrypoints portable across the repo's supported environments.
- Do not weaken protected-area checks without an explicit replacement guard.
- Keep hook changes minimal and verify them in the same turn they are edited.

## Patterns
- Read the target hook and its helper before changing behavior.
- If a hook needs new logic, prefer the smallest script-level change that preserves the current contract.
- Run the control-plane checks after any hook change.

## Anti-patterns
- Don't bypass a hook just to make a local edit easier.
- Don't add cross-platform behavior that the current shell wrapper cannot support.

## Related Context
- Parent node: `../AGENTS.md`
- Control-plane rules: `../rules/AGENTS.md`

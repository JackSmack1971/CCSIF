# /control-plane-check

Run the deterministic control-plane validation after any edit to governance files, hooks, commands, rules, skills, workflows, settings, or root agent instructions.

## Command

```bash
python3 .claude/scripts/control_plane_check.py
```

## Required pass criteria

- Required control-plane files exist.
- Shared settings parse as JSON.
- Required governance paths are not hidden by `.gitignore`.
- Hook shell scripts parse with `bash -n`.
- The PreToolUse guard blocks synthetic writes to protected governance paths and self-improvement ledgers, including `.github/**`, `SECURITY.md`, and `.claude/rules/**` examples.
- Protected-area guidance requires the agent to halt on the first block instead of attempting repeated edits or workarounds.

If the command fails, fix the reported control-plane defect before making release-readiness claims.

# Verification

## Checks performed

- Metadata linted manually for `name`, description length, activation-first wording, trigger patterns, negative space, and distinctive terms.
- `SKILL.md` kept under 500 lines and organized with one-level references.
- References are directly linked from `SKILL.md` and do not require nested reference traversal.
- Scripts use Python standard library only.
- Scripts define CLI arguments and deterministic exit behavior.
- Python scripts compiled with `python -m py_compile scripts/*.py`.
- Self-audit was run against the generated skill pack.

## Known limits

- The scripts do not use an LLM and therefore cannot safely invent domain-specific description rewrites.
- The fixer intentionally applies only mechanical changes; semantic repairs are routed through the skill workflow.
- Git commits are performed by the activated Claude Code session, not by the packaged script, so the user can inspect diffs first.

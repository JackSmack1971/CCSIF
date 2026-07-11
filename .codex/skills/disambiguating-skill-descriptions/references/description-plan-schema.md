# Description Plan Schema

## File

Use `description-plan.json`.

## Shape

```json
{
  "version": 1,
  "changes": [
    {
      "path": ".claude/skills/example/SKILL.md",
      "name": "example-skill",
      "old_description": "Old description copied exactly from frontmatter.",
      "new_description": "Use when rewriting one exact skill description. Trigger on fix this skill description, improve skill routing, prevent skill collision. NOT for creating a new skill; use skill-creator instead. Requires validated single line YAML description under 1024 chars.",
      "rationale": "Narrows broad documentation language into router-specific activation conditions.",
      "negative_space": "Excludes new skill creation and general documentation rewriting."
    }
  ]
}
```

## Validation rules

- `version` must be `1`.
- `changes` must be a non-empty array.
- `path`, `name`, `old_description`, `new_description`, `rationale`, and `negative_space` are required strings.
- `path` must resolve under the supplied root.
- `path` must end with `SKILL.md`.
- `old_description` must exactly match the current file before apply.
- `new_description` must pass the description standard.
- No duplicate paths.

## Apply safety

The apply script edits only the description scalar line in frontmatter. It refuses multi-line or folded descriptions because those are invalid for this standard and require manual repair first.

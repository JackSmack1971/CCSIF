# Fix Policy

## Safe automatic fixes

The fixer may automatically:

- Add a missing `name` from the containing directory when the normalized name is valid.
- Normalize simple one-line YAML frontmatter ordering without changing values.
- Add a missing `VERIFICATION.md` placeholder that clearly says validation is pending.
- Create `evals/` with a minimal placeholder only when the skill has no tests and the workflow is structured enough to identify candidate prompts.
- Generate machine-readable fix plans and audit reports.

## Judgment-required fixes

Claude must inspect the skill and preserve domain intent before changing:

- Descriptions and trigger patterns.
- Negative-space routing to adjacent skills.
- Moving content into references.
- Adding or changing tool permissions.
- Creating validation scripts or eval expectations.
- Any behavior that could alter how the skill executes.

## Forbidden automatic fixes

Do not automatically:

- Delete skills, references, scripts, or tests.
- Rename directories.
- Invent domain facts, external dependencies, or compatibility promises.
- Add network access.
- Add `allowed-tools` that bypass prompts for destructive commands.
- Silence a finding by weakening the rubric.

## Description repair template

Use this template, then adapt it to the skill domain:

```yaml
description: Use when [specialized action] for [domain or artifact] under [constraints]. Trigger on queries that say [pattern 1], [pattern 2], [pattern 3], [pattern 4]. NOT for [adjacent scenario] use [other skill] instead. Distinct keywords [unique terms].
```

Rules:

- Keep it under 1024 characters.
- Keep it one line.
- Avoid colons and angle brackets.
- Prefer exact phrases a user would actually type.
- Avoid generic words as the only triggers such as analyze, improve, review, help, docs, code, data.

## Validation repair template

Add this pattern to fragile skills:

```markdown
## Validation loop

- [ ] Produce the plan artifact.
- [ ] Validate the plan with the bundled script or schema.
- [ ] Apply the change only after validation passes.
- [ ] Re-run validation.
- [ ] Document remaining warnings before completion.
```

## Stop conditions

Stop and report instead of editing when:

- The skill target is outside a git repository and the user did not explicitly permit uncommitted edits.
- The intended fix requires domain knowledge not present in the skill or adjacent references.
- The audit would need to fetch untrusted network content.
- A tool permission change would broaden write, shell, network, deploy, or git push capability.

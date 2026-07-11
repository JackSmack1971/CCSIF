# Description Standard

## Required shape

A production description is a router rule, not marketing copy.

Use this structure:

```yaml
description: Use when [specialized action] for [specific artifact or domain]. Trigger on [phrase 1], [phrase 2], [phrase 3], [optional phrase 4], [optional phrase 5]. NOT for [adjacent general case]; use [other skill] instead. Requires [mandatory output or validation constraint].
```

## Pass criteria

- Begins with `Use when` or `Trigger on queries that`.
- Contains 3 to 5 natural trigger phrases after `Trigger on`.
- Contains `NOT for` negative space.
- Names adjacent skill routing when known.
- Includes unique domain nouns, file types, artifacts, or constraints.
- Is one line and under 1024 characters.
- Contains no colon and no angle brackets.

## Rewrite rules

1. Replace broad purpose language with exact activation conditions.
2. Replace internal labels with user phrases.
3. Add negative space for every likely adjacent route.
4. Add mandatory output or validation constraint.
5. Keep the most important routing words in the first 180 characters.

## Bad patterns

Avoid these unless narrowed by unique domain constraints:

- `use for analysis`
- `help with code`
- `improve docs`
- `documentation helper`
- `review changes`
- `optimize project`
- `general automation`

## Examples

Bad:

```yaml
description: Helps with documentation and improves docs.
```

Good:

```yaml
description: Use when generating repository SECURITY.md files from a codebase security posture and disclosure policy. Trigger on create SECURITY.md, update security policy, generate vulnerability disclosure process, audit repository security docs. NOT for general README writing or code vulnerability review; use documentation-writing or security-review instead. Requires final SECURITY.md plus assumptions and verification notes.
```

Bad:

```yaml
description: Use for code review and analysis.
```

Good:

```yaml
description: Use when reviewing pull requests for merge risk, blast radius, reversibility, and evidence-gated approval. Trigger on review this PR, decide if safe to merge, analyze PR risk, fix merge blockers, clean merge open PRs. NOT for general linting, repository hygiene, or feature implementation; use repo-hygiene or implementation skills instead. Requires risk tier, blocking findings, tests, and merge decision.
```

# .github Governance

This subtree is for repository governance files only.

Before editing anything under `.github/`, read root `CLAUDE.md` and `.claude/rules/control-plane.md`.

## Scope

- Treat `.github/workflows/**`, `CODEOWNERS`, issue templates, PR templates, labels, and security reporting as governance-sensitive.
- Preserve the single-owner repository model unless another owner is verified in repository evidence.
- Keep issue and PR templates concise, structured, and agent-actionable.
- Validate YAML issue forms after edits.

## Guardrails

- Do not invent labels, teams, contact links, or broad CI rewrites.
- Do not touch CI/CD workflows, branch protection, or rulesets without explicit approval.
- Prefer separate PRs for `CODEOWNERS`, templates/forms, labels, and workflows.

## Verification

- Use the repo's existing control-plane validation for governance edits when available.
- Include exact command output in PRs.
- If Markdown formatting changes, run a local readability or lint check when one exists.

# Audit Rubric

## Measurable gates

### Discovery metadata

A skill passes discovery when:

- `name` exists, is lowercase kebab-case, is 1 to 64 characters, and avoids reserved namespaces.
- `description` exists, is a single-line YAML scalar, is at most 1024 characters, has no colons or angle brackets, and starts with `Use when` or `Trigger on queries that`.
- Description names the core action, activation condition, 3 to 5 user-sayable trigger patterns, negative space, and distinctive domain keywords.
- `when_to_use` or equivalent body guidance reinforces triggers without duplicating generic phrasing.
- Adjacent skills or scenarios are routed elsewhere with `NOT for` or `use X instead` language.

High severity:

- Missing frontmatter, missing description, invalid name, or description that can collide with broad helper skills.
- Description lacks negative space for a skill likely to overlap with others.

### Progressive disclosure

A skill passes progressive disclosure when:

- `SKILL.md` is under 500 lines and roughly under 5000 loaded tokens.
- Long details live in `references/`, templates in `assets/`, deterministic code in `scripts/`, and tests in `evals/`.
- Every reference needed by the workflow is linked directly from `SKILL.md`.
- Reference files over 100 lines have a table of contents.
- Reference files do not require following a second reference chain to understand required workflow steps.

High severity:

- Critical operating instructions are buried only in a second-level reference.
- `SKILL.md` is so large that activation loads unnecessary domain detail.

### Workflow and validation

A skill passes workflow quality when:

- Complex tasks have a checklist with artifact-producing steps.
- Stop conditions and completion gates are explicit.
- Critical operations use validate then fix then repeat loops.
- Fragile or structured outputs have evals, fixtures, schema checks, or deterministic validators.
- Verification logs state what was actually tested and what was not.

High severity:

- A state-mutating skill has no dry-run, plan, validation, or completion gate.
- A skill asks Claude to trust prose without checking artifacts.

### Script quality

A script-enabled skill passes script quality when:

- Scripts have clear CLI arguments, deterministic stdout or JSON output, and documented exit codes.
- Scripts use only declared dependencies and degrade gracefully when optional tools are missing.
- Python scripts parse and compile with the project Python.
- No script contains `eval`, unsafe `exec`, `shell=True` without justification, `os.system`, secret echoing, or destructive file operations without dry-run and path guards.

High severity:

- Bundled scripts can delete, push, deploy, exfiltrate, or mutate outside the target root without an explicit confirmation gate.

### Security and portability

A skill passes security and portability when:

- Tool permissions are least-privilege for the workflow.
- Network tools are disallowed unless the skill explicitly needs them.
- MCP tools use fully qualified names.
- Environment requirements are documented for Claude Code, Claude.ai, and Claude API where relevant.
- The skill treats third-party resources as untrusted.

High severity:

- A network-consuming skill can write files or execute shell commands without defensive boundaries.
- A destructive skill is model-invocable without a human gate.

## Severity scale

- High means routing failure, unsafe mutation, hidden context bloat, or validation absence can cause wrong execution.
- Medium means the skill works but loses reliability, portability, or measurable quality.
- Low means cleanup, clarity, or maintainability improvement.

## Scoring

Start each skill at 100. Subtract 20 for each high finding, 8 for each medium finding, and 3 for each low finding. Cap the minimum at 0. Corpus health is the mean skill score plus a collision penalty based on duplicate or overly generic descriptions.

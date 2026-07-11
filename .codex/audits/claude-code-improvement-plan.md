# Claude Code Architecture Improvement Plan

Repository: `C:\workspaces\CCSIF`
Source audit: `.claude/audits/claude-code-architecture-audit.json` / `.md` (deterministic, 5 findings, status PARTIAL)
Plan generated: 2026-07-10

This supersedes the 2026-07-09 plan (25 findings, FAIL). That plan's critical/high items — the untracked self-modifying rule file, empty hook placeholders, missing path scoping, negative-phrasing rewrites, missing decision log — were resolved in commit `5d25b74`. The audit now shows **0 critical / 0 high**, meeting this skill's stop condition on its own. The 5 remaining findings are medium/low polish items.

## Goal

Resolve the 5 medium/low findings without weakening security-governance rule content or breaking existing skill script execution.

## Ranked Findings

| ID | Severity | Axis | File | Evidence | Fix | Stop condition |
| --- | --- | --- | --- | --- | --- | --- |
| CCA-001 | Medium | context budget | `.claude/rules/constitutional-agent-engineering-rules.md` | 73 lines (generic target ≤50) | The file **self-documents** an 80-line compaction threshold under "Context Dilution" mitigation ("Decompose only if total line count exceeds 80"); it currently sits at 73/80. It is also a project-local copy of the user's global ruleset — trimming to the generic 50-line target risks losing precision-tuned security language and diverging from the canonical global copy at `~/.claude/rules/`. | Rule file is at or below 50 lines **or** documented as intentionally under its own declared threshold |
| CCA-002 | Medium | context budget | `.claude/rules/surgical-density.md` | 55 lines (target ≤50) | 5 lines over; every bullet is a distinct, load-bearing instruction with no obvious redundant pair to merge without loss. `paths: ["**/*"]` marks it as deliberately global. | Rule file is at or below 50 lines or documented as intentionally global |
| CCA-003 | Medium | MCP governance | `.claude/settings.json` | No `allowedMcpServers`, `deniedMcpServers`, or `allowManagedMcpServersOnly` key; no `.mcp.json` in the repo | Add an explicit policy block documenting that this project authorizes no MCP servers (none configured today) | Settings define MCP access policy or document that the project uses no MCP servers |
| CCA-004 | Low | security boundaries | `.claude/settings.json` | `disableSkillShellExecution` is not `true` | **Not recommended to auto-apply.** Most of this repo's skill corpus (skill-auditor, changelog-updater, generate-codeowners, maintaining-repository-hygiene, and others) executes Python/Bash scripts as their core mechanism. This key's exact scope (blocks inline shell prose in SKILL.md vs. blocks all skill-invoked Bash tool calls) is not verified against current Claude Code docs; setting it blind risks breaking the corpus this session already audited and fixed. | Policy is explicit in settings or documented as intentionally permissive |
| CCA-005 | Low | memory hygiene | `.gitignore` | No `.claude/projects` or `.claude/memory` ignore pattern | Confirmed: this repo does not currently create either directory (session memory lives at `~/.claude/projects/<hash>/memory/`, outside the repo). Add the pattern anyway as cheap, zero-risk defensive hygiene. | Gitignore covers local memory artifacts, or repo confirms none are created inside project root |

## Proposed Edits

| File | Change | Risk |
| --- | --- | --- |
| `.gitignore` | Add `.claude/memory/` and `.claude/projects/` ignore patterns | None — purely additive, no directory exists today |
| `.claude/settings.json` | Add an explicit MCP policy block stating no servers are authorized | Low — additive documentation, no behavior change |
| `.claude/settings.json` | Set `disableSkillShellExecution: true` | **High** — unverified blast radius against the active skill corpus |
| `.claude/rules/constitutional-agent-engineering-rules.md` | Trim to ≤50 lines | Medium — risks security-language precision loss and drift from the global canonical copy |
| `.claude/rules/surgical-density.md` | Trim to ≤50 lines | Low-medium — no clean 5-line cut without dropping a distinct rule |

## Approval Needed

- [ ] `disableSkillShellExecution: true` (CCA-004) — recommend **not applying** without first verifying exact semantics; high risk of breaking the skill corpus
- [ ] MCP governance block in `settings.json` (CCA-003) — permission-adjacent file edit
- [ ] Trimming `constitutional-agent-engineering-rules.md` (CCA-001) — rewriting security-governance prose
- [ ] Trimming `surgical-density.md` (CCA-002) — rewriting operational-governance prose

## Not gated (safe to apply directly)

- `.gitignore` memory-path additions (CCA-005) — purely additive, no behavior change

## Validation

- [ ] Run audit script again after any approved edit
- [ ] Run repository-native verification (none defined beyond the skill corpus's own scripts; no build/test manifest exists at the repo root)
- [ ] Compare before and after findings

## Semantic observation (not a scored finding)

`constitutional-agent-engineering-rules.md` explicitly instructs "Place this file at `~/.claude/rules/...` with no YAML path-scoping header," yet it is committed inside this project's `.claude/rules/` with a `paths: ["**/*"]` header — a self-referential placement inconsistency. This is a maintainer decision (keep both copies, or de-duplicate in favor of the global one) outside this audit's automated scoring, so it is not in the edit list above.

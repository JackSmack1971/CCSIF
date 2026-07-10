# Claude Code Architecture Improvement Plan

Repository: `C:\workspaces\CCSIF`
Source audit: `.claude/audits/claude-code-architecture-audit.json` / `.md` (deterministic, 25 findings, status FAIL)
Plan generated: 2026-07-09 (manual review layered on top of the deterministic scan)

## Executive Summary

Status: **FAIL** — 1 critical (manual finding, not caught by the scanner), 2 high (scanner) + 1 high (manual), 21 medium, 2 low.

The repository has a reasonable settings/hook/rule skeleton, but three things need a human decision before any edit:

1. An **untracked, unconditionally-loaded rule file** contains self-modifying operational instructions (commit `.claude/`, restructure rules, prune memory) dressed up as an empirical whitepaper with 2026-dated citations. It is not yet part of git history — this is the highest-leverage finding.
2. **`PreToolUse` and `Stop` hooks are empty placeholders.** Every "Tier 1 requires human approval" / "Protected Areas" / "verify before claiming success" statement in `CLAUDE.md` currently exists only as prose — nothing blocks a destructive command or a false success claim.
3. Most rule files under `.claude/rules/` have **no `paths:` frontmatter**, so they load unconditionally on every turn rather than only when relevant files are touched.

## Ranked Findings

| # | Severity | Axis | File | Evidence | Fix | Stop condition |
|---|---|---|---|---|---|---|
| M-1 | **Critical** (manual) | untrusted control-plane content | `.claude/rules/System Architecture and Empirically Grounded Self-Improvement in Claude Code v2.1.206.md` | Untracked (`git status` shows `??`). 204 lines / ~7k+ words, no `paths:` frontmatter (loads every turn). Contains a "June 2026 Modular Migration Protocol" instructing the agent to autonomously restructure `.claude/`, trim `CLAUDE.md`, and **commit the `.claude/` directory to version control** as part of self-improvement — i.e. operational instructions embedded in what reads as a citation-heavy research document, sitting in the same trust tier as your hand-authored rules. | Decide: delete, or move to `.claude/docs/` (non-auto-loaded reference, no longer injected) and strip the autonomous-commit/self-restructure directives so any control-plane change still routes through the existing approval gates in `operating-constitution.md` and `control-plane.md`. | File is either removed, or lives outside auto-loaded rule paths and contains no unreviewed self-modification instructions. |
| M-2 | **High** (manual) | verification / security boundaries | `.claude/hooks/pre-tool-use.sh`, `.claude/hooks/stop.sh` | Both are stub scripts — `pre-tool-use.sh` has no deny logic (just a comment: "Placeholder: implement repo-specific deny checks here"); `stop.sh` has no verification command (just a comment: "Placeholder: final session checks"). `CLAUDE.md`'s constitution ("Tier 1 changes require explicit human approval," "Protected Areas") and the audit SOP's High-severity rule ("Destructive-operation policy exists only as markdown prose") both apply directly. | Implement real deny checks in `pre-tool-use.sh` for the CLAUDE.md Protected Areas (prod config, secrets, migrations, auth, payments, CI/CD) and a real verification command in `stop.sh` (e.g. `git status --short` plus the repo's actual test/lint/typecheck commands once they're defined). This is a security-sensitive change — needs explicit scope agreement before editing. | `pre-tool-use.sh` exits 2 / denies on a synthetic Protected-Area write attempt; `stop.sh` runs an actual check and blocks on a synthetic failure. |
| CCA-001 | High | path-scoped rules | `CLAUDE.md` | No Read First guidance detected. | Add a short "Read First" line: read one existing matching file in a path-scoped area before creating new files there, so path-scoped rules actually get injected before writes. | Root manifest contains explicit Read First guidance. |
| CCA-008 | High | context budget | (same file as M-1) | 204 lines, far above the 50-line rule-file budget. | Resolved by the M-1 decision. | Rule file is below 50 lines or moved out of active rules. |
| CCA-002/004/005/006/007/009/010 | Medium | path-scoped rules | `architecture.md`, `constitutional-agent-engineering-rules.md`, `README.md`, `security.md`, `surgical-density.md`, `testing.md`, and M-1's file | No `paths:` key. | For each: either add precise `paths:` globs (e.g. `security.md` → `["**/*"]` only if truly global, otherwise scope to relevant dirs) or add an explicit one-line "intentionally global" label so the audit script and future readers know it's a deliberate choice, not an oversight. `constitutional-agent-engineering-rules.md` explicitly documents itself as unscoped-by-design ("no YAML path-scoping frontmatter") — that one is likely fine to label global rather than scope. | Every rule file has either `paths:` frontmatter or an explicit global-scope label. |
| CCA-011 | Medium | MCP governance | `.claude/settings.json` | No `allowedMcpServers`/`deniedMcpServers`/`allowManagedMcpServersOnly`. | Add explicit MCP governance keys once the project's actual MCP usage is known (session shows several `claude_ai_*` connectors available — confirm which are sanctioned for this repo). | Settings define MCP policy or document "no MCP servers used." |
| CCA-013/014/015/016/017/018/019/020/021/022/023 | Medium | linguistic architecture | `CLAUDE.md` + 9 rule files | Negative phrasing ("Do not...", "Never...", "Avoid...") in operational rules. | Rewrite each flagged line as an affirmative imperative with a measurable completion criterion (see audit table for exact lines). Batch this as one mechanical pass across the 10 files. | Each replacement line states the desired action plus a verification condition. |
| CCA-024 | Medium | metacognitive improvement | `.claude/docs/decision-log.md` | Missing. | Create `.claude/docs/decision-log.md`; log this audit's decisions (M-1 disposition, hook implementation) as the first entries. | File exists with dated, evidence-backed entries. |
| CCA-012 | Low | security boundaries | `.claude/settings.json` | `disableSkillShellExecution` not set to `true`. | Set explicitly (`true` or `false`) so the policy is intentional rather than implicit. | Key present with a documented choice. |
| CCA-025 | Low | memory hygiene | `.gitignore` | No `.claude/projects`/`.claude/memory` pattern. | Not applicable as-is — auto-memory lives at `~/.claude/projects/<hash>/memory/`, outside the repo. Add a pattern only if this project ever writes memory artifacts inside the repo root. | Confirmed no in-repo memory writes, or pattern added. |

## Proposed Execution Order

1. **M-1 decision** (blocks everything else touching context budget/path-scoping for that file).
2. **M-2** hook implementation — security-sensitive, isolate for explicit approval, smallest diff per script.
3. CCA-001 Read First line in `CLAUDE.md` (one line, low risk).
4. CCA-002/004–010 paths frontmatter / global labels (mechanical, low risk, one commit per file or batched).
5. CCA-013–023 linguistic rewrites (mechanical, low risk, mirror existing tone).
6. CCA-024 decision log creation.
7. CCA-011, CCA-012, CCA-025 (settings tweaks — confirm actual MCP usage before writing CCA-011; ask before choosing `disableSkillShellExecution` value since it changes skill behavior).

## Explicit Approval Needed Before Editing

- Disposition of M-1's file (delete vs. relocate vs. keep-and-trim).
- Content of the `pre-tool-use.sh` deny list and `stop.sh` verification command (M-2) — these are security-sensitive and currently unimplemented, not regressions, so scope must be agreed rather than assumed.
- Whether to proceed with the full mechanical batch (frontmatter + linguistic rewrites) in one pass or file-by-file.

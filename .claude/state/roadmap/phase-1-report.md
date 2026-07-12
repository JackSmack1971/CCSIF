# Phase 1 Report

Status: complete

## Summary

Phase 0 was confirmed evidence-complete (`.claude/state/roadmap/phase-0-report.md`, checkpoint `status: complete`, `control_plane_check.py` and `rules_fidelity_check.py` both re-verified `PASS` before this phase started) before any Phase 1 work began, per the roadmap's sequencing requirement.

The repository already carried a mature `.claude/` tree (rules, skills, commands, agents, hooks, `.mcp.json`) from prior work, so Phase 1 was a verification-and-repair pass rather than a from-scratch build: every "existing" criterion in the completion matrix was re-proven against live behavior instead of trusted from static file presence, and both "partial" criteria were closed with real fixes. Three genuine defects were found and fixed:

1. `.claude/settings.json` declared `allowedMcpServers` (a managed-scope-only key with the wrong shape) instead of the documented project-scope key `enabledMcpjsonServers`. The `graphiti-memory` server in `.mcp.json` would have re-prompted every collaborator on every session instead of being auto-approved.
2. `.claude/agents/reflect-agent.md` and `.claude/agents/upstream-auditor.md` declared `tools: [read, grep, git, shell, ...]` — lowercase, and `git`/`shell`/`github` are not real Claude Code tool identifiers. The other two agent files already used the correct form (`tools: Read, Grep, Bash`).
3. `.claude/rules/claude-code-ecosystem.md` had no explicit skill-promotion rule, so "repeated procedures split into skills" had no governing policy an agent could point to — only the incidental fact that 57 skills already existed.

## Fixed / Changed Files

- `.claude/settings.json` — `allowedMcpServers` → `enabledMcpjsonServers: ["graphiti-memory"]`
- `.claude/agents/reflect-agent.md` — `tools:` frontmatter corrected
- `.claude/agents/upstream-auditor.md` — `tools:` frontmatter corrected
- `.claude/rules/claude-code-ecosystem.md` — added skill-promotion rule, within the existing 20-line budget
- `.claude/state/completion-matrix.md` — Phase 1 section updated with live-verified evidence
- `.claude/state/execution-manifest.json` — `phase_1` marked `complete`, `phase_1_completion` block added
- `.claude/state/ledger.md` — Phase 1 entry appended

## Verification Performed

| Check | Command | Exit |
|---|---|---:|
| Config syntax | `python3 -c "import json; json.load(open('.claude/settings.json'))"` | `0` |
| Manifest syntax | `python3 -c "import json; json.load(open('.claude/state/execution-manifest.json'))"` | `0` |
| Control-plane check | `python3 .claude/scripts/control_plane_check.py` | `0` |
| Rules fidelity check | `python3 .claude/scripts/rules_fidelity_check.py` | `0` |
| Phase 0 regression | `python -m unittest discover -s tests -v` | `0` (6 tests, no regression) |

### PreToolUse hook allow/block/error paths (live, Windows-native `cwd`)

Ran a scripted session (SessionStart → PreToolUse → PostToolUse → PreToolUse) using a `cwd` value in the same format Claude Code actually sends on Windows (`C:\workspaces\CCSIF`), not a git-bash POSIX-style path — an earlier ad hoc test with a POSIX-style `cwd` surfaced a `Path.resolve()` artifact (`path escapes workspace: C:\c\workspaces\CCSIF`) that turned out to be a test-harness quoting artifact, not a product bug, once the payload matched real invocation shape.

- **Block**: `Edit` on `.env.production` and `Bash` `rm migrations/0001.sql` both exit `2` with a stderr reason naming the Protected Area and citing the Constitution.
- **Allow**: `Read` on `README.md` exits `0` and the request is logged by the Phase 0 harness.
- **Error (visible, non-blocking)**: malformed/empty stdin exits `1` with `Phase0 error: ...` on stderr. Per `.claude/docs/.../code-claude-com-docs-en-hooks-88d3d79.md`, exit code 1 is a non-blocking error for `PreToolUse` — Claude Code shows a `<hook name> hook error` notice plus the first line of stderr in the transcript and lets the tool call proceed. This is the correct "fail visibly, don't block on infra errors" shape distinct from the guard's `exit 2` blocking path.

### Config, path-scoping, and discoverability

- Every non-index file in `.claude/rules/` carries `paths:` frontmatter (verified structurally by `rules_fidelity_check.py`, which also enforces per-file line budgets and a single top-level H1).
- `.claude/agents/implementation-agent.md`, `pr-reviewer.md`, `reflect-agent.md`, and `upstream-auditor.md` all appear in this session's live Agent-tool registry, confirming project-scope agent discovery with no `~/.claude/agents/` dependency.
- `/control-plane-check` (`.claude/commands/control-plane-check.md`) is a discoverable project slash command.
- Repo-wide scan for `~/.claude` found no active dependency — only descriptive/comparative references inside audit and skill-reference docs (e.g. noting that a rule file is *also* mirrored at the user's global `~/.claude/rules/` by the maintainer's own choice, not that anything in this repo requires it).

### Agent-tool delegation (live subagent spawn)

- Spawned `pr-reviewer` (role defined in `.claude/agents/pr-reviewer.md`) via the Agent tool with a diagnostic prompt. It called `Bash` (`git status --short`) and `Read` (its own frontmatter file) and returned real, verifiably-accurate live repository state (`tool_uses: 2`), matching the actual `git status` output for this session's in-progress edits.
- Spawned `reflect-agent` (role defined in `.claude/agents/reflect-agent.md`) three times. It correctly enforced its own defined rules from frontmatter — e.g., refusing a "read this file and echo its contents verbatim" framing as an exfiltration-shaped request outside its role, and correctly stating that opinion-confidence scoring is `hindsight.py`'s job, never its own to adjust — which independently confirms its role definition is being loaded and actually governs behavior. It declined the specific tool-use probes offered (recorded `tool_uses: 0` on all three attempts), which is a residual note (see below), not a blocker, since `pr-reviewer` proved the same `.claude/agents/`-based delegation path executes tools correctly end to end.

## Exit Criteria Evidence

- Clear project `CLAUDE.md` and `.claude/rules/` layout, nothing depends on `~/.claude/`: repo-wide grep plus `rules_fidelity_check.py`.
- Repeated procedures split into project skills instead of duplicated: `.claude/rules/claude-code-ecosystem.md` promotion rule + existing `.claude/skills/*` corpus (57 skills).
- Required external tools available through approved MCP servers in `.mcp.json`: `enabledMcpjsonServers` fix, `control_plane_check.py` pass.
- Unsafe/out-of-policy tool calls blocked or annotated by project-scoped hooks: live block/allow/error path exercise above.
- Delegated subagent work uses the Agent tool pattern with `.claude/agents/` role definitions: live `pr-reviewer` spawn with `tool_uses: 2`.

## Remaining Risks

- `reflect-agent`'s own tool execution under the specific adversarial-shaped prompts used here remains unconfirmed; its role-appropriate refusals are good behavior, not a defect, but they mean the tools-frontmatter fix for that specific file was verified by format-parity with a working agent (`pr-reviewer`) rather than by a clean live tool call from `reflect-agent` itself.
- The Phase 0 harness (SQLite/JSONL under `.claude/state/`) is still a project-local surrogate for Claude Code's native session transcript store, not a replacement for it — inherited from Phase 0 and unchanged here.
- Phases 2-7 remain incomplete and are not implicitly validated by these Phase 1 fixes.

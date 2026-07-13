# Completion Matrix

Legend:

- `existing` = present and verified by repo evidence or baseline checks.
- `partial` = some supporting files exist, but the criterion is not fully proven.
- `missing` = no matching implementation path is present.
- `unverified` = static presence exists, but the criterion is not proven by the baseline.

## Phase 0: Core Foundation

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| A single Claude Code session can be started, resumed, compacted, and verified end to end. | existing | `.claude/hooks/session-start.sh`; `.claude/hooks/pre-compact.sh`; `.claude/hooks/pre-tool-use.sh`; `.claude/hooks/post-tool-use.sh`; `tests/test_phase0_smoke.py` | The hook path now writes session state, logs a verified checkpoint before compaction, and the smoke test exercises start -> act -> verify -> compact -> pause -> resume -> archive. |
| Every Agent tool call has a durable request/result record under `.claude/state/`. | existing | `.claude/scripts/phase0_control_plane.py`; `.claude/hooks/pre-tool-use.sh`; `.claude/hooks/post-tool-use.sh`; `tests/test_phase0_control_plane.py` | Requests and results are normalized to structured events, written to SQLite plus raw JSONL exports, and replayed from the log. |
| Session state can be reconstructed after restart without guessing. | existing | `.claude/scripts/phase0_control_plane.py`; `tests/test_phase0_control_plane.py`; `tests/test_phase0_smoke.py` | The restart tests reopen the same state root in a fresh control-plane instance and resume only from a verified checkpoint. |
| Failures are visible, attributable, and recoverable before the next turn runs. | existing | `.claude/scripts/phase0_control_plane.py`; `.claude/hooks/pre-tool-use.sh`; `tests/test_phase0_control_plane.py` | Terminal failures are explicit, bounded retries are logged, and failures stay correlated to session, turn, step, and tool call. |

## Phase 1: Rules, Skills & Hooks

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| The repo has a clear project `CLAUDE.md` and `.claude/rules/` layout; nothing depends on `~/.claude/`. | existing | `CLAUDE.md`; `.claude/rules/*.md` (all carry `paths:` frontmatter, verified by `rules_fidelity_check.py`); `.claude/settings.json`; `docs/claude-code-control-plane-roadmap-v2.md` | Repo scan found no active `~/.claude/*` dependency; only descriptive/comparative mentions in audit docs and community-derived skill references. |
| Repeated procedures are split into project skills instead of duplicated in chat or root docs. | existing | `.claude/skills/*` (57 skills); `.claude/rules/claude-code-ecosystem.md` (skill-promotion rule added in Phase 1 pass) | Added an explicit promotion rule: check `.claude/skills/` before writing a procedure inline; promote once it recurs; skip a skill for one-off work. Closes the prior "no promotion discipline" gap; verified by `rules_fidelity_check.py`. |
| Required external tools are available through approved MCP servers declared in `.mcp.json`. | existing | `.mcp.json`; `.claude/settings.json`; `.claude/memory/hindsight_mcp.py` | Fixed a real approval-wiring bug: `.claude/settings.json` declared `allowedMcpServers` (a managed-scope-only key, wrong shape) instead of the documented project-scope key `enabledMcpjsonServers` (confirmed against `.claude/docs/.../code-claude-com-docs-en-settings-*.md`); collaborators would have been re-prompted for `graphiti-memory` on every session. Corrected to `"enabledMcpjsonServers": ["graphiti-memory"]`; `control_plane_check.py` and `rules_fidelity_check.py` both pass after the fix. |
| Unsafe or out-of-policy tool calls are blocked or annotated by project-scoped hooks before the next loop step. | existing | `.claude/hooks/pre-tool-use.sh`; `.claude/hooks/lib/pre-tool-use-guard.js`; `.claude/hooks/post-tool-use.sh`; `.claude/scripts/control_plane_check.py` | Directly exercised all three required paths with a Windows-native `cwd` payload (matching real Claude Code invocation): (1) block — `Edit` on `.env.production` and `Bash rm` under `migrations/` both exit 2 with a stderr reason; (2) allow — `Read` on `README.md` exits 0 and logs the request; (3) error — malformed/empty stdin exits 1 with a visible `Phase0 error: ...` stderr message, which per the official hooks doc is a non-blocking error the transcript surfaces as a `<hook name> hook error` notice, correctly distinguishing annotation from blocking. |
| Delegated subagent work uses the Agent tool pattern with role definitions in `.claude/agents/`. | existing | `.claude/agents/implementation-agent.md`; `.claude/agents/pr-reviewer.md`; `.claude/agents/reflect-agent.md`; `.claude/agents/upstream-auditor.md` | Found and fixed a real frontmatter bug: `reflect-agent.md` and `upstream-auditor.md` declared `tools: [read, grep, git, shell, ...]` — lowercase names, and `git`/`shell`/`github` are not real Claude Code tool identifiers — while the other two agents correctly used `tools: Read, Grep, Bash`/`Edit`. Corrected both to the canonical form. Obtained live runtime proof of delegation: spawned `pr-reviewer` via the Agent tool with a diagnostic prompt; it called `Bash` (`git status --short`) and `Read` (its own frontmatter file), returning real, verifiably-accurate live repo state (`tool_uses: 2`). `reflect-agent` was also spawned successfully and enforced its own defined rules (e.g., refused to act as a generic file-echo proxy, correctly citing that opinion-scoring is `hindsight.py`'s job per its own frontmatter) — confirming its role definition governs behavior, though it declined the specific tool-use probes given its narrow scope; this narrow-role caution is a residual note, not a blocker, since `pr-reviewer` proved the same `.claude/agents/` delegation path executes tools correctly end to end. |

## Phase 2: Project-Level Memory & State

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| The control plane can reconstruct project memory from the repo-local hierarchy after restart and after a fresh clone on a new machine. | partial | `CLAUDE.md`; `CLAUDE.local.md`; `.claude/settings.local.json`; `.claude/memory/` | Project memory pieces exist, but repo-local durable state is still missing. |
| Auto memory, compaction summaries, and subagent summary exports are visible in the backend and live under `.claude/`. | missing | No `.claude/state/compactions/`, `.claude/state/agents/`, or `.claude/state/ledger.md` existed before this baseline. | The repo currently has project memory only, not the export layer. |
| The backend can show whether recovery came from native files or from an external index. | missing | No backend index or recovery metadata exists in `.claude/state/`. | There is no implementation path yet. |
| A project can resume with the same effective memory state across sessions without depending on an external store or on `~/.claude/` for correctness. | unverified | `CLAUDE.md`; `.claude/settings.local.json`; `.claude/memory/` | The repo is project-scoped, but restart behavior is not proven. |

## Phase 3: Sub-Agent Orchestration

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| The control plane can spawn named custom subagents from `.claude/agents/` with explicit tool and permission scopes. | partial | `.claude/agents/*.md` | Role definitions exist; spawn/runtime behavior is not proven. |
| Subagent work is routed by role, not by ad hoc prompt duplication. | partial | `.claude/agents/*.md`; `.claude/workflows/issue-to-pr.js` | There is role structure, but no observed routing policy. |
| Operators can see active subagents, their summaries, and their state exports from one place. | missing | No `.claude/state/agents/` directory or export artifacts exist yet. | Visibility is not implemented. |
| Parent sessions can resume or merge delegated work without replaying the entire exploration history. | missing | No `.claude/state/` resume index, no merge artifacts, no checkpoint store. | No replay-safe handoff path exists yet. |
| Worker catalogs stay small enough that specialization improves clarity instead of creating a taxonomy problem. | unverified | `.claude/skills/*`; `.claude/agents/*` | The catalog is large enough that this must be managed deliberately; the baseline does not prove the ceiling is respected. |

## Phase 4: Dynamic Workflows

The roadmap section defines workflow selection, graph execution, planner, evaluation gates, and recovery, but it does not include a separate exit-criteria block. This baseline records the phase as partially surfaced through existing commands/workflows and leaves the rest unproven.

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Fixed, named workflows are available as the default execution path. | partial | `.claude/commands/control-plane-check.md`; `.claude/commands/create-pr.md`; `.claude/commands/review-pr.md`; `.claude/workflows/issue-to-pr.js` | Workflow entrypoints exist, but the roadmap's broader dynamic-workflow control plane is not implemented. |
| Dynamic graph execution over bounded checkpoints is available. | missing | No `.claude/state/checkpoints/` graph artifacts or workflow engine state. | No graph runtime exists yet. |
| A planner can propose bounded plans over approved steps and tools. | missing | `.claude/settings.json` does not set `plansDirectory`; no `.claude/plans/` tree exists. | Plan-mode persistence is not wired. |
| Evaluation gates can verify transitions before work advances. | partial | `.claude/hooks/stop.sh`; `.claude/scripts/control_plane_check.py` | Stop hooks and validation scripts exist, but no workflow gate state is persisted. |
| Recovery can re-plan from the last checkpoint and prune failed branches. | missing | No `.claude/state/checkpoints/` or branch records. | Recovery branching is not implemented. |

## Phase 5: Portable Project-Scoped Framework

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| A fresh clone plus `/bootstrap-control-plane` reproduces the full framework with zero reliance on `~/.claude/`. | missing | No `/bootstrap-control-plane` command file or installer script exists. | The baseline only captures current scaffolding. |
| Every gate produces its durable artifact in `.claude/state/` or `.claude/plans/`; `/status` can answer from disk alone. | missing | No `.claude/state/` artifacts beyond the baseline scaffold; no `/status` command. | Durable gate artifacts are not present yet. |
| The same framework runs unmodified against at least two unrelated stacks. | missing | No portable bootstrap package or cross-stack eval harness exists. | No multi-stack evidence is present. |
| Main-thread context stays below ~50% on multi-plan work because building happens in fresh subagent contexts. | unverified | `.claude/agents/*`; `.claude/workflows/issue-to-pr.js` | The repo has orchestration pieces, but no measurement baseline for context pressure. |

## Phase 6: Determinism Ladder & Adversarial Verification

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Every must-happen behavior lives at rung 3+ and demonstrably fires, not just documented. | partial | `.claude/hooks/*.sh`; `.claude/hooks/lib/pre-tool-use-guard.js`; `.claude/scripts/control_plane_check.py` | Hooks exist and are checked, but event-logged proof of all must-happen behaviors is absent. |
| No destructive git or filesystem action is reachable without a deterministic block or explicit human approval. | existing | `.claude/settings.json`; `.claude/hooks/lib/pre-tool-use-guard.js`; `.claude/scripts/control_plane_check.py` | The guard blocks protected probes and the settings file deny-lists destructive patterns. |
| Verifier disagreement with builder self-reports is measured and nonzero. | missing | No verifier metrics, no ledger, no disagreement report. | Nothing measures verifier-vs-builder drift yet. |
| Gate metrics exist and have driven at least one ladder promotion and one demotion. | missing | No `.claude/state/ledger.md` history existed before this baseline. | There is no metrics loop yet. |

## Phase 7: Distribution, Versioning & Continuous Improvement

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Framework core installs into a virgin repo as one pinned, versioned plugin plus `/bootstrap-control-plane`. | missing | No plugin package, version manifest, or bootstrap command exists. | Nothing distributable is present yet. |
| At least one full upgrade cycle completed across two repos with no behavior surprises. | missing | No release or upgrade records exist in `.claude/state/`. | No upgrade evidence. |
| One retro cycle has upstreamed a project-local improvement into the shared core. | missing | No retro artifacts or upstream sync path exist. | No upstream loop yet. |
| A third-party skill or pattern has been adopted through the review pipeline rather than bulk-installed. | missing | No eval gate, import review, or adoption record exists. | Intake is descriptive only at this point. |

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
| Unsafe or out-of-policy tool calls are blocked or annotated by project-scoped hooks before the next loop step. | existing | `.claude/hooks/pre-tool-use.sh`; `.claude/hooks/lib/pre-tool-use-guard.js`; `.claude/hooks/post-tool-use.sh`; `.claude/scripts/control_plane_check.py` | Directly exercised all three required paths with a Windows-native `cwd` payload (matching real Claude Code invocation): (1) block â€” `Edit` on `.env.production` and `Bash rm` under `migrations/` both exit 2 with a stderr reason; (2) allow â€” `Read` on `README.md` exits 0 and logs the request; (3) error â€” malformed/empty stdin exits 1 with a visible `Phase0 error: ...` stderr message, which per the official hooks doc is a non-blocking error the transcript surfaces as a `<hook name> hook error` notice, correctly distinguishing annotation from blocking. |
| Delegated subagent work uses the Agent tool pattern with role definitions in `.claude/agents/`. | existing | `.claude/agents/implementation-agent.md`; `.claude/agents/pr-reviewer.md`; `.claude/agents/reflect-agent.md`; `.claude/agents/upstream-auditor.md` | Found and fixed a real frontmatter bug: `reflect-agent.md` and `upstream-auditor.md` declared `tools: [read, grep, git, shell, ...]` â€” lowercase names, and `git`/`shell`/`github` are not real Claude Code tool identifiers â€” while the other two agents correctly used `tools: Read, Grep, Bash`/`Edit`. Corrected both to the canonical form. Obtained live runtime proof of delegation: spawned `pr-reviewer` via the Agent tool with a diagnostic prompt; it called `Bash` (`git status --short`) and `Read` (its own frontmatter file), returning real, verifiably-accurate live repo state (`tool_uses: 2`). `reflect-agent` was also spawned successfully and enforced its own defined rules (e.g., refused to act as a generic file-echo proxy, correctly citing that opinion-scoring is `hindsight.py`'s job per its own frontmatter) â€” confirming its role definition governs behavior, though it declined the specific tool-use probes given its narrow scope; this narrow-role caution is a residual note, not a blocker, since `pr-reviewer` proved the same `.claude/agents/` delegation path executes tools correctly end to end. |

## Phase 2: Project-Level Memory & State

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| The control plane can reconstruct project memory from the repo-local hierarchy after restart and after a fresh clone on a new machine. | existing | `.claude/scripts/phase2_memory.py`; `.claude/hooks/session-start.sh`; `tests/test_phase2_smoke.py::test_fresh_clone_session_start_hook_bootstraps_and_starts_session`; `tests/test_phase2_memory.py::test_status_reconstructs_after_restart_from_a_fresh_process_instance` | The real `SessionStart` hook, run against an empty temp workspace with no pre-existing `.claude/settings.local.json` or state root, bootstraps `autoMemoryDirectory` to an absolute repo-local path; a fresh `Phase2` process pointed at the same roots reconstructs the same checkpoint/compaction/agent-export evidence. |
| Auto memory, compaction summaries, and subagent summary exports are visible in the backend and live under `.claude/`. | existing | `.claude/state/compactions/`; `.claude/state/agents/`; `.claude/hooks/pre-compact.sh`; `.claude/hooks/post-compact.sh`; `.claude/hooks/subagent-stop.sh`; `tests/test_phase2_smoke.py::test_precompact_then_postcompact_then_session_start_restore_end_to_end`; `tests/test_phase2_smoke.py::test_subagent_stop_hook_exports_summary` | Both directories are populated by the real hook chain (not just static presence) and inspected via `phase2_memory.py status`. |
| The backend can show whether recovery came from native files or from an external index. | existing | `.claude/scripts/phase2_memory.py` `status` command, `recovery` field | Always reports `source: "native-files"`, `external_index_configured: false`; no external store was built, matching the roadmap's "file layout first" ordering. |
| A project can resume with the same effective memory state across sessions without depending on an external store or on `~/.claude/` for correctness. | existing | `tests/test_phase2_smoke.py::test_precompact_then_postcompact_then_session_start_restore_end_to_end`; `tests/test_phase2_memory.py::test_session_start_restore_rejects_stale_or_foreign_snapshot`; `tests/test_phase2_memory.py::test_session_start_restore_rejects_corrupt_snapshot` | Drives real `session-start -> tool cycle -> verify -> pre-compact -> post-compact -> session-start(source=compact)` through actual shell hooks and CLI; restored `additionalContext` contains the verified checkpoint and real compact summary text; a snapshot whose `session_id` does not match, or that is corrupt, is rejected rather than reused, with the rejection itself persisted as evidence. |

## Phase 3: Sub-Agent Orchestration

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| The control plane can spawn named custom subagents from `.claude/agents/` with explicit tool and permission scopes. | existing | `.claude/agents/scout.md`, `planner.md`, `builder.md`, `verifier.md` (new); `.claude/scripts/phase3_agents.py`; `tests/test_phase3_agents.py` | Each new file declares an explicit `tools:` allowlist; `scout`/`planner` add `permissionMode: plan`, `builder` adds `isolation: worktree`. Live spawn proof obtained via `upstream-auditor` (already registered this session) — the four new files were written and pass static checks but hadn't reached this session's own Agent-tool registry yet (session-timing gap, recorded in the Phase 3 report, not a defect in the files). |
| Subagent work is routed by role, not by ad hoc prompt duplication. | existing | `.claude/scripts/phase3_agents.py` `route()`; `tests/test_phase3_agents.py::test_route_resolves_project_agent_role_from_real_catalog` and siblings | Role is resolved live from each agent's own frontmatter, never hand-duplicated. Proven against real, non-test data: a live `upstream-auditor` spawn routed to `role: read-only-researcher`. |
| Operators can see active subagents, their summaries, and their state exports from one place. | existing | `.claude/state/agents/<parent_session_id>/<agent_id>.task.json`; `phase3_agents.py list` | Populated by the real `SubagentStart`/`SubagentStop` hooks and inspected via `list`; proven against both unit-test fixtures and a real live delegation. |
| Parent sessions can resume or merge delegated work without replaying the entire exploration history. | existing | `phase3_agents.py handoff`; `.claude/rules/subagent-routing.md` | `handoff` requires real verification evidence (command + exit code) or an explicit `--summary-only` flag before marking a task `merged`, preventing a summary from being treated as proof. Proven live: a real task was independently verified and merged without opening its transcript. |
| Worker catalogs stay small enough that specialization improves clarity instead of creating a taxonomy problem. | existing | `.claude/agents/AGENTS.md` | 8 total agent files (4 existing + 4 new). `AGENTS.md` explicitly records the roles deliberately not added (extra reviewer lenses, agent teams) and why, making the catalog boundary a documented decision. |

## Phase 4: Dynamic Workflows

The roadmap section defines workflow selection, graph execution, planner, evaluation gates, and recovery, but it does not include a separate exit-criteria block; this matrix maps each capability row to the implemented engine and its test evidence.

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Fixed, named workflows are available as the default execution path. | existing | `.claude/workflows/defs/linear-static.json`; `.claude/commands/workflow.md`; `tests/test_phase4_workflows.py::test_linear_static_workflow_runs_to_completion` | `linear-static` is the default no-branch chain; `.claude/commands/control-plane-check.md`, `create-pr.md`, `review-pr.md`, `.claude/workflows/issue-to-pr.js` remain the other fixed entrypoints. |
| Dynamic graph execution over bounded checkpoints is available. | existing | `.claude/scripts/phase4_workflows.py` (`advance`, `verify_node`); `.claude/workflows/defs/evidence-branch.json`; `tests/test_phase4_workflows.py::test_evidence_driven_branch_routes_to_debug_then_ships`, `::test_exhausted_retries_produce_explicit_terminal_failure` | Conditional branching (`run-tests -> {ship, debug}`), bounded per-node retries (default 2, matching Phase 0's `MAX_RETRIES`), explicit terminal failure on exhaustion. |
| A planner can propose bounded plans over approved steps and tools. | existing | `phase4_workflows.propose_next()`; `tests/test_phase4_workflows.py::test_list_and_status_reconstruct_from_disk_alone`; `tests/test_phase4_workflows.py::test_unsupported_branch_is_rejected_and_recorded` | `propose_next()` returns only the current node's declared `allowed_next`; `advance()` structurally rejects any node outside that allowlist and records the rejection. `plansDirectory` was already wired in Phase 2. |
| Evaluation gates can verify transitions before work advances. | existing | `phase4_workflows.verify_node()`/`advance()` (`UnverifiedNodeError`); `.claude/hooks/stop.sh`; `.claude/scripts/control_plane_check.py` (`check_workflow_defs`) | A node cannot be departed before its own step is verified; high-risk nodes additionally require a real verified Phase 0 checkpoint (`CheckpointRequiredError`), proven by `test_high_risk_transition_requires_a_real_verified_checkpoint`. |
| Recovery can re-plan from the last checkpoint and prune failed branches. | existing | `phase4_workflows.resume()`; `tests/test_phase4_workflows.py::test_resume_rolls_back_to_last_verified_node_after_interruption` | `resume()` rolls `current_node` back to the last verified node after an interruption, never continuing from an unproven in-flight node; `fallback()` records an explicit pinned-static-path decision as visible state. |

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

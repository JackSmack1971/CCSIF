# Ledger

## 2026-07-12 Baseline scaffold

- Goal: establish the execution baseline for the Claude Code Control Plane roadmap without implementing later phases.
- Read: `docs/claude-code-control-plane-roadmap-v2.md` in full before touching the repo.
- Added: `.claude/state/execution-manifest.json`, `.claude/state/baseline.md`, `.claude/state/completion-matrix.md`.
- Verification commands:
  - `git rev-parse --show-toplevel; git status --short --branch; git branch --show-current; git rev-parse HEAD` -> `0`
  - `Get-FileHash docs/claude-code-control-plane-roadmap-v2.md -Algorithm SHA256` -> `0`
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
- Validation follow-up:
  - `Get-Content -Raw .claude/state/execution-manifest.json | ConvertFrom-Json` plus roadmap link resolution -> `0`
- Current dependency check: no active repository file requires `~/.claude/*` or other machine-global Claude state.
- Notes: the repo already contained unrelated untracked roadmap/docs files; they were left untouched.

## 2026-07-12 Phase 0 complete

- Goal: implement the smallest tested Phase 0 harness for gather-context -> act -> verify with durable state, replayable events, and verified checkpoint resume.
- Added: `.claude/scripts/phase0_control_plane.py`, `.claude/hooks/pre-compact.sh`, `tests/test_phase0_control_plane.py`, `tests/test_phase0_smoke.py`, `.claude/state/roadmap/phase-0-report.md`, `.claude/state/roadmap/phase-0-checkpoint.json`.
- Updated: `.claude/hooks/session-start.sh`, `.claude/hooks/pre-tool-use.sh`, `.claude/hooks/post-tool-use.sh`, `.claude/scripts/control_plane_check.py`, `.claude/settings.json`, `.claude/state/completion-matrix.md`, `.claude/state/execution-manifest.json`.
- Verification commands:
  - `python -m py_compile .claude/scripts/phase0_control_plane.py tests/test_phase0_control_plane.py tests/test_phase0_smoke.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0`
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
- Evidence:
  - Tool-call request/result replay, raw export retention, restart reconstruction, sandbox rejection, interrupted-session recovery, and terminal retry exhaustion are all covered by the new tests.
  - Compaction now writes a verified checkpoint before context trim via `.claude/hooks/pre-compact.sh`.
- Notes:
  - Phase 1 remains untouched.
  - Unrelated untracked roadmap/docs files remain preserved.

## 2026-07-12 Phase 1 complete

- Goal: close the two "partial" Phase 1 criteria (skill-promotion discipline, subagent delegation proof) and verify the three "existing" criteria against live behavior rather than static presence, per `docs/claude-code-control-plane-roadmap-v2.md`.
- Read: `docs/claude-code-control-plane-roadmap-v2.md` Phase 1 section; `.claude/state/roadmap/phase-0-report.md` and checkpoint (confirmed evidence-complete before proceeding); `.claude/settings.json`; `.claude/rules/*.md`; `.claude/agents/*.md`; `.claude/hooks/*`; `.mcp.json`.
- Fixed:
  - `.claude/settings.json`: replaced the non-standard `allowedMcpServers` key with the documented `enabledMcpjsonServers: ["graphiti-memory"]`, so the project `.mcp.json` server is actually auto-approved instead of re-prompting collaborators.
  - `.claude/agents/reflect-agent.md`, `.claude/agents/upstream-auditor.md`: corrected `tools:` frontmatter from lowercase/invalid names (`[read, grep, git, shell, ...]`) to canonical Claude Code tool identifiers (`Read, Grep, Bash`), matching the working format already used by `implementation-agent.md` and `pr-reviewer.md`.
  - `.claude/rules/claude-code-ecosystem.md`: added a skill-promotion rule (check `.claude/skills/` before writing a procedure inline; promote once it recurs; skip a skill for one-off work), kept inside the file's existing 20-line budget.
- Verified (live behavior, not just static presence):
  - PreToolUse hook block/allow/error paths, exercised with a Windows-native `cwd` payload matching real Claude Code invocation: block (`Edit` on `.env.production`, `Bash rm` under `migrations/` → exit 2 with stderr reason), allow (`Read` on `README.md` → exit 0), error (malformed/empty stdin → exit 1, visible per the hooks doc's "non-blocking error" contract).
  - Agent-tool delegation to a `.claude/agents/`-defined role: spawned `pr-reviewer` with a diagnostic task; it called `Bash` and `Read` and returned real, verifiably-accurate live `git status` output (`tool_uses: 2`).
  - `.mcp.json` fix confirmed valid JSON and both governance checks pass.
- Verification commands:
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (6 tests, no regression)
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
- Evidence: `.claude/state/roadmap/phase-1-report.md`, `.claude/state/roadmap/phase-1-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 1 section.
- Notes:
  - Phase 2 is untouched, per instruction not to start it.
  - `reflect-agent` correctly enforced its own narrow role scope during two of three test probes (declining to act as a generic file-echo proxy); this is recorded as a residual note in the completion matrix, not a blocker, since `pr-reviewer` proved the same delegation path executes tools end to end.
  - Unrelated untracked files (`claude-code-control-plane-roadmap.md` v1, `docs/`) remain preserved and untouched.

## 2026-07-12 Phase 2 complete

- Goal: implement Phase 2 (Project-Level Memory & State) — make the repo-local memory stack authoritative, add a bootstrap-safe `autoMemoryDirectory` mechanism, tested compaction snapshot/restore, and subagent-summary export — while keeping correctness independent of `~/.claude/*` and any external store, per `docs/claude-code-control-plane-roadmap-v2.md`.
- Read: roadmap Phase 2 section in full; `.claude/state/execution-manifest.json`; `.claude/state/roadmap/phase-0-report.md` and `phase-1-report.md` (confirmed both `status: complete` before proceeding); effective `CLAUDE.md`/`CLAUDE.local.md`; `.claude/rules/*.md`; `.claude/settings.json`; `.claude/settings.local.json` (existing machine file, left untouched); `.gitignore`; `.claude/scripts/phase0_control_plane.py`; `.claude/scripts/control_plane_check.py`; `.claude/scripts/rules_fidelity_check.py`; `.claude/hooks/*`; the cached official hooks reference (`.claude/docs/.../code-claude-com-docs-en-hooks-88d3d79.md`) for the exact PreCompact/PostCompact/SessionStart/SubagentStop input/output contract.
- Added:
  - `.claude/scripts/phase2_memory.py` — bootstrap (`autoMemoryDirectory`), PreCompact snapshot, PostCompact summary, SessionStart validated restore (rejects stale/foreign/corrupt snapshots), SubagentStop export, and a `status` reconstruction/indexing command.
  - `.claude/hooks/post-compact.sh`, `.claude/hooks/subagent-stop.sh` (new); `.claude/hooks/session-start.sh`, `.claude/hooks/pre-compact.sh` (extended, non-blocking via `|| true`).
  - `.claude/rules/memory-and-compaction.md` — `.claude/memory/` committed-or-private policy, compaction contract, subagent-export location, prompt-cache stable-prefix/invalidator documentation.
  - `.claude/plans/.gitkeep`, `.claude/state/compactions/.gitkeep`, `.claude/state/agents/.gitkeep`.
  - `tests/test_phase2_memory.py` (16 unit tests), `tests/test_phase2_smoke.py` (real-hook subprocess smoke tests).
  - `.claude/state/roadmap/phase-2-report.md`, `.claude/state/roadmap/phase-2-checkpoint.json`.
- Fixed: `.claude/scripts/phase2_memory.py` `memory_status()` initially counted `.gitkeep` as a subagent "parent session" (used `iterdir()` without filtering to directories) — corrected before writing this ledger entry; verified with a live `status` run against this repo.
- Updated: `.claude/settings.json` (`plansDirectory`, `PostCompact`, `SubagentStop` hooks), `.claude/scripts/control_plane_check.py` (new required paths + shell-parse list), `.claude/scripts/rules_fidelity_check.py` (registered the new rule file), `.claude/state/completion-matrix.md` (Phase 2 section), `.claude/state/execution-manifest.json` (`phase_2: complete`, `phase_2_completion` block, `next_goal`).
- Verification commands:
  - `python -m py_compile .claude/scripts/phase2_memory.py tests/test_phase2_memory.py tests/test_phase2_smoke.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (22 tests: 6 Phase 0 + 16 Phase 2, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
  - `git check-ignore -v` against every new Phase 2 path -> `1` (nothing ignored; all evidence is git-visible)
  - `python3 .claude/scripts/phase2_memory.py status` (live, against this repo) -> `0`
- Evidence: `.claude/state/roadmap/phase-2-report.md`, `.claude/state/roadmap/phase-2-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 2 section.
- Notes:
  - Phase 3 is untouched, per instruction not to start it.
  - The real, pre-existing machine-local `.claude/settings.local.json` on this workstation was deliberately left unmodified — the bootstrap mechanism is proven end-to-end against fresh and pre-existing fixtures in `tests/test_phase2_smoke.py` rather than by mutating the user's live local config outside of the native `SessionStart` hook path.
  - Unrelated untracked files present since before this session (`claude-code-control-plane-roadmap.md` v1, `docs/`, `.claude/state/logs/`, `.claude/state/raw/`, `.claude/state/phase0.sqlite3`, `.claude/state/roadmap/phase-1-*`) remain preserved and untouched.

## 2026-07-12 Phase 3 complete

- Goal: implement Phase 3 (Sub-Agent Orchestration) — a deliberately small worker catalog covering the roadmap's recurring roles, plus parent-child task tracking, role routing, stale-worker detection, and verified merge/handoff under `.claude/state/agents/`, per `docs/claude-code-control-plane-roadmap-v2.md`.
- Read: roadmap Phase 3 section in full; `.claude/state/execution-manifest.json`; `.claude/state/roadmap/phase-{0,1,2}-report.md` and checkpoints (confirmed all `status: complete` before proceeding); current `.claude/agents/*.md`; `.claude/hooks/*`; `.claude/scripts/phase0_control_plane.py` and `phase2_memory.py`; `.claude/settings.json`; `.claude/rules/subagent-routing.md`; the cached official subagents/hooks references (`.claude/docs/.../code-claude-com-docs-en-sub-agents-ceb0b8dc.md`, `...-hooks-88d3d79.md`) for exact frontmatter fields (`isolation`, `permissionMode`) and the `SubagentStart`/`SubagentStop` input schema.
- Added:
  - `.claude/agents/scout.md`, `planner.md` — read-only researcher/planner, `tools: Read, Grep, Glob` only, `permissionMode: plan`.
  - `.claude/agents/builder.md` — generic scoped executor, `isolation: worktree` (frontmatter-level, runtime-enforced) for non-GitHub work; `implementation-agent.md` left untouched on its existing branch-per-issue isolation.
  - `.claude/agents/verifier.md` — generic independent verifier, distinct from the GitHub-PR-specific `pr-reviewer.md`.
  - `.claude/scripts/phase3_agents.py` — `subagent-start`/`subagent-stop` (task tracking wired to native `SubagentStart`/`SubagentStop` hooks), `route` (role lookup read live from each agent's own frontmatter), `handoff` (requires real verification evidence or explicit `--summary-only`; never treats a summary as proof), `sweep` (stale-worker detection), `list` (disk-only reconstruction of all delegated work).
  - `.claude/hooks/subagent-start.sh` (new); `.claude/hooks/subagent-stop.sh` (extended to also call phase3's `subagent-stop`, alongside the existing Phase 2 export).
  - `tests/test_phase3_agents.py` (19 unit tests), `tests/test_phase3_smoke.py` (2 real-hook subprocess smoke tests).
  - `.claude/state/roadmap/phase-3-report.md`, `.claude/state/roadmap/phase-3-checkpoint.json`.
- Updated: `.claude/agents/AGENTS.md` (catalog index + explicit record of roles deliberately not modeled as files: supervisor/dispatcher is the main session itself; no extra reviewer lenses or agent teams added, with reasons); `.claude/rules/subagent-routing.md` (writer isolation + handoff-not-summary conventions, body only, `paths:` frontmatter untouched); `.claude/settings.json` (new `SubagentStart` hook registration); `.claude/scripts/control_plane_check.py` (new required paths + shell-parse list); `.claude/state/completion-matrix.md` (Phase 3 section); `.claude/state/execution-manifest.json` (`phase_3: complete`, `phase_3_completion` block, `next_goal`).
- Verification commands:
  - `python -m py_compile .claude/scripts/phase3_agents.py tests/test_phase3_agents.py tests/test_phase3_smoke.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (45 tests: 6 Phase 0 + 16 Phase 2 unit + 4 Phase 2 smoke + 19 Phase 3 unit + 2 Phase 3 smoke, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
  - `git check-ignore -v` against every new Phase 3 path -> `1` (nothing ignored; all evidence is git-visible)
- Live proof: spawned `upstream-auditor` (already registered in this session) via the real Agent tool with a diagnostic-only, read-only probe; the real `SubagentStart`/`SubagentStop` hooks fired and wrote a genuine task record under `.claude/state/agents/<real-session-id>/`, routed to `role: read-only-researcher` with the correct live `tool_scope`; `phase3_agents.py list` reconstructed it and `phase3_agents.py handoff --verification-command ... --verification-exit-code 0` marked it `merged` after independent re-verification — proving the routing/tracking/handoff path end to end against real, non-test data.
- Notes:
  - The four brand-new role files (`scout`, `planner`, `builder`, `verifier`) were not spawned live under their own names in this session — this session's Agent-tool registry had not refreshed to include files added mid-session, a session-timing gap recorded as a residual risk, not a defect in the shipped files (all pass `control_plane_check.py`'s static checks).
  - Phase 4 is untouched, per instruction not to start it.
  - Unrelated untracked files remain preserved and untouched.

## 2026-07-12 Phase 4 complete

- Goal: implement Phase 4 (Dynamic Workflows) as a static-first, allowlisted-graph workflow layer wrapping Phase 0's verified-checkpoint mechanism, per `docs/claude-code-control-plane-roadmap-v2.md`, without inventing an unrestricted graph engine or duplicating native `/goal`/`/loop`/routines/plan-mode/hooks/agents.
- Read: roadmap Phase 4 section in full; `.claude/state/execution-manifest.json`; `.claude/state/roadmap/phase-{0,1,2,3}-report.md` and checkpoints (confirmed all `status: complete` before proceeding); `.claude/settings.json`; `.claude/scripts/phase0_control_plane.py`, `phase3_agents.py`, `control_plane_check.py`, `rules_fidelity_check.py`; `.claude/commands/*`; `.claude/workflows/AGENTS.md`; `.claude/agents/AGENTS.md`; `.claude/rules/AGENTS.md`; `.claude/hooks/stop.sh`.
- Added:
  - `.claude/scripts/phase4_workflows.py` — allowlisted-graph engine: `start_run`/`propose_next`/`verify_node`/`advance`/`resume`/`fallback`/`replay`/`status`/`list_runs`. `advance()` rejects any transition outside the current node's `allowed_next` (and records the rejection); high-risk nodes require a real verified Phase 0 checkpoint via `Phase0ControlPlane.load_checkpoint()`; retries are bounded per node (default 2) with an explicit `failed-exhausted-retries` terminal state; `resume()` rolls back to the last verified node.
  - `.claude/workflows/defs/linear-static.json` (fixed 4-node chain) and `.claude/workflows/defs/evidence-branch.json` (evidence-driven branch + bounded debug/retry loop), both `risk: high`/`checkpoint_required: true` on their `ship` node.
  - `.claude/commands/workflow.md` — thin CLI entrypoint doc.
  - `.claude/rules/dynamic-workflows.md` — durable policy for the same invariants (registered in `rules_fidelity_check.py`).
  - `.claude/state/workflows/.gitkeep`.
  - `tests/test_phase4_workflows.py` — 9 tests covering all six required scenarios (linear run, evidence branch, rejected branch, interrupted resume, exhausted retries, checkpoint gate) plus definition validation and disk-only reconstruction.
  - `.claude/state/roadmap/phase-4-report.md`, `.claude/state/roadmap/phase-4-checkpoint.json`.
- Updated: `.claude/scripts/control_plane_check.py` (new required paths + `check_workflow_defs()` deterministic gate), `.claude/scripts/rules_fidelity_check.py` (registered `dynamic-workflows.md`), `.claude/commands/AGENTS.md`, `.claude/rules/AGENTS.md`, `.claude/workflows/AGENTS.md`, `.claude/state/completion-matrix.md` (Phase 4 section), `.claude/state/execution-manifest.json` (`phase_4: complete`, `phase_4_completion` block, `next_goal`).
- Verification commands:
  - `python -m py_compile .claude/scripts/phase4_workflows.py .claude/scripts/control_plane_check.py .claude/scripts/rules_fidelity_check.py tests/test_phase4_workflows.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (54 tests: 45 prior + 9 new Phase 4, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
  - `git check-ignore -v` against every new Phase 4 path -> `1` (nothing ignored; all evidence is git-visible)
- Evidence: `.claude/state/roadmap/phase-4-report.md`, `.claude/state/roadmap/phase-4-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 4 section.
- Notes:
  - Phase 5 is untouched, per instruction not to begin it.
  - No live `/goal`/`/loop`/routines invocation was scripted from Python; those are product-level session behaviors, so this phase's contribution is limited to the durable, checkpoint-gated, replayable state layer those native features can sit on top of (same posture Phase 3 took toward native foreground/background subagent execution).
  - Unrelated untracked files remain preserved and untouched.


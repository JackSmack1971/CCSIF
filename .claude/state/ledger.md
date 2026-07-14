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

## 2026-07-12 Phase 5A complete

- Goal: complete Roadmap Phase 5A — establish the portable "Control Plane in a Folder" core, layout, operating doctrine, and skill taxonomy — by auditing the existing `.claude/` tree first and consolidating rather than duplicating, per `docs/claude-code-control-plane-roadmap-v2.md` Phase 5 and the task's explicit instruction.
- Read: roadmap in full; `.claude/state/execution-manifest.json`; `.claude/state/roadmap/phase-{0,1,2,3,4}-report.md` and checkpoints (confirmed all `status: complete` before proceeding); the full existing `.claude/rules/*.md` corpus (16 files), all 5 `.claude/commands/*.md` bodies, and a sample of `.claude/skills/*/SKILL.md` frontmatter (57 skills) to audit for existing taxonomy compliance before writing new rules; `.claude/scripts/rules_fidelity_check.py` and `control_plane_check.py` to understand the existing fidelity-check mechanics before registering new files.
- Added:
  - `.claude/rules/10-karpathy-guidelines.md` — assumption-surfacing, verify-before-done, metric-gated experiment loops; deliberately excludes content already in `surgical-density.md`.
  - `.claude/rules/20-lifecycle-gates.md` — the five-gate Align/Research/Plan/Build/Verify&Ship contract: inputs, outputs, durable artifact, verification owner, risk escalation, explicit-skip policy. Documentation only; no gate command files added, per task scope.
  - `.claude/rules/30-skill-taxonomy.md` — the two-axis rule (commands orchestrate and never invoke each other; skills are single-purpose, may be `user-invocable: true` without becoming orchestrators).
  - `.claude/scripts/taxonomy_check.py` — deterministic linter: command-cross-invocation, duplicate skill/command description, always-loaded context budget (measured 140/400 lines), global-path (`~/.claude`) dependency in hooks/scripts/commands, oversized root `CLAUDE.md` (measured 74/200 lines). Wired into `control_plane_check.py` as `check_taxonomy()`.
  - `tests/test_taxonomy_check.py` — 11 tests, one positive/negative pair per check against isolated fixture trees, plus a real-repo pass-through test.
  - `docs/CONTEXT.md` — domain glossary (term, meaning, owning file).
  - `docs/adr/0000-template.md`, `docs/adr/0001-phase-5a-portable-layout.md` — minimal ADR template plus the real ADR recording every consolidation-vs-new-file decision this phase made.
  - `.claude/state/handoffs/.gitkeep`, `.claude/state/research/.gitkeep` — the two durable-state subdirectories the roadmap names that did not already exist (`ledger.md`, `agents/`, `checkpoints/`, `roadmap/` existed from Phases 0-2).
  - `.claude/state/roadmap/phase-5a-report.md`, `.claude/state/roadmap/phase-5a-checkpoint.json`.
- Extended (not replaced): `.claude/rules/00-core-workflow.md` — added a Scope Doctrine pointer and a loop-discipline cross-reference; kept its existing role as the operating-doctrine file rather than adding a competing `00-operating-doctrine.md`.
- Updated: `.claude/scripts/control_plane_check.py` (new `check_taxonomy()` step + required path), `.claude/scripts/rules_fidelity_check.py` (registered 3 new rule files with `paths:`/`MAX_LINES`), `.claude/rules/AGENTS.md` (entry-point list), `.claude/state/completion-matrix.md` (Phase 5 split into 5A-complete and 5B/5C-not-started sections), `.claude/state/execution-manifest.json` (`phase_5a: complete`, `phase_5a_completion` block, `next_goal`).
- Audit finding: the existing 57-skill, 5-command, 8-agent corpus already followed the two-axis convention (every skill description states one job plus an explicit `NOT for X; use Y instead` non-goal; no command body invokes another command) — `30-skill-taxonomy.md` documents a convention that was already live, and `taxonomy_check.py` found 0 violations rather than needing to fix any.
- Verification commands:
  - `python -m py_compile .claude/scripts/taxonomy_check.py .claude/scripts/control_plane_check.py .claude/scripts/rules_fidelity_check.py tests/test_taxonomy_check.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (65 tests: 54 prior + 11 new, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
  - `git check-ignore -v` against every new Phase 5A path -> `1` (nothing ignored; all evidence is git-visible)
- Evidence: `.claude/state/roadmap/phase-5a-report.md`, `.claude/state/roadmap/phase-5a-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 5 section.
- Notes:
  - Phase 5B/5C (`/bootstrap-control-plane`, cross-stack proof, main-thread context measurement) and Phase 6/7 are untouched, per instruction not to begin them.
  - The global-path-dependency check does not scan `.claude/skills/` or `.claude/agents/`; a manual grep found 7 skill files with descriptive, non-functional `~/.claude` mentions (optional install-scope documentation), recorded as a residual risk rather than silently treated as clean.
  - Unrelated untracked files remain preserved and untouched.

## 2026-07-12 Phase 5B complete

- Goal: implement Phase 5B — task-agnostic lifecycle commands, discipline skills, a code-agnostic verify adapter, and durable artifacts — per `docs/claude-code-control-plane-roadmap-v2.md` Phase 5.2/5.3/5.4, without starting Phase 5C or Phase 6.
- Read: roadmap in full; `.claude/state/execution-manifest.json`; `.claude/state/roadmap/phase-5a-report.md` and checkpoint (confirmed `status: complete` before proceeding); `.claude/rules/{20-lifecycle-gates,30-skill-taxonomy}.md`; `.claude/scripts/{taxonomy_check,control_plane_check,phase0_control_plane,phase3_agents,phase4_workflows}.py`; the full existing `.claude/commands/*.md` (5 files) and a broad sample of `.claude/skills/*/SKILL.md` (handoff, research, tdd, fsv-verify, grill-with-docs, test-strategy, to-spec, git-automation, diagnosing-bugs) to identify which disciplines already had a fitting skill before writing anything new.
- Added:
  - 11 thin commands (`.claude/commands/{brainstorm,grill,research,plan,build,verify,ship,handoff,status,debug,experiment}.md`) — each orchestrates skills/agents/scripts, never another command (0 cross-invocation violations, machine-checked).
  - 4 new model-invoked skills for the disciplines with no existing fit: `alignment-interview` (open/interrogative requirements interviewing), `atomic-planning` (≤3-task plan creation via the lifecycle script), `session-takeover` (durable repo-committed cold-start handoff, distinct from the pre-existing OS-temp-directory `handoff` skill), `metric-gated-experiment` (Karpathy AutoResearch keep/revert loop). Reused unmodified: `research`, `tdd`, `fsv-verify`, `diagnosing-bugs`, `git-automation`, `grill-with-docs`.
  - `.claude/scripts/phase5b_verify.py` + `.claude/hooks/verify.sh`/`verify.ps1` — a single code-agnostic verify adapter that parses `CLAUDE.md`'s own Source-of-Truth Commands block into named targets (`full`/`lint`/`test`/`<slug>`), plus non-code `rubric`/`citation`/`factcheck` targets that deterministically return exit 2 (defer to model judgment) instead of fabricating a pass/fail. Exit codes are always 0 (pass), 1 (fail), or 2 (unavailable).
  - `.claude/scripts/phase5b_lifecycle.py` — atomic plan create/validate/list (≤3 tasks, explicit assumptions, per-task verification target, explicit commit boundary, blocking edges validated against real plan files on disk), disk-only status reconstruction, cold-start handoff creation (verification evidence or explicit `summary_only`, mirroring Phase 3's `handoff` pattern), and metric-gated experiment start/record/decide.
  - `tests/test_phase5b_verify.py` (21 tests), `tests/test_phase5b_lifecycle.py` (20 tests) — parsing, target resolution, pass/fail/unavailable exit-code propagation (including through the real bash hook wrapper), plan-sizing rejection cases, status reconstruction against real fixture state, handoff cold-start content, and experiment keep/revert decisions in both directions.
  - `.claude/state/roadmap/phase-5b-report.md`, `.claude/state/roadmap/phase-5b-checkpoint.json`.
- Updated: `.claude/rules/20-lifecycle-gates.md` (replaced a now-stale "command implementations remain future work" sentence with pointers to the real command files and the verify adapter; stayed within its 40-line budget at 39 lines), `.claude/scripts/control_plane_check.py` (registered every new required path, added `verify.sh` to the shell-parse check, added `check_verify_adapter()`), `.claude/state/completion-matrix.md` (Phase 5B section added, Phase 5C section split out from the old combined 5B/5C row), `.claude/state/execution-manifest.json` (`phase_5b: complete`, `phase_5b_completion` block, `next_goal`).
- Incidents caught and fixed before any test run completed: (1) `check_verify_adapter()` initially called the `control-plane` verify target, which shells out to `control_plane_check.py` itself — infinite self-recursion; fixed to use the non-recursive `rules` target. (2) `test_phase5b_verify.py`'s synthetic `CLAUDE.md` fixture initially pointed its fake "unit tests" command at the real `tests/` directory with `cwd=ROOT`, which would re-run the entire real suite (including itself) as a subprocess; two orphaned `python.exe` processes were observed and killed (not a runaway fork bomb), and the fixture was repointed at a nonexistent `fixture_tests` directory that fails fast instead.
- Verification commands:
  - `python -m py_compile .claude/scripts/phase5b_lifecycle.py .claude/scripts/phase5b_verify.py .claude/scripts/control_plane_check.py tests/test_phase5b_lifecycle.py tests/test_phase5b_verify.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (106 tests: 65 prior + 41 new, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 .claude/scripts/taxonomy_check.py` -> `0`
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
  - `git check-ignore -v` against every new Phase 5B path -> `1` (nothing ignored; all evidence is git-visible)
  - `bash .claude/hooks/verify.sh run control-plane` -> `0`; `run rubric` -> `2`; `run does-not-exist` -> `2`
- Evidence: `.claude/state/roadmap/phase-5b-report.md`, `.claude/state/roadmap/phase-5b-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 5B/5C sections.
- Notes:
  - Phase 5C (`/bootstrap-control-plane`, cross-stack proof, main-thread context measurement) and Phase 6/7 are untouched, per instruction not to begin them.
  - `/build` and `/ship`'s delegated agent/skill flows (builder, pr-reviewer, tdd, git-automation) were verified statically (taxonomy, frontmatter) rather than by a real live delegated run in this session.
  - The `/experiment` gate's revert step is a documented `SKILL.md` instruction, not a script-enforced git action; nothing mechanically verifies the working tree matches a `revert` decision.
  - Unrelated untracked files remain preserved and untouched.

## Phase 5C: /bootstrap-control-plane, fresh-clone recovery, cross-stack portability proof

- Confirmed Phase 5B complete before starting (`phase-5b-report.md`, `phase-5b-checkpoint.json`, status `complete`; `control_plane_check.py`, `rules_fidelity_check.py`, and 106 tests re-verified `PASS`). Read `docs/claude-code-control-plane-roadmap-v2.md`, the manifest, Phase 5A/5B evidence, existing verify-adapter/lifecycle scripts, `.gitignore`, and both settings files in full before any change.
- Added:
  - `.claude/scripts/bootstrap_control_plane.py` — additive-only, idempotent installer/reconciler. Scans/interviews for issue tracker, build/test/lint or non-code verifier, commit convention, mandatory/skippable gates, memory policy, and platform; generates a stack-agnostic minimal payload (`verify_adapter.py`, `lifecycle.py`, `common.py`, generic rule/command/skill stubs) rather than copying this repo's own CCSIF-specific Phase 0-5B scripts; merges (never overwrites) `CLAUDE.md`'s Source-of-Truth Commands facts block; writes `autoMemoryDirectory` (absolute) only into gitignored `.claude/settings.local.json`, additive-only, mirroring `phase2_memory.bootstrap_local_settings`'s exact contract; appends safe `.gitignore` entries; validates hooks/permissions/required paths; runs a trivial five-gate smoke workflow.
  - `.claude/commands/bootstrap-control-plane.md` — thin orchestrator delegating entirely to the script above.
  - `.claude/scripts/phase5c_portability_proof.py` — builds two throwaway fixture repos (a Python code stack and a docs-only non-code research pipeline), bootstraps each from a fresh copy, runs every post-bootstrap step (validate/smoke/status) as an independent fresh subprocess with `HOME`/`USERPROFILE` pointed at a directory that does not exist, and persists evidence to `.claude/state/roadmap/phase-5c-portability-evidence.json`.
  - `.claude/scripts/phase5c_context_pressure.py` — documented, reproducible byte-based context-pressure proxy (no live token metering available in this environment): reuses the always-loaded instruction budget measurement (140/400 lines, 35%) and adds a 10-plan dispatcher-load-vs-naive-inline-cost ratio (15.9%), both under the roadmap's ~50% target; persisted to `.claude/state/roadmap/phase-5c-context-pressure-evidence.json`.
  - `tests/test_bootstrap_control_plane.py` (18 tests), `tests/test_phase5c_portability.py` (1 integration test), `tests/test_phase5c_context_pressure.py` (2 tests) — idempotence, migration/preservation of pre-existing customizations, Windows/POSIX path handling, rollback-safe (resumable) failure, validate/smoke, stack detection, full two-workload portability proof, context-pressure proxy assertions.
  - `.claude/state/roadmap/phase-5c-report.md`, `.claude/state/roadmap/phase-5c-checkpoint.json`.
- Updated: `.claude/scripts/control_plane_check.py` (registered 5 new required paths), `.claude/state/completion-matrix.md` (Phase 5C section moved from "not started" to "complete" with real evidence), `.claude/state/execution-manifest.json` (`phase_5c: complete`, `phase_5: complete`, `phase_5c_completion` block, `next_goal`).
- Incident caught and fixed before any full test run completed: `taxonomy_check.py`'s global-path-dependency scanner flagged `~/.claude/*` mentions inside the new scripts' own no-dependency documentation (docstrings/comments describing the guarantee, not creating one); fixed by rewording each to include an explicit negation word (`never`/`must never`) within the checker's 120-character negation window, re-verifying `control_plane_check.py` and `taxonomy_check.py` `PASS` after each fix.
- Verification commands:
  - `python -m py_compile .claude/scripts/bootstrap_control_plane.py .claude/scripts/phase5c_portability_proof.py .claude/scripts/phase5c_context_pressure.py .claude/scripts/control_plane_check.py tests/test_bootstrap_control_plane.py tests/test_phase5c_portability.py tests/test_phase5c_context_pressure.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (127 tests: 106 prior + 21 new, no regression)
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python3 .claude/scripts/taxonomy_check.py` -> `0`
  - `python3 .claude/scripts/phase5c_portability_proof.py` -> `0` (`both_passed: true` for both fixture workloads)
  - `python3 .claude/scripts/phase5c_context_pressure.py` -> `0` (`within_target: true`, 15.9% dispatcher load vs. 50% target)
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
- Evidence: `.claude/state/roadmap/phase-5c-report.md`, `.claude/state/roadmap/phase-5c-checkpoint.json`, `.claude/state/roadmap/phase-5c-portability-evidence.json`, `.claude/state/roadmap/phase-5c-context-pressure-evidence.json`, updated `completion-matrix.md` Phase 5C section.
- Notes:
  - Phases 6 and 7 are untouched, per instruction not to begin them.
  - Context-pressure figures are a documented byte-based proxy, not live Agent-SDK token metering; none is available in this environment.
  - The portability proof uses fresh temp-directory copies to simulate a fresh clone; no real `git clone` of a pushed remote was performed (no remote was designated for this task).
  - Bootstrap's generated framework is a deliberately minimal, stack-agnostic payload; it does not transplant this repo's own accumulated Phase 0-5B tooling (session harness, subagent tracking, dynamic workflow engine), which remains Phase 7's "package the stable core as a versioned plugin" concern.
  - Unrelated untracked files (pre-existing roadmap docs, `.scratch/`, prior-session state dirs) remain preserved and untouched.

## Phase 6 ladder promotion: git force-push/reset/branch-delete prohibition (2026-07-12T23:22:51.732978Z)

- Promoted from rung-1 documentation-only guidance (`CLAUDE.md` Protected Areas, the user's global `git-workflow.md` 'Never use raw `--force`') and rung-5 literal-prefix `permissions.deny` entries to rung-4 hook enforcement (`pre-tool-use-guard.js`'s `GIT_DESTRUCTIVE_RULES`).
- Why: a string-prefix deny rule (`Bash(git push --force:*)`) does not catch `git push -f`, `git push --force-with-lease`, a compound command (`npm test && git push -f`), or an env-var-prefixed invocation (`GIT_TRACE=1 git push --force`) -- all reachable bypasses of the rung-1/5 guidance that a real user or agent could hit.
- Evidence: `tests/test_phase6a_guardrails.py::GitGuardrailTests` (18 cases: force-push variants, remote ref/tag deletion, reset --hard, clean -f*, branch -D, filter-branch/filter-repo/rebase, stash drop/clear, reflog expire), all asserting `permissionDecision: ask` (native human-approval prompt), never re-blocking silently.

## Phase 6 ladder demotion/refinement: fd-duplication redirect carve-out (retroactively logged) (2026-07-12T23:23:04.899539Z)

- Rule: `MUTATING_BASH_TOKEN`'s `(?!&)` negative lookahead in `pre-tool-use-guard.js`, excluding `2>&1`/`1>&2`/`>&2` fd-duplication redirects from the mutating-command trigger.
- Why: an earlier version of this rung-4 rule blocked legitimate stderr-redirect commands (which never write to a file) twice before the carve-out was added -- the roadmap's own audit rule (a rung-4 rule that blocks legitimate work twice should be demoted/refined) applied, and the fix predates this phase's formal ladder documentation. Logged now, retroactively, per `.claude/rules/40-determinism-ladder.md`'s instruction to record every ladder change.
- Evidence: `tests/test_phase6a_guardrails.py::PreExistingBehaviorRegressionTests::test_fd_dup_redirects_still_allowed` and `control_plane_check.py`'s `check_fd_dup_redirects()`, both passing against the current guard.

## 2026-07-12 Phase 6A complete (2026-07-12T23:28:02.851410Z)

- Goal: implement Phase 6A -- the determinism ladder plus baseline guardrails with measured, bounded enforcement -- per `docs/claude-code-control-plane-roadmap-v2.md` Phase 6.1/6.2/6.4, without starting Phase 6B or Phase 7.
- Confirmed Phase 5 complete before starting (`execution-manifest.json` phase_5/phase_5c `complete`; `phase-5c-report.md`/`phase-5c-checkpoint.json`). Read the roadmap Phase 6 section, the manifest, current `.claude/settings.json`, all `.claude/hooks/*.sh`, `pre-tool-use-guard.js`, `control_plane_check.py`, and the pre-existing Phase 6 completion-matrix baseline (partial/missing) before any change.
- Added: `.claude/rules/40-determinism-ladder.md` (ladder table, rung-4-vs-5 split, promotion/demotion audit rule with two real ladder-change records); `.claude/scripts/ledger_append.py` (append-only ledger writer, the only sanctioned path -- the guard blocks every direct write to `ledger.md`); `.claude/scripts/phase6a_lint_on_edit.py` + extended `post-tool-use.sh` (verify-adapter lint-on-touched-file, in-process import to dodge a Windows bare-`bash`-resolves-to-non-git-bash hazard); `.claude/scripts/phase6a_stop_gate.py` + rewritten `stop.sh` (bounded per-session Stop-gate retries, `stop_hook_active` short-circuit, ledger escalation, never an infinite loop); `.claude/scripts/phase6a_metrics.py` (read-only trigger/block/ask/error/latency/false-block-review/ladder-change measurement); 66 new tests across 5 files (`test_phase6a_{guardrails,stop_gate,metrics,ledger_append,lint_on_edit}.py`).
- Extended `pre-tool-use-guard.js`: `GIT_DESTRUCTIVE_RULES` (force push incl. `-f`/`--force-with-lease`/compound/env-prefixed variants, remote ref/tag delete, `reset --hard`, `clean -f*`, `branch -D`, `filter-branch`/`filter-repo`/`rebase`, `stash drop/clear`, `reflog expire`) returning `ask`; path-traversal (`..` segment) block; new `lockfile mass-edit` (ask) and `append-only ledger` (block) protected-path categories; per-category `severity`; correlation-id + latency JSONL logging for every allow/ask/block/error decision.
- Updated: `control_plane_check.py` (5 new required paths, 2 new protected + 2 new allowed probes), `rules_fidelity_check.py` (registered the new rule file's path scope + line budget), `completion-matrix.md` Phase 6 section, `execution-manifest.json` (`phase_6a: complete`, `phase_6a_completion` block; `phase_6` stays `partial` since Phase 6B's verifier-disagreement measurement is out of this phase's scope).
- Verification: `node -c pre-tool-use-guard.js` -> 0; `python -m unittest discover -s tests -v` -> 0 (193 tests: 127 prior + 66 new, no regression); `control_plane_check.py` -> PASS; `rules_fidelity_check.py` -> PASS; `taxonomy_check.py` -> PASS; `phase6a_metrics.py` -> 293 guardrail events (184 allow/42 ask/62 block/5 error, p50 2ms/p95 4ms/max 13ms), `ledger_ladder_changes` promotions=1 demotions=1; `settings.json` JSON-valid.
- Evidence: `.claude/state/roadmap/phase-6a-report.md`, `phase-6a-checkpoint.json`, updated `completion-matrix.md` Phase 6 section, this entry and the two ladder-change entries above (all via `ledger_append.py`).
- Notes: Phase 6B (verifier-vs-builder disagreement, review-lens agents, red-team pass) and Phase 7 (distribution/versioning) are untouched, per instruction not to begin them. The secrets-path regex's benign-lookalike false positives are a documented, intentional precision tradeoff within an otherwise-deterministic rule, not a probabilistic trigger. Unrelated untracked files (pre-existing roadmap docs, `.scratch/`, prior-session state dirs) remain preserved and untouched.

## 2026-07-14 Gone-upstream branch review

- Reviewed the 21 local branches reported by `git branch -vv` as `origin/*: gone`.
- Confirmed the current checkout had no live worktree attached to any of those gone-upstream refs in `git worktree list --porcelain`.
- Retained the branch refs unchanged in this PR because the actual cleanup step is destructive and should go through a separate approved maintenance pass.
- Verification for this review is the branch inventory in `git branch -vv` and the worktree inventory in `git worktree list --porcelain`; no branch delete or force-push was performed here.

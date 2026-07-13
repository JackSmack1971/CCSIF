# Phase 3 Report

Status: complete

## Summary

Phase 0, 1, and 2 were confirmed evidence-complete before this phase started
(`.claude/state/roadmap/phase-{0,1,2}-report.md`, all `status: complete`;
`control_plane_check.py` and `rules_fidelity_check.py` re-verified `PASS`
before any change), per the roadmap's sequencing requirement.
`docs/claude-code-control-plane-roadmap-v2.md` Phase 3 section was read in
full before any change.

Implemented a deliberately small worker catalog covering the roadmap's
recurring roles, plus a project-scoped tracking layer under
`.claude/state/agents/` that turns delegated subagent work into visible,
reconstructable, verified state instead of an ad hoc prompt pattern.

### Worker catalog (`.claude/agents/`)

| Role | Agent | Tools | Isolation / permission mode | Notes |
|---|---|---|---|---|
| Read-only scout/researcher | `scout.md` (new) | Read, Grep, Glob | `permissionMode: plan`; no Bash/Write/Edit | Structurally cannot write — no write-capable tool is in its list at all, and `plan` mode is a second, independent enforcement layer |
| Planner | `planner.md` (new) | Read, Grep, Glob | `permissionMode: plan` | Proposes ≤3-task atomic plans with assumptions/verification target; never edits files |
| Scoped builder | `builder.md` (new) | Read, Grep, Glob, Edit, Write, Bash | `isolation: worktree` | Generic bounded-change executor for non-GitHub work; frontmatter `isolation: worktree` is enforced by the Claude Code runtime itself, not just documented policy |
| Scoped builder (existing) | `implementation-agent.md` | Read, Grep, Edit, Bash | branch-per-issue (its own conflict-safe convention) | Left as-is: GitHub issue-to-pr flow; branch-per-issue is its equivalent isolation, not retrofitted with worktree isolation to avoid changing the working `issue-to-pr` skill's assumptions |
| Independent verifier | `verifier.md` (new) | Read, Grep, Bash | default | Re-derives pass/fail from a plan's success criteria + diff, never the builder's narrative; distinct from `pr-reviewer`, which is GitHub-PR-specific |
| Independent verifier (existing) | `pr-reviewer.md` | Read, Grep, Bash | default | Unchanged; GitHub PR merge-readiness lens |
| Read-only researcher (existing) | `upstream-auditor.md` | Read, Grep, Bash | default | Unchanged; audit-only, creates GitHub issues but never edits code |
| Memory synthesis (existing) | `reflect-agent.md` | Read, Grep, Bash | default | Unchanged; outside the Phase 3 delegation catalog proper |

Supervisor/dispatcher is **not** a new agent file: the roadmap and the
official subagent docs both describe it as the main Claude Code session
itself ("the lead agent coordinates subtasks and merges results"), so it is
documented in `.claude/agents/AGENTS.md` as a role-not-modeled-as-a-file,
governed by `.claude/rules/subagent-routing.md` and this phase's tracking
script instead. Additional reviewer lenses (security/architecture/
maintainer) and collaborative agent teams were deliberately **not** added —
this repo's actual content (governance scripts, hooks, docs) shows no
evidenced recurring need beyond the existing correctness/merge-readiness
lens plus the new generic verifier, and no task here has required workers to
exchange state mid-task. Both omissions are recorded in
`.claude/agents/AGENTS.md` so the decision is visible, not silent.

### Control-plane tracking (`.claude/scripts/phase3_agents.py`)

- `subagent-start` / `subagent-stop`: wired to the native `SubagentStart`
  (new) and `SubagentStop` (extended) hooks. Each subagent spawn gets a task
  record at `.claude/state/agents/<parent_session_id>/<agent_id>.task.json`
  carrying `task_id` (`<parent_session_id>:<agent_id>`), `agent_type`, a
  routed `role`, `tool_scope` (parsed live from the agent's own `.md`
  frontmatter — never hand-duplicated, so it cannot drift), `isolation`,
  `status`, `started_at`/`completed_at`, a best-effort `checkpoint` (the
  parent session's latest verified Phase 0 checkpoint at spawn time, if
  any), `exported_summary`, `transcript_pointer`, `stop_resume_state`, and
  `merge_handoff_result`. This coexists with, and does not replace, Phase 2's
  own `<agent_id>.json` summary export.
- `route`: resolves an `agent_type` to a role by reading
  `.claude/agents/*.md` frontmatter directly (built-ins `Explore`/`Plan`/
  `general-purpose` are routed via a fixed table since they have no file to
  read). An unknown `agent_type` is routed `"unrouted"` rather than blocked —
  `SubagentStart` hooks cannot block per the documented hook contract, so
  visibility, not enforcement, is the correct control here.
- `handoff`: the parent-verification gate. Requires either
  `--verification-command` + `--verification-exit-code` (recorded, and the
  task is marked `merged` only if the exit code is `0`) or an explicit
  `--summary-only` flag (recorded `verified: false`, reason "a subagent's
  own summary is not treated as proof"). Refuses to hand off a task that
  hasn't reached `completed`/`stale` status, and refuses an unknown task
  outright. This is the mechanism that prevents a returned summary from
  being silently treated as proof of completion.
- `sweep`: marks `running` tasks whose `started_at` exceeds a threshold
  (default 120 minutes) as `stale`, so an interrupted/hung worker is visible
  rather than silently assumed still in flight. Completed tasks are never
  touched regardless of age.
- `list`: reconstructs every active and completed delegated task across all
  parent sessions from disk, satisfying the "reconstruct without opening
  every transcript" exit criterion.

### Hooks

- `.claude/hooks/subagent-start.sh` (new): calls `phase3_agents.py
  subagent-start`, non-blocking (`|| true`), matching the documented
  "`SubagentStart` cannot block" contract.
- `.claude/hooks/subagent-stop.sh` (extended): now calls both the existing
  Phase 2 `subagent-export` and the new Phase 3 `subagent-stop`, side by
  side, non-blocking.
- `.claude/settings.json`: registered the new `SubagentStart` hook.

### Foreground/background and resume

Per the official subagent docs (`.claude/docs/.../code-claude-com-docs-en-
sub-agents-ceb0b8dc.md`), subagents already run foreground or background
natively, and resume is done via `SendMessage` to an agent ID — there is no
separate Claude-Code-native persistence layer to wrap here beyond what the
tracking script already records (`stop_resume_state`, `transcript_pointer`,
`agent_id`). The control plane's job is limited to what it can actually
influence: recording whether a task is `running` (potentially resumable),
`completed`, or `stale` (interrupted), which it does. No custom
foreground/background scheduler was built, because Claude Code's own
mechanism already covers it end to end; building a parallel one would
duplicate, not support, the native capability — this is the intended
"degrade explicitly" behavior for a capability that's already native rather
than missing.

## Verification

| Command | Exit |
|---|---:|
| `python -m py_compile .claude/scripts/phase3_agents.py tests/test_phase3_agents.py tests/test_phase3_smoke.py` | `0` |
| `python -m unittest discover -s tests -v` (45 tests: 6 Phase 0 + 16 Phase 2 + 4 Phase 2 smoke + 19 Phase 3 unit + 2 Phase 3 smoke, no regression) | `0` |
| `python3 .claude/scripts/control_plane_check.py` | `0` |
| `python3 .claude/scripts/rules_fidelity_check.py` | `0` |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | `0` |
| `git check-ignore -v` against every new Phase 3 path | `1` (nothing ignored; all evidence is git-visible) |
| Live delegation via the real Agent tool (`upstream-auditor`, diagnostic-only `git status --short` probe) | subagent completed; real `SubagentStart`/`SubagentStop` hooks fired against the live session and wrote a real task record under `.claude/state/agents/<real-session-id>/` |
| `python3 .claude/scripts/phase3_agents.py list` (against the live task record above) | `0`, task reconstructed with `role: read-only-researcher`, `tool_scope: [Read, Grep, Bash]` |
| `python3 .claude/scripts/phase3_agents.py handoff --parent-session-id <real> --agent-id <real> --verification-command "..." --verification-exit-code 0 --note "..."` (against the live task) | `0`, `status: merged`, `merge_handoff_result.verified: true` |

### Exit Criteria Evidence

- **The control plane can spawn named custom subagents from `.claude/agents/`
  with explicit tool and permission scopes**: `scout.md`, `planner.md`,
  `builder.md`, `verifier.md` each declare an explicit `tools:` allowlist
  (and `scout`/`planner` additionally declare `permissionMode: plan`);
  `builder.md` declares `isolation: worktree`. Live spawn proof was obtained
  via `upstream-auditor` (already registered in this session); the four new
  role files are written correctly and pass `control_plane_check.py`'s
  required-path and shell-parse checks, but this session's own Agent-tool
  registry had not refreshed to include them by the time of writing (see
  Remaining Risks — an environment/session-timing gap, not a defect in the
  files themselves).
- **Subagent work is routed by role, not ad hoc prompt duplication**:
  `phase3_agents.route()`, exercised in
  `tests/test_phase3_agents.py::test_route_resolves_project_agent_role_from_real_catalog`
  and siblings, plus the live proof above showing `upstream-auditor` routed
  to `role: read-only-researcher` in real, non-test data.
- **Operators can see active subagents, their summaries, and their state
  exports from one place**: `phase3_agents.py list`, proven against both
  the unit-test fixtures (`test_list_tasks_reconstructs_across_parent_sessions`)
  and the live task record from the real delegation above.
- **Parent sessions can resume/merge delegated work without replaying the
  entire exploration history**: `phase3_agents.py handoff`, proven live —
  the parent verified the subagent's claim independently (`git status
  --short (manually re-run...)`, exit `0`) and the task was marked `merged`
  without re-opening the subagent's transcript. `merge_handoff_result` is
  `null` until a `handoff` call happens, so an un-handed-off task is
  visibly distinct from a merged one.
- **Worker catalogs stay small enough that specialization improves clarity**:
  8 total agent files after this phase (4 existing + 4 new); `AGENTS.md`
  explicitly records the roles deliberately *not* added (extra reviewer
  lenses, agent teams) and why, so the catalog's boundary is a documented
  decision rather than an accident of not having gotten to it yet.

## Design Decisions

1. Task tracking piggybacks on Phase 2's `<agent_id>.json` export
   convention but writes a separate `<agent_id>.task.json` file rather than
   extending Phase 2's schema, so a completed, signed-off phase's file
   format and tests are never touched by this phase.
2. Tool scope is read live from each agent's own frontmatter (`tools:`
   line) rather than hand-copied into a routing table, so the routing
   table cannot silently drift from the real, enforced tool list.
3. `SubagentStart` cannot block per the documented hook contract, so
   `route()` marks an unknown `agent_type` `"unrouted"` for visibility
   rather than attempting to enforce anything at that hook — enforcement of
   what a subagent can do lives entirely in its own frontmatter `tools:`/
   `permissionMode:`, which the Claude Code runtime itself enforces
   deterministically.
4. `handoff` treats "not yet verified" and "verified" as genuinely
   different states rather than defaulting a missing verification to
   either success or failure — a caller must explicitly choose
   `--summary-only` to record an unverified handoff; omitting all
   verification arguments without that flag is a hard error, not a silent
   default.
5. `builder.md` gets `isolation: worktree` in frontmatter (a real,
   runtime-enforced field) rather than a written policy asking the agent to
   "use a worktree" — `implementation-agent.md` is deliberately left on its
   existing branch-per-issue convention instead of being retrofitted, since
   it already provides equivalent conflict safety for the specific
   issue-to-pr flow it serves, and changing it was out of this phase's
   narrow scope.
6. No custom background/resume scheduler was built. Claude Code's own
   foreground/background execution and `SendMessage`-based resume already
   satisfy the roadmap's "support foreground and background/resumable work"
   requirement natively; the control plane's contribution is limited to
   recording `stop_resume_state` and the real `agent_id`/`transcript_pointer`
   so an operator can act on that native capability without duplicating it.
7. Collaborative agent teams were not implemented or tested. The roadmap
   explicitly scopes this to "a tested scenario that truly needs
   coordination" — no such scenario exists in this repo today, so building
   the pattern now would be speculative infrastructure with no proof it
   works, which the repo's own change-discipline rules (`surgical-density.md`,
   `constitutional-agent-engineering-rules.md`) rule out.

## Remaining Risks

- The four new agent role files (`scout`, `planner`, `builder`, `verifier`)
  were not exercised via a live Agent-tool spawn under their own names in
  this session — the session's Agent-tool registry was fixed at session
  start and had not refreshed to include files added mid-session, matching
  a known edge case in the official docs ("the watcher covers only
  directories that existed when the session started" — here the directory
  existed, but this host's registry still didn't pick up the new files
  within the session). The underlying mechanism (routing, tracking,
  handoff) was proven live end-to-end using `upstream-auditor`, an
  already-registered custom agent, which exercises the identical
  `SubagentStart`/`SubagentStop`/`phase3_agents.py` code path the new
  agents will use once a session restart picks them up. A follow-up session
  should spawn `scout`/`planner`/`builder`/`verifier` directly once
  available and confirm the same routing/tracking behavior, but this is a
  session-timing gap, not a defect in the shipped files (all four pass
  `control_plane_check.py`'s static required-path/shell-parse checks).
- `checkpoint` on a task record is best-effort: it is the parent session's
  latest *verified Phase 0* checkpoint at spawn time, which is only
  populated for sessions that have gone through the Phase 0 harness's own
  verify/compact cycle. A parent session that hasn't yet compacted will
  correctly show `checkpoint: null` rather than a fabricated value (see
  `test_subagent_start_checkpoint_is_none_when_no_verified_checkpoint`).
- Phases 4-7 remain incomplete and are not implicitly validated by these
  Phase 3 changes.

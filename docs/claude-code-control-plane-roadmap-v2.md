# Claude Code Control Plane Roadmap — v2 (Project-Scoped, Portable)

> **Revision notes (v2).** This revision (a) cross-references every native-mechanism claim against the current official Claude Code docs (code.claude.com/docs), (b) re-scopes every global-path dependency to an equally functional project-scoped path under `<project-root>/.claude/*` so the entire control plane travels with the repo, and (c) appends Phases 5–7: a portable, code-agnostic project framework informed by GSD Core, Superpowers, gstack, mattpocock/skills, Karpathy's guidelines/AutoResearch pattern, and Anthropic's own best-practices guidance. Community material is treated as inspirational pattern-stock, not gospel.

---

## Scope Doctrine: Project-Local by Default

Everything the control plane depends on must live inside the repository so a `git clone` reproduces the full operating environment on any machine. The official scope system (Managed > CLI args > Local > Project > User) makes this straightforward: the **Project** scope (`.claude/` committed to git) is the canonical home; the **Local** scope (`.claude/settings.local.json`, gitignored) absorbs machine-specific values that cannot be relative paths. User scope (`~/.claude/*`) and managed scope are explicitly out of the framework's dependency graph — they may exist, but nothing in this roadmap may *require* them.

### Global → Project-Scoped Path Map (verified against official docs)

| Capability | Global path (avoid as dependency) | Project-scoped equivalent | Notes / caveats |
|---|---|---|---|
| Settings & permissions | `~/.claude/settings.json` | `.claude/settings.json` (team, committed) + `.claude/settings.local.json` (personal, gitignored) | Local overrides project overrides user. Committed `allow` rules pass through the workspace-trust gate; `settings.local.json` allow rules apply without it because the file is yours, not the repo's. |
| Memory / instructions | `~/.claude/CLAUDE.md` | `./CLAUDE.md` or `./.claude/CLAUDE.md`, plus `./CLAUDE.local.md` (gitignored) for per-machine overrides | Project CLAUDE.md is re-read from disk and re-injected after `/compact`; nested subdirectory CLAUDE.md files reload lazily. Target <200 lines per file. |
| Modular rules | `~/.claude/rules/` | `.claude/rules/*.md` with optional `paths:` frontmatter for path-scoped loading | Recursive discovery; symlinks supported for shared policy, but prefer committed copies for true portability. |
| Skills | `~/.claude/skills/` | `.claude/skills/<name>/SKILL.md` | Load-on-use; live change detection; team members get them automatically via git. |
| Slash commands | `~/.claude/commands/` | `.claude/commands/*.md` | Project commands show as "(project)". Supports `$ARGUMENTS`, bash execution, namespacing via subfolders. |
| Subagents | `~/.claude/agents/` | `.claude/agents/*.md` | Frontmatter controls model, tools, permission mode, preloaded skills, persistent memory, hooks. No local scope exists for agents — project scope is the portable unit. |
| Hooks | hooks in `~/.claude/settings.json` | `hooks` block in `.claude/settings.json` (or `.claude/settings.local.json` for personal ones) | Repo-supplied hooks are gated by workspace trust on first open — this is a feature, not a bug. Reference scripts by relative path inside `.claude/hooks/`. |
| MCP servers | user scope in `~/.claude.json` | `.mcp.json` at project root | Project scope is designed for team sharing. Pair with `"enableAllProjectMcpServers": true` or an explicit `enabledMcpjsonServers` list in `.claude/settings.json` so collaborators aren't re-prompted. `.mcp.json` supports `${ENV_VAR}` expansion — keep secrets out of the file. |
| Plan files | `~/.claude/plans` (default) | `"plansDirectory": "./.claude/plans"` in `.claude/settings.json` | Officially documented setting; path is relative to project root. Commit plans that constitute durable design records; gitignore scratch plans if noisy. |
| Auto memory | `~/.claude/projects/<project>/memory/` (default) | `autoMemoryDirectory` in `.claude/settings.local.json` pointing at `<abs-path-to-repo>/.claude/memory/` | **Caveat (per docs):** the value must be absolute or `~/`-prefixed — relative paths are not accepted, and honoring it from project settings requires accepting the workspace-trust dialog. Because the path is machine-specific, set it in `settings.local.json` and have the bootstrap skill (Phase 5) write it per machine. Add `.claude/memory/` to git (curated) or gitignore it (private) per project policy. |
| Plugins | `~/.claude/settings.json` `enabledPlugins` | `enabledPlugins` in `.claude/settings.json` | Team-pinned plugin set travels with the repo; marketplaces can be declared via `extraKnownMarketplaces`. |
| Session transcripts | `~/.claude/projects/...` transcript store | Not relocatable — treat as machine-local cache | Mitigate with the control plane's own export: durable state that matters (plans, checkpoints, summaries, ledgers) is written by hooks/skills into `.claude/state/` (Phase 2/5). Never treat the transcript store as the source of truth. |

### Canonical project tree

```text
<project-root>/
├── CLAUDE.md                     # facts + pointers only; <200 lines
├── CLAUDE.local.md               # gitignored personal overrides
├── .mcp.json                     # team MCP servers (env-var expansion, no secrets)
└── .claude/
    ├── settings.json             # permissions, hooks, plansDirectory, plugins, env
    ├── settings.local.json       # gitignored: autoMemoryDirectory, personal allows
    ├── rules/                    # modular, path-scoped instruction files
    ├── skills/                   # load-on-use procedures (one folder per skill)
    ├── commands/                 # user-invoked orchestration entrypoints
    ├── agents/                   # named subagent role definitions
    ├── hooks/                    # executable hook scripts (referenced from settings)
    ├── plans/                    # plan-mode outputs (plansDirectory)
    ├── memory/                   # relocated auto memory (optional, see caveat)
    └── state/                    # control-plane-owned durable state: ledgers, checkpoints, handoffs
```

---

## Phase 0: Core Foundation

Build only the pieces that make the agentic loop reliable before adding any dashboard workflows, orchestration UX, or multi-session extensions. The control plane must first support gather context -> act -> verify with durable state, predictable tool patterns, and compaction-safe session history. If this layer is weak, every later feature amplifies context pressure, hides tool failures, and makes recovery guesswork instead of verification.

| Component | Key tasks | Suggested stack | Success metrics | Risks |
|---|---|---|---|---|
| Agent loop harness / wrapper | Run the gather context -> act -> verify loop; normalize Agent tool calls; enforce one-step-at-a-time execution; gate compaction boundaries | Small Node.js or Python wrapper around Claude Code session calls (Agent SDK) | Loop can start, pause, resume, and verify without manual repair; wrapper preserves tool-call order and outputs | Wrapper drift from Claude Code behavior; accidental extra abstraction around the loop |
| Tool call + result handling | Capture every tool request and result; preserve structured payloads; attach errors to the originating turn; keep result parsing deterministic | Structured JSON event log plus thin parser/serializer, written under `.claude/state/logs/` | Every tool call is replayable from logs; failed tool calls are attributable to the exact turn; no silent result loss | Loose parsing; losing tool context across retries |
| Session lifecycle & state management | Create, resume, archive, and compact sessions; persist turn state, tool state, and session metadata; map sessions to dashboard records | SQLite for session metadata and turn index under `.claude/state/`, filesystem for raw exports | Sessions survive restart; compaction does not break resumption; session state is queryable by ID and status | State duplication; stale session pointers; compaction corrupting history |
| Observability / logging | Emit turn-by-turn logs, tool timings, failures, and compaction events; surface the active session and last verified step | JSON logs with a simple queryable index in `.claude/state/logs/`; stdout for local dev | Operators can answer "what happened" from logs alone; failures are traceable to one turn or tool call | Logging noise without signal; missing correlation IDs |
| Sandboxed execution | Constrain tool execution to approved paths and commands; isolate workspace writes; prevent cross-session leakage | Native sandbox settings + `permissions.deny` path rules in `.claude/settings.json`; OS-level allowlist only if native sandboxing is insufficient | Tool actions stay inside the intended workspace; unsafe paths are rejected before execution | Over-broad permissions; sandbox rules that block legitimate Claude Code workflows |
| Error recovery / verification | Retry bounded transient failures; verify tool outputs before progressing; recover from interrupted sessions; keep error states explicit | Minimal retry policy plus verification checks on returned tool output; native checkpoints (`/rewind`) as the file-level undo layer | Broken tool calls fail fast and are visible; resumed sessions continue from a verified checkpoint | Infinite retries; masking real failures; false-positive verification |

Why this comes first:

- The agentic loop only works if the harness can reliably gather context, act through tool calls, and verify before the next turn.
- Tool patterns must be stable before any UI or multi-session routing exists, otherwise the dashboard only reflects inconsistent turn data.
- Compaction creates hard context pressure, so session state has to survive trimming without losing the action trail or verification trail.
- Error recovery is foundational because every later feature depends on knowing whether a turn actually completed or just looked complete.

Exit criteria:

- A single Claude Code session can be started, resumed, compacted, and verified end to end.
- Every Agent tool call has a durable request/result record under `.claude/state/`.
- Session state can be reconstructed after restart without guessing.
- Failures are visible, attributable, and recoverable before the next turn runs.

## Phase 1: Rules, Skills & Hooks

Phase 1 adds the policy and extension layer on top of the Phase 0 loop. Use Claude Code's native mechanisms first: `CLAUDE.md` and `.claude/rules/` for persistent guidance, `SKILL.md` and MCP for reusable procedures plus external tools, and hooks for deterministic enforcement at loop boundaries. A custom rules engine is only worth adding when you need machine-enforced policy that cannot live as context or be enforced by hooks. **All three layers live at project scope.**

| Layer | Native Claude Code capability | Custom layer only if needed | Depends on Phase 0 | Suggested implementation | Metrics | Pitfalls |
|---|---|---|---|---|---|---|
| Rules | Project `CLAUDE.md` (`./CLAUDE.md` or `./.claude/CLAUDE.md`), `.claude/rules/*.md` with `paths:` frontmatter, `CLAUDE.local.md` for personal overrides | Thin rules registry or linter that normalizes duplicates or generates scoped files; do not re-implement memory | Stable session state, compaction-safe history, reliable context loading | Keep project facts in root `CLAUDE.md`; split multi-step procedures or path-specific guidance into `.claude/rules/`; prefer committed rule files over symlinks for portability; use `claudeMdExcludes` in `settings.local.json` to mute irrelevant monorepo ancestors | Fewer repeated corrections; lower re-typing of the same instruction; smaller context footprint for the same guidance | Treating rules as enforcement (they are context, not policy — the docs are explicit that blocking requires a PreToolUse hook); overstuffed root files (>200 lines degrades adherence); conflicting scopes; stale duplicates |
| Skills + MCP | `.claude/skills/<name>/SKILL.md` load-on-use, bundled skills, subagent execution (`context: fork`), dynamic context injection, and project `.mcp.json` for external tools/data | Packaging or routing layer that selects skills or servers by repo policy; avoid custom tool wrappers unless multiple repos need them | Stable tool-call capture, verified results, sandboxed execution, session metadata | Promote repeated procedures into project skills; if a skill needs live data or actions, connect an MCP server via `.mcp.json` instead of hard-coding API access; auto-approve team servers with `enabledMcpjsonServers` in `.claude/settings.json`; use the Agent tool for isolated verbose work | Skill reuse rate; fewer repeated prompt blocks; lower main-context token use; successful MCP calls per task | Loading too many skills; hiding simple instructions behind skills; trusting unvetted MCP servers; using a skill when a hook is required |
| Hooks | SessionStart, Setup, InstructionsLoaded, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, Stop, SubagentStart/Stop, TaskCreated/TaskCompleted, PreCompact/PostCompact, SessionEnd, ConfigChange, FileChanged, plus prompt-based, agent-based, and HTTP hooks | Minimal policy evaluator only when hook decisions need shared state or cross-event aggregation; keep it thin | Reliable loop iteration points, tool/result logs, and retry/verification behavior from Phase 0 | Define hooks in `.claude/settings.json`; store scripts in `.claude/hooks/` and reference by relative path; use PreToolUse to block unsafe actions, PostToolUse to validate or inject follow-up context, Stop for end-of-turn checks, PreCompact/SessionStart to re-inject critical context, and subagent/task hooks to enforce delegated-work rules | Blocked unsafe calls; hook latency; percent of failed actions caught before execution; verification pass rate after hooks | Turning hooks into business logic; blocking benign work; brittle JSON parsing; slow hook handlers that stall the loop; forgetting the workspace-trust gate on repo-supplied hooks |

Sequencing:

1. Start with the project memory files and path-scoped rules. That gives you low-friction guidance without adding runtime machinery.
2. Promote repeated procedures into `.claude/skills/` only after they recur enough to justify a reusable `SKILL.md`.
3. Add MCP servers to `.mcp.json` when a skill needs authoritative external data or actions.
4. Add hooks last, because they are the enforcement layer and depend on the loop being stable and observable.
5. Introduce a custom rules engine only if you need deterministic policy that cannot be expressed as scoped docs plus hooks.

Exit criteria:

- The repo has a clear project `CLAUDE.md` and `.claude/rules/` layout; nothing depends on `~/.claude/`.
- Repeated procedures are split into project skills instead of duplicated in chat or root docs.
- Required external tools are available through approved MCP servers declared in `.mcp.json`.
- Unsafe or out-of-policy tool calls are blocked or annotated by project-scoped hooks before the next loop step.
- Delegated subagent work uses the Agent tool pattern with role definitions in `.claude/agents/`.

## Phase 2: Project-Level Memory & State

Phase 2 turns Claude Code's memory model into a control-plane feature instead of a passive repository convention. The target is to keep project knowledge inside the native project memory stack — project `CLAUDE.md`, `.claude/rules/`, relocated auto memory, compaction instructions, and subagent transcript exports — then decide whether any external store is needed for indexing or fleet-wide reporting. The default design preserves Claude Code's own memory boundaries so the backend enhances recall and recovery without replacing the tool's native context model, and every durable artifact lives inside the repo.

| Capability | File-backed enhancement (project-scoped) | External store option | Prerequisites | Control plane backend integration | Metrics | Risks |
|---|---|---|---|---|---|---|
| Project memory stack | Maintain project `CLAUDE.md` (or `.claude/CLAUDE.md`) as the committed source of truth; use `CLAUDE.local.md` (gitignored) for per-machine/per-worktree overrides; treat user-level `~/.claude/CLAUDE.md` as personal-only and never framework-required | Mirror memory fragments into a database, but only as an index to the native files | Stable Phase 0 session state and Phase 1 rule loading | Backend reads the active hierarchy, shows effective memory scope, and tracks which file last changed a behavior rule | Fewer repeated corrections; lower main-context token use; higher instruction-follow-through after restart | Overstuffed root files; conflicting scopes; stale local overrides |
| Auto memory | Relocate auto memory into the repo: bootstrap writes `autoMemoryDirectory` (absolute path to `<repo>/.claude/memory/`) into `.claude/settings.local.json`; Claude maintains `MEMORY.md` (first 200 lines / 25KB load at session start) plus topic files read on demand | External persistence for auto-memory records, with a sync job back into repo files | `/memory` audit workflow; workspace trust accepted; clear policy on what becomes persistent memory and whether `.claude/memory/` is committed or gitignored | Backend surfaces new auto-memory entries for review, approval, and cleanup | More cross-session recall; fewer re-explained preferences; lower token churn on repeated tasks | Memory bloat; capturing transient mistakes as durable facts; noisy duplication; forgetting the absolute-path requirement and silently falling back to the global default |
| Compaction pipeline | Add custom compaction instructions in project `CLAUDE.md` so summaries preserve code samples, API usage, and current task state; rely on the documented behavior that project-root `CLAUDE.md` is re-injected after `/compact`; use `SessionStart` and `PreCompact`/`PostCompact` hooks (scripts in `.claude/hooks/`) to persist and restore critical context | Store compaction summaries externally and re-inject them on session resume | Stable hook execution and verified compaction behavior from Phase 0 | Backend records compaction boundaries, stores the summary text under `.claude/state/compactions/`, and replays only the approved subset after compaction | Lower prompt length after compaction; fewer lost instructions; faster resume after context pressure | Summary drift; leaking stale context back into the conversation; hook latency |
| Subagent transcripts & summaries | Subagent transcripts persist natively but in the machine-local store; the control plane's SubagentStop hook exports each subagent's summary + transcript pointer into `.claude/state/agents/` so the durable record travels with the repo | External archive of subagent transcripts for retention, search, or audit | Subagent spawning and transcript path discovery | Backend links parent session IDs to exported summaries and exposes resume status per agent | Better isolation for delegated work; preserved subagent history; fewer context collisions in the main thread | Transcript sprawl; cleanup gaps; false confidence that a forked result reached the main session |
| Prompt caching | Structure stable project instructions and repeated prefixes so Claude Code can reuse cached prompt prefixes across sessions; know the documented invalidators (model/effort switches, MCP connect/disconnect, plugin toggles, compaction) vs. cache-safe actions (editing repo files, mid-session CLAUDE.md edits, invoking skills) | External cache of rendered prompts or serialized memory chunks | Stable file layout and predictable prompt assembly | Backend tracks cacheable prefixes and separates stable memory from volatile session state | Reduced input tokens on repeated starts; faster session warm-up; lower cost for long-lived projects | Cache invalidation mistakes; caching the wrong prefix; treating cache as source of truth |
| Cross-session state | Persist project memory in files committed to the repo (`CLAUDE.md`, rules, `.claude/state/` ledgers, plans in `./.claude/plans` via `plansDirectory`) so a restart, new worktree, or fresh clone recovers the same operating context | External store for org-wide memory, analytics, or non-repo history | Repository-local persistence and session identity mapping | Backend indexes the active session, memory file versions, and restore points; it prefers file-backed state for recovery and uses the store only for lookup | Successful resume rate; memory recovery after restart; stable behavior across sessions and machines | Duplicate sources of truth; privacy and access-control complexity; backend drift from Claude Code's own memory model |

Implementation order:

1. Make the repo-local memory path authoritative: project `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/`, relocated auto memory, compaction instructions, `.claude/state/` ledgers, and `plansDirectory: "./.claude/plans"`.
2. Add backend indexing only after the file layout is stable, so the store reflects Claude Code's native memory rather than defining it.
3. Use the external store for search, audit, and fleet metrics, not as the primary runtime memory for the project.
4. Keep prompt caching and compaction summaries focused on stable instructions, recent decisions, and the active task so token savings do not erase recovery data.

Expected gains:

- Lower repeated prompt cost because stable project instructions are cached and re-used instead of being retyped.
- Better restart behavior because the same project memory stack is available after a new session begins — on any machine that clones the repo.
- Better delegated-work recovery because subagent summaries are exported into the repo instead of living only in the machine-local transcript store.
- Less context loss after compaction because the backend knows what must be re-injected and what should stay summarized.

Exit criteria:

- The control plane can reconstruct project memory from the repo-local hierarchy after restart *and after a fresh clone on a new machine*.
- Auto memory, compaction summaries, and subagent summary exports are visible in the backend and live under `.claude/`.
- The backend can show whether recovery came from native files or from an external index.
- A project can resume with the same effective memory state across sessions without depending on an external store — or on `~/.claude/` — for correctness.

## Phase 3: Sub-Agent Orchestration

Phase 3 turns custom subagents into a control-plane primitive instead of a one-off delegation trick. Claude Code already gives each subagent its own context window, custom system prompt, tool restrictions, and independent permissions; the current docs add per-agent model selection, preloaded skills, persistent per-agent memory, frontmatter hooks, foreground/background execution, resumable subagents, nested spawning, and native agent teams. The orchestration layer should focus on when to spawn, how to route work, and how to collect summaries without bloating the parent conversation. Use subagents for side work that would otherwise flood the main thread with search results, logs, or file contents; use background agents (agent view / dispatch) when you need many isolated sessions; use agent teams when those sessions need to coordinate with each other. **All role definitions live in `.claude/agents/` and travel with the repo.**

| Pattern | Native Claude Code behavior | Control plane support | Depends on | Metrics | Risks |
|---|---|---|---|---|---|
| Supervisor / dispatcher | The lead agent coordinates subtasks and merges results. A subagent works in its own context window and returns only a summary to the parent conversation. | Provide spawn policies, task templates, and summary normalization so the parent thread keeps only the decisions and verified outcomes. | Phase 0 session state, Phase 1 hooks, Phase 2 summary exports | Main-thread token reduction; summary completeness; delegated task success rate | Over-delegation; weak summaries; the parent agent trusting a summary that is too thin to verify |
| Collaborative team | Native agent teams let multiple Claude Code agents work on different parts of a task simultaneously, with task assignment, plan approval per teammate, direct messaging, and quality gates via hooks. Each worker keeps its own independent context. | Track a shared task graph, explicit handoff points, and merge steps so parallel work converges instead of drifting; enforce worktree isolation to avoid file conflicts. | Phase 1 hook boundaries and Phase 2 memory/state recovery | Parallel throughput; merge latency; duplicate-work rate | Chatty agents; conflicting edits; coordination overhead that eats the benefit of parallelism; agent-team token multiplication |
| Research worker | Built-in (Explore/Plan) and custom subagents are good for exploration, code search, and other read-heavy work that should stay out of the main conversation. | Default these workers to read-only or narrowly scoped tool sets via frontmatter `tools:`; route findings back as structured summaries or artifacts into `.claude/state/agents/`. | Phase 1 skills and MCP, Phase 2 compaction-safe state | Context saved in the parent session; research turnaround time; read-only task completion rate | Tool creep; research output too large to summarize cleanly; hidden dependency on the wrong worker |
| Specialized executor | Custom subagents in `.claude/agents/` can have focused prompts, narrower tools, per-agent model choice, preloaded skills, and permission constraints so they behave like role-specific workers rather than generic clones. | Keep a small catalog of named worker types for repeated jobs, each with a clear description that tells Claude when to delegate. | Phase 1 rules and skills, Phase 2 memory hygiene | Reuse rate of worker definitions; permission exceptions avoided; fewer ad hoc prompt blocks | Over-customization; too many near-duplicate agents; privilege creep as workers accumulate exceptions |
| Monitoring and resume | Subagents can run foreground or background, be resumed, and appear in agent view alongside dispatched background sessions. | Surface parent-child trees, exported summaries, current status, and resume controls from `.claude/state/agents/` so operators can inspect without opening every transcript. | Phase 0 observability, Phase 2 state storage | Resume success rate; time-to-diagnosis; state cleanup rate | State sprawl; stale resumes; operators mistaking a background run for a finished result |

Orchestration rules:

1. Spawn a subagent when the task is large enough to pollute the parent context, not just because a worker feels available.
2. Prefer a supervisor pattern for one-way delegation with a single verified result.
3. Use collaborative teams only when workers truly need to exchange state or split a task that cannot be merged cleanly after the fact.
4. Keep subagent descriptions specific so Claude can decide when to delegate without guessing.
5. Keep the default tool scope small and add write permissions only where the worker's job actually requires them; isolate writers in worktrees.
6. Treat background work as visible state: every spawned worker needs a status, an exported summary, and a clear stop or resume path.

Why this matters:

- The parent conversation stays smaller because exploration and implementation detail live in the subagent's own context window.
- Permission scoping becomes a control surface instead of a convention, which is safer than relying on prompt wording alone.
- Summary returns make it possible to keep the main thread focused on decisions while preserving the evidence in the exported record.
- The control plane can scale delegation without turning every task into a manually managed multi-agent protocol.

Exit criteria:

- The control plane can spawn named custom subagents from `.claude/agents/` with explicit tool and permission scopes.
- Subagent work is routed by role, not by ad hoc prompt duplication.
- Operators can see active subagents, their summaries, and their state exports from one place.
- Parent sessions can resume or merge delegated work without replaying the entire exploration history.
- Worker catalogs stay small enough that specialization improves clarity instead of creating a taxonomy problem.

## Phase 4: Dynamic Workflows

Phase 4 turns the proven agentic loop into a controlled workflow engine. Start static: use the native gather context -> act -> verify loop, fixed task templates, and explicit checkpoints as the default execution path. Note that Claude Code now ships a native dynamic-workflows feature (bundled workflows, Claude-authored workflow scripts, `/goal` for condition-driven loops, `/loop` for scheduled repetition, and routines for triggered runs) — prefer wrapping these primitives over reinventing a graph engine. Move to dynamic planning only after the loop, memory, subagents, and evaluation gates are reliable enough that the planner is choosing among known-safe primitives instead of inventing new ones on the fly.

| Capability | Static default | Dynamic extension | Prerequisites | Monitoring | Prefer static when |
|---|---|---|---|---|---|
| Workflow selection | Fixed, named workflows for common tasks (project slash commands in `.claude/commands/`) | LLM chooses the next workflow or graph branch from approved options; native workflow scripts saved for reuse | Stable Phase 0 loop, Phase 2 memory, Phase 3 subagents, and verified step results | Selected path vs. expected path, branch frequency, fallback rate | The task is repeatable, compliance-sensitive, or cheap to encode as a template |
| Graph execution | Linear step lists with explicit checkpoints | Directed graph with conditional edges, retries, and branch merges | Deterministic step IDs, checkpoint persistence in `.claude/state/`, and resume-safe records | Node completion rate, retry loops, dead-end branches, and time-in-branch | The path is already known and branching would only add overhead |
| Planner | No planner; the workflow is authored by the control plane | LLM planner proposes a bounded plan over approved steps and tools; plan-mode outputs persisted via `plansDirectory` | Good tool/result logging, prompt caching, and evaluation checkpoints | Plan quality, rejected steps, unsupported tool requests, and token cost | The work is short, routine, or can be expressed as a static playbook |
| Evaluation gates | Verify after each major step | Gate transitions on assertions, tests, or rubric-based checks; `/goal` conditions and Stop hooks as native gate mechanisms | Reliable verification hooks and clear success criteria from earlier phases | Gate pass rate, manual override rate, and false-pass rate | There is no meaningful check to attach to the transition |
| Recovery | Resume the last verified step | Re-plan from the last checkpoint and prune failed branches | Durable state, exported records, and branch-aware session records | Recovery success rate, branch replay correctness, and rollback count | Recovery is rare and a simpler linear resume is enough |

Implementation approach:

1. Keep workflow definitions declarative and small: named tasks, allowed transitions, checkpoints, and required verifiers.
2. Let the LLM plan only within that bounded graph, not invent arbitrary tool chains.
3. Promote a static workflow to dynamic only when repeated executions show branching is common and the extra flexibility saves time.
4. Require a checkpoint before every high-risk transition: write, merge, deploy, delegate, or hand off to another agent.
5. Store the active plan, chosen branch, and verification result with the session in `.claude/state/` so the control plane can replay what happened.

Monitoring:

- Track path selection, branch depth, retries, time-to-checkpoint, and planner token spend.
- Alert on repeated replans, unsupported branches, or workflows that spend more time choosing than doing.
- Keep a visible fallback to the static path so operators can pin a workflow when the planner is unstable.
- Review failed graphs as first-class artifacts; the branch that failed is as important as the one that succeeded.

When to use static vs fully dynamic:

- Use static workflows for predictable maintenance, known release steps, simple research, and anything with strict approval or audit needs.
- Use dynamic workflows for open-ended debugging, multi-step investigation, agent coordination, and tasks where the next step depends on evidence gathered mid-run.
- Move to fully dynamic only after static templates and bounded planners consistently pass evaluation gates at low cost.

---

## Phase 5: Portable Project-Scoped Framework ("Control Plane in a Folder")

Phase 5 packages Phases 0–4 into a **portable, code-agnostic operating framework** that lives entirely in `.claude/` and works for any repository — TypeScript, Python, Pine Script, infra, docs-only, anything. The design synthesizes the strongest ideas from the community corpus while staying native-first: no runtime dependency beyond Claude Code itself.

### Inspiration corpus (patterns adopted, not code copied)

| Source | Core insight | What Phase 5 adopts |
|---|---|---|
| **GSD Core (TÂCHES)** — discuss/plan/execute/verify phases, atomic XML-ish task plans (≤3 tasks), fresh subagent context per plan, all state persisted to disk (`.planning/`), commit-per-task, `--local` install to `./.claude/` | Context rot is the enemy; treat the context window as a managed resource and keep the main thread at dispatcher load | Phase-gated lifecycle commands; atomic plan files in `.claude/plans/`; fresh-context execution via subagents; per-task commits; disk-persisted state so any session resumes cold |
| **Superpowers (obra)** — constrain the *process*: TDD discipline, subtask dispatch, brainstorm-before-build skills | Skills that encode process discipline outperform skills that merely add capability | Process skills (brainstorm, TDD gate, review) as model-invoked discipline modules |
| **gstack** — constrain the *decision perspective*: think → plan-review → build → review → ship, with role-based review lenses | Multi-perspective review catches what a single lens misses; the build phase is where most frameworks are weakest | Review-lens agents (architect, security, maintainer) in `.claude/agents/`; explicit ship gate |
| **mattpocock/skills** — grill-me (relentless requirements interview), to-prd/to-spec, to-tickets (vertical tracer-bullet slices with blocking edges), tdd, handoff (compact session into a takeover doc), git-guardrails (hooks blocking destructive git), CONTEXT.md domain glossary + ADRs, and the user-invoked vs model-invoked skill axis | Misalignment is the #1 failure mode; interview before building; small composable skills over mega-frameworks; skills are probabilistic, hooks are deterministic | The two-axis skill taxonomy; `/grill` alignment interview; `CONTEXT.md` glossary + `docs/adr/`; handoff documents in `.claude/state/handoffs/`; git guardrail hooks |
| **Karpathy** — keep the agent on a leash: small incremental chunks, many generation-and-verification cycles, surface assumptions before coding, smallest surgical implementation, define verification before finishing; AutoResearch pattern: fixed time budget, single metric, keep-if-improved/revert-if-not | Verifiability is the property everything compounds on; ambition without verification is how messes ship | A `karpathy-guidelines` rule loaded unconditionally; assumption-surfacing required in plans; metric-gated experiment loops for optimization tasks |
| **Anthropic best-practices docs** — explore → plan → code; give Claude something to verify against; manage context aggressively; delegate investigation to subagents; adversarial review step; `/init` interactive setup | The vendor's own guidance already encodes the loop; align with it rather than fight it | Plan-mode-first defaults; verification targets required in every task spec |

Treat all of the above as **inspirational pattern-stock**: adopt the shape, write your own thin implementations, and keep the total system prompt overhead small (GSD's own trajectory — a 94% minimal-profile cut — shows bloat is the failure mode even for the category leader).

### 5.1 Framework layout (superset of the canonical tree)

```text
.claude/
├── settings.json            # permissions, hooks wiring, plansDirectory, plugins
├── settings.local.json      # machine-specific (autoMemoryDirectory, personal allows)
├── rules/
│   ├── 00-operating-doctrine.md   # loop discipline, leash rules, scope doctrine
│   ├── 10-karpathy-guidelines.md  # assumptions → smallest change → verify → surgical diffs
│   └── <domain>/*.md              # path-scoped rules (paths: frontmatter)
├── skills/                  # model-invoked discipline + user-invoked orchestrators
├── commands/                # thin entrypoints: /brainstorm /research /plan /build /debug /ship ...
├── agents/                  # scout, planner, builder, verifier, reviewer-*, librarian
├── hooks/                   # guardrail + state-export scripts
├── plans/                   # atomic plan files (plansDirectory target)
├── memory/                  # relocated auto memory (optional)
└── state/
    ├── ledger.md            # append-only decision + progress ledger (the project's flight recorder)
    ├── handoffs/            # session-takeover documents
    ├── agents/              # exported subagent summaries
    ├── research/            # research briefs with source citations
    └── checkpoints/         # verified-step markers for resume
docs/
├── CONTEXT.md               # domain glossary — one word where twenty were used
└── adr/                     # architecture decision records
```

### 5.2 Task-agnostic lifecycle (works for code and non-code)

Every unit of work flows through the same five gates, each a project slash command that orchestrates skills and subagents. Any gate can be skipped explicitly for trivial work — the gates are a ladder, not a cage.

| Gate | Command | What happens | Native mechanism | Durable artifact |
|---|---|---|---|---|
| 1. Align | `/brainstorm` (open-ended) or `/grill` (interrogative) | Structured interview surfaces requirements, assumptions, constraints, and success criteria before anything is built; updates `docs/CONTEXT.md` glossary and drafts ADRs as decisions crystallize | Skill with `context: fork` optional; AskUserQuestion-style interviewing | Spec in `.claude/state/research/` or issue tracker; ledger entry |
| 2. Research | `/research <question>` | Scout subagents (read-only tools) investigate the codebase, docs, and web in parallel; findings return as summaries, never raw dumps | Explore-type subagents; background dispatch for breadth | Research brief with citations in `.claude/state/research/` |
| 3. Plan | `/plan` | Plan mode produces atomic plans (≤3 tasks each, per GSD sizing evidence) with explicit assumptions, verification targets, and blocking edges between plans (per Pocock's tracer-bullet tickets) | Plan mode + `plansDirectory: "./.claude/plans"`; plan-approval gate | Plan files committed under `.claude/plans/` |
| 4. Build | `/build <plan>` | Each atomic plan executes in a fresh subagent context; the main thread only dispatches and merges; one commit per completed task; TDD skill gates implementation where tests apply | Agent tool with per-role definitions; worktree isolation for parallel builders; PostToolUse format/lint hooks | Commits; updated ledger; exported builder summaries |
| 5. Verify & Ship | `/verify` then `/ship` | Verifier agent re-derives success criteria from the plan and checks them (never trusts the builder's self-report); reviewer-lens agents (architect/security/maintainer) run adversarial passes; `/ship` handles branch, PR, and CI handoff | Stop hooks + prompt-based hooks as gate checks; `/goal` for keep-fixing-until-green loops; GitHub/GitLab integrations or `gh` CLI | Review report in ledger; PR link; checkpoint marker |

Cross-cutting commands: `/handoff` (compact the session into a takeover doc in `.claude/state/handoffs/` for a fresh session or a different agent), `/status` (reconstruct where-are-we purely from `.claude/state/`), `/debug` (systematic root-cause protocol: reproduce → isolate → hypothesize → test → fix → regression-guard), `/experiment <metric>` (Karpathy AutoResearch loop: bounded time budget, single metric, keep-if-improved/revert-if-not).

### 5.3 Skill taxonomy (the two-axis rule)

Adopt Pocock's invocation axis as a hard convention:

- **User-invoked skills/commands** (`/brainstorm`, `/plan`, `/ship`…) are orchestrators. They may invoke model-invoked skills, never each other.
- **Model-invoked skills** (`tdd`, `debugging-protocol`, `commit-hygiene`, `research-citation`…) hold reusable discipline the agent reaches for automatically when the task fits. Keep each small, composable, and single-purpose — one skill trying to own the whole process becomes a new giant prompt.

### 5.4 Code-agnostic adapter layer

The framework must not assume a language or toolchain. All stack-specific knowledge is confined to two places:

1. **`CLAUDE.md` facts block** — build/test/lint commands, entry points, conventions. Generated by the bootstrap skill (`/init`-style interview + codebase scan), never hardcoded in skills.
2. **A single `verify` adapter** — `.claude/hooks/verify.sh` (or `.ps1`) that maps "run the checks" to whatever this repo means by it (pytest, `npm test`, `pine-lint`, `terraform validate`, or "render the doc and diff it"). Every skill and gate calls the adapter, never a raw toolchain command.

For non-code work (research reports, trading-strategy specs, article pipelines), the same gates apply with different verifiers: source-citation checks, rubric-based review agents, and fact-check passes replace test suites.

### 5.5 Bootstrap skill

`/bootstrap-control-plane` is the one-command installer for a new repo. It:

1. Creates the tree above and a starter `CLAUDE.md` (via native `/init` flow where available).
2. Interviews for: issue tracker (GitHub / Linear / local files), verify command(s), commit conventions, and which gates are mandatory vs skippable.
3. Writes machine-specific values (`autoMemoryDirectory` absolute path) into `settings.local.json` and appends gitignore entries (`CLAUDE.local.md`, `.claude/settings.local.json`, optionally `.claude/memory/`).
4. Registers guardrail hooks and runs a smoke test: one trivial task through all five gates.

Exit criteria:

- A fresh clone on a new machine + `/bootstrap-control-plane` (or nothing, if already bootstrapped) reproduces the full framework with zero reliance on `~/.claude/`.
- Every gate produces its durable artifact in `.claude/state/` or `.claude/plans/`; `/status` can answer "where are we" from disk alone.
- The same framework runs unmodified against at least two unrelated stacks (e.g., a TypeScript app and a Python research pipeline) with only `CLAUDE.md` facts and the verify adapter differing.
- Main-thread context stays below ~50% on multi-plan work because building happens in fresh subagent contexts (the GSD threshold at which community testing shows quality degrading).

## Phase 6: Determinism Ladder & Adversarial Verification

Phase 6 hardens Phase 5. The organizing insight, borne out across the corpus: **skills are probabilistic, hooks are deterministic** — community measurement puts unhooked skill-triggering around ~20% and hook-reinforced triggering above 80%. Anything that must *always* happen migrates down the ladder.

### 6.1 The determinism ladder

| Rung | Mechanism | Guarantee | Use for |
|---|---|---|---|
| 1 | CLAUDE.md / rules | Context — Claude tries to follow | Facts, conventions, tone |
| 2 | Skills | Loaded when invoked or matched | Procedures, discipline modules |
| 3 | Prompt/agent-based hooks | Model-evaluated at fixed lifecycle points | Rubric gates, "did the stop condition really pass?" checks |
| 4 | Command hooks (PreToolUse / PostToolUse / Stop / PermissionRequest) | Deterministic shell execution, can block | Git guardrails, protected paths, format-on-edit, gate enforcement |
| 5 | Permission rules + sandbox settings | Enforced by the client regardless of model behavior | Deny-lists, secret exclusion, path confinement |

Audit rule: whenever a rung-1/2 instruction fails twice, promote it one rung. Whenever a rung-4/5 rule blocks legitimate work twice, demote or refine it. Track promotions/demotions in the ledger.

### 6.2 Guardrail baseline (rung 4–5, committed in `.claude/settings.json` + `.claude/hooks/`)

- **Git guardrails**: PreToolUse hook blocking `push --force`, `reset --hard`, `clean -fd`, `branch -D`, history rewrites — require explicit human approval (pattern proven by mattpocock's git-guardrails).
- **Protected paths**: `permissions.deny` for `.env*`, `secrets/**`, lockfile mass-edits, and the `.claude/state/ledger.md` (append via hook only).
- **Format/lint on edit**: PostToolUse hook running the verify adapter's lint target on touched files.
- **Compaction insurance**: PreCompact snapshot of active task state into `.claude/state/checkpoints/`; SessionStart re-injection.
- **Stop-gate**: Stop hook that refuses to end the turn while the declared verification target is red (bounded retries; escalate to human, never loop forever).

### 6.3 Adversarial verification battery

- **Independent verifier**: the verifier agent receives the plan's success criteria and the diff — never the builder's narrative — and re-derives pass/fail (prevents self-grading).
- **Review lenses**: parallel reviewer agents with distinct mandates (correctness, security, architecture depth per Ousterhout's deep-modules lens, maintainability) each returning a bounded findings list; the lead merges and triages.
- **Red-team pass for high-risk changes**: a skeptic agent attacks the change's assumptions before ship — required for auth, money paths, data migrations, and destructive operations.
- **Metric-gated experiments**: for optimization work, only the `/experiment` loop may claim improvement — single metric, fixed budget, revert on non-improvement.

### 6.4 Measurement

Instrument via the Phase 0 event log plus native telemetry (skill-activation, hook-execution, and compaction events are all emitted): skill trigger rate, hook block rate and false-block rate, gate pass rate, verifier-vs-builder disagreement rate, rework rate (commits reverted within N days), and context-pressure at dispatch. Review monthly; every metric drives a ladder promotion/demotion or a skill edit.

Exit criteria:

- Every must-happen behavior lives at rung 3+ and demonstrably fires (log-verified), not just documented.
- No destructive git or filesystem action is reachable without a deterministic block or explicit human approval.
- Verifier disagreement with builder self-reports is measured and nonzero (if it's zero, the verifier is rubber-stamping).
- Gate metrics exist and have driven at least one ladder promotion and one demotion (proof the feedback loop is alive).

## Phase 7: Distribution, Versioning & Continuous Improvement

Phase 7 makes the framework reusable across every project you touch without recreating a global dependency.

| Concern | Approach | Native mechanism | Pitfalls |
|---|---|---|---|
| Packaging | Convert the stable framework core (skills, agents, commands, hooks, default settings) into a versioned plugin; keep per-project `CLAUDE.md`, rules, plans, and state out of the package | Plugin structure + local/git marketplace; `enabledPlugins` pinned in each repo's `.claude/settings.json` keeps installs project-scoped | Packaging project-specific facts; letting the plugin grow into a mega-framework |
| Versioning | Semver the plugin; changelog every skill/hook behavior change; repos pin versions and upgrade deliberately | Marketplace version resolution and release channels; plugin dependency constraints | Silent auto-upgrades changing agent behavior mid-project |
| Project deltas | Each repo overrides via its own `.claude/` files (project skills shadow plugin skills; rules extend; hooks append) | Documented precedence: project config layers over plugin defaults | Divergence with no path back to core; fix by upstreaming recurring overrides |
| Skill evaluation | Treat skills like code: eval scenarios per skill, run before release (skill-creator-style evals); A/B a skill edit on real tasks before promoting | Skill testing guidance + headless mode (`claude -p`) for scripted eval runs | Editing skills on vibes; no regression detection when a skill quietly stops triggering |
| Cross-run learning | A retro skill mines the ledger + metrics after each milestone and proposes: rule edits, ladder moves, new skills, skill deletions; human approves; changes flow upstream to the plugin | Ledger in `.claude/state/`; headless batch analysis; routines/scheduled tasks for periodic retros | Accumulating learnings as bloat; every addition needs a deletion candidate |
| Community intake | Quarterly scan of the ecosystem (GSD releases, Superpowers, Pocock's repo, awesome-lists) as *pattern* intake — adopt shapes, port minimal implementations, never bulk-import | Marketplace browsing; reading SKILL.md sources before adoption | Supply-chain risk: malicious CLAUDE.md/skills in cloned repos are a documented attack vector — review everything, install from canonical sources only, rely on rung-5 guardrails as the backstop |

Exit criteria:

- Framework core installs into a virgin repo as one pinned, versioned plugin plus `/bootstrap-control-plane`; total added always-loaded context stays under a declared token budget.
- At least one full upgrade cycle completed across two repos with no behavior surprises (changelog + eval gate caught everything).
- One retro cycle has upstreamed a project-local improvement into the shared core.
- A third-party skill/pattern has been adopted through the review pipeline — read, minimized, evaled — rather than bulk-installed.

---

## Build Order Justification Matrix

| Phase | Why it must come before the next phase |
|---|---|
| Phase 0: Core Foundation | You need a reliable gather context -> act -> verify loop, durable state, and safe execution before adding policy or orchestration. |
| Phase 1: Rules, Skills & Hooks | Rules, skills, and hooks give the control plane reusable policy and enforcement without rebuilding Claude Code primitives — and pinning them to project scope early prevents global-path debt. |
| Phase 2: Project-Level Memory & State | Dynamic workflows need stable, repo-resident memory and state recovery so plan execution survives compaction, restart, and machine changes. |
| Phase 3: Sub-Agent Orchestration | Workflow branching is only useful once delegated work is already isolated, visible, and resumable. |
| Phase 4: Dynamic Workflows | Only after the primitives are trustworthy does it make sense to let the control plane choose or graph the path at runtime. |
| Phase 5: Portable Framework | The lifecycle gates and skill taxonomy only pay off once loop, memory, agents, and workflows exist to orchestrate; packaged too early it would encode unproven conventions. |
| Phase 6: Determinism & Adversarial Verification | Hardening requires real usage data (what fails, what needs promotion) that only Phase 5 operation generates. |
| Phase 7: Distribution & Improvement | You can only version and distribute what has stabilized; the retro loop needs ledgers and metrics from Phases 5–6. |

## Quick Wins

- Add explicit checkpoint objects to the existing agent loop; write them to `.claude/state/checkpoints/`.
- Set `"plansDirectory": "./.claude/plans"` today — one line, and plans immediately travel with the repo.
- Move any skills/agents/commands currently in `~/.claude/` into `.claude/` and commit them.
- Add the git-guardrails PreToolUse hook and `.env`/secrets deny rules — highest safety return per line of config.
- Add a PreCompact + SessionStart hook pair that snapshots and restores active task state.
- Start the append-only ledger (`.claude/state/ledger.md`) now; every later phase reads it.
- Adopt the `/grill`-style alignment interview before any multi-file change — the single highest-ROI process import from the community corpus.
- Expose a static workflow catalog (`.claude/commands/`) before enabling any planner; show path traces in logs so operators can see why a branch was chosen.

# CCSIF → Closed-Loop Autonomous Self-Improvement
## Architecture Assessment & Actionable Improvement Plan

**Repo audited:** `JackSmack1971/CCSIF@main` (full clone, all 21 skills, 9 rules, 3 agents, 4 hooks, 2 workflow stubs, settings, both audit reports)
**Date:** 2026-07-10
**Provenance vocabulary:** `[OBSERVED: path]` = read directly from the repo. `[INFERRED]` = deduced from structure. `[EXTERNAL]` = grounded in the current Claude Code hooks reference (verified July 2026 — 30 lifecycle events; `command`/`http`/`mcp_tool`/`prompt`/`agent` handler types; `async: true`; `hookSpecificOutput.additionalContext`; `modifyInput`; frontmatter-scoped hooks in skills/agents; `session_crons`).

---

## 1. Executive Summary

CCSIF is further along than most "self-improving agent" scaffolds: it has a delimited constitution, hook-generated trace telemetry, a proposal-only `/self-improve` skill with a scoring rubric, and — critically — the **7axes subsystem already demonstrates the correct safety architecture**: a model *proposes* (`evolution_patch.json`), a deterministic bounded script *applies* (`evolve.py`, clamped weights, marker-fenced directive blocks, capped memory, git-auditable changelog), and an outer loop (`feedback.py`) converts human issue-closure judgments into calibration updates. That propose/apply/feedback triad is the seed of genuine autonomy.

**But the system-wide improvement loop is open.** Nothing runs unless a human types `/self-improve`; the skill emits diffs that nothing applies; the constitution's "Tier 2 changes may auto-apply only after passing automated validation" clause `[OBSERVED: CLAUDE.md]` has **no tier classifier, no validator, and no applier** anywhere in the repo; KPIs are defined but never computed; all 21 skills ship `evals/evals.json` but **no eval runner exists**; there is no `.github/` directory, so no CI can validate a self-applied change; and traces are gitignored, so the evidence corpus can never drive an out-of-session loop.

The path to autonomy is not "let the model edit its own files." It is: **generalize the 7axes propose→deterministic-apply→measure→rollback pattern to the whole control plane, wire the 2026 hook surface (SubagentStop, PostToolUseFailure, ConfigChange, Stop-gating, prompt/agent hooks, async hooks) as the sensor and actuator layer, and close the loop with a scheduler (SessionStart cadence + nightly GitHub Action).** Section 4 gives 34 concrete improvements; Section 6 sequences them into four phases, from safety hardening (a hard prerequisite — several current gaps make autonomy actively dangerous) to scheduled unattended cycles.

---

## 2. Current State: Where Each Component Sits on the Autonomy Ladder

Autonomy ladder used below: **L0** manual · **L1** instrumented (observes itself) · **L2** advisory (proposes changes) · **L3** gated auto-apply (applies within deterministic bounds) · **L4** scheduled closed loop (triggers itself, verifies, rolls back).

| Component | Level | Evidence |
|---|---|---|
| Trace telemetry (`hooks/lib/trace-writer.js`) | L1 | Writes JSONL per tool call with redaction; best-effort, never blocks `[OBSERVED]` |
| `/self-improve` skill | L2 | Proposal-only; `disable-model-invocation: true`; "never edits production files" `[OBSERVED: SKILL.md]` |
| 7axes audit subsystem | **L3** | `evolve.py` applies bounded patches (directives ≤12/axis, weights clamped [0.5,2.0]); `feedback.py` learns from closed issues; ledger dedup `[OBSERVED]` |
| Hooks (4 of ~30 events) | L1 | SessionStart/PreToolUse/PostToolUse/Stop only; PreToolUse guard **fails open** when node absent `[OBSERVED: pre-tool-use.sh]` |
| Workflows (`issue-to-pr.js`, `upstream-audit.js`) | L0 | Return static scaffold objects; no execution logic `[OBSERVED]` |
| Agents (implementation, pr-reviewer, upstream-auditor) | L0 | Prose contracts only; no hook-enforced output contracts `[OBSERVED]` |
| Skill evals (21 × `evals.json`) | L0 | No runner, no CI — evals are inert documents `[OBSERVED: no .github/, no run script found]` |
| KPI system (`kpi-defaults.md`) | L0 | Definitions and targets exist; nothing measures them; `/self-improve` *estimates* deltas `[OBSERVED]` |
| Tier system (constitution) | L0 | Tier 1/Tier 2 named; membership never defined; no enforcement mechanism `[OBSERVED: CLAUDE.md]` |

### Defects found during this audit (fix regardless of autonomy goals)

1. **Dead rule scope.** `.claude/rules/failure-escalation.md` is path-scoped to `.claude/skills/healing-test-failures/SKILL.md` — **that skill does not exist**, so the entire failure-escalation protocol (the two-retry stop condition, the escalation payload contract) never loads. `[OBSERVED]` This is exactly the kind of rule an autonomous loop depends on.
2. **Phantom command.** `control-plane.md` and `mcp-resilience.md` both mandate running `/control-plane-check` after control-plane edits — no such command exists in `.claude/commands/`. `[OBSERVED]` An autonomous applier following the rules would hit a non-existent gate.
3. **Fail-open protected-area guard.** `pre-tool-use.sh` exits 0 with "Protected Area guard skipped (fails open)" when node is unavailable. Reasonable for tracing; wrong for the security gate. `[OBSERVED]`
4. **Guard doesn't protect the guard.** `pre-tool-use-guard.js` protects secrets/auth/payments/migrations/CI-CD — but **not** `CLAUDE.md`'s constitution block, `.claude/settings.json`, the hook scripts themselves, `.7axes/ledger.jsonl`, or `calibration.json`. The 7axes invariant "Never edit ledger.jsonl or calibration.json by hand — scripts only" is prose, not enforcement. `[OBSERVED]`
5. **Telemetry granularity mismatch.** `input-discovery.md` §4 expects one trace entry per *task* with `outcome` and `error_class`; the trace writer fires per *tool call* and infers task text from the transcript tail. `activation_miss` — the error class the worked example is built on — is structurally unmeasurable: no signal records that a skill *should* have fired but didn't. `[OBSERVED + INFERRED]`
6. **Deferred issues have no memory.** The proposal schema defines a Deferred Issues appendix "review if recurrence increases in subsequent cycles" — but nothing persists deferred issues between `/self-improve` runs, so recurrence across cycles is invisible. `[OBSERVED: proposal-schema.md]`
7. **Traces gitignored, no artifact path.** `.gitignore` excludes `.claude/traces/*.jsonl`. Correct for privacy, but it means no CI/scheduled runner can ever see the evidence corpus without an explicit summarization/artifact mechanism. `[OBSERVED]`
8. **`settings.json` `$schema` points to `example.invalid`** and the file mixes real Claude Code keys with speculative ones (`tools.git.protectBranches`, `tools.shell.timeoutSeconds` are not native settings keys — they're aspirational). `[OBSERVED + EXTERNAL]`
9. **Two learning systems, zero shared memory.** `/self-improve` (traces → proposals) and 7axes (`ledger.jsonl` + `calibration.json` + `feedback.py`) never exchange state. A rule 7axes suppressed for low precision can be re-proposed by self-improve, and vice versa. `[INFERRED from both file sets]`

---

## 3. Target Architecture: The Closed Loop

The loop CCSIF should implement, mapped to what already exists:

```
        ┌──────────────────────────────────────────────────────────┐
        │                     SENSE (L1)                           │
        │  30-event hook telemetry → typed traces + measured KPIs  │
        │  exists: trace-writer.js (4 events)                      │
        │  add: PostToolUseFailure, SubagentStop, TaskCompleted,   │
        │       Stop-time outcome grading, kpi_compute.py          │
        └────────────────────────┬─────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │                    PROPOSE (L2)                          │
        │  /self-improve emits proposals — human AND machine-      │
        │  readable (proposals.json alongside markdown)            │
        │  exists: SKILL.md + proposal-schema.md                   │
        │  add: tier classification field, executable verification │
        └────────────────────────┬─────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │              CLASSIFY & GATE (missing)                   │
        │  tier_classify.py: Tier-0 auto / Tier-2 validated-auto / │
        │  Tier-1 human PR. Deterministic path+change-type rules.  │
        └───────────┬─────────────────────────────┬────────────────┘
              Tier 0/2                        Tier 1
                    ▼                             ▼
        ┌───────────────────────────┐   ┌─────────────────────────┐
        │   APPLY (L3, bounded)     │   │  PR for human review    │
        │  apply_proposal.py in an  │   │  (claude-code-action /  │
        │  isolated worktree; runs  │   │   create-pr flow)       │
        │  eval harness + linters;  │   └─────────────────────────┘
        │  merge only if green      │
        │  exists as prototype:     │
        │  7axes evolve.py          │
        └────────────┬──────────────┘
                     ▼
        ┌──────────────────────────────────────────────────────────┐
        │              VERIFY & ROLLBACK (missing)                 │
        │  Post-apply KPI window vs pre-apply window;              │
        │  regression → automatic git revert + suppression entry   │
        └────────────────────────┬─────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │              LEARN (L4 outer loop)                       │
        │  Proposal outcomes (kept/reverted/rejected) feed back    │
        │  into proposal-generator calibration — the improver      │
        │  improves its own precision.                             │
        │  exists as prototype: 7axes feedback.py                  │
        └────────────────────────┬─────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │              TRIGGER (missing)                           │
        │  SessionStart cadence counter · Stop-hook threshold ·    │
        │  session_crons · nightly GitHub Action                   │
        └──────────────────────────────────────────────────────────┘
```

**The single most important design decision, carried over from `evolve.py`'s header comment:** *"Separation of propose (model) from apply (deterministic, bounded) is what keeps a self-modifying workflow safe: the model can't rewrite its own guardrails, and every mutation is a reviewable git diff."* `[OBSERVED]` Everything below generalizes that sentence.

---

## 4. Actionable Improvements

Priorities: **P0** = prerequisite for any autonomy (safety/correctness) · **P1** = closes the loop · **P2** = raises loop quality · **P3** = polish. Effort: S (<1 day), M (1–3 days), L (multi-day).

### A. Safety Hardening — the improver must not be able to modify its own guardrails (all P0)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| A1 | **Protect the control plane's control plane.** Extend `pre-tool-use-guard.js` `PROTECTED_AREAS` with: the `CLAUDE.md` constitution block, `.claude/settings.json`, `.claude/hooks/**`, `.claude/scripts/apply_proposal.py` (once built), `.7axes/ledger.jsonl`, `.7axes/calibration.json`. Writes to these by `Edit`/`Write`/mutating `Bash` → exit 2. The only sanctioned mutation path is the deterministic applier scripts, which the guard whitelists by process invocation (`python3 scripts/7axes/evolve.py`, `apply_proposal.py`). | Edit existing guard regexes; ~30 lines | S |
| A2 | **ConfigChange hook.** `[EXTERNAL]` Claude Code now fires `ConfigChange` (blockable via exit 2). Register a handler that blocks any settings/hook/rule change not accompanied by an approved-proposal marker file (`.claude/pending/approved-<id>.json`). This catches config mutations that bypass the file tools. | New hook script + settings entry | S |
| A3 | **Constitution hash pinning.** `session-start.sh` computes SHA-256 of the `CONSTITUTION:START..END` block and compares to `.claude/constitution.sha256` (committed). Mismatch → print blocking warning into session context (SessionStart stdout is injected as context `[EXTERNAL]`) and set a flag the PreToolUse guard reads to deny all writes until a human re-pins. Constitution changes become deliberate two-step acts. | ~20 lines bash + guard flag check | S |
| A4 | **Fail closed on the security path.** Split `pre-tool-use.sh`: if node is unavailable, *tracing* may fail open but *protected-area enforcement* must exit 2 for mutating tools (`Edit|Write|NotebookEdit` and mutating Bash). Add a pure-bash fallback denylist so the gate survives without node. | Restructure one script | S |
| A5 | **Fix the dead references.** Re-scope `failure-escalation.md` to `"**/*"` (its two-retry stop condition is exactly what an autonomous loop needs globally); create `.claude/commands/control-plane-check.md` implementing what the rules already mandate (referenced files exist, edited scripts parse, governance paths not gitignored — the rule text is effectively the spec). | Two files | S |
| A6 | **Deny-list gaps.** Current denies stop `git push --force`, `rm -rf`, etc. Add: `curl`/`wget` POST exfil patterns, `crontab`, `chmod +x` outside `.claude/scripts/`, `git push` to protected branches (plain push is currently unconstrained), `gh secret`, `npx` arbitrary-package execution. Prefer `[EXTERNAL]` `hookSpecificOutput.permissionDecision` JSON (`allow`/`deny`/`ask` + reason) over bare exit codes for graded responses. | settings.json + guard | S |
| A7 | **Set `disableSkillShellExecution` explicitly** (their own architecture audit CCA-004/012 flags this `[OBSERVED]`). For an autonomous posture: `false`, but only because A1/A4 make the shell gate real. Document the decision in `decision-log.md`. | One key + log entry | S |

### B. Telemetry Upgrade — you cannot autonomously improve what you cannot measure (P1)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| B1 | **Instrument the failure-rich events.** Add hooks for `PostToolUseFailure` (the single highest-signal event for `error_class=tool_failure` — currently invisible), `SubagentStop` (per-agent outcome + contract compliance), `TaskCompleted`, and `PostCompact` (context_overflow signal). All can share `trace-writer.js` with an event-type field. `[EXTERNAL: all four events exist in the 2026 hook surface]` | Extend trace-writer switch + 4 settings entries | M |
| B2 | **Turn-level outcome grading.** The trace schema wants `outcome: success/partial/failure` per task; no code assigns it. Use a `[EXTERNAL]` `prompt`-type Stop hook (single-turn Haiku evaluator, ~30s timeout) that reads `last_assistant_message` + recent tool results and appends a graded task-summary entry to the trace. Mark it `async: true` so grading never blocks the session. This makes `outcome` and `error_class` *measured*, not inferred. | One prompt-hook config + small writer change | M |
| B3 | **Make `activation_miss` measurable.** Log a `UserPromptSubmit` entry per prompt (prompt text hash + timestamp) and a `skill_fired` entry when any SKILL loads (skills can carry their own frontmatter hooks `[EXTERNAL]` — add a one-line SessionStart-style logger to each skill via a generator script). A nightly labeling job (or the Stop grader from B2) joins prompts to fired skills and flags in-scope prompts with no fire. Without this, the self-improve worked example's core scenario cannot occur in real data. | Generator script + join script | M |
| B4 | **`kpi_compute.py` — deterministic KPI snapshots.** Reads the trace corpus, computes every KPI in `kpi-defaults.md` (trigger reliability, under/overtrigger, block precision, hook latency p95 from PreToolUse→PostToolUse deltas, MCP success rate), writes `.claude/metrics/kpi-<date>.json`. Run from the Stop hook (async) and from CI. `/self-improve` step 3 then loads *measured* KPIs; the "Estimating KPI Delta" section becomes the fallback, not the norm. | ~200-line Python script | M |
| B5 | **Trace summarization for the outer loop.** Because raw traces are (correctly) gitignored, add `summarize_traces.py` producing a redacted, aggregate `.claude/metrics/trace-summary.json` (counts by error_class/component/skill, no prompt text) that IS committed / uploaded as a CI artifact. This is what scheduled runs consume. | Small script + gitignore whitelist | S |

### C. Close the Loop — classifier, applier, verifier, trigger (P1, the heart of the request)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| C1 | **Machine-readable proposals.** Amend `proposal-schema.md` + SKILL step 8: alongside the markdown, emit `.claude/pending/proposals-<run_id>.json` — array of `{id, component, tier, diff, kpi, kpi_delta_est, rollback_cmd, verification_cmd, evidence_refs, score}`. `verification_cmd` must be an *executable* check (e.g. `python3 .claude/scripts/kpi_compute.py --assert 'skill:x.activation_miss==0' --window 5`), replacing today's human-directed prose ("Re-run /self-improve after applying"). | Schema + skill edit | S |
| C2 | **`tier_classify.py` — define the tiers the constitution names but never specifies.** Deterministic rules, committed as `references/tier-policy.json`:<br>• **Tier 0 (auto, no validation gate):** ledger/calibration/learned-directive blocks, trace summaries, deferred-issue registry — the surfaces `evolve.py` already owns.<br>• **Tier 2 (auto-apply after validation):** skill `description` keyword additions (additive only), `when_to_use` text, reference-doc content, KPI threshold tuning within clamps, rule `paths:` narrowing (never widening).<br>• **Tier 1 (human PR, never auto):** constitution block, `settings.json` permissions/hooks, hook scripts, agent tool lists, anything under `PROTECTED_AREAS`, any *deletion* of existing behavior, any rule-scope *widening*.<br>Unclassifiable → Tier 1 by default. | Script + policy JSON + CLAUDE.md tier table | M |
| C3 | **`apply_proposal.py` — generalize `evolve.py` repo-wide.** For each Tier-0/2 proposal: create branch in `.claude/worktrees/selfimprove-<ts>` (the directory already exists with a `.gitkeep` — clearly intended for this `[OBSERVED]`), `git apply --check` then apply the diff, run the validation battery (D1 eval runner + skill linters + `control-plane-check` + affected `verification_cmd`s where cheap), commit with a structured trailer (`Self-Improve-Proposal-Id:`, `Tier:`, `Evidence:`), fast-forward merge if green, else discard worktree and write a rejection record. Every mutation remains a reviewable git commit — the `evolve.py` doctrine, generalized. | ~300-line Python script | L |
| C4 | **Post-apply verification & auto-rollback.** `verify_applied.py` runs on a delay: compares the KPI window after apply (next N graded tasks from B2/B4) against the pre-apply window for the proposal's named KPI. Regression beyond tolerance → `git revert <sha>` (the commit trailer makes the target findable), append a `reverted` outcome to the proposal registry, and add a suppression fingerprint so the same diff is not re-proposed (mirrors `feedback.py`'s `suppressed_fingerprints` `[OBSERVED]`). Wire it into SessionStart ("any applied proposals awaiting verification with a full window? verify now") so no daemon is needed. | Script + SessionStart line | M |
| C5 | **Triggers — make the loop self-starting.** Three complementary layers:<br>1. **SessionStart cadence:** counter file; every N sessions (or when trace-summary failure count crosses a threshold) inject "run `/self-improve all 25` this session" via SessionStart stdout / `initialUserMessage` `[EXTERNAL]`.<br>2. **Stop-hook nudge:** if the just-ended turn logged ≥2 same-signature failures (the failure-escalation rule's own threshold `[OBSERVED]`), return `additionalContext` suggesting an immediate scoped `/self-improve component:<x>`.<br>3. **Nightly GitHub Action** (see C7). Keep `disable-model-invocation: true` — the trigger injects an explicit invocation rather than letting the model free-fire, preserving the skill's own guard. | Hook edits + counter | M |
| C6 | **Proposal registry with cross-run memory.** `.claude/pending/registry.jsonl`: every proposal ever emitted, with lifecycle state (`proposed → applied → verified-kept / reverted / human-rejected / deferred`). Deferred issues from the schema's appendix land here with their scores, so "review if recurrence increases in subsequent cycles" becomes computable — self-improve step 5 reads the registry and sums recurrence across runs. Fixes defect #6. | Schema + read/write in skill + applier | S |
| C7 | **Nightly outer loop via GitHub Actions.** Create `.github/workflows/self-improve.yml`: scheduled run using `anthropics/claude-code-action` → executes `/self-improve all 50` against the committed trace summaries (B5) → applier handles Tier 0/2 on a branch, CI validates, auto-merges on green with a `self-improve` label → Tier-1 proposals become a single PR for human review. A companion `feedback` step reads merged/closed `self-improve`-labeled PRs and updates the proposal registry — the improver's precision loop, exactly the `feedback.py` pattern lifted from 7axes to repo level. This is the maximum-autonomy configuration: the human's only mandatory touchpoint is Tier-1 PR review. | Workflow YAML + CI job | L |

### D. Make the Inert Assets Real (P1–P2)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| D1 | **Eval runner.** 21 skills ship `evals/evals.json` and `VERIFICATION.md` with zero execution path. Build `.claude/scripts/run_evals.py`: for each eval case, execute via headless `claude -p` (or Agent SDK) in a scratch worktree, assert expected outputs/behaviors, emit junit-style results. This is the validation gate C3 depends on — **without it, "Tier 2 may auto-apply after passing automated validation" can never be honored.** Run in CI on every PR touching `.claude/`. | Runner + CI wiring | L |
| D2 | **Implement or delete the workflow stubs.** `issue-to-pr.js` / `upstream-audit.js` return static objects `[OBSERVED]`. Either implement them as real orchestrations against the workflow schema (tighten `workflow.schema.json` — `status` should be an enum, `steps` should be objects with `{name, status, evidence}`), or fold them into the commands/agents that actually do the work and remove the dead layer. Dead scaffolds are context cost and audit noise. | Decision + implementation | M |
| D3 | **Skill-auditor → applier integration.** `apply_skill_fixes.py` already exists `[OBSERVED]`; route its fix plan through `tier_classify.py` so description-lint fixes (Tier 2) auto-apply through the same gated pipeline instead of a separate side door. One mutation pathway, one audit trail. | Glue code | S |
| D4 | **Fill `CLAUDE.md` Source-of-Truth Commands.** `stop.sh` itself comments that the section is an unfilled template and only git hygiene is verified `[OBSERVED]`. Once D1 exists: `python3 .claude/scripts/run_evals.py --changed` becomes the repo's real test command, and `stop.sh` wires it in — closing the "verify before claiming success" gap their own improvement plan (M-2) flags. | Doc + stop.sh edit | S |

### E. Agents & Sub-agent Contracts (P2)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| E1 | **Hook-enforced output contracts.** Agent prose says "PR with evidence, test output, risk, rollback" — nothing enforces it. Add frontmatter `SubagentStop` hooks to each agent `[EXTERNAL: frontmatter hooks; Stop auto-converts to SubagentStop in subagents]`: implementation-agent must show a created PR + verification stdout; pr-reviewer must emit a parseable verdict block; upstream-auditor must show created issue URLs and zero working-tree mutations (`git status --short` empty). Non-compliant → block stop with `additionalContext` telling the agent what's missing. Contracts become mechanical, and contract-compliance rates become a KPI B4 can compute per agent. | Frontmatter hooks + small check scripts | M |
| E2 | **Learned-directive blocks for all agents.** Only 7axes auditor agents carry machine-managed `LEARNED-DIRECTIVES` fences `[OBSERVED: evolve.py]`. Add the same fenced block to implementation-agent/pr-reviewer/upstream-auditor and teach `apply_proposal.py` to write into them (Tier 0). Recurring PR-review misses become standing directives without touching the hand-authored core prompt. | Markers + applier support | S |
| E3 | **Add a `meta-improver` agent.** A read-only Plan-mode agent that the triggers (C5) invoke, whose entire job is running the self-improve procedure in a fork — mirroring the existing `context: fork` / `agent: Plan` frontmatter intent — so improvement analysis never contaminates the working session's context. | One agent file | S |
| E4 | **Routing-accuracy telemetry.** `subagent-routing.md` warns that overlapping descriptions reduce routing accuracy `[OBSERVED]` — measure it: SubagentStart events (B1) + task text let `kpi_compute.py` produce a per-agent mis-routing rate, which becomes evidence for description-tuning proposals. | Falls out of B1/B4 | S |

### F. Rules, Constitution & Governance Text (P2–P3)

| # | Improvement | Mechanism | Effort |
|---|---|---|---|
| F1 | **Write the Tier table into the constitution.** The constitution references tiers it never defines. Add a compact table (from C2) inside the fenced block, then re-pin the hash (A3). This single edit makes the central governance clause enforceable. | Doc edit | S |
| F2 | **Add an autonomy budget clause.** Constitutional caps the applier reads as config: max Tier-2 auto-applies per day (e.g. 5), max lines changed per auto-applied diff (e.g. 30), mandatory human review if two consecutive auto-applies were reverted (circuit breaker). Bounded autonomy is what makes L4 defensible; the numbers are clamps in `tier-policy.json`, adjustable only at Tier 1. | Doc + policy keys | S |
| F3 | **Unify the two ledgers.** Define one shared suppression/fingerprint store consumed by both `feedback.py` and the proposal registry (C6), so a finding suppressed in one system cannot resurface via the other. Longer term, migrate 7axes' `evolution_patch.json` to emit C1-format proposals so 100% of self-modification flows through one classified, budgeted, audited pipeline. | Schema unification | M |
| F4 | **Adopt native `permissions.additionalDirectories` / real settings keys, drop speculative ones.** Replace `tools.git.protectBranches` etc. with mechanisms that actually execute: branch protection via the PreToolUse Bash matcher, timeouts via hook `timeout` fields. Fix the `$schema` URL. Aspirational config that doesn't execute is the most dangerous kind — it reads as protection and provides none. | settings.json cleanup | S |
| F5 | **PreCompact continuity.** Register a `PreCompact` hook that snapshots the in-flight improvement state (current proposal ids, verification windows) to `.claude/pending/session-state.json`, and have SessionStart(source=compact) reload it — so long autonomous sessions survive compaction without losing loop state. `[EXTERNAL: PreCompact/PostCompact + SessionStart source field]` | Two small hooks | S |

---

## 5. What Deliberately Stays Human (and why that's the right ceiling)

Full L4 across *all* surfaces is not the recommendation. Three touchpoints should remain human even at maximum build-out:

1. **Tier-1 PR review** — constitution, permissions, hooks, agent tool grants. The `evolve.py` doctrine is load-bearing: the moment the model can modify its own guardrails, every other guarantee in this document becomes decorative. Their own architecture audit's top finding (M-1: an untracked rule file containing self-modification instructions disguised as research `[OBSERVED: improvement-plan.md]`) is a live demonstration of why this boundary must be mechanical, not normative.
2. **Constitution re-pinning** (A3) — a human signs every constitution change by updating the hash.
3. **Circuit-breaker resets** (F2) — after consecutive reverts, a human decides whether the improver's judgment has degraded before autonomy resumes.

Everything else — sensing, scoring, proposing, Tier-0/2 application, validation, verification, rollback, learning from outcomes, and scheduling — can run unattended once Phases 0–2 below are in place.

---

## 6. Sequenced Roadmap

**Phase 0 — Harden (P0 items, ~1 week):** A1–A7, F4, fix defects #1–#4. *Exit criterion:* a synthetic write to the constitution, settings.json, or ledger is blocked with node present AND absent; `/control-plane-check` exists and passes.

**Phase 1 — Measure (B1–B5, D1, ~2 weeks):** full-event telemetry, graded outcomes, computed KPIs, eval runner in CI. *Exit criterion:* `kpi_compute.py` produces a snapshot containing at least trigger reliability, tool-failure rate, and hook block precision from real traces; `run_evals.py` passes in CI on a no-op PR.

**Phase 2 — Gated auto-apply (C1–C4, C6, D3, F1–F2, ~2 weeks):** machine-readable proposals, tier policy, worktree applier, verification/rollback, registry, budgets. *Exit criterion:* a seeded Tier-2 description fix flows proposal → auto-apply → eval-validated merge → KPI verification with zero human input, and a seeded regression auto-reverts.

**Phase 3 — Scheduled autonomy (C5, C7, E1–E4, F3, F5, D2, D4):** triggers, nightly Action, agent contracts, unified ledger. *Exit criterion:* one full unattended nightly cycle completes: analysis → 1+ Tier-2 auto-merge → Tier-1 PR opened → registry updated from prior PR outcomes.

At Phase 3 completion, CCSIF is a closed-loop L4 system on Tier-0/2 surfaces with a deliberate, hash-pinned human boundary around Tier 1 — which is as close to "autonomously self-improving its own framework" as is defensible to build.

---

## Appendix: Highest-Leverage Quick Wins (do these today)

1. Re-scope `failure-escalation.md` to `**/*` (defect #1) — one line.
2. Add constitution/settings/ledger patterns to `pre-tool-use-guard.js` (A1) — ~30 lines.
3. Create `control-plane-check.md` (A5) — the spec is already written in the rules.
4. Emit `proposals-<run>.json` from `/self-improve` (C1) — schema edit only; unblocks everything in section C.
5. Add the Tier table to the constitution (F1) — makes the existing governance clause meaningful.

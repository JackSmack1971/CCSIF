# Phase 5A Report

Status: complete (scoped to Phase 5A: portable core, layout, operating
doctrine, and skill taxonomy — not Phase 5B/5C or Phase 6)

## Summary

Phases 0-4 were confirmed evidence-complete before this phase started
(`.claude/state/roadmap/phase-{0,1,2,3,4}-report.md`, all `status: complete`;
`control_plane_check.py` and `rules_fidelity_check.py` re-verified `PASS`
before any change), per the roadmap's sequencing requirement.
`docs/claude-code-control-plane-roadmap-v2.md` was read in full, then the
manifest and every prior phase report/checkpoint, before any change.

This repo already carried a mature `.claude/` tree (16 rule files, 57
skills, 8 agents, a 4-phase Python control-plane harness) built in Phases
0-4. The task instruction — "audit existing files before adding new ones;
consolidate rather than duplicate" — governed every decision below;
rationale for each consolidation-vs-new-file choice is in
`docs/adr/0001-phase-5a-portable-layout.md`.

## What was added

| Artifact | Purpose | New or extended |
|---|---|---|
| `.claude/rules/10-karpathy-guidelines.md` | Assumption-surfacing, verify-before-done, metric-gated experiment loops (the delta `surgical-density.md` did not already cover) | New |
| `.claude/rules/20-lifecycle-gates.md` | Five-gate contract (Align/Research/Plan/Build/Verify&Ship): inputs, outputs, durable artifact, verification owner, risk escalation, explicit-skip policy | New |
| `.claude/rules/30-skill-taxonomy.md` | Two-axis rule: commands orchestrate and never invoke each other; skills are single-purpose and may be `user-invocable: true` without becoming orchestrators | New |
| `.claude/rules/00-core-workflow.md` | Extended (not replaced) with a Scope Doctrine pointer and a loop-discipline cross-reference, keeping its existing role as the operating-doctrine file | Extended |
| `.claude/scripts/taxonomy_check.py` | Deterministic linter: command-cross-invocation, duplicate skill/command description, always-loaded context budget, global-path (`~/.claude`) dependency, oversized root `CLAUDE.md` | New |
| `tests/test_taxonomy_check.py` | 11 tests: one per check against isolated fixture trees (positive and negative cases) plus a real-repo pass-through test | New |
| `docs/CONTEXT.md` | Domain glossary — term, meaning, owning file | New |
| `docs/adr/0000-template.md`, `docs/adr/0001-phase-5a-portable-layout.md` | Minimal ADR template plus the real ADR for this phase's layout decisions | New |
| `.claude/state/handoffs/.gitkeep`, `.claude/state/research/.gitkeep` | Durable artifact locations named by the lifecycle-gate rule (`checkpoints/` and `ledger.md` already existed from Phases 0/2) | New |

## Why this is not a rewrite of the existing corpus

- `00-core-workflow.md` was extended, not replaced, and no competing
  `00-operating-doctrine.md` file was created — see ADR 0001 decision 1.
- `surgical-density.md` was left untouched; `10-karpathy-guidelines.md`
  contains only the content that file did not already have (assumption
  surfacing before code, metric-gated experiments), cross-referencing it
  instead of duplicating it — see ADR 0001 decision 2.
- The five-gate lifecycle contract is documentation only in this phase, per
  the task's explicit "without yet implementing every command" instruction;
  no `/brainstorm`, `/research`, `/plan`, `/build`, `/ship`, `/handoff`,
  `/status`, or `/experiment` command files were added. `.claude/commands/`
  still holds exactly its Phase 0-4 set (`create-pr.md`, `review-pr.md`,
  `audit-upstream.md`, `control-plane-check.md`, `workflow.md`).
- The 57-skill corpus and 8-agent corpus were audited (every `SKILL.md`
  description scanned; every `.claude/commands/*.md` body scanned) and found
  to already follow the two-axis convention (each skill's description states
  one job plus one explicit `NOT for X; use Y instead` non-goal; no command
  body invokes another command). `30-skill-taxonomy.md` documents the
  convention that was already live; `taxonomy_check.py` proves it
  mechanically rather than by inspection.

## Linter evidence (`.claude/scripts/taxonomy_check.py`)

| Check | Current repo state | Declared budget |
|---|---|---|
| Command cross-invocation | 0 violations across 5 command files | n/a (structural) |
| Duplicate skill/command description | 0 duplicates across 57 skills + 5 commands | n/a (structural) |
| Always-loaded context (`CLAUDE.md` + `paths: ["**/*"]` rules) | 140 lines (`CLAUDE.md`=74, `failure-escalation.md`=27, `hindsight-memory.md`=12, `persona-profile.md`=11, `surgical-density.md`=16) | 400 lines (35% used) |
| Global-path (`~/.claude`, `$HOME/.claude`) dependency in hooks/scripts/commands | 0 (one documented non-dependency statement in `phase2_memory.py` correctly excluded by the negation-window heuristic) | n/a (structural) |
| Root `CLAUDE.md` size | 74 lines | 200 lines (37% used) |

Path-scoped rules (`architecture.md`, `security.md`, etc.) are intentionally
excluded from the always-loaded total — they load only when their `paths:`
glob matches the active file, per the existing `rules_fidelity_check.py`
convention this phase reused rather than duplicated.

## Verification

| Command | Result |
|---|---|
| `python -m py_compile .claude/scripts/taxonomy_check.py .claude/scripts/control_plane_check.py .claude/scripts/rules_fidelity_check.py tests/test_taxonomy_check.py` | exit 0 |
| `python -m unittest discover -s tests -v` | exit 0, 65 tests (54 prior + 11 new), no regression |
| `python3 .claude/scripts/control_plane_check.py` | `control-plane-check: PASS` (includes the new `check_taxonomy()` step) |
| `python3 .claude/scripts/rules_fidelity_check.py` | `rules-fidelity-check: PASS` (3 new files registered, `00-core-workflow.md` re-validated after its extension) |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | exit 0 |
| `git check-ignore -v` against every new Phase 5A path | exit 1 (nothing ignored; all evidence is git-visible) |

## Exit Criteria Evidence (Phase 5A scope only)

Phase 5's full exit criteria (bootstrap skill, cross-stack proof, main-thread
context measurement) belong to Phase 5B/5C and are explicitly out of scope
here, per the task instruction. Phase 5A's own scope is covered:

1. **Concise root `CLAUDE.md`** — 74/200 lines (unchanged this phase),
   measured and enforced by `taxonomy_check.check_root_guidance_size()`.
2. **`.claude/settings.json`, gitignored local settings** — already present
   from Phase 0-2 (`plansDirectory`, hooks, `enabledMcpjsonServers`);
   `.gitignore` already excludes `.claude/settings.local.json`. Unchanged
   this phase; re-verified via `check_json()`.
3. **Numbered operating and Karpathy-style rules** —
   `.claude/rules/00-core-workflow.md`, `10-karpathy-guidelines.md` present
   and fidelity-checked.
4. **Small skills, thin commands, bounded agents** — audited, not
   regenerated; 0 taxonomy violations found across the existing corpus.
5. **Relative hooks** — unchanged from Phase 0-3 (`bash .claude/hooks/*.sh`
   relative commands in `.claude/settings.json`).
6. **Plans; optional memory; durable state subdirectories** —
   `.claude/plans/`, `.claude/memory/` (Phase 2), `.claude/state/{ledger.md,
   handoffs,agents,research,checkpoints,roadmap}` all present; `handoffs/`
   and `research/` added this phase to close the two missing subdirectories.
7. **`docs/CONTEXT.md` and `docs/adr/`** — added this phase.
8. **Five-gate lifecycle contract encoded, not fully implemented** —
   `.claude/rules/20-lifecycle-gates.md`.
9. **Two-axis taxonomy enforced with a linter/test** —
   `.claude/rules/30-skill-taxonomy.md` + `.claude/scripts/taxonomy_check.py`
   + `tests/test_taxonomy_check.py`, wired into
   `control_plane_check.py`.
10. **Always-loaded instruction size measured with a declared budget** —
    140/400 lines, enforced by `check_always_loaded_context_budget()`.
11. **ADR for major architecture choices** — `docs/adr/0001-phase-5a-
    portable-layout.md`.

## Design Decisions

See `docs/adr/0001-phase-5a-portable-layout.md` for the full rationale on
each consolidation-vs-new-file choice; not duplicated here.

## Remaining Risks

- Phase 5B/5C (bootstrap skill `/bootstrap-control-plane`, cross-stack
  proof against two unrelated stacks, main-thread context measurement on
  multi-plan work) remain unimplemented; this report does not claim them.
- The five-gate lifecycle contract is documentation only; no `/brainstorm`,
  `/research`, `/plan`, `/build`, `/ship`, `/handoff`, `/status`, or
  `/experiment` command exists yet. A future phase implementing one of
  these must re-run `taxonomy_check.py` to prove it does not violate the
  two-axis rule.
- The duplicate-responsibility check compares exact description strings; it
  will not catch near-duplicate (paraphrased) skill descriptions. This
  matches the roadmap's own admonition to keep the linter thin rather than
  build an NLP similarity system; a future phase could add a stricter
  similarity threshold if paraphrased duplicates are observed in practice.
- The global-path-dependency check is a regex heuristic scoped to
  `.claude/hooks/`, `.claude/scripts/`, `.claude/commands/`; it does not
  scan `.claude/skills/` or `.claude/agents/`. A manual grep for
  `~/.claude` found 7 skill files (`self-improve`, `skill-auditor`,
  `official-docs-pack`, `claude-code-architecture-auditor`,
  `maintaining-repository-hygiene`) with descriptive or optional-scope
  mentions (e.g. "install at project or user scope", or `self-improve`'s
  own read-only reflection scope) rather than functional dependencies —
  none require `~/.claude` for this control plane's own correctness — but
  they were not mechanically verified as non-dependencies the way
  `phase2_memory.py` was. Extending the linter's scan scope to
  `.claude/skills/` and `.claude/agents/` is a candidate Phase 6 hardening
  item, not done here.
- Phases 5B, 5C, 6, and 7 remain incomplete and are not implicitly validated
  by these Phase 5A changes.

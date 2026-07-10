---
name: 7axes-audit
description: Trigger on queries that say run the 7 axes audit, full code quality audit, audit this repo, or slash 7axes-audit, to orchestrate seven parallel axis auditors with coverage rotation, deduplicate findings against a persistent ledger so each run surfaces only new or escalated issues, file agent-ready GitHub issues for downstream PR agents, and apply a bounded self-improvement patch. Accepts targetPath, axes subset, live-issues, and assign-agent arguments. NOT for a single-axis or ad hoc lint pass use the individual axis auditor subagents or the 7axes-reference skill instead. Distinct keywords ledger diff, novelty mandate, axis briefs, evolution patch, coverage rotation.
when_to_use: Trigger for a full seven-axis code quality audit across the whole repository with ledger-based deduplication and GitHub issue filing, not for a single-axis or ad hoc lint pass.
argument-hint: "[targetPath] [--axes x,y] [--live-issues] [--assign-agent]"
arguments:
  - targetPath
  - axes
  - live-issues
  - assign-agent
allowed-tools: Bash, Read, Grep, Glob, Task, Write
---

# 7-Axes Self-Improving Audit — Orchestration Protocol

You are the control plane. Sub-agents are the execution boundaries; scripts are the deterministic state machine. Follow the phases IN ORDER — each phase's script output feeds the next. Parse `$ARGUMENTS`: first positional token = targetPath (default `.`); `--axes x,y` = subset; `--live-issues` = actually create GitHub issues (otherwise dry-run); `--assign-agent` = tag @claude on created issues.

## Phase 0 — Sync feedback, then preflight
```bash
python3 scripts/7axes/feedback.py            # learn from closed issues (no-op if gh absent)
python3 scripts/7axes/preflight.py --target <targetPath> [--axes <axes>]
```
Capture the printed mission brief JSON and its `run_id`. The `axis_briefs` object is your fan-out payload.

## Phase 1 — Parallel fan-out to leaf auditors
For EVERY axis in the brief, launch its subagent (`readability-auditor`, `maintainability-auditor`, `reliability-auditor`, `security-compliance-auditor`, `performance-scalability-auditor`, `testability-coverage-auditor`, `operability-observability-auditor`) **in parallel in a single message** via the Task tool. Each task prompt must contain:
1. The target path.
2. That axis's full brief from `axis_briefs` (verbatim JSON — including `novelty_mandate`).
3. "Return ONLY the JSON contract from the 7axes-reference skill."

Do not fail fast: collect whatever returns; a failed axis becomes a `failed_axes` note, never a run abort.

## Phase 2 — Validate & persist (deterministic gate)
For each auditor's raw output, write it to a temp file, then:
```bash
python3 scripts/7axes/validate_report.py --run <run_id> --axis <axis> --file <tmp>
```
Exit 2 = that axis failed validation; retry that auditor ONCE with the validator's stderr appended to its prompt, then give up on it.

## Phase 3 — Novelty diff (the anti-repetition engine)
```bash
python3 scripts/7axes/ledger.py diff --run <run_id>
```
This classifies every finding as new / repeat / escalated / resolved / suppressed against all prior runs. Only NEW and ESCALATED move forward.

## Phase 4 — Synthesis
Launch `7axes-synthesizer` with the run_id and the path `.7axes/runs/<run_id>/novelty.json`. Save its JSON reply to `.7axes/runs/<run_id>/synthesis.json` if it could not write it itself.

## Phase 5 — GitHub issues for downstream PR agents
```bash
python3 scripts/7axes/issues.py --run <run_id> --min-severity medium [--execute] [--assign-agent]
```
Use `--execute` only when the user passed `--live-issues`. Report created/deduped/escalated counts to the user.

## Phase 6 — Self-improvement (the reason this gets better every run)
1. Launch `7axes-meta-auditor` with the run_id. It writes `.7axes/runs/<run_id>/evolution_patch.json`.
2. Apply, bounded and audited:
```bash
python3 scripts/7axes/evolve.py --run <run_id>
python3 scripts/7axes/ledger.py commit --run <run_id>
```

## Phase 7 — Deterministic report
```bash
python3 scripts/7axes/report.py --run <run_id> --out reports
```
Show the user: composite + per-axis deltas, the NEW findings list with issue links, escalations, resolutions, and one line on what the system just learned (from evolve.py output). Recommend committing `.7axes/`, `reports/`, and any `.claude/agents/*.md` directive changes so learning persists.

## Checklist

- [ ] Phase 0: feedback synced, preflight brief captured with `run_id`.
- [ ] Phase 1: every axis auditor launched in parallel, results collected (failures noted, not fatal).
- [ ] Phase 2: each axis report validated against the deterministic gate.
- [ ] Phase 3: novelty diff computed against the ledger.
- [ ] Phase 4: synthesis written to `synthesis.json`.
- [ ] Phase 5: GitHub issues filed (or dry-run reported) per `--live-issues`.
- [ ] Phase 6: self-improvement patch generated, applied, and committed to the ledger.
- [ ] Phase 7: deterministic report rendered and shown to the user.

**Stop condition:** halt and report the failed axis or phase if any deterministic gate script exits non-zero twice in a row; do not claim the run is complete.

## Invariants
- Never edit ledger.jsonl or calibration.json by hand — scripts only.
- Never let a subagent spawn further subagents.
- If `.7axes/` is missing, scripts create it — first run on any repo is zero-config.
- Partial results are acceptable; silent failures are not: always tell the user which axes failed.

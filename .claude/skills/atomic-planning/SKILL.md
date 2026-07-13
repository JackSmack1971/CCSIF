---
name: atomic-planning
description: Use when turning aligned requirements and research into one or more atomic implementation plans of at most three tasks each, with explicit assumptions, per-task verification targets, commit boundaries, and blocking edges between plans. Trigger on queries that say plan this out, break this into atomic plans, write the implementation plan, what are the tasks and verification steps. NOT for a long-form PRD with user stories published to an issue tracker use to-spec instead, and NOT for choosing which tests to run for an already-planned change use test-strategy instead. Distinct keywords atomic, three-task-cap, blocking-edges, commit-boundary, verification-target.
when_to_use: Use to convert aligned requirements into small, disk-persisted, atomic plans (max three tasks each) with explicit assumptions and per-task verification. Do not use for a full PRD (to-spec) or for choosing a test strategy on its own (test-strategy).
argument-hint: "[feature or change to plan]"
allowed-tools: Read, Grep, Glob, Bash
---

# Atomic Planning

Gate 3 (Plan) of the five-gate lifecycle. Produces plan files under `.claude/plans/` via `.claude/scripts/phase5b_lifecycle.py plan-create`, never hand-written JSON, so every plan is validated at creation time.

## Why atomic

A plan capped at three tasks fits in one fresh subagent's context without drift. If the work needs more than three tasks, split it into multiple plans and connect them with `blocking_edges` — never widen a single plan past the cap.

## Process

- [ ] Restate the assumptions surfaced during alignment (`alignment-interview`); a plan with zero assumptions listed is treated as under-specified, not as evidence nothing was assumed.
- [ ] Break the work into at most three tasks. If more are needed, create multiple plan files and set `blocking_edges` on the dependent plan to the prerequisite plan's `plan_id`.
- [ ] For every task, name the exact verification target from `.claude/hooks/verify.sh list-targets` (or a non-code target: rubric/citation/factcheck) — never leave verification implicit.
- [ ] For every task, decide `commit_boundary: true/false` explicitly: true means this task's diff is its own commit; false means it shares a commit boundary with an adjacent task (state why in the description if false).
- [ ] Create the plan:
      ```bash
      python3 .claude/scripts/phase5b_lifecycle.py plan-create --title "<title>" <<'JSON'
      {"assumptions": ["..."], "tasks": [{"task_id": "t1", "description": "...", "verification": {"target": "..."}, "commit_boundary": true}], "blocking_edges": []}
      JSON
      ```
- [ ] Re-run `plan-validate <plan_id>` after any manual edit to the plan file, since the validator is the only thing enforcing the three-task cap and required fields.

## Checklist

- [ ] At most three tasks per plan file; extra work split into a blocking-edge-connected plan instead of widening this one
- [ ] Every assumption from alignment carried into `assumptions`
- [ ] Every task has a named verification target and an explicit `commit_boundary` boolean
- [ ] `blocking_edges` reference only plan files that already exist on disk

## Completion gate

Do not consider planning complete until `plan-validate <plan_id>` exits 0 for every plan created for this unit of work, and every task's verification target actually exists (per `verify.sh list-targets`) or is a documented non-code target.

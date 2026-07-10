# Proposal Schema

Every `/self-improve` output must use exactly this format. No conversational text outside proposal blocks and the no-qualifying-improvement message.

---

## PROPOSAL [N] of [TOTAL]

**Component**: `CLAUDE.md` | `skill:<name>` | `hook:<name>` | `mcp:<tool>`

**Evidence**: Quote the exact trace entry or metric. Include the file name and entry index or line number. Maximum 5 lines of quoted trace text per proposal.

**Constitution Clause**: `"[verbatim substring of the Constitution — not paraphrased, not summarized]"`

**Proposed Change**:
```diff
--- a/[project-relative/path/to/file]
+++ b/[project-relative/path/to/file]
@@ -[start-line],[count] +[start-line],[count] @@
 [unchanged context line]
 [unchanged context line]
 [unchanged context line]
-[removed line]
+[added line]
 [unchanged context line]
 [unchanged context line]
 [unchanged context line]
```

**KPI Impact**: Name the specific KPI from `kpi-defaults.md` (or user-defined). State direction (+/−) and estimated magnitude with reasoning. Example: `Trigger reliability +27% — eliminates 4 of 15 observed activation_miss events.`

**Reversibility**: Exact rollback instruction. Minimum: `git revert <commit>` or the specific string to restore. State any cascading effects on downstream components.

**Risk**: Known side effects, potential regressions, or monitoring requirements. May be `None identified — change is additive with no removal of existing behavior.` only if explicitly reasoned.

**Verification**: Observable check that confirms the change had the intended effect. Must be a concrete action, not a vague instruction. Example: `Re-run /self-improve skill:<name> 5 after applying and confirm activation_miss count = 0.`

---

## Validation Rules

A proposal is emittable only if ALL of the following are true:

1. `Component` is one of the four declared types.
2. `Evidence` contains at least one direct trace quote with a location identifier (file + entry index or line).
3. `Constitution Clause` is a verbatim substring of the extracted Constitution text — not paraphrased.
4. `Proposed Change` is a valid unified diff: contains `---`, `+++`, and at least one `@@ ... @@` hunk header.
5. `KPI Impact` names a specific KPI, states direction, and gives a magnitude estimate with reasoning.
6. `Reversibility` provides a concrete rollback path.
7. `Risk` is present and explicitly reasoned (not omitted).
8. `Verification` names an observable, repeatable check.

If any rule fails, fix that field before emitting. Do not emit invalid proposals.

---

## No-Qualifying-Improvement Message

If no issue meets the evidence + impact threshold (score < 5 with no critical failures), output exactly:

```
No qualifying improvement found. Current configuration is stable on measured dimensions.
Window analyzed: [N] tasks. Components reviewed: [list]. KPIs checked: [list].
```

Do not emit proposals below threshold to pad output.

---

## Deferred Issues Appendix

When more than 3 issues were identified but not carried forward (score too low or single non-critical occurrence), append after all proposals:

```markdown
## DEFERRED ISSUES
The following issues did not meet the proposal threshold this cycle.
Review if recurrence increases in subsequent cycles.

- [Issue 1 — one-line description] (trace ref: file, entry N; score: X)
- [Issue 2 — one-line description] (trace ref: file, entry N; score: X)
```

---

## Scoring Reference

```
Score = recurrence_count × kpi_delta_magnitude × reversibility_factor
```

- `recurrence_count`: raw count of occurrences in the analysis window
- `kpi_delta_magnitude`: estimated percentage-point improvement (e.g., 15 for +15 pp)
- `reversibility_factor`: `1.0` (full git revert) | `0.7` (partial, requires manual steps) | `0.3` (difficult to reverse, affects other components)

Carry forward if `Score ≥ 5` OR failure class is `critical` (data loss, security bypass, Constitution violation, unauthorized external call).

Proposals are ordered by Score descending.

# Report and State Contracts

## Contents

- [Merge-order analysis](#merge-order-analysis)
- [Conflict plan](#conflict-plan)
- [Resolution state](#resolution-state)
- [Resolution record](#resolution-record)
- [Exit codes](#exit-codes)

## Merge-order analysis

`check_merge_order.py` writes:

```json
{
  "schema_version": 1,
  "status": "ok | partial | blocked | error",
  "repository": "OWNER/REPO",
  "repository_url": "https://HOST/OWNER/REPO",
  "remote": "origin",
  "generated_at": "RFC3339 UTC",
  "fetch_performed": true,
  "selected_pr_numbers": [],
  "prs": [],
  "dependencies": [],
  "components": [],
  "global_waves": [],
  "independent_prs": [],
  "warnings": [],
  "errors": []
}
```

An `ok` result means complete evidence, an acyclic graph, and no blocking warning. Each PR includes GitHub snapshot OIDs, fetched effective OIDs, head repository, base/head branch names, and readiness metadata.

A direct dependency records `before`, `after`, evidence from `ancestry` or `base_target`, and whether declared targeting contradicted ancestry.

## Conflict plan

`conflict_pass.py plan` writes an immutable review artifact:

```json
{
  "schema_version": 1,
  "kind": "stack_conflict_resolution_plan",
  "status": "clean | conflicts | blocked",
  "strategy": "merge_exact_base_into_exact_head",
  "analysis_sha256": "...",
  "plan_sha256": "...",
  "actions": [
    {
      "pr_number": 42,
      "component": 1,
      "wave": 2,
      "predecessors": [41],
      "head_ref_name": "feature-b",
      "base_ref_name": "feature-a",
      "head_oid": "...",
      "base_oid": "...",
      "preflight": "clean | conflicted | error",
      "eligible": true,
      "conflicts": [
        {
          "path": "src/example.ts",
          "type": "content_or_mode",
          "stages": {
            "1": {"mode": "100644", "oid": "..."},
            "2": {"mode": "100644", "oid": "..."},
            "3": {"mode": "100644", "oid": "..."}
          }
        }
      ]
    }
  ],
  "blocking_errors": []
}
```

Only the first currently conflicted action is `eligible`. Any publication invalidates the remaining plan.

## Resolution state

State transitions are monotonic:

```text
prepared -> verified -> published
```

`prepared` records exact PR/base OIDs, worktree path, conflict set, and plan hash. `verified` adds the merge commit OID, validation results, and resolution-record hash. `published` adds the push target and GitHub-confirmed new head OID.

The state file remains after worktree cleanup as an audit record.

## Resolution record

```json
{
  "schema_version": 1,
  "kind": "stack_conflict_resolution_record",
  "pr_number": 42,
  "plan_sha256": "...",
  "conflict_resolutions": [
    {
      "path": "src/example.ts",
      "type": "content_or_mode",
      "diagnosis": "Base changed the API while the PR added validation against the prior signature.",
      "resolution": "Adapt validation to the new signature while preserving the PR's error behavior.",
      "evidence": ["commit abc123", "tests/example.test.ts"]
    }
  ],
  "validation_commands": [["npm", "test", "--", "example"]],
  "validation_waiver": "",
  "allow_marker_paths": []
}
```

`allow_marker_paths` is only for files that intentionally contain conflict-marker examples. Its use requires an explicit diagnosis and resolution rationale.

## Exit codes

### Merge-order analyzer

- `0` — complete and safe order evidence.
- `2` — local prerequisite failure.
- `3` — GitHub resolution/query failure.
- `4` — partial evidence.
- `5` — blocking inconsistency.

### Conflict pass

- `0` — clean plan, successful verification, publication, or cleanup.
- `2` — missing local prerequisite.
- `3` — invalid input or state.
- `10` — conflicts found or prepared for resolution.
- `11` — stale, blocked, or unsafe plan.
- `12` — diagnosis, staging, validation, or commit verification failure.
- `13` — live PR query or publication failure.

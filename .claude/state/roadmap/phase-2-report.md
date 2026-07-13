# Phase 2 Report

Status: complete

## Summary

Phase 0 and Phase 1 were confirmed evidence-complete before this phase started (`.claude/state/roadmap/phase-0-report.md`, `.claude/state/roadmap/phase-1-report.md`, both `status: complete`; `control_plane_check.py` and `rules_fidelity_check.py` re-verified `PASS`) per the roadmap's sequencing requirement, and `docs/claude-code-control-plane-roadmap-v2.md` Phase 2 section was read in full before any change.

Implemented the smallest project-local layer that makes Claude Code's own memory model into control-plane state, per the roadmap's "file-backed enhancement, external store secondary" design:

- `plansDirectory: "./.claude/plans"` wired in `.claude/settings.json`, with the directory created and git-visible.
- `.claude/scripts/phase2_memory.py`: a bootstrap-safe, idempotent writer for `autoMemoryDirectory` in gitignored `.claude/settings.local.json` (absolute path, never clobbers existing personal keys, refuses to overwrite unreadable local settings rather than guessing); PreCompact snapshot capture; PostCompact summary capture; SessionStart restoration that validates a snapshot's `session_id` before reusing it and rejects stale/foreign/corrupt snapshots outright; SubagentStop summary+transcript-pointer export; and a `status` command that reconstructs effective memory sources, the latest verified checkpoint, and whether recovery is native-file-backed or index-backed.
- New hooks `.claude/hooks/post-compact.sh` and `.claude/hooks/subagent-stop.sh`, and extensions to the existing `.claude/hooks/session-start.sh` (bootstrap + restore) and `.claude/hooks/pre-compact.sh` (snapshot), all registered in `.claude/settings.json`.
- `.claude/rules/memory-and-compaction.md`: the committed-or-private policy for `.claude/memory/`, the compaction/restore contract, the subagent-export location, and documented prompt-cache-stable-prefix/invalidator guidance (registered in `rules_fidelity_check.py`'s `EXPECTED_SCOPES`/`MAX_LINES`).
- `.claude/state/compactions/` and `.claude/state/agents/` durable directories (git-visible via `.gitkeep`).
- `control_plane_check.py` extended: new required paths (the new script, hooks, and durable directories) and new hook scripts added to the `bash -n` parse check.

## Implemented / Changed Files

- `.claude/scripts/phase2_memory.py` (new)
- `.claude/hooks/post-compact.sh` (new)
- `.claude/hooks/subagent-stop.sh` (new)
- `.claude/hooks/session-start.sh` (extended: bootstrap + restore)
- `.claude/hooks/pre-compact.sh` (extended: snapshot)
- `.claude/rules/memory-and-compaction.md` (new)
- `.claude/plans/.gitkeep`, `.claude/state/compactions/.gitkeep`, `.claude/state/agents/.gitkeep` (new)
- `.claude/settings.json` (`plansDirectory`, `PostCompact`, `SubagentStop` hooks)
- `.claude/scripts/control_plane_check.py` (required paths + shell-parse list)
- `.claude/scripts/rules_fidelity_check.py` (new rule file registered)
- `tests/test_phase2_memory.py`, `tests/test_phase2_smoke.py` (new)
- `.claude/state/completion-matrix.md`, `.claude/state/execution-manifest.json`, `.claude/state/ledger.md` (Phase 2 evidence)

## Design Decisions

1. Reuse Phase 0's `state_root()`/`workspace_root()` env-overridable helpers (`PHASE0_STATE_ROOT`, `PHASE0_WORKSPACE_ROOT`) instead of inventing new environment variables, so Phase 2 tests share the exact fresh-clone/restart fixture pattern Phase 0 already established.
2. Bootstrap is additive-only: it reads an existing `.claude/settings.local.json`, sets only `autoMemoryDirectory`, and leaves every other key (personal env vars, extra allow rules) untouched. An unreadable existing file is a hard error, not a silent overwrite.
3. Compaction restoration trusts nothing by identity alone: a PreCompact snapshot is only replayed at the next `SessionStart` if its `session_id` matches the current session; a missing, foreign, or corrupt snapshot is explicitly rejected and the rejection reason is itself persisted as evidence (`*-restore.json`), never silently ignored.
4. `PostCompact` has no decision-control channel per the hooks contract (context-only), so restoration happens at the following `SessionStart` (`source: "compact"` or `"resume"`), which does support `hookSpecificOutput.additionalContext` — matching the documented hook capability matrix instead of assuming a channel that doesn't exist.
5. All new hook side effects (`bootstrap-local-settings`, `precompact`, `postcompact`, `subagent-export`) are wired with `|| true` in the calling shell hook so a Phase 2 failure never blocks the pre-existing Phase 0/1 hook contract (no new blocking failure mode introduced).
6. No external index was added. `phase2_memory.py status` always reports `recovery.source: "native-files"` and `recovery.external_index_configured: false`, satisfying the "show whether recovery came from native files or an optional index" exit criterion without building a store that isn't needed yet.

## Verification

| Command | Exit |
|---|---:|
| `python -m py_compile .claude/scripts/phase2_memory.py tests/test_phase2_memory.py tests/test_phase2_smoke.py` | `0` |
| `python -m unittest discover -s tests -v` (22 tests: 6 Phase 0 + 16 Phase 2, no regression) | `0` |
| `python3 .claude/scripts/control_plane_check.py` | `0` |
| `python3 .claude/scripts/rules_fidelity_check.py` | `0` |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | `0` |
| `git check-ignore -v <all new Phase 2 paths>` | `1` (nothing ignored; all evidence paths are git-visible) |
| `python3 .claude/scripts/phase2_memory.py status` (live, against this repo) | `0` |

### Exit Criteria Evidence

- **Reconstruct project memory after restart and after a fresh clone, with no `~/.claude/*` dependency**: `tests/test_phase2_smoke.py::test_fresh_clone_session_start_hook_bootstraps_and_starts_session` runs the real `session-start.sh` hook against an empty temp workspace (no pre-existing `.claude/settings.local.json`, no state root) and proves `autoMemoryDirectory` is bootstrapped to an absolute repo-local path; `tests/test_phase2_memory.py::test_status_reconstructs_after_restart_from_a_fresh_process_instance` proves a brand-new `Phase2` process pointed at the same roots reconstructs the same checkpoint/compaction/agent-export evidence.
- **Auto memory, compaction summaries, subagent exports visible under `.claude/`**: `.claude/state/compactions/` and `.claude/state/agents/` are populated by the hook chain and inspected directly by `phase2_memory.py status`; `.claude/settings.local.json`'s `autoMemoryDirectory` points at `.claude/memory/`.
- **Backend shows native-files vs. external-index recovery**: `status.recovery` field, exercised in `test_status_reconstructs_after_restart_from_a_fresh_process_instance`.
- **Resume with the same effective memory state, no external-store or `~/.claude/` dependency**: `tests/test_phase2_smoke.py::test_precompact_then_postcompact_then_session_start_restore_end_to_end` drives the full `session-start -> tool cycle -> verify -> pre-compact -> post-compact -> session-start(source=compact)` chain through the real shell hooks and CLI, and asserts the restored `additionalContext` contains both the verified checkpoint and the real compact summary text.
- **Stale-summary rejection**: `test_session_start_restore_rejects_stale_or_foreign_snapshot` (foreign `session_id`) and `test_session_start_restore_rejects_corrupt_snapshot` (unreadable JSON) both assert `validated: False` with an explicit reason, and a `-restore.json` record is written either way so the rejection itself is durable evidence.
- **Missing-local-settings recovery**: `test_missing_auto_memory_key_is_added_without_clobbering_other_keys` starts from a hand-written `settings.local.json` missing the key and proves it is added without touching pre-existing personal keys; `test_session_start_hook_is_safe_when_settings_local_already_exists` proves the same through the real hook.
- **Subagent-summary linkage**: `test_subagent_export_links_back_to_parent_session` and the hook-level `test_subagent_stop_hook_exports_summary` both assert the export path is `.claude/state/agents/<parent_session_id>/<agent_id>.json` and the record's `parent_session_id` matches.
- **Prompt-cacheable stable prefixes / invalidation boundaries documented**: `.claude/rules/memory-and-compaction.md`.
- **Committed-or-private policy for `.claude/memory/`**: `.claude/rules/memory-and-compaction.md`, matching the existing `.gitignore` rules (source tracked, `state/`/`.venv/`/db/jsonl generated artifacts ignored).

## Remaining Risks

- The real, machine-local `.claude/settings.local.json` on this workstation was left untouched by this session (it predates Phase 2 and already carries personal `env`/`localPaths` keys); the bootstrap only runs automatically on the next real `SessionStart` hook invocation, or on manual invocation of `python3 .claude/scripts/phase2_memory.py bootstrap-local-settings`. This was a deliberate choice to avoid mutating the user's existing local file outside of the native hook path, not a gap in the mechanism — the mechanism itself is proven end-to-end against fresh and pre-existing fixtures in `tests/test_phase2_smoke.py`.
- `PostCompact` hooks have no decision-control channel per the documented hook contract; restoration is deferred to the following `SessionStart`, which is correct per the docs but means there is a window (between compaction completing and the next `SessionStart`) where no re-injection has happened yet — this matches Claude Code's own native behavior (root `CLAUDE.md` re-injection also happens at read time, not mid-compaction) and is not a Phase 2 regression.
- No external memory index was built; Phase 2 intentionally stops at "native files are the source of truth, `status` reports that fact," per the roadmap's "external store only after the file layout is stable" ordering. A future phase may add one without changing this contract.
- Phases 3-7 remain incomplete and are not implicitly validated by these Phase 2 changes.

# HINDSIGHT Hardening Roadmap

This roadmap documents the current status of the repository-local HINDSIGHT memory system in `.claude/memory/`, its related `hindsight-*` skills, and the optional Graphiti backend. It is a living implementation checklist, not evidence of a missing security policy or missing repository roadmap.

## Current Baseline

- [x] `hindsight.py` is the single CLI entrypoint with `bootstrap`, `retain`, `replay`, `recall`, `observe`, `reflect`, `reinforce`, `graphiti-check`, and `self-test` commands.
- [x] Local memory records are split into `world`, `experience`, `observation`, and `opinion` stores.
- [x] Retained records carry source trace file and line-number provenance.
- [x] `retain` tracks a cursor and suppresses duplicate `(kind, source_trace, source_line)` records.
- [x] `replay` can rebuild local state from `.claude/traces/`.
- [x] `recall`, `observe`, `reflect`, and `reinforce` are implemented for local mode.
- [x] `reflect` reuses the latest matching opinion and deterministically reinforces confidence when new evidence supports or contradicts it.
- [x] Graphiti is optional and environment-driven; local mode remains the default.
- [x] `.claude/memory/README.md` documents setup, fallback behavior, `graphiti-check`, and example commands.
- [x] Repository CI runs the authoritative unittest suite plus control-plane and rules validation on Linux, macOS, and Windows.

## Current Hardening Status

Implemented hardening behavior now includes:

- Protected-area enforcement through the `PreToolUse` hook and `pre-tool-use-guard.js`.
- Phase 0 request tracking that warns on tracking/state errors without blocking otherwise-safe tool calls, while preserving hard blocks for genuine safety failures.
- Explicit Claude settings for manual default mode, bypass-permission disabling, shell allow/ask/deny rules, MCP server enablement, skill shell-execution disabling, and sensitive-path sandbox metadata.
- GitHub governance automation through issue forms, a PR template, CODEOWNERS, Dependabot, a checked-in branch-protection ruleset definition, and CI.
- Security disclosure through `SECURITY.md`; references to a missing security policy are stale and should not be reintroduced.

## Remaining Follow-Up

- [ ] Add focused regression tests for `retain` cursor replay and duplicate suppression if future memory changes alter ingestion logic.
- [ ] Add focused regression tests for neutral `observe` output if future prompt or record-shaping logic changes.
- [ ] Add focused regression tests for repeated `reflect`/`reinforce` confidence movement if future persona or confidence math changes.
- [ ] Validate live Graphiti ingest/search/observation projection in an environment with `HINDSIGHT_BACKEND=graphiti` and the required Neo4j, LLM, and Voyage settings. Keep this optional; local mode remains the default supported path.
- [ ] Keep issue and PR workflow docs aligned with `.github/ISSUE_TEMPLATE/**`, `.github/PULL_REQUEST_TEMPLATE.md`, and `.claude/skills/issue-to-pr/scripts/issue_to_pr.py` whenever those files change.

## Verification Commands

Use these checks when changing HINDSIGHT or hardening behavior:

```bash
python .claude/memory/hindsight.py self-test
python .claude/memory/hindsight.py graphiti-check
python -m unittest discover -s tests -v
python .claude/scripts/control_plane_check.py
python .claude/scripts/rules_fidelity_check.py
bash .claude/hooks/verify.sh run rules
pwsh ./.claude/hooks/verify.ps1 run rules
```

`graphiti-check` is expected to report an unavailable optional backend unless `HINDSIGHT_BACKEND=graphiti` and the backend credentials/services are configured. Treat that as an environment limitation, not a local-mode failure.

## Maintenance Notes

- The HINDSIGHT docs under `.claude/docs/Hindsight-memory-architecture/` are background material and implementation guidance, not runtime policy.
- Local memory state under `.claude/memory/` is implementation data; avoid hand-editing generated state and prefer `replay` when state needs to be rebuilt from traces.
- If Graphiti support is intentionally out of scope for a change, document that the local fallback was verified and leave live Graphiti validation as optional environment-specific follow-up.

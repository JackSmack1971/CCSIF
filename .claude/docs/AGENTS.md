# Architecture Docs

## Purpose
Reference material and history for this repo's own Claude Code control-plane (not auto-loaded into every turn — read on demand). Covers why the current rules/hooks/skills setup looks the way it does, plus third-party research notes on an external memory architecture (HINDSIGHT) that informed `.claude/memory/`. This directory does not define active behavior; `.claude/rules/`, `.claude/hooks/`, and `.claude/skills/` do that.

## Entry Points
- `decision-log.md` - append-only record of control-plane audit/remediation decisions (e.g. removing an untracked rule file that granted itself unreviewed operational authority, fixing `globs:` vs `paths:` frontmatter mismatches). Append new entries; do not rewrite history.
- `claude-code-architecture-reference.md` - descriptive reference relocated out of an active rule file; its citations are unverified, so treat claims here as unconfirmed until cross-checked against official docs.
- `CCSIF-Autonomous-Self-Improvement-Report.md` - report on the self-improvement/autonomy mechanism (Tier 0/1/2 change budget) defined in the root `CLAUDE.md` Constitution.
- `Claude Code Memory Architecture Map.md` - map of how `.claude/memory/` and related state fit into this repo's Claude Code setup.
- `Hindsight-memory-architecture/` - external research notes (not authored for this repo) on the HINDSIGHT memory architecture (episodic/observation/opinion networks, TEMPR pipeline); background reading, not a spec this repo implements verbatim.

## Contracts & Invariants
- These docs are historical/reference, not enforceable policy — enforcement lives in `.claude/rules/*.md` (loaded per-turn) and `.claude/hooks/` (deterministic gates). Don't treat a claim in `claude-code-architecture-reference.md` as ground truth without verifying against current official Claude Code docs.
- `decision-log.md` entries must cite their source evidence (an audit report path, a specific hook/script) — see the 2026-07-09 entry for the expected format.

## Patterns
To record a new control-plane decision:
1. Append a dated `##` section to `decision-log.md` (don't edit or remove prior entries).
2. Cite the source evidence (audit report, script, commit) that justified the change.
3. Note residual risk explicitly if the change is a heuristic/partial fix rather than a complete one.

## Anti-patterns
- Don't cite `claude-code-architecture-reference.md` or the Hindsight notes as authoritative for a live behavioral change — verify against current official docs first, per `.claude/rules/claude-code-ecosystem.md`.
- Don't hand-edit `decision-log.md` history to "clean it up"; it's an append-only audit trail.

## Related Context
- Skills library: `../skills/AGENTS.md`
- Control-plane rules: `../rules/`
- Root constitution and Tier rules: `../../CLAUDE.md`

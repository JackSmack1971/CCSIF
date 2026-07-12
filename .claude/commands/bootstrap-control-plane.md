Bootstrap or reconcile the portable, code-agnostic control-plane tree (Phase 5.5) in the current repo or a `--target` path. Idempotent: never overwrites an existing file under `.claude/` or an existing `CLAUDE.md` Source-of-Truth Commands block; only creates what is missing.

Delegate entirely to `.claude/scripts/bootstrap_control_plane.py`; this command never re-implements the scaffold/interview/validate/smoke logic inline (two-axis taxonomy: commands orchestrate, never duplicate a script's own logic).

Steps:

1. Scan the target repo for stack markers (`package.json`, `pyproject.toml`, `requirements.txt`, docs-only) via `python3 .claude/scripts/bootstrap_control_plane.py facts --target <path>`, or accept an explicit `--facts-json` file for a non-interactive interview answer set (issue tracker, build/test/lint or non-code verifier, commit convention, mandatory/skippable gates, memory policy, platform).
2. Run `python3 .claude/scripts/bootstrap_control_plane.py run --target <path> [--facts-json <path>] [--dry-run]` to create or reconcile the tree, generate/merge the `CLAUDE.md` facts block, write `autoMemoryDirectory` (absolute path) into the gitignored `.claude/settings.local.json`, and append safe `.gitignore` entries.
3. Validate with `python3 .claude/scripts/bootstrap_control_plane.py validate --target <path>` (required paths present, `.claude/settings.json` is valid JSON, the verify adapter parses `CLAUDE.md`).
4. Run the trivial five-gate smoke workflow with `python3 .claude/scripts/bootstrap_control_plane.py smoke --target <path>` and confirm every gate's durable artifact was written and the verify adapter's `smoke` target exits 0.

Durable artifact: the scaffolded `.claude/` tree itself, plus the `run`/`validate`/`smoke` JSON output as evidence (redirect to `.claude/state/roadmap/` when bootstrapping this repo's own history; a target repo keeps only the tree).

# Ledger

## 2026-07-12 Baseline scaffold

- Goal: establish the execution baseline for the Claude Code Control Plane roadmap without implementing later phases.
- Read: `docs/claude-code-control-plane-roadmap-v2.md` in full before touching the repo.
- Added: `.claude/state/execution-manifest.json`, `.claude/state/baseline.md`, `.claude/state/completion-matrix.md`.
- Verification commands:
  - `git rev-parse --show-toplevel; git status --short --branch; git branch --show-current; git rev-parse HEAD` -> `0`
  - `Get-FileHash docs/claude-code-control-plane-roadmap-v2.md -Algorithm SHA256` -> `0`
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
- Validation follow-up:
  - `Get-Content -Raw .claude/state/execution-manifest.json | ConvertFrom-Json` plus roadmap link resolution -> `0`
- Current dependency check: no active repository file requires `~/.claude/*` or other machine-global Claude state.
- Notes: the repo already contained unrelated untracked roadmap/docs files; they were left untouched.

## 2026-07-12 Phase 0 complete

- Goal: implement the smallest tested Phase 0 harness for gather-context -> act -> verify with durable state, replayable events, and verified checkpoint resume.
- Added: `.claude/scripts/phase0_control_plane.py`, `.claude/hooks/pre-compact.sh`, `tests/test_phase0_control_plane.py`, `tests/test_phase0_smoke.py`, `.claude/state/roadmap/phase-0-report.md`, `.claude/state/roadmap/phase-0-checkpoint.json`.
- Updated: `.claude/hooks/session-start.sh`, `.claude/hooks/pre-tool-use.sh`, `.claude/hooks/post-tool-use.sh`, `.claude/scripts/control_plane_check.py`, `.claude/settings.json`, `.claude/state/completion-matrix.md`, `.claude/state/execution-manifest.json`.
- Verification commands:
  - `python -m py_compile .claude/scripts/phase0_control_plane.py tests/test_phase0_control_plane.py tests/test_phase0_smoke.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0`
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
- Evidence:
  - Tool-call request/result replay, raw export retention, restart reconstruction, sandbox rejection, interrupted-session recovery, and terminal retry exhaustion are all covered by the new tests.
  - Compaction now writes a verified checkpoint before context trim via `.claude/hooks/pre-compact.sh`.
- Notes:
  - Phase 1 remains untouched.
  - Unrelated untracked roadmap/docs files remain preserved.

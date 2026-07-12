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

## 2026-07-12 Phase 1 complete

- Goal: close the two "partial" Phase 1 criteria (skill-promotion discipline, subagent delegation proof) and verify the three "existing" criteria against live behavior rather than static presence, per `docs/claude-code-control-plane-roadmap-v2.md`.
- Read: `docs/claude-code-control-plane-roadmap-v2.md` Phase 1 section; `.claude/state/roadmap/phase-0-report.md` and checkpoint (confirmed evidence-complete before proceeding); `.claude/settings.json`; `.claude/rules/*.md`; `.claude/agents/*.md`; `.claude/hooks/*`; `.mcp.json`.
- Fixed:
  - `.claude/settings.json`: replaced the non-standard `allowedMcpServers` key with the documented `enabledMcpjsonServers: ["graphiti-memory"]`, so the project `.mcp.json` server is actually auto-approved instead of re-prompting collaborators.
  - `.claude/agents/reflect-agent.md`, `.claude/agents/upstream-auditor.md`: corrected `tools:` frontmatter from lowercase/invalid names (`[read, grep, git, shell, ...]`) to canonical Claude Code tool identifiers (`Read, Grep, Bash`), matching the working format already used by `implementation-agent.md` and `pr-reviewer.md`.
  - `.claude/rules/claude-code-ecosystem.md`: added a skill-promotion rule (check `.claude/skills/` before writing a procedure inline; promote once it recurs; skip a skill for one-off work), kept inside the file's existing 20-line budget.
- Verified (live behavior, not just static presence):
  - PreToolUse hook block/allow/error paths, exercised with a Windows-native `cwd` payload matching real Claude Code invocation: block (`Edit` on `.env.production`, `Bash rm` under `migrations/` → exit 2 with stderr reason), allow (`Read` on `README.md` → exit 0), error (malformed/empty stdin → exit 1, visible per the hooks doc's "non-blocking error" contract).
  - Agent-tool delegation to a `.claude/agents/`-defined role: spawned `pr-reviewer` with a diagnostic task; it called `Bash` and `Read` and returned real, verifiably-accurate live `git status` output (`tool_uses: 2`).
  - `.mcp.json` fix confirmed valid JSON and both governance checks pass.
- Verification commands:
  - `python3 .claude/scripts/control_plane_check.py` -> `0`
  - `python3 .claude/scripts/rules_fidelity_check.py` -> `0`
  - `python -m unittest discover -s tests -v` -> `0` (6 tests, no regression)
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> `0`
- Evidence: `.claude/state/roadmap/phase-1-report.md`, `.claude/state/roadmap/phase-1-checkpoint.json`, updated `.claude/state/completion-matrix.md` Phase 1 section.
- Notes:
  - Phase 2 is untouched, per instruction not to start it.
  - `reflect-agent` correctly enforced its own narrow role scope during two of three test probes (declining to act as a generic file-echo proxy); this is recorded as a residual note in the completion matrix, not a blocker, since `pr-reviewer` proved the same delegation path executes tools end to end.
  - Unrelated untracked files (`claude-code-control-plane-roadmap.md` v1, `docs/`) remain preserved and untouched.


# Execution Baseline

Scope: repository-local baseline for [docs/claude-code-control-plane-roadmap-v2.md](../../docs/claude-code-control-plane-roadmap-v2.md)

## Snapshot

- Repo root: `C:/workspaces/CCSIF`
- Branch: `main`
- HEAD: `e9358b553a9a05c16de00af28e35a9f29e5b16b1`
- Roadmap hash: `7D6F35A16DEE91F0BD8B4DA98EA29F05CDC13003DF1C096BFA620C7610E08AE6`
- Roadmap length: `287` lines
- Baseline date: `2026-07-12`

## What Exists

- Project-scoped Claude files already exist at `CLAUDE.md`, `CLAUDE.local.md`, `.claude/settings.json`, and `.claude/settings.local.json`.
- The rules, hooks, commands, agents, skills, workflows, and memory surfaces are present under `.claude/`.
- Repo-local control-plane checks exist in `.claude/scripts/control_plane_check.py` and `.claude/scripts/rules_fidelity_check.py`.
- The control-plane guard hooks are wired in `.claude/settings.json` to `.claude/hooks/*.sh`.

## What Is Missing

- `.claude/state/` had no durable baseline scaffold before this turn.
- No `execution-manifest.json`, `baseline.md`, `completion-matrix.md`, or `ledger.md` existed under `.claude/state/`.
- The roadmap's Phase 0 durable-state pieces are not implemented yet, so session recovery, tool-call logging, and checkpoint replay remain unproven.
- The roadmap's Phase 5 bootstrap, Phase 6 measurement, and Phase 7 distribution flows are not present as executable repo assets.

## Global-State Check

No current repository file depends on `~/.claude/*` or other machine-global Claude state.

- The roadmap mentions `~/.claude/*` only as an anti-pattern to avoid.
- `.claude/settings.local.json` contains only project-local placeholders.
- `.mcp.json` points to the repo-local `graphiti-memory` server under `.claude/memory/`.

## Verification Baseline

| Command | Exit | Output |
|---|---:|---|
| `git rev-parse --show-toplevel; git status --short --branch; git branch --show-current; git rev-parse HEAD` | `0` | Repo root `C:/workspaces/CCSIF`; branch `main`; HEAD `e9358b553a9a05c16de00af28e35a9f29e5b16b1`; untracked roadmap/docs files already present before baseline scaffolding. |
| `Get-FileHash docs/claude-code-control-plane-roadmap-v2.md -Algorithm SHA256` | `0` | `7D6F35A16DEE91F0BD8B4DA98EA29F05CDC13003DF1C096BFA620C7610E08AE6` |
| `python3 .claude/scripts/control_plane_check.py` | `0` | `control-plane-check: PASS` |
| `python3 .claude/scripts/rules_fidelity_check.py` | `0` | `rules-fidelity-check: PASS` |
| `Get-Content -Raw .claude/state/execution-manifest.json | ConvertFrom-Json` plus roadmap link resolution | `0` | Manifest parsed; `.claude/state/execution-manifest.json`, `.claude/state/baseline.md`, `.claude/state/completion-matrix.md`, and `.claude/state/ledger.md` exist; `../../docs/claude-code-control-plane-roadmap-v2.md` resolves to the roadmap file. |

## Baseline Notes

- The repo already has a working project-scoped control-plane surface, but the durable state layer is still absent.
- This baseline intentionally stops at state scaffolding and documentation.
- The completion matrix records presence vs. proof separately so later work can move criteria from `missing` or `partial` to `existing`.
- Current `git status` remains dirty because the repo already had untracked `claude-code-control-plane-roadmap.md` and `docs/`, and this baseline added `.claude/state/`.

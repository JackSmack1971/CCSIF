---
paths:
  - ".claude/**"
  - "CLAUDE.md"
  - "CLAUDE.local.md"
  - "AGENTS.md"
  - "README.md"
  - "CONTRIBUTING.md"
  - "SECURITY.md"
  - ".github/**"
---

# Lifecycle Gates

Every non-trivial unit of work flows through five gates. Skip a gate
explicitly (state which and why) for trivial, single-file, reversible work;
never skip silently. See `docs/claude-code-control-plane-roadmap-v2.md`
Phase 5.2 for the source, `.claude/state/roadmap/` for phase evidence, and
the matching `.claude/commands/*.md` file for each gate's thin command
implementation.

| Gate | Input | Output | Durable artifact | Verification owner |
|---|---|---|---|---|
| 1. Align | Task request, open questions | Requirements, assumptions, constraints | `.claude/state/research/` note or ledger entry | Requester confirms scope |
| 2. Research | A question | Cited findings, no raw dumps | `.claude/state/research/<topic>.md` | Author cites sources |
| 3. Plan | Research + constraints | Atomic plan(s), explicit assumptions, verification target | `.claude/plans/` | Plan approver |
| 4. Build | One approved plan | Diff, commits | Ledger entry; builder summary in `.claude/state/agents/` | Builder self-checks, never self-certifies |
| 5. Verify & Ship | Plan + diff | Pass/fail re-derived independently, PR/checkpoint | `.claude/state/checkpoints/`; ledger entry | Verifier agent, never the builder |

Risk escalation: a gate whose change touches a Protected Area (`CLAUDE.md`
Protected Areas list) or is `risk: high` per `.claude/workflows/defs/`
requires a real verified Phase 0 checkpoint before advancing, per
`.claude/rules/dynamic-workflows.md`.

Cross-cutting, not gated: `/handoff` (session takeover doc in
`.claude/state/handoffs/`), `/status` (reconstruction from `.claude/state/`
alone), `/debug`, and `/experiment` (metric-gated keep/revert loop). Every
gate's verification step calls one adapter, `.claude/hooks/verify.sh` (or
`.ps1`), never a raw toolchain command directly.

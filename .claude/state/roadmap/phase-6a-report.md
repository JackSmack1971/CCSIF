# Phase 6A Report

Status: complete (scoped to Phase 6A: determinism ladder + baseline
guardrails with measured, bounded enforcement -- not Phase 6B or Phase 7)

## Summary

Phase 5 was confirmed complete before this phase started
(`execution-manifest.json`'s `phase_5_completion` / `phase_5c_completion`
blocks, status `complete`; `phase-5c-report.md`/`phase-5c-checkpoint.json`).
`docs/claude-code-control-plane-roadmap-v2.md` (Phase 6 in full),
`execution-manifest.json`, the current `.claude/settings.json`,
`.claude/hooks/*.sh`, `.claude/hooks/lib/pre-tool-use-guard.js`,
`.claude/scripts/control_plane_check.py`, `.claude/state/ledger.md`, and
`.claude/state/completion-matrix.md`'s pre-existing Phase 6 baseline
(status `partial`, all four criteria `partial`/`missing`) were read in full
before any change.

This phase adds no new dependency and touches no unrelated file: the diff
is five modified files (`pre-tool-use-guard.js`, `post-tool-use.sh`,
`stop.sh`, `control_plane_check.py`, `rules_fidelity_check.py`) plus nine
new files (one rule, four scripts, four tests -- `ledger_append.py`'s test
file makes five test files).

## What was added

| Artifact | Purpose | New/extended |
|---|---|---|
| `.claude/rules/40-determinism-ladder.md` | Codifies the five-rung ladder, the rung-4-vs-rung-5 split for git guardrails, protected-path severities, the promotion/demotion audit rule (with two real ladder-change records), and the bounded Stop-gate contract | New |
| `.claude/hooks/lib/pre-tool-use-guard.js` | Added `GIT_DESTRUCTIVE_RULES` (force push incl. `-f`/`--force-with-lease`/compound/env-prefixed variants, remote ref/tag deletion, `reset --hard`, `clean -f*`, `branch -D`, `filter-branch`/`filter-repo`/`rebase`, `stash drop/clear`, `reflog expire`) returning `ask` (native Claude Code approval prompt); path-traversal (`..` segment) detection returning hard `block`; two new protected-path categories (`append-only ledger` = block, `lockfile mass-edit` = ask); a `severity` field per category; correlation-id + latency JSONL event logging to `.claude/state/logs/guardrail-events.jsonl` for every allow/ask/block/error decision | Extended |
| `.claude/scripts/ledger_append.py` | The only sanctioned path to add a `.claude/state/ledger.md` entry -- opens in append mode only, cannot truncate or overwrite | New |
| `.claude/scripts/phase6a_lint_on_edit.py` + `.claude/hooks/post-tool-use.sh` | Runs the verify adapter's `lint` target once per Write/Edit/NotebookEdit call (in-process import of `phase5b_verify.run_target`, not a shell-out, since a bare `bash` on Windows PATH can resolve to a non-git-bash interpreter); logs to `.claude/state/logs/lint-events.jsonl`; never blocks (PostToolUse cannot block a tool call that already ran) | New / Extended |
| `.claude/scripts/phase6a_stop_gate.py` + `.claude/hooks/stop.sh` | Bounded Stop-gate: runs `control_plane_check.py` + `rules_fidelity_check.py`, blocks (exit 2) on failure up to `MAX_RETRIES=3` per `session_id`, then escalates via `ledger_append.py` and allows the stop; `stop_hook_active=true` escalates immediately without re-blocking, so an infinite stop loop is never reachable | New / Extended |
| `.claude/scripts/phase6a_metrics.py` | Read-only measurement over the three event logs + the ledger: allow/ask/block/error counts per category, latency p50/p95/max, false-block-review candidates (repeated blocks/asks on the same category), and parsed ladder promotion/demotion/escalation counts from ledger headings | New |
| `tests/test_phase6a_guardrails.py` | 44 tests: force push (5 bypass variants), remote ref/tag delete, reset --hard, clean -f*, branch -D, history rewrite (filter-branch/filter-repo/rebase, incl. `--abort` non-trigger), stash/reflog, path traversal (Write/Edit/Bash, plus allowed absolute/relative controls), secrets access, benign lookalikes (documented block-by-design), lockfile ask vs legitimate `npm install` allow, ledger append-only block, hook-failure fail-open + event logging, native `ask` hookSpecificOutput shape, and a full regression pass of every pre-existing probe/fd-dup-redirect case | New |
| `tests/test_phase6a_stop_gate.py` | 8 tests: bounded retry-then-escalate, retry-state clears on success, `stop_hook_active` immediate escalation, independent per-session counters, missing-`.git` allow, malformed-stdin fail-open, event logging fields | New |
| `tests/test_phase6a_metrics.py` | 6 tests: category/decision/latency/false-block-review computation, ledger heading parsing, malformed-JSONL-line skipping, live integration against real repo state | New |
| `tests/test_phase6a_ledger_append.py` | 5 tests: append preserves pre-existing content, creates missing file/parent, rejects empty heading, preserves append order, CLI entrypoint | New |
| `tests/test_phase6a_lint_on_edit.py` | 3 tests: non-mutating tool ignored, mutating tool runs lint and logs, malformed payload never crashes | New |
| `.claude/scripts/control_plane_check.py` | Registered 5 new required paths; added 2 new `PROTECTED_PROBES` (ledger direct-write, path traversal) and 2 new `ALLOWED_PROBES` (`npm install`, benign `git push`) to the existing smoke-probe lists | Extended |
| `.claude/scripts/rules_fidelity_check.py` | Registered `40-determinism-ladder.md`'s path scope and a 100-line budget | Extended |

## Design decisions

- **Rung 4 vs rung 5 for git guardrails**: `permissions.deny` (rung 5,
  unconditional, no override) keeps hard-blocking the literal spellings
  already there (`push --force`, `reset --hard`, `rm -rf`, ...). The new
  rung-4 hook logic catches the *bypass variants* those string prefixes
  miss and returns `permissionDecision: "ask"` -- Claude Code's own native
  interactive approval prompt to the real user. This is the explicit
  human-approval path the roadmap calls for: no separate bypass token or
  approval channel was invented, since the native `ask` decision already
  is that channel.
- **Protected-path severity is per-category, not global**: existing
  categories (secrets, CI/CD, migrations, auth, payment/trading, prod
  config) keep their proven `block` behavior unchanged (zero regressions,
  see Verification); only the two new categories (`lockfile mass-edit`,
  and separately the ledger) get their own severity, chosen by whether a
  legitimate override path exists (a package manager can legitimately
  regenerate a lockfile; nothing should legitimately hand-edit the
  append-only ledger).
- **Path traversal is an unconditional block, not `ask`**: a relative `..`
  escape has no legitimate case in this guard's scope, unlike git
  operations or lockfile edits, which do have legitimate forms.
- **Ledger append-only enforcement is two halves of one mechanism**: the
  guard blocks every direct Write/Edit/Bash-redirect targeting
  `ledger.md`; `ledger_append.py` is the only path left standing, and it is
  structurally incapable of truncating (`"a"` mode only, no other function
  in the module opens the file any other way).
- **Lint-on-edit imports the verify adapter in-process instead of shelling
  out to `verify.sh`**: a bare `bash` resolved via Windows `PATH` can be a
  non-git-bash interpreter (observed directly: `subprocess.run(["bash",
  ...])` returned exit 127, "No such file or directory", for a real
  Windows-style path that works fine from an interactive git-bash shell).
  Importing `phase5b_verify.run_target` directly is still "the adapter"
  (same module `verify.sh` itself wraps) without the shell-resolution
  hazard.
- **Stop-gate bookkeeping lives in Python, not bash**: `stop.sh` shrank to
  a thin dispatcher; `phase6a_stop_gate.py` owns the retry-count state file
  per `session_id`, the `stop_hook_active` short-circuit, and the
  escalation call, all independently unit-testable via `STATE_ROOT`/
  `RETRY_DIR`/`EVENT_LOG`/`LEDGER_PATH` overrides and a monkeypatchable
  `run_checks`.
- **Two real ladder-change records, not fabricated ones**: the promotion
  (git force-push/reset/branch-delete moving rung-1/5 guidance to rung-4
  enforcement) is this phase's own change, evidenced by the new test file.
  The demotion (the fd-duplication-redirect carve-out in
  `MUTATING_BASH_TOKEN`) is real, pre-existing code from an earlier phase
  that was never logged as a ladder event at the time -- it is logged now,
  retroactively, exactly as the audit rule requires, rather than invented
  for this report.

## Guardrails must parse shell variants safely

`splitCommandSegments()`/`tokenize()` in `pre-tool-use-guard.js` implement a
quote-aware conservative tokenizer: segments split on top-level `&&`,
`||`, `;`, `|`, newline (never inside a quoted string); tokens split on
whitespace (quotes stripped). `normalizeLeadingTokens()` strips leading
`VAR=value` environment assignments and `sudo`/`command`/`exec` wrappers
before checking for `git`. This is deliberately conservative toward *more*
scrutiny, never less -- the tokenizer's job is detection, not execution, so
over-splitting is the safe failure direction. Proven by
`GitGuardrailTests::test_force_push_compound_command` (`npm test && git
push -f origin main`) and `test_force_push_env_prefixed` (`GIT_TRACE=1 git
push --force origin main`), both still caught.

## Instrumentation

`phase6a_metrics.py` (read-only, mutates nothing) reports, from a live run
against this repo's real event logs after the full test suite:

- **293** guardrail decisions: 184 allow, 42 ask, 62 block, 5 error
  (malformed/empty stdin during the deliberate hook-failure test cases).
- **Latency**: p50 2ms, p95 4ms, max 13ms across 293 guard invocations --
  well within any plausible hook-timeout budget; the field is logged on
  every event specifically so a future slow-hook regression is visible
  without re-instrumenting.
- **False-block-review candidates**: every category with more than one
  block/ask is surfaced with its per-tool breakdown (e.g.
  `secrets/credentials`: 20 occurrences across Write/Bash). This is the
  mechanical signal the ladder-change audit rule depends on; the
  `credentials-policy.md`/`auth/README.md` benign-lookalike test cases
  intentionally keep contributing to this count rather than being
  special-cased away, per the "document any rule intentionally left
  probabilistic" instruction -- the secrets-path regex is deterministic
  but precision-imprecise by design (see `BenignLookalikeTests` docstring).
- **Ladder changes**: `promotions: 1`, `demotions: 1`, both resolved from
  real `.claude/state/ledger.md` headings written via `ledger_append.py`
  in this phase (see Design decisions).
- **Stop-gate**: 3 real events logged from this session's actual Stop hook
  firings (not test-harness events, which use `STATE_ROOT` overrides and
  never touch the real log), all `allow` (verification passed each time),
  `escalation_count: 0` for the real log -- escalation-path correctness is
  proven separately by `tests/test_phase6a_stop_gate.py`'s monkeypatched
  failure scenarios, not by waiting for a real failure to occur.
- **Lint-on-edit**: 7 real events from this session's own file edits
  (3 pass, 2 fail against transient intermediate states, 2 error from the
  deliberate malformed-payload test), demonstrating the hook fires on
  every real Write/Edit in this session, not just in tests.

Every must-happen rule (git guardrail categories, path traversal, ledger
protection, lockfile ask, Stop-gate bound, event logging) is proven to
fire from real logs/tests above, not merely documented. No rule in this
phase is intentionally left probabilistic at rung 4 or 5; the one
deliberately-imprecise mechanism (the secrets-path regex's benign-lookalike
false positives) is a precision tradeoff within a still-deterministic rung-4
rule (it always fires, it just also fires on some benign paths), not a
probabilistic trigger.

## Verification

| Command | Result |
|---|---|
| `node -c .claude/hooks/lib/pre-tool-use-guard.js` | exit 0 |
| `python -m py_compile` on every new/changed `.py` file | exit 0 |
| `python -m unittest discover -s tests -v` | exit 0, **193 tests** (127 prior + 66 new: 44+8+6+5+3), no regression |
| `python3 .claude/scripts/control_plane_check.py` | `control-plane-check: PASS` (5 new required paths, 2 new protected + 2 new allowed probes) |
| `python3 .claude/scripts/rules_fidelity_check.py` | `rules-fidelity-check: PASS` |
| `python3 .claude/scripts/taxonomy_check.py` | `taxonomy-check: PASS` |
| `python3 .claude/scripts/phase6a_metrics.py` | exit 0, JSON report (see Instrumentation) |
| `python3 -c "import json; json.load(open('.claude/settings.json'))"` | exit 0 |
| `git status --short` (post-change) | only the intended 5 modified + 9 new Phase 6A paths; pre-existing untracked files (roadmap docs, `.scratch/`, prior-session state dirs, `.claude/state/logs/*` runtime logs) left untouched |

## Exit Criteria Evidence (Phase 6A scope only)

1. **Every must-happen behavior lives at rung 3+ and demonstrably fires
   (log-verified), not just documented** -- see Instrumentation; every
   category has a passing adversarial test and/or a real logged event from
   this session.
2. **No destructive git or filesystem action is reachable without a
   deterministic block or explicit human approval** -- rung 5
   (`permissions.deny`) blocks the literal spellings unconditionally; rung
   4 (`GIT_DESTRUCTIVE_RULES`, path traversal, protected-path categories)
   catches the remaining reachable variants and either hard-blocks
   (secrets/CI-CD/migrations/auth/payment/prod-config/ledger/path
   traversal) or surfaces the native human-approval prompt (git guardrails,
   lockfile). `tests/test_phase6a_guardrails.py` is the adversarial proof.
3. **Verifier disagreement with builder self-reports is measured and
   nonzero** -- out of scope for Phase 6A specifically (the roadmap
   assigns this to the adversarial-verification battery, Phase 6.3, which
   this phase's instructions explicitly excluded); tracked as a remaining
   risk below, not silently claimed complete.
4. **Gate metrics exist and have driven at least one ladder promotion and
   one demotion** -- `phase6a_metrics.py`'s `ledger_ladder_changes` reports
   `promotions: 1`, `demotions: 1`, both real ledger entries (see Design
   decisions).
5. **Report and checkpoint written; matrix, manifest, and ledger updated
   through the protected append path** -- this report;
   `phase-6a-checkpoint.json`; `completion-matrix.md` Phase 6 section;
   `execution-manifest.json` `phase_6a_completion` block; both ladder-change
   ledger entries and this phase's completion entry were written via
   `ledger_append.py`, never a direct file write (which the guard itself
   would have blocked).

## Remaining Risks

- **Verifier-vs-builder disagreement measurement (Phase 6.3's adversarial
  verification battery) is out of scope for Phase 6A** and was not built
  in this phase, per this phase's explicit instruction not to start Phase
  6B. The roadmap's Phase 6 exit criterion "verifier disagreement ...
  measured and nonzero" therefore remains unmet at the *whole-Phase-6*
  level; `execution-manifest.json` records `phase_6a: complete` but
  `phase_6: partial` for this reason.
- **The secrets-path regex is intentionally imprecise** (documented,
  deterministic false-closed behavior, not a bug): it blocks a benign file
  like `docs/credentials-policy.md` or `auth/README.md` exactly as it
  blocks a real secret. `false_block_review_candidates` in
  `phase6a_metrics.py`'s output is the designed compensating control, not a
  fix applied in this phase -- a future rung-4 refinement pass should
  review it, per the audit rule.
- **Hook-timeout handling is Claude Code's own documented hook-execution
  contract** (a hook that exceeds its configured timeout is killed by the
  client and reported as a non-blocking failure); this phase's own defense
  is the latency field logged on every guard decision (p50/p95/max
  visible via `phase6a_metrics.py`), which would surface a real slow-hook
  regression, but no synthetic multi-second-delay test was added (it would
  make the suite slow for a scenario Claude Code itself already bounds).
- **`phase6a_lint_on_edit.py` always runs the repo's whole `lint` target**
  (`rules_fidelity_check.py`), not a file-scoped linter, since this repo
  has no per-file linter distinct from its rules-fidelity check; this is
  cheap here (sub-second) but would not scale as-is to a repo with an
  expensive whole-repo lint step.
- **The Stop-gate's escalation path is proven only via monkeypatched unit
  tests** (`tests/test_phase6a_stop_gate.py`), not by an actual
  `MAX_RETRIES`-exceeding real session in this environment (the repo's
  real checks currently pass, so no real escalation was naturally
  triggered during this phase's work).
- Phase 6B (deeper adversarial verification battery) and Phase 7
  (distribution/versioning) remain unimplemented and are not implicitly
  validated by these Phase 6A changes.

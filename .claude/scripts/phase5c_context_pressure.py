#!/usr/bin/env python3
"""Phase 5C main-thread context-pressure proxy.

Live token metering is not available in this environment, so this is the
documented, reproducible proxy the roadmap explicitly allows: measure what
the main thread would have to hold for a multi-plan scenario under the
dispatcher-load model this control plane actually uses, versus the naive
alternative of inlining full plan/build detail into the main thread instead
of dispatching to fresh subagent contexts.

Two numbers, both reproducible from repo state:

1. Always-loaded instruction budget (unconditional context on every turn):
   reuses `taxonomy_check.check_always_loaded_context_budget`'s own
   measurement -- CLAUDE.md + `paths: ["**/*"]` rules -- already gated at
   400 lines and currently ~140/400 (35%).
2. Multi-plan dispatcher-load proxy: build N atomic plans (bootstrap-sized
   fixture), estimate character count for (a) what `/status` actually
   returns to the main thread (plan_id/title/status/task-count only, per
   `reconstruct_status()`), versus (b) what the main thread would hold if
   it inlined each plan's full task/assumption/verification detail instead
   of dispatching each `/build` to a fresh subagent context (per
   `.claude/commands/build.md` + `builder.md`'s `isolation: worktree`).
   Token estimate uses the conservative 4-chars-per-token heuristic.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

import taxonomy_check  # noqa: E402
import bootstrap_control_plane as bcp  # noqa: E402

CHARS_PER_TOKEN = 4
PLAN_COUNT = 10


def _build_multi_plan_fixture(target: Path) -> list[dict]:
    bcp.scaffold_tree(target)
    sys.path.insert(0, str(target / ".claude" / "scripts"))
    for mod in ("lifecycle", "common"):
        sys.modules.pop(mod, None)
    import lifecycle  # noqa: E402

    plans = []
    for i in range(PLAN_COUNT):
        plan = lifecycle.create_plan(
            title=f"Plan {i}: implement feature slice {i}",
            assumptions=[f"Assumption {i}a: upstream contract is stable.", f"Assumption {i}b: no schema change required."],
            tasks=[
                {
                    "task_id": f"t{i}-1",
                    "description": f"Implement feature slice {i} across the relevant module boundary, " * 3,
                    "verification": {"target": "test"},
                    "commit_boundary": True,
                },
                {
                    "task_id": f"t{i}-2",
                    "description": f"Add regression coverage for feature slice {i}. " * 3,
                    "verification": {"target": "test"},
                    "commit_boundary": True,
                },
            ],
            workspace=target,
        )
        plans.append(plan)
    return plans


def measure() -> dict:
    always_loaded_lines = 0
    parts = []
    claude_md = REPO_ROOT / "CLAUDE.md"
    if claude_md.is_file():
        n = len(claude_md.read_text(encoding="utf-8").splitlines())
        always_loaded_lines += n
        parts.append(f"CLAUDE.md={n}")
    rules_dir = REPO_ROOT / ".claude" / "rules"
    for path in sorted(rules_dir.glob("*.md")):
        if path.name in taxonomy_check.SKIP_NAMES:
            continue
        text = path.read_text(encoding="utf-8")
        if "**/*" in taxonomy_check.parse_rule_paths(text):
            n = len(text.splitlines())
            always_loaded_lines += n
            parts.append(f"{path.name}={n}")
    budget = taxonomy_check.ALWAYS_LOADED_MAX_LINES
    always_loaded_pct = round(100 * always_loaded_lines / budget, 1)

    with tempfile.TemporaryDirectory(prefix="phase5c-context-pressure-") as tmp:
        target = Path(tmp)
        plans = _build_multi_plan_fixture(target)

        sys.path.insert(0, str(target / ".claude" / "scripts"))
        for mod in ("lifecycle",):
            sys.modules.pop(mod, None)
        import lifecycle  # noqa: E402

        status = lifecycle.reconstruct_status(root=target / ".claude" / "state", workspace=target)
        dispatcher_load_chars = len(json.dumps(status, sort_keys=True))

        inlined_chars = sum(len(json.dumps(p, sort_keys=True)) for p in plans)

    dispatcher_tokens = dispatcher_load_chars / CHARS_PER_TOKEN
    inlined_tokens = inlined_chars / CHARS_PER_TOKEN
    ratio_pct = round(100 * dispatcher_tokens / inlined_tokens, 1) if inlined_tokens else 0.0

    return {
        "kind": "phase5c-context-pressure-proxy",
        "method": "documented reproducible proxy (no live token metering available in this environment)",
        "always_loaded_instruction_budget": {
            "measured_lines": always_loaded_lines,
            "budget_lines": budget,
            "pct_of_budget": always_loaded_pct,
            "parts": parts,
        },
        "multi_plan_dispatcher_load_proxy": {
            "plan_count": PLAN_COUNT,
            "dispatcher_status_call_chars": dispatcher_load_chars,
            "dispatcher_status_call_tokens_est": round(dispatcher_tokens),
            "naive_inline_all_plans_chars": inlined_chars,
            "naive_inline_all_plans_tokens_est": round(inlined_tokens),
            "dispatcher_load_as_pct_of_naive_inline": ratio_pct,
            "roadmap_target_pct": 50.0,
            "within_target": ratio_pct < 50.0,
            "note": (
                "Building happens in a fresh subagent context per plan "
                "(builder.md: isolation: worktree); the main thread only "
                "ever holds the compact /status summary shown here, never "
                "each plan's full task/assumption detail."
            ),
        },
    }


def main() -> int:
    result = measure()
    out_path = REPO_ROOT / ".claude" / "state" / "roadmap" / "phase-5c-context-pressure-evidence.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

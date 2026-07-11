#!/usr/bin/env python3
"""
evolve.py — Phase 6b. The self-modification applier.

The meta-auditor subagent PROPOSES improvements as a JSON patch file
(runs/<id>/evolution_patch.json). This script APPLIES them deterministically,
bounded to safe surfaces only:

  1. Learned-directive blocks inside .claude/agents/*-auditor.md
     (only between the LEARNED-DIRECTIVES markers — the rubric/core prompt
     is never touched by the machine).
  2. calibration.json fields: axis_weights, escalation_threshold,
     learned_directives.
  3. An improvement changelog (.7axes/improvements.log.md) so every
     self-modification is auditable and revertable via git.

Separation of propose (model) from apply (deterministic, bounded) is what
keeps a self-modifying workflow safe: the model can't rewrite its own
guardrails, and every mutation is a reviewable git diff.

Patch schema (all keys optional):
{
  "directives":        {"<axis>": ["new directive", ...]},
  "axis_weight_deltas":{"<axis>": +0.1},          # clamped to [0.5, 2.0]
  "escalation_threshold": 3,                       # clamped to [1, 5]
  "retire_directives": {"<axis>": ["substring to remove"]},
  "notes": "why these changes"
}
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib7axes import (ALL_AXES, STATE_DIR, load_calibration, now_iso,
                      run_dir, save_calibration)

AGENTS_DIR = Path(".claude/agents")
BEGIN = "<!-- LEARNED-DIRECTIVES:BEGIN (machine-managed — edit via evolve.py) -->"
END = "<!-- LEARNED-DIRECTIVES:END -->"
MAX_DIRECTIVES_PER_AXIS = 12  # bounded memory: oldest directives age out
LOG = STATE_DIR / "improvements.log.md"


def rewrite_agent_block(axis: str, directives: list):
    p = AGENTS_DIR / f"{axis.replace('_', '-')}-auditor.md"
    if not p.exists():
        return False
    # surrogateescape round-trips any isolated non-UTF-8 byte losslessly instead of
    # mis-decoding the whole file under a single-byte fallback encoding (which would
    # corrupt every other valid multi-byte UTF-8 sequence elsewhere in the file).
    text = p.read_text(encoding="utf-8", errors="surrogateescape")
    block = "\n".join([BEGIN] + [f"- {d}" for d in directives] + [END])
    if BEGIN in text and END in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block,
                      text, flags=re.DOTALL)
    else:
        text = text.rstrip() + "\n\n## Learned Directives (from prior runs)\n" + block + "\n"
    p.write_text(text, encoding="utf-8", errors="surrogateescape")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    args = ap.parse_args()

    patch_p = run_dir(args.run) / "evolution_patch.json"
    if not patch_p.exists():
        print(json.dumps({"applied": False, "reason": "no evolution_patch.json for this run"}))
        return
    patch = json.loads(patch_p.read_text())
    cal = load_calibration()
    log_lines = [f"\n## Run {args.run} — {now_iso()}",
                 f"> {patch.get('notes', 'no rationale provided')}"]

    # 1. directives (add + retire, capped)
    for axis, subs in (patch.get("retire_directives") or {}).items():
        if axis in ALL_AXES:
            before = cal["learned_directives"].get(axis, [])
            cal["learned_directives"][axis] = [
                d for d in before if not any(s.lower() in d.lower() for s in subs)]
            removed = len(before) - len(cal["learned_directives"][axis])
            if removed:
                log_lines.append(f"- retired {removed} directive(s) on `{axis}`")

    for axis, new in (patch.get("directives") or {}).items():
        if axis not in ALL_AXES:
            continue
        cur = cal["learned_directives"].setdefault(axis, [])
        for d in new:
            d = str(d).strip()
            if d and d not in cur:
                cur.append(f"[{args.run}] {d}")
                log_lines.append(f"- `{axis}` += \"{d[:100]}\"")
        cal["learned_directives"][axis] = cur[-MAX_DIRECTIVES_PER_AXIS:]

    # 2. weights (clamped)
    for axis, delta in (patch.get("axis_weight_deltas") or {}).items():
        if axis in ALL_AXES and isinstance(delta, (int, float)):
            w = cal["axis_weights"].get(axis, 1.0) + float(delta)
            cal["axis_weights"][axis] = round(min(2.0, max(0.5, w)), 2)
            log_lines.append(f"- weight `{axis}` → {cal['axis_weights'][axis]}")

    # 3. escalation threshold (clamped)
    if isinstance(patch.get("escalation_threshold"), int):
        cal["escalation_threshold"] = min(5, max(1, patch["escalation_threshold"]))
        log_lines.append(f"- escalation_threshold → {cal['escalation_threshold']}")

    save_calibration(cal)

    # 4. project the directive state into the agent prompt files
    touched = [axis for axis in ALL_AXES
               if rewrite_agent_block(axis, cal["learned_directives"].get(axis, []))]

    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write("\n".join(log_lines) + "\n")

    print(json.dumps({"applied": True, "agents_updated": touched,
                      "log": str(LOG)}, indent=2))


if __name__ == "__main__":
    main()

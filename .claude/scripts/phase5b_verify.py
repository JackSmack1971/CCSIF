#!/usr/bin/env python3
"""Phase 5B code-agnostic verification adapter.

The control plane must not hard-code a language or toolchain into any skill
or command. Instead every gate calls this one adapter, which derives its
targets from the repo's own `CLAUDE.md` "## Source-of-Truth Commands" fenced
block (`# label` comment lines above each command) rather than guessing a
stack. Add or change a project's real verification commands in `CLAUDE.md`;
this script never needs to change to support a new language.

Targets:
  full            every parsed source-of-truth command
  lint            parsed commands whose label matches lint/rule/format
  test            parsed commands whose label matches test (supports
                   --pattern, appended as `-k <pattern>` to any command
                   containing "unittest discover", for focused runs)
  <label-slug>    any individually parsed command, addressable directly
                   (e.g. "control-plane", "rules", "memory-tests")
  rubric|citation|factcheck
                  non-code verifiers. No deterministic shell check exists
                  for model-judged review, so these print the relevant
                  protocol pointer and exit 2 rather than fabricating a
                  pass/fail signal.

Exit codes (always deterministic):
  0  every selected command exited 0
  1  at least one selected command exited non-zero
  2  target unavailable: no command matched, CLAUDE.md source-of-truth
     block is missing/unparseable, or a non-code verifier was requested
     (deferred to model judgment by design, not a shell-checkable result)
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

HEADING = "## Source-of-Truth Commands"
LABEL_RE = re.compile(r"^#\s*(.+)$")
LINT_LABEL_RE = re.compile(r"lint|rule|format", re.IGNORECASE)
TEST_LABEL_RE = re.compile(r"test", re.IGNORECASE)
NON_CODE_MODES = {
    "rubric": (
        "Rubric verifier: no shell check exists for model-judged review. "
        "Use the fsv-verify skill's PRE/ACT/POST/DIFF protocol against the "
        "task's stated acceptance criteria, scored explicitly per criterion."
    ),
    "citation": (
        "Citation verifier: no shell check exists for source-grounding "
        "review. Use the research skill's completion gate: every claim "
        "must cite the primary source it was verified against."
    ),
    "factcheck": (
        "Fact-check verifier: no shell check exists for factual accuracy "
        "review. Cross-check each claim against its primary source and "
        "record any discrepancy explicitly, per the research skill."
    ),
}


class VerifyAdapterError(RuntimeError):
    pass


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")


def parse_source_of_truth(claude_md: Path) -> list[dict[str, str]]:
    if not claude_md.is_file():
        raise VerifyAdapterError(f"no CLAUDE.md at {claude_md}")
    lines = claude_md.read_text(encoding="utf-8").splitlines()
    try:
        heading_index = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
    except StopIteration as exc:
        raise VerifyAdapterError(f"CLAUDE.md has no {HEADING!r} section") from exc

    fence_start = None
    for i in range(heading_index + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            fence_start = i
            break
        if stripped.startswith("## "):
            break
    if fence_start is None:
        raise VerifyAdapterError(f"no fenced command block found under {HEADING!r}")

    entries: list[dict[str, str]] = []
    pending_label: str | None = None
    for line in lines[fence_start + 1 :]:
        if line.strip().startswith("```"):
            break
        stripped = line.strip()
        if not stripped:
            continue
        label_match = LABEL_RE.match(stripped)
        if label_match:
            pending_label = label_match.group(1).strip()
            continue
        label = pending_label or stripped
        entries.append({"label": label, "slug": slugify(label), "command": stripped})
        pending_label = None
    if not entries:
        raise VerifyAdapterError(f"{HEADING!r} fenced block has no commands")
    return entries


def resolve_targets(entries: list[dict[str, str]], target: str) -> list[dict[str, str]]:
    if target == "full":
        return list(entries)
    if target == "lint":
        return [e for e in entries if LINT_LABEL_RE.search(e["label"])]
    if target == "test":
        return [e for e in entries if TEST_LABEL_RE.search(e["label"])]
    return [e for e in entries if e["slug"] == target]


def _augment_command(command: str, *, pattern: str | None) -> str:
    if pattern and "unittest discover" in command:
        return f"{command} -k {shlex.quote(pattern)}"
    return command


def run_target(
    target: str,
    *,
    claude_md: Path | None = None,
    pattern: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    claude_md = claude_md or (ROOT / "CLAUDE.md")
    cwd = cwd or claude_md.parent

    if target in NON_CODE_MODES:
        return {
            "target": target,
            "exit_code": 2,
            "status": "unavailable",
            "message": NON_CODE_MODES[target],
            "commands": [],
        }

    entries = parse_source_of_truth(claude_md)
    selected = resolve_targets(entries, target)
    if not selected:
        return {
            "target": target,
            "exit_code": 2,
            "status": "unavailable",
            "message": f"no source-of-truth command matched target {target!r}",
            "commands": [e["slug"] for e in entries],
        }

    results = []
    overall = 0
    for entry in selected:
        command = _augment_command(entry["command"], pattern=pattern)
        proc = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if proc.returncode != 0:
            overall = 1
        results.append(
            {
                "label": entry["label"],
                "slug": entry["slug"],
                "command": command,
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
    return {
        "target": target,
        "exit_code": overall,
        "status": "pass" if overall == 0 else "fail",
        "message": None,
        "commands": results,
    }


def list_targets(claude_md: Path | None = None) -> dict[str, Any]:
    claude_md = claude_md or (ROOT / "CLAUDE.md")
    entries = parse_source_of_truth(claude_md)
    return {
        "aggregate_targets": ["full", "lint", "test"],
        "non_code_targets": sorted(NON_CODE_MODES),
        "individual_targets": [e["slug"] for e in entries],
    }


def command_run(args: argparse.Namespace) -> int:
    result = run_target(
        args.target,
        claude_md=Path(args.claude_md) if args.claude_md else None,
        pattern=args.pattern,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["exit_code"])


def command_list_targets(args: argparse.Namespace) -> int:
    try:
        payload = list_targets(claude_md=Path(args.claude_md) if args.claude_md else None)
    except VerifyAdapterError as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phase5b_verify")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run")
    p.add_argument("target")
    p.add_argument("--pattern", help="focused-test filter appended as -k <pattern> to unittest discover commands")
    p.add_argument("--claude-md")
    p.set_defaults(func=command_run)

    p = sub.add_parser("list-targets")
    p.add_argument("--claude-md")
    p.set_defaults(func=command_list_targets)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except VerifyAdapterError as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

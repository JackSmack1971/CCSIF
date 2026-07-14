#!/usr/bin/env python3
"""Phase 5B code-agnostic verification adapter."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from verification_manifest import (  # noqa: E402
    VerifyAdapterError,
    list_targets,
    manifest_digest,
    manifest_path,
    parse_manifest,
    resolve_targets,
    run_target,
    slugify,
)


def command_run(args: argparse.Namespace) -> int:
    result = run_target(
        args.target,
        manifest=Path(args.manifest) if args.manifest else None,
        pattern=args.pattern,
        cwd=Path(args.cwd) if args.cwd else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["exit_code"])


def command_list_targets(args: argparse.Namespace) -> int:
    try:
        payload = list_targets(manifest=Path(args.manifest) if args.manifest else None)
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
    p.add_argument("--manifest")
    p.add_argument("--cwd")
    p.set_defaults(func=command_run)

    p = sub.add_parser("list-targets")
    p.add_argument("--manifest")
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


__all__ = [
    "VerifyAdapterError",
    "list_targets",
    "manifest_digest",
    "manifest_path",
    "parse_manifest",
    "resolve_targets",
    "run_target",
    "slugify",
    "main",
]

#!/usr/bin/env python3
"""Append-only writer for `.claude/state/ledger.md` (Phase 6A rung 4/5).

`pre-tool-use-guard.js` blocks every direct Write/Edit/Bash-redirect
targeting `ledger.md`, so this script is the only sanctioned path to add a
new entry. It only ever opens the file in append mode -- there is no
function here that can truncate, overwrite, or delete a byte that is
already on disk.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = ROOT / ".claude" / "state" / "ledger.md"


class LedgerAppendError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_entry(heading: str, body: str, *, ledger_path: Path = DEFAULT_LEDGER) -> str:
    if not heading.strip():
        raise LedgerAppendError("heading must not be empty")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    block = f"\n## {heading.strip()} ({now()})\n\n{body.strip()}\n"
    # 'a' mode: POSIX/Windows both guarantee this never truncates existing
    # content; a new file is created only if none exists yet.
    with ledger_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(block)
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heading", required=True, help="Section heading (without the leading ##)")
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body", help="Markdown body for the entry")
    body_group.add_argument("--body-file", help="Path to a file containing the Markdown body")
    parser.add_argument("--ledger-path", default=str(DEFAULT_LEDGER))
    args = parser.parse_args(argv)

    body = args.body if args.body is not None else Path(args.body_file).read_text(encoding="utf-8")

    try:
        append_entry(args.heading, body, ledger_path=Path(args.ledger_path))
    except LedgerAppendError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("ledger-append: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create a JSON snapshot of file hashes for FSV pre/post comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--glob", default="**/*")
    args = parser.parse_args()

    root = Path(args.root)
    snapshot = {}
    for path in sorted(root.glob(args.glob)):
        if path.is_file() and ".git" not in path.parts:
            snapshot[str(path.relative_to(root))] = digest(path)

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

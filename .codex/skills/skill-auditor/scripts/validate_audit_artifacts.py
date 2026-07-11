#!/usr/bin/env python3
"""Validate skill-auditor output artifacts and enforce commit gates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate skill audit artifacts.")
    parser.add_argument("--audit", required=True, help="Audit JSON path.")
    parser.add_argument("--max-high", type=int, default=0, help="Maximum allowed high findings.")
    parser.add_argument("--require-markdown", default=None, help="Markdown report path that must exist.")
    args = parser.parse_args(argv)

    audit_path = Path(args.audit)
    if not audit_path.exists():
        print(f"ERROR audit file not found: {audit_path}", file=sys.stderr)
        return 3
    try:
        report = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR audit JSON parse failed: {exc}", file=sys.stderr)
        return 3
    if report.get("schema_version") != "1.0":
        print("ERROR unsupported or missing schema_version", file=sys.stderr)
        return 3
    summary = report.get("summary", {})
    if summary.get("skills_audited", 0) < 1:
        print("ERROR no skills audited", file=sys.stderr)
        return 3
    high = summary.get("findings_by_severity", {}).get("high", 0)
    if high > args.max_high:
        print(f"ERROR high findings {high} exceeds max {args.max_high}", file=sys.stderr)
        return 2
    if args.require_markdown:
        md = Path(args.require_markdown)
        if not md.exists() or not md.read_text(encoding="utf-8", errors="replace").strip():
            print(f"ERROR markdown report missing or empty: {md}", file=sys.stderr)
            return 3
    print(json.dumps({
        "status": "ok",
        "skills_audited": summary.get("skills_audited"),
        "corpus_score": summary.get("corpus_score"),
        "high_findings": high,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

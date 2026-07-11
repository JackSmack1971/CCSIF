#!/usr/bin/env python3
"""Deterministically score and rank UX feature candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WEIGHTS = {
    "user_pain": 25,
    "frequency_or_reach": 15,
    "ux_leverage": 20,
    "strategic_fit": 15,
    "evidence_confidence": 10,
    "implementation_feasibility": 10,
    "differentiation": 5,
}


def fail(message: str, code: int, as_json: bool) -> int:
    payload = {"status": "error", "error": message, "exit_code": code}
    print(json.dumps(payload, separators=(",", ":")) if as_json else f"ERROR: {message}")
    return code


def score_candidate(candidate: dict[str, Any]) -> float:
    scores = candidate.get("scores")
    if not isinstance(scores, dict):
        raise ValueError(f"{candidate.get('id', '<unknown>')}: scores must be an object")

    total = 0.0
    for key, weight in WEIGHTS.items():
        value = scores.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{candidate.get('id', '<unknown>')}: {key} must be numeric")
        if not 0 <= float(value) <= 5:
            raise ValueError(f"{candidate.get('id', '<unknown>')}: {key} must be between 0 and 5")
        total += (float(value) / 5.0) * weight

    penalty = candidate.get("risk_penalty", 0)
    if not isinstance(penalty, (int, float)) or isinstance(penalty, bool) or not 0 <= float(penalty) <= 15:
        raise ValueError(f"{candidate.get('id', '<unknown>')}: risk_penalty must be between 0 and 15")

    return round(max(0.0, total - float(penalty)), 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON file containing an array or {'candidates': [...]} object")
    parser.add_argument("--write", action="store_true", help="Write total_score values back to the input file")
    parser.add_argument("--json", action="store_true", help="Emit compact machine-readable JSON")
    args = parser.parse_args()

    if not args.input.is_file():
        return fail(f"input file not found: {args.input}", 2, args.json)

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        return fail(f"cannot read input: {exc}", 2, args.json)
    except json.JSONDecodeError as exc:
        return fail(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", 3, args.json)

    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict) and isinstance(data.get("candidates"), list):
        candidates = data["candidates"]
    elif isinstance(data, dict) and isinstance(data.get("decision"), dict):
        candidates = data["decision"].get("candidates")
    else:
        candidates = None
    if not isinstance(candidates, list) or not candidates:
        return fail("input must contain a non-empty candidates array", 4, args.json)

    try:
        ranked = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("each candidate must be an object")
            candidate_id = candidate.get("id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError("each candidate requires a non-empty id")
            total = score_candidate(candidate)
            candidate["total_score"] = total
            ranked.append({"id": candidate_id, "title": candidate.get("title", ""), "total_score": total})
    except ValueError as exc:
        return fail(str(exc), 4, args.json)

    ranked.sort(key=lambda item: (-item["total_score"], item["id"]))

    if args.write:
        try:
            args.input.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as exc:
            return fail(f"cannot write input: {exc}", 5, args.json)

    payload = {"status": "ok", "ranked": ranked}
    if args.json:
        print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    else:
        for index, item in enumerate(ranked, start=1):
            print(f"{index}. {item['id']} | {item['total_score']:.1f} | {item['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

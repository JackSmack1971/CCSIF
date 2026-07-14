#!/usr/bin/env python3
"""Phase 5B code-agnostic verification adapter.

The control plane must not hard-code a language or toolchain into any skill
or command. Every gate calls this one adapter, which reads its targets from
the repository-owned, versioned verification manifest
(`.claude/verification.json`) — a machine-readable JSON file whose commands
are argv arrays executed with ``shell=False``. The manifest replaces the
former free-text parsing of `CLAUDE.md`'s "## Source-of-Truth Commands"
fenced block as the executable source of truth; that Markdown block remains
the human-readable documentation of the same commands.

Safety contract (fail-closed, exit 2 on violation, no subprocess spawned):
  - strict schema validation (`schema_version`, argv arrays, unique ids)
  - executable allowlist: argv[0] must be an allowlisted interpreter or
    resolve inside the repository
  - repository containment for path-shaped argv elements (no `..`, no
    absolute escapes)
  - shell metacharacters (`;`, `&`, `|`, `>`, `<`, backtick, `$(`,
    newline) are rejected in every argv element, so a compound shell
    command cannot be smuggled through an interpreter's `-c` argument

Targets:
  full            every manifest target
  lint            targets whose label matches lint/rule/format
  test            targets whose label matches test (supports --pattern,
                  appended as `-k <pattern>` to unittest-discover argv)
  <id>            any individual manifest target, addressable directly
                  (e.g. "control-plane", "rules", "memory-tests")
  rubric|citation|factcheck
                  non-code verifiers. No deterministic shell check exists
                  for model-judged review, so these print the relevant
                  protocol pointer and exit 2 rather than fabricating a
                  pass/fail signal.

Exit codes (always deterministic):
  0  every selected command exited 0
  1  at least one selected command exited non-zero; a pending triage record is
     written and the same target cannot be retried blindly
  2  target unavailable: no target matched, manifest missing/invalid, pending
     failure triage is missing/invalid, or a non-code verifier was requested
     (deferred to model judgment by design)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

MANIFEST_RELPATH = Path(".claude") / "verification.json"
SCHEMA_VERSION = 1
ALLOWED_TOP_LEVEL_KEYS = {"schema_version", "description", "targets"}
ALLOWED_TARGET_KEYS = {"id", "label", "command"}
ALLOWED_EXECUTABLES = ("python3", "python", "node", "bash")
FORBIDDEN_SUBSTRINGS = (";", "&", "|", ">", "<", "`", "$(", "\n", "\r")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
LINT_LABEL_RE = re.compile(r"lint|rule|format", re.IGNORECASE)
TEST_LABEL_RE = re.compile(r"test", re.IGNORECASE)
TRIAGE_CLASSIFICATIONS = {
    "implementation bug",
    "flaky/environmental issue",
    "missing dependency",
    "test defect",
    "unclear",
}

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


def _manifest_root(manifest: Path) -> Path:
    # <root>/.claude/verification.json -> <root>
    return manifest.resolve().parent.parent


def _reject_metacharacters(element: str, *, target_id: str) -> None:
    for token in FORBIDDEN_SUBSTRINGS:
        if token in element:
            raise VerifyAdapterError(
                f"target {target_id!r}: argv element {element!r} contains "
                f"forbidden shell metacharacter {token!r}"
            )


def _looks_path_shaped(element: str) -> bool:
    if element.startswith("-"):
        return False
    return "/" in element or "\\" in element or element in (".", "..")


def _check_containment(element: str, *, root: Path, target_id: str) -> None:
    if re.match(r"^[A-Za-z]:", element) or Path(element).is_absolute():
        resolved = Path(element).resolve()
        if root != resolved and root not in resolved.parents:
            raise VerifyAdapterError(
                f"target {target_id!r}: absolute path {element!r} escapes the repository"
            )
        return
    if ".." in Path(element).parts:
        raise VerifyAdapterError(
            f"target {target_id!r}: path {element!r} contains a '..' segment"
        )
    resolved = (root / element).resolve()
    if root != resolved and root not in resolved.parents:
        raise VerifyAdapterError(
            f"target {target_id!r}: path {element!r} escapes the repository"
        )


def _validate_argv(argv: Any, *, root: Path, target_id: str) -> list[str]:
    if not isinstance(argv, list) or not argv:
        raise VerifyAdapterError(f"target {target_id!r}: command must be a non-empty argv array")
    for element in argv:
        if not isinstance(element, str) or not element.strip():
            raise VerifyAdapterError(
                f"target {target_id!r}: every argv element must be a non-empty string"
            )
        _reject_metacharacters(element, target_id=target_id)
    executable = argv[0]
    if executable not in ALLOWED_EXECUTABLES:
        candidate = (root / executable).resolve() if not Path(executable).is_absolute() else Path(executable).resolve()
        inside = root == candidate or root in candidate.parents
        if not (inside and candidate.is_file()):
            raise VerifyAdapterError(
                f"target {target_id!r}: executable {executable!r} is neither an "
                f"allowlisted interpreter {ALLOWED_EXECUTABLES} nor a file inside the repository"
            )
    for element in argv[1:]:
        if _looks_path_shaped(element):
            _check_containment(element, root=root, target_id=target_id)
    return list(argv)


def load_manifest(manifest: Path) -> list[dict[str, Any]]:
    """Load and strictly validate the verification manifest.

    Fails closed with VerifyAdapterError (mapped to exit 2) on any schema,
    allowlist, or containment violation — never a partial parse.
    """
    if not manifest.is_file():
        raise VerifyAdapterError(f"no verification manifest at {manifest}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerifyAdapterError(f"verification manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise VerifyAdapterError("verification manifest root must be a JSON object")
    unknown = set(data) - ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        raise VerifyAdapterError(f"verification manifest has unknown top-level keys: {sorted(unknown)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise VerifyAdapterError(
            f"verification manifest schema_version must be {SCHEMA_VERSION}, "
            f"got {data.get('schema_version')!r}"
        )
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise VerifyAdapterError("verification manifest must declare a non-empty 'targets' list")

    root = _manifest_root(manifest)
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in targets:
        if not isinstance(raw, dict):
            raise VerifyAdapterError("every manifest target must be a JSON object")
        unknown = set(raw) - ALLOWED_TARGET_KEYS
        if unknown:
            raise VerifyAdapterError(f"manifest target has unknown keys: {sorted(unknown)}")
        target_id = raw.get("id")
        if not isinstance(target_id, str) or not ID_RE.match(target_id):
            raise VerifyAdapterError(f"manifest target id {target_id!r} must match {ID_RE.pattern}")
        if target_id in seen_ids:
            raise VerifyAdapterError(f"duplicate manifest target id {target_id!r}")
        seen_ids.add(target_id)
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            raise VerifyAdapterError(f"target {target_id!r}: label must be a non-empty string")
        argv = _validate_argv(raw.get("command"), root=root, target_id=target_id)
        entries.append({"label": label, "slug": target_id, "argv": argv})
    return entries


def resolve_targets(entries: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    if target == "full":
        return list(entries)
    if target == "lint":
        return [e for e in entries if LINT_LABEL_RE.search(e["label"])]
    if target == "test":
        return [e for e in entries if TEST_LABEL_RE.search(e["label"])]
    return [e for e in entries if e["slug"] == target]


def _augment_argv(argv: list[str], *, pattern: str | None) -> list[str]:
    if pattern and "unittest" in argv and "discover" in argv:
        return [*argv, "-k", pattern]
    return list(argv)


def _manifest_sha256(manifest: Path) -> str:
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def _verify_log_dir(root: Path) -> Path:
    return root / ".claude" / "state" / "logs" / "verify"


def _trust_record_path(root: Path) -> Path:
    return _verify_log_dir(root) / "manifest-sha256.json"


def _pending_triage_path(root: Path, target: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", target).strip("-") or "target"
    return _verify_log_dir(root) / "pending-triage" / f"{safe}.json"


def _manifest_changed_since_last_verified(manifest: Path, digest: str) -> bool:
    record = _trust_record_path(_manifest_root(manifest))
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
        return data.get("sha256") != digest
    except (OSError, json.JSONDecodeError):
        # No trusted record yet: surface as changed so a reviewer sees the
        # signal on first use rather than a silent pass.
        return True


def _record_verified_manifest(manifest: Path, digest: str) -> None:
    record = _trust_record_path(_manifest_root(manifest))
    try:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps({"sha256": digest, "manifest": str(manifest)}) + "\n",
            encoding="utf-8",
        )
    except OSError:
        # Recording the trusted hash is best-effort telemetry; never let a
        # read-only state dir break verification itself.
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json_best_effort(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerifyAdapterError(f"triage file {path} is missing or invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise VerifyAdapterError(f"triage file {path} must contain a JSON object")
    return data


def validate_triage_record(data: dict[str, Any]) -> dict[str, Any]:
    classification = data.get("classification")
    if classification not in TRIAGE_CLASSIFICATIONS:
        raise VerifyAdapterError(
            "triage classification must be one of: " + ", ".join(sorted(TRIAGE_CLASSIFICATIONS))
        )
    for key in ("reason", "next_action"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise VerifyAdapterError(f"triage {key} must be a non-empty string")
    return {
        "classification": classification,
        "reason": data["reason"].strip(),
        "next_action": data["next_action"].strip(),
    }


def _record_pending_triage(root: Path, target: str, result: dict[str, Any]) -> None:
    payload = {
        "target": target,
        "created_at": _now_iso(),
        "required_classifications": sorted(TRIAGE_CLASSIFICATIONS),
        "status": "triage-required-before-retry",
        "failed_commands": [
            {
                "slug": command.get("slug"),
                "command": command.get("command"),
                "exit_code": command.get("exit_code"),
            }
            for command in result.get("commands", [])
            if command.get("exit_code") != 0
        ],
    }
    _write_json_best_effort(_pending_triage_path(root, target), payload)


def _clear_pending_triage(root: Path, target: str) -> None:
    try:
        _pending_triage_path(root, target).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _consume_triage_for_retry(root: Path, target: str, triage_file: Path | None) -> dict[str, Any] | None:
    pending = _pending_triage_path(root, target)
    if not pending.exists():
        return None
    if triage_file is None:
        raise VerifyAdapterError(
            f"previous verification for {target!r} failed; triage is required before retry. "
            f"Classify it as implementation bug, flaky/environmental issue, missing dependency, "
            f"test defect, or unclear, and rerun with --triage-file <json> containing "
            f"classification, reason, and next_action. Pending record: {pending}"
        )
    triage = validate_triage_record(_read_json(triage_file))
    _write_json_best_effort(
        pending.with_suffix(".triaged.json"),
        {**triage, "triaged_at": _now_iso(), "target": target},
    )
    try:
        pending.unlink()
    except OSError:
        pass
    return triage


def run_target(
    target: str,
    *,
    manifest: Path | None = None,
    pattern: str | None = None,
    cwd: Path | None = None,
    triage_file: Path | None = None,
) -> dict[str, Any]:
    manifest = manifest or (ROOT / MANIFEST_RELPATH)
    root = _manifest_root(manifest)
    cwd = cwd or root
    triage = _consume_triage_for_retry(root, target, triage_file)

    if target in NON_CODE_MODES:
        return {
            "target": target,
            "exit_code": 2,
            "status": "unavailable",
            "message": NON_CODE_MODES[target],
            "commands": [],
        }

    entries = load_manifest(manifest)
    digest = _manifest_sha256(manifest)
    manifest_changed = _manifest_changed_since_last_verified(manifest, digest)
    selected = resolve_targets(entries, target)
    if not selected:
        return {
            "target": target,
            "exit_code": 2,
            "status": "unavailable",
            "message": f"no manifest target matched {target!r}",
            "commands": [e["slug"] for e in entries],
            "manifest_sha256": digest,
            "manifest_changed": manifest_changed,
        }

    results = []
    overall = 0
    for entry in selected:
        argv = _augment_argv(entry["argv"], pattern=pattern)
        proc = subprocess.run(argv, shell=False, cwd=cwd, capture_output=True, text=True)
        if proc.returncode != 0:
            overall = 1
        results.append(
            {
                "label": entry["label"],
                "slug": entry["slug"],
                "command": shlex.join(argv),
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
    if overall == 0:
        _record_verified_manifest(manifest, digest)
        _clear_pending_triage(_manifest_root(manifest), target)
    result = {
        "target": target,
        "exit_code": overall,
        "status": "pass" if overall == 0 else "fail",
        "message": None,
        "commands": results,
        "manifest_sha256": digest,
        "manifest_changed": manifest_changed,
        **({"retry_triage": triage} if triage else {}),
    }
    if overall != 0:
        _record_pending_triage(_manifest_root(manifest), target, result)
    return result


def list_targets(manifest: Path | None = None) -> dict[str, Any]:
    manifest = manifest or (ROOT / MANIFEST_RELPATH)
    entries = load_manifest(manifest)
    return {
        "aggregate_targets": ["full", "lint", "test"],
        "non_code_targets": sorted(NON_CODE_MODES),
        "individual_targets": [e["slug"] for e in entries],
    }


def command_run(args: argparse.Namespace) -> int:
    result = run_target(
        args.target,
        manifest=Path(args.manifest) if args.manifest else None,
        pattern=args.pattern,
        triage_file=Path(args.triage_file) if args.triage_file else None,
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
    p.add_argument("--pattern", help="focused-test filter appended as -k <pattern> to unittest discover argv")
    p.add_argument("--manifest", help="path to a verification manifest (default: .claude/verification.json)")
    p.add_argument("--triage-file", help="JSON triage record required before retrying a previously failed target")
    p.set_defaults(func=command_run)

    p = sub.add_parser("list-targets")
    p.add_argument("--manifest", help="path to a verification manifest (default: .claude/verification.json)")
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

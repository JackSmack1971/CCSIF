#!/usr/bin/env python3
"""Shared deterministic primitives for repository-hygiene scripts."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = 1
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class HygieneError(RuntimeError):
    """Expected operational failure with an actionable user-facing message."""

    def __init__(self, message: str, *, code: str = "HYGIENE_ERROR", details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class Finding:
    id: str
    rule_id: str
    category: str
    severity: str
    confidence: str
    title: str
    summary: str
    evidence: list[dict[str, Any]]
    remediation_key: str
    recommended_actions: list[str]
    acceptance_criteria: list[str]
    verification: list[str]
    destructive: bool = False
    actionable: bool = True
    dependencies: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Coverage:
    check: str
    status: str  # complete | degraded | skipped
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def fingerprint(*parts: Any, length: int = 16) -> str:
    return digest_value(list(parts))[:length]


def attach_digest(plan: dict[str, Any]) -> dict[str, Any]:
    body = dict(plan)
    body.pop("digest", None)
    body["digest"] = digest_value(body)
    return body


def verify_digest(plan: dict[str, Any], supplied: str | None = None) -> str:
    expected = plan.get("digest")
    if not isinstance(expected, str):
        raise HygieneError("Plan has no digest.", code="PLAN_DIGEST_MISSING")
    body = dict(plan)
    body.pop("digest", None)
    actual = digest_value(body)
    if actual != expected:
        raise HygieneError(
            "Plan content does not match its embedded digest.",
            code="PLAN_DIGEST_INVALID",
            details={"embedded": expected, "computed": actual},
        )
    if supplied is not None and supplied != expected:
        raise HygieneError(
            "Confirmation digest does not match the plan.",
            code="CONFIRMATION_DIGEST_MISMATCH",
            details={"expected": expected, "supplied": supplied},
        )
    return expected


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HygieneError(f"File not found: {path}", code="FILE_NOT_FOUND") from exc
    except json.JSONDecodeError as exc:
        raise HygieneError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}",
            code="INVALID_JSON",
        ) from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
    timeout: int = 60,
    input_text: str | None = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HygieneError(f"Required command is unavailable: {args[0]}", code="COMMAND_NOT_FOUND") from exc
    except subprocess.TimeoutExpired as exc:
        raise HygieneError(
            f"Command timed out after {timeout}s: {shell_join(args)}",
            code="COMMAND_TIMEOUT",
        ) from exc
    result = CommandResult(tuple(args), completed.returncode, completed.stdout, completed.stderr)
    if check and result.returncode != 0:
        raise HygieneError(
            f"Command failed ({result.returncode}): {shell_join(args)}\n{result.stderr.strip()}",
            code="COMMAND_FAILED",
            details={"returncode": result.returncode, "stderr": result.stderr[-4000:]},
        )
    return result


def run_json(args: Sequence[str], *, cwd: Path | None = None, timeout: int = 60) -> Any:
    result = run(args, cwd=cwd, check=True, timeout=timeout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HygieneError(
            f"Command returned invalid JSON: {shell_join(args)}",
            code="COMMAND_INVALID_JSON",
            details=result.stdout[-4000:],
        ) from exc


def shell_join(args: Sequence[str]) -> str:
    import shlex

    return shlex.join(list(args))


def command_exists(name: str) -> bool:
    from shutil import which

    return which(name) is not None


def git_root(path: Path) -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=path, check=True)
    return Path(result.stdout.strip()).resolve()


def git_text(repo: Path, *args: str, check: bool = True, timeout: int = 60) -> str:
    return run(["git", *args], cwd=repo, check=check, timeout=timeout).stdout


def tracked_files(repo: Path) -> list[str]:
    output = run(["git", "ls-files", "-z"], cwd=repo, check=True).stdout
    return sorted(item for item in output.split("\0") if item)


def safe_relative(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_text_bounded(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        data = path.read_bytes()
    except (OSError, PermissionError):
        return None
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return None


def find_line(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def evidence(path: str, observation: str, *, line: int | None = None, command: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"source": path, "observation": observation}
    if line is not None:
        item["line"] = line
    if command is not None:
        item["command"] = command
    return item


def make_finding(
    *,
    rule_id: str,
    category: str,
    severity: str,
    confidence: str,
    title: str,
    summary: str,
    evidence_items: list[dict[str, Any]],
    remediation_key: str,
    actions: Iterable[str],
    acceptance: Iterable[str],
    verification: Iterable[str],
    destructive: bool = False,
    actionable: bool = True,
    dependencies: Iterable[str] = (),
    non_goals: Iterable[str] = (),
    references: Iterable[str] = (),
) -> Finding:
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"Unknown severity: {severity}")
    stable = fingerprint(rule_id, remediation_key, evidence_items)
    return Finding(
        id=f"RH-{stable.upper()}",
        rule_id=rule_id,
        category=category,
        severity=severity,
        confidence=confidence,
        title=title,
        summary=summary,
        evidence=evidence_items,
        remediation_key=remediation_key,
        recommended_actions=list(actions),
        acceptance_criteria=list(acceptance),
        verification=list(verification),
        destructive=destructive,
        actionable=actionable,
        dependencies=list(dependencies),
        non_goals=list(non_goals),
        references=list(references),
    )


def json_status(status: str, **kwargs: Any) -> None:
    payload = {"status": status, **kwargs}
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def fail_cli(exc: Exception) -> int:
    if isinstance(exc, HygieneError):
        json_status("error", code=exc.code, message=str(exc), details=exc.details)
        print(f"ERROR [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    json_status("error", code="UNEXPECTED_ERROR", message=str(exc))
    print(f"ERROR [UNEXPECTED_ERROR]: {exc}", file=sys.stderr)
    return 3


def normalize_label(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def severity_at_least(severity: str, minimum: str) -> bool:
    return SEVERITY_ORDER.get(severity, -1) >= SEVERITY_ORDER.get(minimum, 999)


def repository_identity(repo: Path) -> dict[str, Any]:
    remote = run(["git", "remote", "get-url", "origin"], cwd=repo)
    head = run(["git", "rev-parse", "HEAD"], cwd=repo)
    branch = run(["git", "branch", "--show-current"], cwd=repo)
    return {
        "root": repo.as_posix(),
        "origin": remote.stdout.strip() if remote.returncode == 0 else None,
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
    }

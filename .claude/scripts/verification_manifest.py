#!/usr/bin/env python3
"""Shared manifest-backed verification adapter core.

The adapter reads a repo-owned JSON manifest instead of parsing shell
commands out of ``CLAUDE.md``. The manifest is versioned, machine-readable,
and validated before any subprocess is spawned.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_REL = Path(".claude") / "verification-manifest.json"
ALLOWED_EXECUTABLES = {"python3", "python", "node", "bash", "npm", "npx", "yarn", "pnpm"}
SHELL_META_RE = re.compile(r"(;|&&|\|\||\||`|\$\(|>|<)")
PATH_ARG_FLAGS = {"-s", "--start-directory", "--cwd", "--directory"}
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


def manifest_path(root: Path | None = None) -> Path:
    return (root or ROOT) / MANIFEST_REL


def manifest_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_contains(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_within_root(token: str, *, cwd: Path, root: Path) -> Path:
    candidate = Path(token)
    resolved = (candidate if candidate.is_absolute() else cwd / candidate).resolve()
    if not _root_contains(resolved, root):
        raise VerifyAdapterError(f"path escapes repository containment: {token!r}")
    return resolved


def _is_probable_path(token: str, *, index: int, argv: list[str]) -> bool:
    if token in {".", ".."}:
        return True
    if token.startswith(("~", ".", "/", "\\")):
        return True
    if "/" in token or "\\" in token:
        return True
    if Path(token).suffix in {".py", ".md", ".json", ".sh", ".ps1", ".toml", ".yml", ".yaml", ".txt"}:
        return True
    if index > 0 and argv[index - 1] in PATH_ARG_FLAGS:
        return True
    return token in {"tests", "test", "docs", "src", "migrations", "packages"}


def _validate_command(argv: list[str], *, cwd: Path, root: Path) -> None:
    if not argv:
        raise VerifyAdapterError("command cannot be empty")
    if not isinstance(argv[0], str):
        raise VerifyAdapterError("command executable must be a string")
    if SHELL_META_RE.search(argv[0]):
        raise VerifyAdapterError(f"shell operators are not allowed in executables: {argv[0]!r}")

    executable = argv[0]
    if executable in ALLOWED_EXECUTABLES:
        pass
    elif _is_probable_path(executable, index=0, argv=argv):
        _resolve_within_root(executable, cwd=cwd, root=root)
    else:
        raise VerifyAdapterError(f"executable is not allowlisted: {executable!r}")

    for index, token in enumerate(argv[1:], start=1):
        if not isinstance(token, str):
            raise VerifyAdapterError("command argv elements must be strings")
        if SHELL_META_RE.search(token):
            raise VerifyAdapterError(f"shell operators are not allowed in argv: {token!r}")
        if _is_probable_path(token, index=index, argv=argv):
            _resolve_within_root(token, cwd=cwd, root=root)


def _normalize_cwd(cwd: Path | None, *, root: Path = ROOT) -> Path:
    resolved = (cwd or ROOT).resolve()
    if not _root_contains(resolved, root):
        raise VerifyAdapterError(f"cwd escapes repository containment: {resolved}")
    return resolved


def _manifest_root(path: Path) -> Path:
    if path.parent.name == ".claude":
        return path.parent.parent.resolve()
    return path.parent.resolve()


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VerifyAdapterError(f"no verification manifest at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise VerifyAdapterError(f"verification manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise VerifyAdapterError("verification manifest must be a JSON object")

    unexpected = set(data) - {"schema_version", "targets"}
    if unexpected:
        raise VerifyAdapterError(f"verification manifest contains unknown top-level keys: {sorted(unexpected)}")
    if data.get("schema_version") != 1:
        raise VerifyAdapterError("verification manifest requires schema_version == 1")
    if "targets" not in data or not isinstance(data["targets"], list) or not data["targets"]:
        raise VerifyAdapterError("verification manifest requires a non-empty targets list")
    return data


def parse_manifest(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or manifest_path()
    data = _load_manifest(path)
    root = _manifest_root(path)
    cwd = _normalize_cwd(root, root=root)
    seen_ids: set[str] = set()
    entries: list[dict[str, Any]] = []

    for raw in data["targets"]:
        if not isinstance(raw, dict):
            raise VerifyAdapterError("each manifest target must be a JSON object")
        unexpected = set(raw) - {"id", "label", "command", "cwd"}
        if unexpected:
            raise VerifyAdapterError(f"manifest target contains unknown keys: {sorted(unexpected)}")
        target_id = raw.get("id")
        label = raw.get("label")
        command = raw.get("command")
        target_cwd = raw.get("cwd")
        if not isinstance(target_id, str) or not target_id.strip():
            raise VerifyAdapterError("manifest target requires a non-empty string id")
        if target_id in seen_ids:
            raise VerifyAdapterError(f"duplicate manifest target id: {target_id}")
        if not isinstance(label, str) or not label.strip():
            raise VerifyAdapterError(f"manifest target {target_id!r} requires a non-empty label")
        if not isinstance(command, list):
            raise VerifyAdapterError(f"manifest target {target_id!r} requires command as a list")
        if not command or any(not isinstance(item, str) or not item for item in command):
            raise VerifyAdapterError(f"manifest target {target_id!r} requires a non-empty argv list of strings")

        resolved_cwd = cwd
        if target_cwd is not None:
            if not isinstance(target_cwd, str) or not target_cwd.strip():
                raise VerifyAdapterError(f"manifest target {target_id!r} cwd must be a non-empty string")
            resolved_cwd = _resolve_within_root(target_cwd, cwd=cwd, root=root)

        _validate_command(command, cwd=resolved_cwd, root=root)
        seen_ids.add(target_id)
        entries.append(
            {
                "id": target_id,
                "label": label,
                "slug": slugify(label),
                "command": command,
                "cwd": str(resolved_cwd),
            }
        )
    return entries


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")


def resolve_targets(entries: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    if target == "full":
        return list(entries)
    if target == "lint":
        return [entry for entry in entries if re.search(r"lint|rule|format", entry["label"], re.IGNORECASE)]
    if target == "test":
        return [entry for entry in entries if re.search(r"test", entry["label"], re.IGNORECASE)]
    return [entry for entry in entries if entry["slug"] == target or entry["id"] == target]


def _augment_command(command: list[str], *, pattern: str | None) -> list[str]:
    if pattern and command[:4] == ["python3", "-m", "unittest", "discover"] or pattern and command[:4] == ["python", "-m", "unittest", "discover"]:
        return [*command, "-k", pattern]
    return list(command)


def run_target(
    target: str,
    *,
    manifest: Path | None = None,
    pattern: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    if target in NON_CODE_MODES:
        return {
            "target": target,
            "manifest_path": str(manifest_path()),
            "manifest_digest": None,
            "exit_code": 2,
            "status": "unavailable",
            "message": NON_CODE_MODES[target],
            "commands": [],
        }

    manifest = manifest or manifest_path()
    entries = parse_manifest(manifest)
    selected = resolve_targets(entries, target)
    if not selected:
        return {
            "target": target,
            "manifest_path": str(manifest),
            "manifest_digest": manifest_digest(manifest),
            "exit_code": 2,
            "status": "unavailable",
            "message": f"no verification target matched {target!r}",
            "commands": [entry["slug"] for entry in entries],
        }

    runtime_cwd = _normalize_cwd(cwd, root=_manifest_root(manifest))
    results = []
    overall = 0
    for entry in selected:
        command = _augment_command(entry["command"], pattern=pattern)
        proc = subprocess.run(command, shell=False, cwd=entry.get("cwd", runtime_cwd), capture_output=True, text=True)
        if proc.returncode != 0:
            overall = 1
        results.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "slug": entry["slug"],
                "command": command,
                "cwd": entry.get("cwd", str(runtime_cwd)),
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
    return {
        "target": target,
        "manifest_path": str(manifest),
        "manifest_digest": manifest_digest(manifest),
        "exit_code": overall,
        "status": "pass" if overall == 0 else "fail",
        "message": None,
        "commands": results,
    }


def list_targets(manifest: Path | None = None) -> dict[str, Any]:
    manifest = manifest or manifest_path()
    entries = parse_manifest(manifest)
    return {
        "manifest_path": str(manifest),
        "manifest_digest": manifest_digest(manifest),
        "aggregate_targets": ["full", "lint", "test"],
        "non_code_targets": sorted(NON_CODE_MODES),
        "individual_targets": [entry["slug"] for entry in entries],
    }

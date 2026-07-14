#!/usr/bin/env python3
"""Deterministic prerequisite and MCP startup-assumption checks for CCSIF."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def require_executable(name: str, purpose: str) -> str:
    path = shutil.which(name)
    if not path:
        fail(f"missing required executable `{name}` on PATH ({purpose})")
    return path


def parse_major_minor(output: str, prefix: str) -> tuple[int, int]:
    text = output.strip()
    if text.startswith(prefix):
        text = text[len(prefix):]
    parts = text.strip().split()[0].split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        fail(f"could not parse version from output: {output!r}")


def check_python() -> None:
    if sys.version_info < (3, 11):
        fail(f"Python 3.11+ is required; running {sys.version.split()[0]}")
    print(f"OK: python {sys.version.split()[0]}")


def check_node() -> None:
    node = require_executable("node", "Claude hook helpers and workflow modules")
    proc = run([node, "--version"])
    if proc.returncode != 0:
        fail(f"node --version failed: {proc.stderr.strip()}")
    major, _minor = parse_major_minor(proc.stdout, "v")
    if major < 20:
        fail(f"Node.js 20+ is required; found {proc.stdout.strip()}")
    print(f"OK: node {proc.stdout.strip()}")


def check_shell() -> None:
    bash = require_executable("bash", "Claude hook shell wrappers")
    proc = run([bash, "--version"])
    if proc.returncode != 0:
        fail(f"bash --version failed: {proc.stderr.strip()}")
    print(f"OK: bash {proc.stdout.splitlines()[0] if proc.stdout else bash}")


def check_manifests() -> None:
    required = [
        ".python-version",
        ".node-version",
        "package.json",
        ".mcp.json",
        ".claude/memory/pyproject.toml",
        ".claude/memory/uv.lock",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing dependency/runtime manifest(s): {', '.join(missing)}")
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    for script in ("test", "verify", "smoke:mcp"):
        if script not in pkg.get("scripts", {}):
            fail(f"package.json is missing required script `{script}`")
    print("OK: dependency manifests present")


def check_mcp_manifest(*, require_uv: bool) -> None:
    data = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or "graphiti-memory" not in servers:
        fail(".mcp.json must define mcpServers.graphiti-memory")
    server = servers["graphiti-memory"]
    expected_args = ["run", "--project", ".claude/memory", "python", ".claude/memory/hindsight_mcp.py"]
    if server.get("command") != "uv" or server.get("args") != expected_args:
        fail("graphiti-memory MCP command must be `uv run --project .claude/memory python .claude/memory/hindsight_mcp.py`")
    for path in (".claude/memory/hindsight_mcp.py", ".claude/memory/pyproject.toml", ".claude/memory/uv.lock"):
        if not (ROOT / path).is_file():
            fail(f"MCP startup path is missing: {path}")
    if require_uv:
        uv = require_executable("uv", "graphiti-memory MCP startup")
        proc = run([uv, "--version"])
        if proc.returncode != 0:
            fail(f"uv --version failed: {proc.stderr.strip()}")
        print(f"OK: uv {proc.stdout.strip()}")
    print("OK: MCP startup manifest is repository-local and complete")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-smoke", action="store_true", help="also validate MCP startup command assumptions")
    parser.add_argument("--require-uv", action="store_true", help="require uv to be installed for MCP startup")
    args = parser.parse_args(argv)

    check_python()
    check_node()
    check_shell()
    check_manifests()
    if args.mcp_smoke or args.require_uv:
        check_mcp_manifest(require_uv=args.require_uv)
    print("prereq-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Phase 5C `/bootstrap-control-plane` installer.

Creates or reconciles the portable, code-agnostic control-plane tree
(Phase 5.1 layout) inside a target repository. Design constraints, all
required by `docs/claude-code-control-plane-roadmap-v2.md` Phase 5.5 and the
Scope Doctrine:

  - Additive-only, idempotent: an existing file under the target `.claude/`
    or root memory files is never overwritten. Only missing paths are
    created. Re-running with the same or different facts produces the same
    tree and zero diff on already-scaffolded paths (rollback-safety follows
    directly from "never overwrite, never delete" -- a failed or interrupted
    run leaves only completed, correct writes and can simply be re-run).
  - Generated content and this script's own resolution logic must never
    depend on `~/.claude/*`; every path is relative to the target
    repo root, resolved via `Path(__file__)`-relative discovery once copied
    into `<target>/.claude/scripts/`, exactly like this repo's own
    `phase0_control_plane.py` / `phase5b_verify.py` pattern.
  - `autoMemoryDirectory` is written only into the target's gitignored
    `.claude/settings.local.json`, as an absolute path, additive-only
    (mirrors `phase2_memory.bootstrap_local_settings`'s documented
    behavior: never touch another key, never overwrite unreadable JSON).
  - Stack-agnostic: the generated `CLAUDE.md` facts block and the verify
    adapter are the only two places stack knowledge lives (per Phase 5.4);
    every generated command/skill/rule file is identical across stacks.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Shared helpers (duplicated intentionally, not imported from this repo's own
# phaseN_*.py: those scripts are CCSIF's own historical harness, not part of
# the portable payload this installer copies into an unrelated target repo).
# ---------------------------------------------------------------------------


def now_stub() -> str:
    # Bootstrap-time content must not embed a wall-clock timestamp: doing so
    # would make every re-run produce a diff even when nothing else changed,
    # breaking the "re-running produces no unintended diff" requirement.
    return "GENERATED-BY-BOOTSTRAP-CONTROL-PLANE"


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2)


# ---------------------------------------------------------------------------
# Facts (the scan/interview output)
# ---------------------------------------------------------------------------


@dataclass
class Facts:
    issue_tracker: str = "none"
    build_command: str | None = None
    test_command: str | None = None
    lint_command: str | None = None
    commit_convention: str = "conventional-commits"
    mandatory_gates: list[str] = field(default_factory=lambda: ["plan", "verify"])
    skippable_gates: list[str] = field(default_factory=lambda: ["brainstorm", "research", "grill"])
    memory_policy: str = "gitignored"
    platform: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_tracker": self.issue_tracker,
            "build_command": self.build_command,
            "test_command": self.test_command,
            "lint_command": self.lint_command,
            "commit_convention": self.commit_convention,
            "mandatory_gates": self.mandatory_gates,
            "skippable_gates": self.skippable_gates,
            "memory_policy": self.memory_policy,
            "platform": self.platform,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Facts":
        base = cls()
        for key in base.to_dict():
            if key in data and data[key] is not None:
                setattr(base, key, data[key])
        return base


def detect_stack(target: Path) -> Facts:
    """Non-interactive scan: infer verify commands from repo markers. This
    is the "scan" half of "scan/interview"; the "interview" half is the
    caller supplying a facts JSON (headless) or answering AskUserQuestion
    prompts in an interactive session and passing the result the same way."""
    facts = Facts()

    if (target / "package.json").is_file():
        try:
            pkg = json.loads((target / "package.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a broken package.json just yields no npm facts
            pkg = {}
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        if "test" in scripts:
            facts.test_command = "npm test"
        if "lint" in scripts:
            facts.lint_command = "npm run lint"
        if "build" in scripts:
            facts.build_command = "npm run build"
    elif (target / "pyproject.toml").is_file() or (target / "requirements.txt").is_file():
        if (target / "tests").is_dir() or (target / "test").is_dir():
            facts.test_command = "python -m pytest -q"
        if (target / "pyproject.toml").is_file():
            facts.lint_command = "python -m ruff check ."
    elif list(target.glob("*.md")) and not any(
        (target / marker).exists() for marker in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml")
    ):
        # Docs-only / non-code pipeline: verification is rubric/citation
        # based, not a shell toolchain. Never invent a fake test command.
        facts.test_command = None
        facts.lint_command = None

    if (target / ".git").exists():
        facts.commit_convention = "conventional-commits"

    facts.platform = "windows" if os.name == "nt" else "posix"
    return facts


# ---------------------------------------------------------------------------
# Templates (portable, stack-agnostic payload)
# ---------------------------------------------------------------------------

OPERATING_DOCTRINE = """# Operating Doctrine

Installed by `/bootstrap-control-plane`. Everything this control plane
depends on lives under this repo's `.claude/` and root memory files; this
repo must never require `~/.claude/*` for correctness (Scope Doctrine).

- Gather context -> act -> verify, one step at a time.
- State assumptions explicitly before writing code, not after.
- Define the verification target before declaring a task finished.
- Prefer the smallest complete change; never a large unverified batch.
- See `.claude/rules/20-lifecycle-gates.md` for the gated version of this
  loop and `.claude/rules/30-skill-taxonomy.md` for the command/skill split.
"""

KARPATHY_GUIDELINES = """# Karpathy Guidelines

- State assumptions explicitly before writing code, not after; an unstated
  assumption is a defect even if the code happens to work.
- Define the verification target before declaring a task finished, not
  after the diff exists.
- Keep the agent on a leash: small incremental chunks, one
  generate-then-verify cycle at a time, never a large unverified batch.
- For optimization or tuning work, use a metric-gated experiment loop: one
  named metric, a fixed budget, keep the change only if the metric
  improved, revert otherwise. Never claim improvement without that loop.
"""

LIFECYCLE_GATES = """# Lifecycle Gates

Every non-trivial unit of work flows through five gates. Skip a gate
explicitly (state which and why) for trivial, single-file, reversible work;
never skip silently.

| Gate | Input | Output | Durable artifact | Verification owner |
|---|---|---|---|---|
| 1. Align | Task request, open questions | Requirements, assumptions, constraints | `.claude/state/research/` note or ledger entry | Requester confirms scope |
| 2. Research | A question | Cited findings, no raw dumps | `.claude/state/research/<topic>.md` | Author cites sources |
| 3. Plan | Research + constraints | Atomic plan(s) (<=3 tasks), explicit assumptions, verification target | `.claude/plans/` | Plan approver |
| 4. Build | One approved plan | Diff, commits | Ledger entry; builder summary in `.claude/state/agents/` | Builder self-checks, never self-certifies |
| 5. Verify & Ship | Plan + diff | Pass/fail re-derived independently, PR/checkpoint | `.claude/state/checkpoints/`; ledger entry | Verifier, never the builder |

Cross-cutting, not gated: `/handoff` (session takeover doc in
`.claude/state/handoffs/`), `/status` (reconstruction from `.claude/state/`
alone), `/debug`, and `/experiment` (metric-gated keep/revert loop). Every
gate's verification step calls one adapter, `.claude/hooks/verify.sh` (or
`.ps1`), never a raw toolchain command directly.
"""

SKILL_TAXONOMY = """# Skill Taxonomy (Two-Axis Rule)

- User-invoked commands (`.claude/commands/*.md`) are orchestrators. A
  command may call skills, agents, or scripts; it must never invoke another
  command.
- Model-invoked skills (`.claude/skills/<name>/SKILL.md`) hold reusable,
  single-purpose discipline. A skill's description states one job and one
  explicit non-goal (`NOT for X; use Y instead`).
- Before adding a skill or command, check for an existing one covering the
  same job; extend or reference it instead of duplicating it.
"""

COMMON_PY = '''#!/usr/bin/env python3
"""Shared helpers for the bootstrap-installed control-plane scripts.
Must never depend on any specific stack or on ~/.claude/*."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[1]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    return Path(raw).expanduser().resolve()


def workspace_root() -> Path:
    return env_path("CONTROL_PLANE_WORKSPACE_ROOT", REPO_ROOT)


def state_root() -> Path:
    return env_path("CONTROL_PLANE_STATE_ROOT", workspace_root() / ".claude" / "state")
'''


VERIFICATION_MANIFEST_PY = '''#!/usr/bin/env python3
"""Shared manifest-backed verification adapter core."""
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
SHELL_META_RE = re.compile(r"(;|&&|\\|\\||\\||`|\\$\\(|>|<)")
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


def _resolve_within_root(token: str, *, cwd: Path) -> Path:
    candidate = Path(token)
    resolved = (candidate if candidate.is_absolute() else cwd / candidate).resolve()
    if not _root_contains(resolved, ROOT):
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


def _validate_command(argv: list[str], *, cwd: Path) -> None:
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
        _resolve_within_root(executable, cwd=cwd)
    else:
        raise VerifyAdapterError(f"executable is not allowlisted: {executable!r}")

    for index, token in enumerate(argv[1:], start=1):
        if not isinstance(token, str):
            raise VerifyAdapterError("command argv elements must be strings")
        if SHELL_META_RE.search(token):
            raise VerifyAdapterError(f"shell operators are not allowed in argv: {token!r}")
        if _is_probable_path(token, index=index, argv=argv):
            _resolve_within_root(token, cwd=cwd)


def _normalize_cwd(cwd: Path | None) -> Path:
    resolved = (cwd or ROOT).resolve()
    if not _root_contains(resolved, ROOT):
        raise VerifyAdapterError(f"cwd escapes repository containment: {resolved}")
    return resolved


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


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")


def parse_manifest(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or manifest_path()
    data = _load_manifest(path)
    cwd = _normalize_cwd(path.parent.parent)
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
            resolved_cwd = _resolve_within_root(target_cwd, cwd=cwd)

        _validate_command(command, cwd=resolved_cwd)
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


def resolve_targets(entries: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    if target == "full":
        return list(entries)
    if target == "lint":
        return [entry for entry in entries if re.search(r"lint|rule|format", entry["label"], re.IGNORECASE)]
    if target == "test":
        return [entry for entry in entries if re.search(r"test", entry["label"], re.IGNORECASE)]
    return [entry for entry in entries if entry["slug"] == target or entry["id"] == target]


def _augment_command(command: list[str], *, pattern: str | None) -> list[str]:
    if pattern and command[:4] == ["python3", "-m", "unittest", "discover"]:
        return [*command, "-k", pattern]
    if pattern and command[:4] == ["python", "-m", "unittest", "discover"]:
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

    runtime_cwd = _normalize_cwd(cwd)
    results = []
    overall = 0
    for entry in selected:
        command = _augment_command(entry["command"], pattern=pattern)
        proc = subprocess.run(command, shell=False, cwd=entry.get("cwd", str(runtime_cwd)), capture_output=True, text=True)
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
'''


VERIFICATION_MANIFEST_SOURCE = (SCRIPT_DIR / "verification_manifest.py").read_text(encoding="utf-8")


VERIFY_ADAPTER_PY_V2 = '''#!/usr/bin/env python3
"""Code-agnostic verification adapter."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from verification_manifest import VerifyAdapterError, list_targets, run_target


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
    parser = argparse.ArgumentParser(prog="verify_adapter")
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
'''


CONTROL_PLANE_CHECK_PY_V2 = '''#!/usr/bin/env python3
"""Deterministic control-plane validation for CCSIF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    "CLAUDE.md",
    ".claude/verification-manifest.json",
    ".claude/settings.json",
    ".claude/rules/00-operating-doctrine.md",
    ".claude/rules/10-karpathy-guidelines.md",
    ".claude/rules/20-lifecycle-gates.md",
    ".claude/rules/30-skill-taxonomy.md",
    ".claude/scripts/common.py",
    ".claude/scripts/lifecycle.py",
    ".claude/scripts/verify_adapter.py",
    ".claude/scripts/verification_manifest.py",
    ".claude/scripts/control_plane_check.py",
    ".claude/hooks/verify.sh",
    ".claude/hooks/verify.ps1",
    ".claude/commands/plan.md",
    ".claude/commands/build.md",
    ".claude/commands/verify.md",
    ".claude/commands/status.md",
    "docs/CONTEXT.md",
    "docs/adr/0000-template.md",
    ".claude/plans/.gitkeep",
    ".claude/state/ledger.md",
    ".claude/state/checkpoints/.gitkeep",
    ".claude/state/handoffs/.gitkeep",
    ".claude/state/research/.gitkeep",
    ".claude/state/agents/.gitkeep",
    ".claude/state/experiments/.gitkeep",
    ".claude/memory/.gitkeep",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required_paths(root: Path) -> None:
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    if missing:
        fail(f"missing required control-plane paths: {', '.join(missing)}")


def check_json(root: Path) -> None:
    try:
        json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f".claude/settings.json is not valid JSON: {exc}")


def check_verify_adapter(root: Path) -> None:
    sys.path.insert(0, str(root / ".claude" / "scripts"))
    import verify_adapter  # noqa: E402

    try:
        targets = verify_adapter.list_targets()
    except verify_adapter.VerifyAdapterError as exc:
        fail(f"verify adapter cannot parse verification manifest: {exc}")
    if not targets["individual_targets"]:
        fail("verify adapter parsed zero verification targets from the manifest")
    result = verify_adapter.run_target("smoke", cwd=root)
    if result["exit_code"] != 0:
        fail(f"verify adapter's own 'smoke' target did not pass: {result}")


def main() -> int:
    check_required_paths(ROOT)
    check_json(ROOT)
    check_verify_adapter(ROOT)
    print("control-plane-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
VERIFY_ADAPTER_PY = '''#!/usr/bin/env python3
"""Code-agnostic verification adapter.

Parses the repo's own `CLAUDE.md` "## Source-of-Truth Commands" fenced
block into named targets. Every gate calls this adapter, never a raw
toolchain command; the adapter never hard-codes a language.

Targets:
  full          every parsed command
  lint          commands whose label matches lint/rule/format
  test          commands whose label matches test (supports --pattern)
  <label-slug>  any individually parsed command
  rubric|citation|factcheck
                non-code verifiers; no shell check exists for model-judged
                review, so these deterministically exit 2 with a protocol
                pointer instead of fabricating a pass/fail signal

Exit codes: 0 pass, 1 fail, 2 unavailable (missing target / unparseable
CLAUDE.md / non-code verifier).
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

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[1]

HEADING = "## Source-of-Truth Commands"
LABEL_RE = re.compile(r"^#\\s*(.+)$")
LINT_LABEL_RE = re.compile(r"lint|rule|format", re.IGNORECASE)
TEST_LABEL_RE = re.compile(r"test", re.IGNORECASE)
NON_CODE_MODES = {
    "rubric": "Rubric verifier: no shell check exists for model-judged review; grade against the task's stated acceptance criteria explicitly, per criterion.",
    "citation": "Citation verifier: no shell check exists for source-grounding review; every claim must cite the primary source it was verified against.",
    "factcheck": "Fact-check verifier: no shell check exists for factual accuracy review; cross-check each claim against its primary source and record any discrepancy explicitly.",
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


def run_target(target: str, *, claude_md: Path | None = None, pattern: str | None = None, cwd: Path | None = None) -> dict[str, Any]:
    claude_md = claude_md or (REPO_ROOT / "CLAUDE.md")
    cwd = cwd or REPO_ROOT

    if target in NON_CODE_MODES:
        return {"target": target, "exit_code": 2, "status": "unavailable", "message": NON_CODE_MODES[target], "commands": []}

    entries = parse_source_of_truth(claude_md)
    selected = resolve_targets(entries, target)
    if not selected:
        return {"target": target, "exit_code": 2, "status": "unavailable", "message": f"no source-of-truth command matched target {target!r}", "commands": [e["slug"] for e in entries]}

    results = []
    overall = 0
    for entry in selected:
        command = _augment_command(entry["command"], pattern=pattern)
        proc = subprocess.run(command, shell=False, cwd=cwd, capture_output=True, text=True)
        if proc.returncode != 0:
            overall = 1
        results.append({"label": entry["label"], "slug": entry["slug"], "command": command, "exit_code": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]})
    return {"target": target, "exit_code": overall, "status": "pass" if overall == 0 else "fail", "message": None, "commands": results}


def list_targets(claude_md: Path | None = None) -> dict[str, Any]:
    claude_md = claude_md or (REPO_ROOT / "CLAUDE.md")
    entries = parse_source_of_truth(claude_md)
    return {"aggregate_targets": ["full", "lint", "test"], "non_code_targets": sorted(NON_CODE_MODES), "individual_targets": [e["slug"] for e in entries]}


def command_run(args: argparse.Namespace) -> int:
    result = run_target(args.target, claude_md=Path(args.claude_md) if args.claude_md else None, pattern=args.pattern)
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
    parser = argparse.ArgumentParser(prog="verify_adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("target")
    p.add_argument("--pattern")
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
'''

LIFECYCLE_PY = '''#!/usr/bin/env python3
"""Task-agnostic lifecycle: atomic plan files, disk-only status
reconstruction, cold-start handoffs, metric-gated experiments. Must
never depend on any specific stack or on ~/.claude/*."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import make_id, now, stable_json, state_root, workspace_root  # noqa: E402

MAX_TASKS_PER_PLAN = 3


class LifecycleError(RuntimeError):
    pass


def _plans_dir(workspace: Path | None = None) -> Path:
    ws = (workspace or workspace_root()).resolve()
    path = ws / ".claude" / "plans"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _plan_path(plan_id: str, workspace: Path | None = None) -> Path:
    return _plans_dir(workspace) / f"{plan_id}.json"


def validate_plan_dict(data: dict[str, Any], *, workspace: Path | None = None) -> None:
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise LifecycleError("plan requires a non-empty title")
    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        raise LifecycleError("plan requires at least one explicit assumption")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise LifecycleError("plan requires at least one task")
    if len(tasks) > MAX_TASKS_PER_PLAN:
        raise LifecycleError(f"plan has {len(tasks)} tasks; atomic plans are capped at {MAX_TASKS_PER_PLAN}")
    seen_ids: set[str] = set()
    for task in tasks:
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise LifecycleError("every task requires a non-empty task_id")
        if task_id in seen_ids:
            raise LifecycleError(f"duplicate task_id: {task_id}")
        seen_ids.add(task_id)
        if not isinstance(task.get("description"), str) or not task["description"].strip():
            raise LifecycleError(f"task {task_id!r} requires a non-empty description")
        verification = task.get("verification")
        if not isinstance(verification, dict) or not str(verification.get("target") or "").strip():
            raise LifecycleError(f"task {task_id!r} requires a verification target")
        if not isinstance(task.get("commit_boundary"), bool):
            raise LifecycleError(f"task {task_id!r} requires an explicit commit_boundary boolean")
    blocking_edges = data.get("blocking_edges", [])
    if not isinstance(blocking_edges, list):
        raise LifecycleError("blocking_edges must be a list of plan_ids")
    for edge in blocking_edges:
        if not _plan_path(str(edge), workspace).exists():
            raise LifecycleError(f"blocking edge references a plan that does not exist on disk: {edge}")


def create_plan(*, title: str, assumptions: list[str], tasks: list[dict[str, Any]], blocking_edges: list[str] | None = None, plan_id: str | None = None, workspace: Path | None = None) -> dict[str, Any]:
    record = {
        "kind": "atomic-plan",
        "plan_id": plan_id or make_id("plan"),
        "title": title,
        "status": "draft",
        "created_at": now(),
        "updated_at": now(),
        "assumptions": assumptions,
        "blocking_edges": blocking_edges or [],
        "tasks": tasks,
    }
    validate_plan_dict(record, workspace=workspace)
    path = _plan_path(record["plan_id"], workspace)
    path.write_text(stable_json(record) + "\\n", encoding="utf-8")
    return record


def load_plan(plan_id: str, *, workspace: Path | None = None) -> dict[str, Any]:
    path = _plan_path(plan_id, workspace)
    if not path.exists():
        raise LifecycleError(f"no plan: {plan_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_plans(*, workspace: Path | None = None) -> list[dict[str, Any]]:
    plans_dir = _plans_dir(workspace)
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(plans_dir.glob("*.json")) if p.name != ".gitkeep"]
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def set_plan_status(plan_id: str, status: str, *, workspace: Path | None = None) -> dict[str, Any]:
    record = load_plan(plan_id, workspace=workspace)
    record["status"] = status
    record["updated_at"] = now()
    _plan_path(plan_id, workspace).write_text(stable_json(record) + "\\n", encoding="utf-8")
    return record


def _read_json_files(directory: Path, glob: str = "*.json") -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.rglob(glob)):
        if path.name == ".gitkeep":
            continue
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def reconstruct_status(*, root: Path | None = None, workspace: Path | None = None) -> dict[str, Any]:
    state = root or state_root()
    ws = workspace or workspace_root()
    plans = list_plans(workspace=ws)
    plan_summary = {
        "total": len(plans),
        "by_status": {},
        "plans": [{"plan_id": p["plan_id"], "title": p["title"], "status": p["status"], "tasks": len(p["tasks"])} for p in plans],
    }
    for p in plans:
        plan_summary["by_status"][p["status"]] = plan_summary["by_status"].get(p["status"], 0) + 1

    ledger_path = state / "ledger.md"
    ledger_tail: list[str] = []
    if ledger_path.exists():
        lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        ledger_tail = lines[-10:]

    checkpoints = _read_json_files(state / "checkpoints", "*.json")
    checkpoints.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    latest_checkpoint = checkpoints[0] if checkpoints else None

    handoffs_dir = state / "handoffs"
    handoff_files = sorted((p for p in handoffs_dir.glob("*.md") if p.name != ".gitkeep"), key=lambda p: p.name, reverse=True) if handoffs_dir.exists() else []

    experiments = _read_json_files(state / "experiments", "*.json")

    return {
        "reconstructed_at": now(),
        "source": "disk-only",
        "plans": plan_summary,
        "ledger_tail": ledger_tail,
        "latest_checkpoint": {"checkpoint_id": latest_checkpoint.get("checkpoint_id"), "verified": latest_checkpoint.get("verified")} if latest_checkpoint else None,
        "recent_handoffs": [p.name for p in handoff_files[:5]],
        "experiments": [{"experiment_id": e.get("experiment_id"), "metric": e.get("metric"), "status": e.get("status")} for e in experiments],
    }


def _handoffs_dir(root: Path | None = None) -> Path:
    path = (root or state_root()) / "handoffs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_handoff(*, session_summary: str, next_steps: str, verification_evidence: list[dict[str, Any]] | None = None, summary_only: bool = False, plan_id: str | None = None, open_risks: str | None = None, root: Path | None = None) -> dict[str, Any]:
    if not summary_only and not verification_evidence:
        raise LifecycleError("handoff requires verification_evidence or explicit summary_only=True")
    handoff_id = make_id("handoff")
    timestamp = now().replace(":", "").replace("-", "")
    path = _handoffs_dir(root) / f"{timestamp}-{handoff_id}.md"
    if summary_only:
        verified_section = "**UNVERIFIED -- summary only.**"
    else:
        rows = "\\n".join(f"| `{e.get('command')}` | {e.get('exit_code')} |" for e in (verification_evidence or []))
        verified_section = f"| Command | Exit code |\\n| --- | --- |\\n{rows}"
    plan_pointer = f"`.claude/plans/{plan_id}.json`" if plan_id else "none referenced"
    body = f"""# Session Handoff: {handoff_id}

Generated: {now()}

## Session Context

{session_summary}

## Verified State

{verified_section}

## What's Next

{next_steps}

## Open Risks / Assumptions

{open_risks or "None recorded."}

## Pointers

- Plan: {plan_pointer}
- Ledger: `.claude/state/ledger.md`
- Status reconstruction: `python3 .claude/scripts/lifecycle.py status`
"""
    path.write_text(body, encoding="utf-8")
    return {"handoff_id": handoff_id, "path": str(path), "verified": not summary_only, "created_at": now()}


def _experiments_dir(root: Path | None = None) -> Path:
    path = (root or state_root()) / "experiments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _experiment_path(experiment_id: str, root: Path | None = None) -> Path:
    return _experiments_dir(root) / f"{experiment_id}.json"


def start_experiment(*, metric: str, baseline_value: float, budget_minutes: int, direction: str = "higher_is_better", experiment_id: str | None = None, root: Path | None = None) -> dict[str, Any]:
    if direction not in ("higher_is_better", "lower_is_better"):
        raise LifecycleError("direction must be 'higher_is_better' or 'lower_is_better'")
    if budget_minutes <= 0:
        raise LifecycleError("budget_minutes must be a positive, fixed budget")
    record = {"kind": "metric-gated-experiment", "experiment_id": experiment_id or make_id("exp"), "metric": metric, "direction": direction, "baseline_value": baseline_value, "budget_minutes": budget_minutes, "status": "running", "observations": [], "decision": None, "started_at": now(), "updated_at": now()}
    _experiment_path(record["experiment_id"], root).write_text(stable_json(record) + "\\n", encoding="utf-8")
    return record


def load_experiment(experiment_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path = _experiment_path(experiment_id, root)
    if not path.exists():
        raise LifecycleError(f"no experiment: {experiment_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def record_observation(experiment_id: str, value: float, *, root: Path | None = None) -> dict[str, Any]:
    record = load_experiment(experiment_id, root=root)
    if record["status"] != "running":
        raise LifecycleError(f"cannot record an observation on a {record['status']} experiment")
    record["observations"].append({"value": value, "at": now()})
    record["updated_at"] = now()
    _experiment_path(experiment_id, root).write_text(stable_json(record) + "\\n", encoding="utf-8")
    return record


def decide_experiment(experiment_id: str, *, root: Path | None = None) -> dict[str, Any]:
    record = load_experiment(experiment_id, root=root)
    if record["status"] != "running":
        raise LifecycleError(f"experiment {experiment_id} was already decided: {record['status']}")
    if not record["observations"]:
        raise LifecycleError("cannot decide an experiment with no recorded observations")
    latest = record["observations"][-1]["value"]
    baseline = record["baseline_value"]
    improved = (latest > baseline) if record["direction"] == "higher_is_better" else (latest < baseline)
    record["decision"] = {"outcome": "keep" if improved else "revert", "latest_value": latest, "baseline_value": baseline, "improved": improved, "decided_at": now()}
    record["status"] = "kept" if improved else "reverted"
    record["updated_at"] = now()
    _experiment_path(experiment_id, root).write_text(stable_json(record) + "\\n", encoding="utf-8")
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan-create")
    p.add_argument("--title", required=True)
    p.add_argument("--tasks-json", required=True)
    p.set_defaults(func=lambda a: print(stable_json(create_plan(title=a.title, **json.loads(Path(a.tasks_json).read_text(encoding="utf-8"))))) or 0)

    p = sub.add_parser("plan-list")
    p.set_defaults(func=lambda a: print(stable_json(list_plans())) or 0)

    p = sub.add_parser("status")
    p.set_defaults(func=lambda a: print(stable_json(reconstruct_status())) or 0)

    p = sub.add_parser("handoff-create")
    p.add_argument("--summary", required=True)
    p.add_argument("--next-steps", required=True)
    p.add_argument("--verification-evidence")
    p.add_argument("--summary-only", action="store_true")
    p.add_argument("--plan-id")
    p.set_defaults(func=lambda a: print(stable_json(create_handoff(session_summary=a.summary, next_steps=a.next_steps, verification_evidence=json.loads(a.verification_evidence) if a.verification_evidence else None, summary_only=a.summary_only, plan_id=a.plan_id))) or 0)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except LifecycleError as exc:
        print(f"lifecycle error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

CONTROL_PLANE_CHECK_PY = '''#!/usr/bin/env python3
"""Generic control-plane validation for a bootstrap-installed repo."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[1]

REQUIRED_PATHS = [
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/rules/00-operating-doctrine.md",
    ".claude/rules/20-lifecycle-gates.md",
    ".claude/rules/30-skill-taxonomy.md",
    ".claude/scripts/verify_adapter.py",
    ".claude/scripts/lifecycle.py",
    ".claude/hooks/verify.sh",
    ".claude/hooks/verify.ps1",
    ".claude/commands/plan.md",
    ".claude/commands/build.md",
    ".claude/commands/verify.md",
    ".claude/commands/status.md",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required_paths(root: Path) -> None:
    missing = [p for p in REQUIRED_PATHS if not (root / p).exists()]
    if missing:
        fail(f"missing required control-plane paths: {', '.join(missing)}")


def check_json(root: Path) -> None:
    try:
        json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f".claude/settings.json is not valid JSON: {exc}")


def check_verify_adapter(root: Path) -> None:
    sys.path.insert(0, str(root / ".claude" / "scripts"))
    import verify_adapter  # noqa: E402

    try:
        targets = verify_adapter.list_targets(claude_md=root / "CLAUDE.md")
    except verify_adapter.VerifyAdapterError as exc:
        fail(f"verify adapter cannot parse CLAUDE.md: {exc}")
    if not targets["individual_targets"]:
        fail("verify adapter parsed zero source-of-truth commands from CLAUDE.md")


def main() -> int:
    check_required_paths(REPO_ROOT)
    check_json(REPO_ROOT)
    check_verify_adapter(REPO_ROOT)
    print("control-plane-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

VERIFY_SH = """#!/usr/bin/env bash
# Thin platform entrypoint for the code-agnostic verify adapter.
set -euo pipefail
script_path="${BASH_SOURCE[0]//\\\\//}"
script_dir="${script_path%/*}"
if [[ "$script_dir" != /* && "$script_dir" != [A-Za-z]:/* ]]; then
  script_dir="$(pwd)/$script_dir"
fi
exec python3 "$script_dir/../scripts/verify_adapter.py" "$@"
"""

VERIFY_PS1 = """# Thin platform entrypoint for the code-agnostic verify adapter.
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$adapter = Join-Path $scriptDir "../scripts/verify_adapter.py"
python3 $adapter @args
exit $LASTEXITCODE
"""

CONTEXT_MD = """# Domain Glossary

| Term | Meaning in this repo | Owning file |
|---|---|---|
| Control plane | The repo-local `.claude/` tree plus root `CLAUDE.md`/`CLAUDE.local.md` | `.claude/rules/00-operating-doctrine.md` |
| Lifecycle gate | One of Align / Research / Plan / Build / Verify & Ship | `.claude/rules/20-lifecycle-gates.md` |
| Verify adapter | The single stack-agnostic entrypoint every gate calls instead of a raw toolchain command | `.claude/hooks/verify.sh`, `.claude/scripts/verify_adapter.py` |
"""

ADR_TEMPLATE = """# ADR NNNN: <short decision title>

- Status: proposed | accepted | superseded by ADR-NNNN
- Date: YYYY-MM-DD

## Context

## Decision

## Alternatives considered

## Consequences
"""


def _command_stub(name: str, purpose: str, artifact: str) -> str:
    return f"""{purpose}

Delegate to the matching skill/agent/script; never call another
`.claude/commands/*.md` file directly (two-axis taxonomy).

- Verification: `.claude/hooks/verify.sh run <target>` (see
  `.claude/scripts/verify_adapter.py list-targets`).
- Durable artifact: `{artifact}`.
"""


COMMAND_STUBS = {
    "brainstorm": ("Gate 1 (open-ended): surface requirements, assumptions, constraints, success criteria.", ".claude/state/research/"),
    "grill": ("Gate 1 (interrogative): stress-test a plan or design against documented constraints before building.", ".claude/state/research/"),
    "research": ("Gate 2: investigate a question; return cited findings, never raw dumps.", ".claude/state/research/<topic>.md"),
    "plan": ("Gate 3: produce an atomic plan (<=3 tasks) with explicit assumptions and a verification target per task.", ".claude/plans/"),
    "build": ("Gate 4: execute one approved plan; one commit per completed task.", "ledger entry; .claude/state/agents/"),
    "verify": ("Gate 5a: re-derive pass/fail from the plan's stated success criteria and the diff, never the builder's narrative.", ".claude/state/checkpoints/"),
    "ship": ("Gate 5b: branch/PR/CI handoff after verify passes.", "ledger entry; PR link"),
    "handoff": ("Cross-cutting: compact the session into a cold-start takeover doc.", ".claude/state/handoffs/"),
    "status": ("Cross-cutting: reconstruct where-are-we purely from `.claude/state/` on disk.", "stdout only (no artifact write)"),
    "debug": ("Cross-cutting: reproduce -> isolate -> hypothesize -> test -> fix -> regression-guard.", "ledger entry"),
    "experiment": ("Cross-cutting: Karpathy AutoResearch loop -- single metric, fixed budget, keep-if-improved/revert-if-not.", ".claude/state/experiments/"),
}


def _skill_stub(name: str, description: str, body: str) -> str:
    return f"""---
name: {name}
description: {description}
---

{body}
"""


SKILL_STUBS = {
    "alignment-interview": (
        "Surface requirements, assumptions, constraints, and success criteria before anything is built, in open-ended or interrogative mode. NOT for stress-testing an already-written plan against existing docs.",
        "Ask about scope, non-goals, and success criteria until every open question is either answered or explicitly deferred. Write the result to `.claude/state/research/` or the issue tracker.",
    ),
    "atomic-planning": (
        "Convert aligned requirements into one or more atomic plans of at most three tasks each, with explicit assumptions, per-task verification targets, and blocking edges. NOT for a long-form PRD.",
        "Use `.claude/scripts/lifecycle.py plan-create` to persist the plan; validate it before treating it as approved.",
    ),
    "session-takeover": (
        "Produce a durable, repo-committed cold-start handoff document under `.claude/state/handoffs/`. NOT a casual scratch note.",
        "Use `.claude/scripts/lifecycle.py handoff-create` with real verification evidence or an explicit `--summary-only` flag.",
    ),
    "metric-gated-experiment": (
        "Run a Karpathy AutoResearch loop for optimization or tuning work: one named metric, a fixed budget, keep-if-improved/revert-if-not. NOT for correctness fixes.",
        "Use `.claude/scripts/lifecycle.py` experiment-start/-record/-decide (via bootstrap-generated CLI); never claim improvement without a decided experiment.",
    ),
}

GITIGNORE_ENTRIES = [
    "CLAUDE.local.md",
    ".claude/settings.local.json",
]


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------


def _write_if_missing(path: Path, content: str, created: list[str], preserved: list[str]) -> None:
    if path.exists():
        preserved.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    created.append(str(path))


def scaffold_tree(target: Path, *, dry_run: bool = False) -> dict[str, list[str]]:
    created: list[str] = []
    preserved: list[str] = []
    plan: dict[str, str] = {
        ".claude/rules/00-operating-doctrine.md": OPERATING_DOCTRINE,
        ".claude/rules/10-karpathy-guidelines.md": KARPATHY_GUIDELINES,
        ".claude/rules/20-lifecycle-gates.md": LIFECYCLE_GATES,
        ".claude/rules/30-skill-taxonomy.md": SKILL_TAXONOMY,
        ".claude/scripts/common.py": COMMON_PY,
        ".claude/scripts/verification_manifest.py": VERIFICATION_MANIFEST_SOURCE,
        ".claude/scripts/verify_adapter.py": VERIFY_ADAPTER_PY_V2,
        ".claude/scripts/lifecycle.py": LIFECYCLE_PY,
        ".claude/scripts/control_plane_check.py": CONTROL_PLANE_CHECK_PY_V2,
        ".claude/hooks/verify.sh": VERIFY_SH,
        ".claude/hooks/verify.ps1": VERIFY_PS1,
        "docs/CONTEXT.md": CONTEXT_MD,
        "docs/adr/0000-template.md": ADR_TEMPLATE,
        ".claude/plans/.gitkeep": "",
        ".claude/state/ledger.md": "# Ledger\n\nAppend-only. One entry per completed unit of work.\n",
        ".claude/state/checkpoints/.gitkeep": "",
        ".claude/state/handoffs/.gitkeep": "",
        ".claude/state/research/.gitkeep": "",
        ".claude/state/agents/.gitkeep": "",
        ".claude/state/experiments/.gitkeep": "",
        ".claude/memory/.gitkeep": "",
    }
    for name, (purpose, artifact) in COMMAND_STUBS.items():
        plan[f".claude/commands/{name}.md"] = _command_stub(name, purpose, artifact)
    for name, (description, body) in SKILL_STUBS.items():
        plan[f".claude/skills/{name}/SKILL.md"] = _skill_stub(name, description, body)

    if dry_run:
        return {
            "would_create": [str(target / rel) for rel in plan if not (target / rel).exists()],
            "would_preserve": [str(target / rel) for rel in plan if (target / rel).exists()],
        }

    for rel, content in plan.items():
        _write_if_missing(target / rel, content, created, preserved)
    return {"created": created, "preserved": preserved}


def merge_claude_md(target: Path, facts: Facts) -> str:
    path = target / "CLAUDE.md"
    commands_block_lines = [
        "## Verification Manifest",
        "",
        "The machine-readable verification manifest lives at `.claude/verification-manifest.json`.",
        "Update that file when verification commands change; the adapter reads the manifest directly.",
        "",
        "```bash",
    ]
    if facts.build_command:
        commands_block_lines += ["# build", facts.build_command, ""]
    if facts.test_command:
        commands_block_lines += ["# test", facts.test_command, ""]
    if facts.lint_command:
        commands_block_lines += ["# lint", facts.lint_command, ""]
    if not any([facts.build_command, facts.test_command, facts.lint_command]):
        commands_block_lines += ["# rubric", "echo 'no shell-checkable command for this repo; use rubric/citation/factcheck verifiers'", ""]
    commands_block_lines += ["```", ""]
    facts_block = "\n".join(
        [
            "## Repo Facts (bootstrap-generated)",
            "",
            f"- Issue tracker: {facts.issue_tracker}",
            f"- Commit convention: {facts.commit_convention}",
            f"- Mandatory gates: {', '.join(facts.mandatory_gates)}",
            f"- Skippable gates: {', '.join(facts.skippable_gates)}",
            f"- Memory policy: {facts.memory_policy}",
            f"- Platform: {facts.platform}",
            "",
        ]
    )
    commands_block = "\n".join(commands_block_lines)

    if not path.exists():
        content = (
            "# Project Control Plane\n\n"
            "Installed by `/bootstrap-control-plane`.\n\n"
            f"{commands_block}\n{facts_block}"
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return "created"

    text = path.read_text(encoding="utf-8")
    if "## Verification Manifest" in text or "## Source-of-Truth Commands" in text:
        return "preserved"  # never overwrite an existing customized facts block
    text = text.rstrip() + "\n\n" + commands_block + "\n" + facts_block
    path.write_text(text, encoding="utf-8", newline="\n")
    return "appended"


def bootstrap_local_settings(target: Path) -> dict[str, Any]:
    """Additive-only, mirrors `phase2_memory.bootstrap_local_settings`."""
    target_path = target / ".claude" / "settings.local.json"
    desired_memory_dir = str((target / ".claude" / "memory").resolve())

    if target_path.exists():
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - fail closed
            raise RuntimeError(f"{target_path} is not valid JSON, refusing to overwrite: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"{target_path} does not contain a JSON object, refusing to overwrite")
        if data.get("autoMemoryDirectory") == desired_memory_dir:
            return {"status": "unchanged", "path": str(target_path)}
        data["autoMemoryDirectory"] = desired_memory_dir
        target_path.write_text(stable_json(data) + "\n", encoding="utf-8")
        return {"status": "updated", "path": str(target_path)}

    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "version": 1,
        "description": "Personal project overrides. Do not commit real local secrets.",
        "autoMemoryDirectory": desired_memory_dir,
    }
    target_path.write_text(stable_json(data) + "\n", encoding="utf-8")
    return {"status": "created", "path": str(target_path)}


def bootstrap_settings_json(target: Path) -> str:
    path = target / ".claude" / "settings.json"
    if path.exists():
        return "preserved"
    data = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "version": 1,
        "description": "Shared project Claude Code settings, generated by /bootstrap-control-plane.",
        "plansDirectory": "./.claude/plans",
        "permissions": {"mode": "ask", "allow": [], "deny": []},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(data) + "\n", encoding="utf-8")
    return "created"


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=os.name != "nt")


def bootstrap_verification_manifest(target: Path, facts: Facts) -> str:
    path = target / ".claude" / "verification-manifest.json"
    if path.exists():
        return "preserved"
    targets: list[dict[str, Any]] = []
    if facts.build_command:
        targets.append({"id": "build", "label": "build", "command": _split_command(facts.build_command)})
    if facts.test_command:
        targets.append({"id": "test", "label": "test", "command": _split_command(facts.test_command)})
    if facts.lint_command:
        targets.append({"id": "lint", "label": "lint", "command": _split_command(facts.lint_command)})
    targets.append({"id": "smoke", "label": "smoke", "command": ["python3", "-c", "print('smoke ok')"]})
    data = {"schema_version": 1, "targets": targets}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(data) + "\n", encoding="utf-8")
    return "created"


def update_gitignore(target: Path) -> list[str]:
    path = target / ".gitignore"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    existing_set = set(line.strip() for line in existing)
    added = [entry for entry in GITIGNORE_ENTRIES if entry not in existing_set]
    if added:
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            if existing and existing[-1].strip():
                fh.write("\n")
            fh.write("# Added by /bootstrap-control-plane\n")
            for entry in added:
                fh.write(entry + "\n")
    return added


def validate(target: Path) -> dict[str, Any]:
    sys.path.insert(0, str(target / ".claude" / "scripts"))
    for mod in ("verify_adapter", "verification_manifest", "lifecycle", "control_plane_check"):
        sys.modules.pop(mod, None)
    import control_plane_check  # noqa: E402

    try:
        control_plane_check.check_required_paths(target)
        control_plane_check.check_json(target)
        control_plane_check.check_verify_adapter(target)
    except SystemExit as exc:
        return {"status": "fail", "exit_code": exc.code}
    return {"status": "pass"}


def run_smoke(target: Path) -> dict[str, Any]:
    """Trivial five-gate smoke workflow: exercise each gate's durable
    artifact using only the bootstrap-installed scripts."""
    sys.path.insert(0, str(target / ".claude" / "scripts"))
    for mod in ("verify_adapter", "verification_manifest", "lifecycle", "common"):
        sys.modules.pop(mod, None)
    import lifecycle  # noqa: E402
    import verify_adapter  # noqa: E402

    results: dict[str, Any] = {}

    # Gate 1: Align -- research note as the durable artifact.
    research_note = target / ".claude" / "state" / "research" / "smoke-align.md"
    research_note.write_text("# Smoke Align\n\nTrivial task: prove the five gates run end to end.\n", encoding="utf-8")
    results["align"] = {"artifact": str(research_note), "exists": research_note.exists()}

    # Gate 2: Research -- cited finding.
    finding_note = target / ".claude" / "state" / "research" / "smoke-research.md"
    finding_note.write_text("# Smoke Research\n\nFinding: bootstrap-generated CLAUDE.md exists. Source: CLAUDE.md.\n", encoding="utf-8")
    results["research"] = {"artifact": str(finding_note), "exists": finding_note.exists()}

    # Gate 3: Plan -- one atomic plan, one task.
    plan = lifecycle.create_plan(
        title="Smoke plan",
        assumptions=["Bootstrap scaffolding already exists."],
        tasks=[{"task_id": "t1", "description": "Touch a smoke file.", "verification": {"target": "smoke"}, "commit_boundary": False}],
        workspace=target,
    )
    results["plan"] = {"plan_id": plan["plan_id"], "status": plan["status"]}

    # Gate 4: Build -- touch a file (no git commit in the smoke test).
    build_marker = target / ".claude" / "state" / "smoke-build-marker.txt"
    build_marker.write_text("built\n", encoding="utf-8")
    results["build"] = {"artifact": str(build_marker), "exists": build_marker.exists()}

    # Gate 5: Verify & Ship -- run the verify adapter's "smoke" target.
    verify_result = verify_adapter.run_target("smoke", cwd=target)
    results["verify"] = verify_result

    status = lifecycle.reconstruct_status(root=target / ".claude" / "state", workspace=target)
    results["status_reconstruction"] = status
    results["all_artifacts_present"] = all(
        [research_note.exists(), finding_note.exists(), plan["plan_id"], build_marker.exists()]
    )
    return results


def add_smoke_target_to_claude_md(target: Path) -> None:
    """Ensure CLAUDE.md's Source-of-Truth block has a `smoke` target so
    `run_smoke` has a trivially-passing verify step even in a docs-only
    repo with no other shell-checkable command."""
    path = target / "CLAUDE.md"
    text = path.read_text(encoding="utf-8")
    if "# smoke" in text:
        return
    marker = "```bash"
    idx = text.find(marker)
    if idx == -1:
        return
    insert_at = idx + len(marker)
    smoke_line = "\n# smoke\npython3 -c \"print('smoke ok')\"\n"
    text = text[:insert_at] + smoke_line + text[insert_at:]
    path.write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def command_run(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    facts = Facts.from_dict(json.loads(Path(args.facts_json).read_text(encoding="utf-8"))) if args.facts_json else detect_stack(target)

    if args.dry_run:
        print(stable_json(scaffold_tree(target, dry_run=True)))
        return 0

    tree_result = scaffold_tree(target)
    claude_md_result = merge_claude_md(target, facts)
    manifest_result = bootstrap_verification_manifest(target, facts)
    settings_result = bootstrap_settings_json(target)
    local_settings_result = bootstrap_local_settings(target)
    gitignore_result = update_gitignore(target)

    print(
        stable_json(
            {
                "target": str(target),
                "facts": facts.to_dict(),
                "tree": tree_result,
                "claude_md": claude_md_result,
                "verification_manifest": manifest_result,
                "settings_json": settings_result,
                "settings_local_json": local_settings_result,
                "gitignore_added": gitignore_result,
            }
        )
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    result = validate(Path(args.target).resolve())
    print(stable_json(result))
    return 0 if result["status"] == "pass" else 1


def command_smoke(args: argparse.Namespace) -> int:
    result = run_smoke(Path(args.target).resolve())
    print(stable_json(result))
    return 0 if result["verify"]["exit_code"] == 0 and result["all_artifacts_present"] else 1


def command_facts(args: argparse.Namespace) -> int:
    print(stable_json(detect_stack(Path(args.target).resolve()).to_dict()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bootstrap_control_plane")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run")
    p.add_argument("--target", required=True)
    p.add_argument("--facts-json")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=command_run)

    p = sub.add_parser("validate")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_validate)

    p = sub.add_parser("smoke")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_smoke)

    p = sub.add_parser("facts")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_facts)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

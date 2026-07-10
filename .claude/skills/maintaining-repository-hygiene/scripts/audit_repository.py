#!/usr/bin/env python3
"""Read-only, code-agnostic repository audit engine."""
from __future__ import annotations

import fnmatch
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

from hygiene_core import (
    Coverage,
    Finding,
    command_exists,
    evidence,
    git_text,
    make_finding,
    read_text_bounded,
    repository_identity,
    run,
    run_json,
    safe_relative,
    tracked_files,
    utc_now,
)

MANIFEST_RULES: list[tuple[str, str, str]] = [
    ("package.json", "javascript-typescript", "npm-compatible"),
    ("pyproject.toml", "python", "pyproject"),
    ("setup.py", "python", "setuptools"),
    ("setup.cfg", "python", "setuptools"),
    ("requirements.txt", "python", "pip"),
    ("Pipfile", "python", "pipenv"),
    ("Cargo.toml", "rust", "cargo"),
    ("go.mod", "go", "go-modules"),
    ("pom.xml", "java-jvm", "maven"),
    ("build.gradle", "java-jvm", "gradle"),
    ("build.gradle.kts", "java-kotlin-jvm", "gradle"),
    ("Gemfile", "ruby", "bundler"),
    ("composer.json", "php", "composer"),
    ("Package.swift", "swift", "swift-package-manager"),
    ("mix.exs", "elixir", "mix"),
    ("pubspec.yaml", "dart-flutter", "pub"),
    ("CMakeLists.txt", "c-cpp", "cmake"),
    ("meson.build", "c-cpp", "meson"),
    ("WORKSPACE", "bazel", "bazel"),
    ("WORKSPACE.bazel", "bazel", "bazel"),
    ("MODULE.bazel", "bazel", "bazel"),
    ("go.work", "go", "go-workspaces"),
    ("flake.nix", "nix", "nix-flakes"),
    ("Dockerfile", "containers", "docker"),
    ("docker-compose.yml", "containers", "docker-compose"),
    ("docker-compose.yaml", "containers", "docker-compose"),
    ("Chart.yaml", "kubernetes-helm", "helm"),
    ("main.tf", "terraform", "terraform"),
]

LOCKFILES = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "Cargo.lock": "cargo",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
    "Package.resolved": "swift-package-manager",
    "mix.lock": "mix",
    "pubspec.lock": "pub",
}

DEPENDABOT_ECOSYSTEMS = {
    "javascript-typescript": "npm",
    "python": "pip",
    "rust": "cargo",
    "go": "gomod",
    "java-jvm": "maven",
    "java-kotlin-jvm": "gradle",
    "ruby": "bundler",
    "php": "composer",
    "swift": "swift",
    "elixir": "mix",
    "dart-flutter": "pub",
    "terraform": "terraform",
    "containers": "docker",
    "github-actions": "github-actions",
}

FRAMEWORK_PATTERNS: list[tuple[str, str, str]] = [
    ("javascript-typescript", r'"next"\s*:', "Next.js"),
    ("javascript-typescript", r'"react"\s*:', "React"),
    ("javascript-typescript", r'"vue"\s*:', "Vue"),
    ("javascript-typescript", r'"nuxt"\s*:', "Nuxt"),
    ("javascript-typescript", r'"svelte"\s*:', "Svelte"),
    ("javascript-typescript", r'"@angular/core"\s*:', "Angular"),
    ("javascript-typescript", r'"express"\s*:', "Express"),
    ("javascript-typescript", r'"@nestjs/core"\s*:', "NestJS"),
    ("javascript-typescript", r'"vite"\s*:', "Vite"),
    ("javascript-typescript", r'"electron"\s*:', "Electron"),
    ("javascript-typescript", r'"@tauri-apps/', "Tauri frontend"),
    ("python", r"\bdjango\b", "Django"),
    ("python", r"\bfastapi\b", "FastAPI"),
    ("python", r"\bflask\b", "Flask"),
    ("python", r"\bpytest\b", "pytest"),
    ("python", r"\bmkdocs\b", "MkDocs"),
    ("python", r"\bsphinx\b", "Sphinx"),
    ("rust", r"\btauri\b", "Tauri"),
    ("rust", r"\baxum\b", "Axum"),
    ("rust", r"\bactix-web\b", "Actix Web"),
    ("rust", r"\btokio\b", "Tokio"),
    ("go", r"github\.com/gin-gonic/gin", "Gin"),
    ("go", r"github\.com/labstack/echo", "Echo"),
    ("go", r"github\.com/gofiber/fiber", "Fiber"),
    ("java-jvm", r"spring-boot", "Spring Boot"),
    ("java-kotlin-jvm", r"spring-boot", "Spring Boot"),
    ("java-kotlin-jvm", r"ktor", "Ktor"),
    ("ruby", r"\brails\b", "Rails"),
    ("php", r"laravel/framework", "Laravel"),
    ("dart-flutter", r"flutter:", "Flutter"),
]

COMMUNITY_LOCATIONS = [".github", "", "docs"]


def _path_has_name(path: str, name: str) -> bool:
    return Path(path).name.casefold() == name.casefold()


def _find_community_file(files: set[str], names: Iterable[str]) -> str | None:
    lowered = {path.casefold(): path for path in files}
    for directory in COMMUNITY_LOCATIONS:
        for name in names:
            candidate = f"{directory}/{name}" if directory else name
            if candidate.casefold() in lowered:
                return lowered[candidate.casefold()]
    return None


def _json_file(repo: Path, relative: str) -> dict[str, Any] | None:
    try:
        value = json.loads((repo / relative).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def detect_stack(repo: Path, files: list[str], max_text_bytes: int) -> dict[str, Any]:
    ecosystems: dict[str, dict[str, Any]] = {}
    package_managers: dict[str, list[str]] = defaultdict(list)
    manifests: list[dict[str, str]] = []
    framework_evidence: dict[str, list[str]] = defaultdict(list)
    commands: dict[str, list[dict[str, str]]] = defaultdict(list)
    workspace_evidence: list[str] = []

    for path in files:
        basename = Path(path).name
        for target, ecosystem, manager_hint in MANIFEST_RULES:
            if basename == target:
                ecosystems.setdefault(ecosystem, {"evidence": [], "confidence": "high"})["evidence"].append(path)
                manifests.append({"path": path, "ecosystem": ecosystem, "manager_hint": manager_hint})
        if basename in LOCKFILES:
            package_managers[LOCKFILES[basename]].append(path)

    if any(path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")) for path in files):
        ecosystems.setdefault("github-actions", {"evidence": [], "confidence": "high"})["evidence"].append(".github/workflows/")
        package_managers["github-actions"].append(".github/workflows/")

    for manifest in manifests:
        path = manifest["path"]
        text = read_text_bounded(repo / path, max_text_bytes)
        if text is None:
            continue
        ecosystem = manifest["ecosystem"]
        for target_ecosystem, pattern, framework in FRAMEWORK_PATTERNS:
            if ecosystem == target_ecosystem and re.search(pattern, text, re.IGNORECASE):
                framework_evidence[framework].append(path)

        if Path(path).name == "package.json":
            payload = _json_file(repo, path)
            if payload:
                for name, value in (payload.get("scripts") or {}).items():
                    if isinstance(name, str) and isinstance(value, str):
                        commands[name].append({"command": f"<package-manager> run {name}", "source": path, "definition": value})
                if payload.get("workspaces"):
                    workspace_evidence.append(f"{path}:workspaces")
                manager = payload.get("packageManager")
                if isinstance(manager, str) and manager:
                    package_managers[manager.split("@", 1)[0]].append(f"{path}:packageManager")
        if Path(path).name == "Cargo.toml" and re.search(r"(?m)^\s*\[workspace\]", text):
            workspace_evidence.append(f"{path}:[workspace]")
        if Path(path).name == "pyproject.toml":
            for tool, command in (("pytest", "pytest"), ("ruff", "ruff check ."), ("mypy", "mypy .")):
                if re.search(rf"(?im)^\s*\[tool\.{re.escape(tool)}", text) or re.search(rf"(?i)\b{tool}\b", text):
                    commands[tool].append({"command": command, "source": path, "definition": "detected tool configuration"})

    for marker in ("pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json", "go.work"):
        for path in files:
            if Path(path).name == marker:
                workspace_evidence.append(path)

    # Add ecosystem-native defaults only when direct evidence exists.
    if "rust" in ecosystems:
        commands["build"].append({"command": "cargo build --locked", "source": "Cargo.toml", "definition": "ecosystem default"})
        commands["test"].append({"command": "cargo test --locked", "source": "Cargo.toml", "definition": "ecosystem default"})
    if "go" in ecosystems:
        commands["test"].append({"command": "go test ./...", "source": "go.mod", "definition": "ecosystem default"})
    if "java-jvm" in ecosystems or "java-kotlin-jvm" in ecosystems:
        if any(Path(path).name == "pom.xml" for path in files):
            commands["test"].append({"command": "mvn test", "source": "pom.xml", "definition": "ecosystem default"})
        if any(Path(path).name.startswith("gradlew") for path in files):
            commands["test"].append({"command": "./gradlew test", "source": "gradlew", "definition": "wrapper default"})
    if any(path.endswith((".sln", ".csproj", ".fsproj")) for path in files):
        ecosystems.setdefault("dotnet", {"evidence": [], "confidence": "high"})["evidence"].extend(
            path for path in files if path.endswith((".sln", ".csproj", ".fsproj"))
        )
        package_managers["nuget"].append("*.csproj/*.sln")
        commands["build"].append({"command": "dotnet build", "source": "*.sln/*.csproj", "definition": "ecosystem default"})
        commands["test"].append({"command": "dotnet test", "source": "*.sln/*.csproj", "definition": "ecosystem default"})

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "ecosystems": [
            {"name": key, "confidence": value["confidence"], "evidence": sorted(set(value["evidence"]))}
            for key, value in sorted(ecosystems.items())
        ],
        "frameworks": [
            {"name": key, "confidence": "medium", "evidence": sorted(set(value))}
            for key, value in sorted(framework_evidence.items())
        ],
        "package_managers": [
            {"name": key, "evidence": sorted(set(value))} for key, value in sorted(package_managers.items())
        ],
        "manifests": sorted(manifests, key=lambda item: item["path"]),
        "workspace": {"detected": bool(workspace_evidence), "evidence": sorted(set(workspace_evidence))},
        "commands": {key: value for key, value in sorted(commands.items())},
        "confidence": "high" if manifests else "low",
    }


def _package_manager_conflicts(stack: dict[str, Any]) -> list[tuple[str, list[str]]]:
    manager_paths = {item["name"]: item["evidence"] for item in stack["package_managers"]}
    js = {name: paths for name, paths in manager_paths.items() if name in {"npm", "yarn", "pnpm", "bun"}}
    by_directory: dict[str, set[str]] = defaultdict(set)
    for manager, paths in js.items():
        for path in paths:
            clean = path.split(":", 1)[0]
            by_directory[str(Path(clean).parent)].add(manager)
    return [(directory, sorted(managers)) for directory, managers in sorted(by_directory.items()) if len(managers) > 1]


def audit_stack(repo: Path, files: list[str], stack: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for directory, managers in _package_manager_conflicts(stack):
        findings.append(make_finding(
            rule_id="STACK-CONFLICTING-PACKAGE-MANAGERS",
            category="stack",
            severity="medium",
            confidence="high",
            title=f"Resolve conflicting JavaScript package managers in {directory or 'repository root'}",
            summary=f"Multiple JavaScript package-manager lockfiles or declarations exist in the same project boundary: {', '.join(managers)}.",
            evidence_items=[evidence(directory or ".", f"Detected managers: {', '.join(managers)}")],
            remediation_key=f"stack/package-manager/{directory or 'root'}",
            actions=["Select the canonical package manager for this project boundary.", "Remove contradictory lockfiles only after regenerating and validating the retained lockfile.", "Align README and CI install commands."],
            acceptance=["Exactly one canonical JavaScript package manager is declared for the project boundary.", "CI and contributor documentation use the same package manager."],
            verification=["Inspect lockfiles and packageManager declarations.", "Run the repository's canonical install and test commands."],
        ))
    if not stack["ecosystems"]:
        findings.append(make_finding(
            rule_id="STACK-NO-MANIFEST",
            category="stack",
            severity="info",
            confidence="high",
            title="Document the repository's nonstandard build topology",
            summary="No recognized package, build, infrastructure, or container manifest was found.",
            evidence_items=[evidence("git ls-files", "No recognized manifest detected")],
            remediation_key="stack/document-topology",
            actions=["Document how the repository is built, tested, and released, or add the canonical manifest if one is missing."],
            acceptance=["The repository has an evidence-backed development workflow."],
            verification=["Review README and automation for install/build/test commands."],
            actionable=False,
        ))
    return findings


def _tracked_match(path: str, pattern: str) -> bool:
    name = Path(path).name
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern)


def audit_repository_contents(repo: Path, files: list[str], policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    file_set = set(files)
    generated = policy.get("generated_or_vendor_directories", [])
    sensitive = policy.get("sensitive_tracked_patterns", [])

    sensitive_paths = sorted({path for path in files for pattern in sensitive if _tracked_match(path, pattern)})
    if sensitive_paths:
        findings.append(make_finding(
            rule_id="CONTENTS-SENSITIVE-FILENAMES",
            category="repository-contents",
            severity="critical",
            confidence="medium",
            title="Remove and rotate potentially sensitive tracked files",
            summary="Tracked paths match credential or secret filename patterns. Contents were not read or printed.",
            evidence_items=[evidence(path, "Tracked path matches a sensitive filename pattern") for path in sensitive_paths[:100]],
            remediation_key="contents/sensitive-files",
            actions=["Determine whether each file contains live secret material without exposing it in issue text.", "Rotate any exposed credentials before rewriting history.", "Remove secrets from the current tree and add precise ignore rules.", "Use an approved history-rewrite procedure only after coordination."],
            acceptance=["No live credentials remain in the repository or history.", "Affected credentials are rotated and invalidated.", "Preventive scanning or push protection is enabled where available."],
            verification=["git ls-files | inspect against sensitive patterns", "Run the repository's approved secret scanner."],
            destructive=True,
            non_goals=["Do not paste secret values into issues, logs, or remediation commits."],
        ))

    generated_paths = sorted({path for path in files for prefix in generated if path.startswith(prefix) or f"/{prefix}" in path})
    if generated_paths:
        findings.append(make_finding(
            rule_id="CONTENTS-TRACKED-GENERATED",
            category="repository-contents",
            severity="medium",
            confidence="medium",
            title="Remove unintentionally tracked generated or dependency artifacts",
            summary="Tracked files appear inside common generated, cache, virtual-environment, dependency, or build-output directories.",
            evidence_items=[evidence(path, "Tracked under a generated/vendor directory policy pattern") for path in generated_paths[:100]],
            remediation_key="contents/generated-artifacts",
            actions=["Classify each matched directory as source, vendored dependency, or generated output.", "Remove only unintended generated content from version control.", "Add narrowly scoped ignore rules and document intentional vendoring."],
            acceptance=["Generated artifacts are either untracked and ignored or explicitly documented as intentionally versioned."],
            verification=["git ls-files", "git status --ignored --short"],
            destructive=True,
        ))

    large = []
    for path in files:
        try:
            size = (repo / path).stat().st_size
        except OSError:
            continue
        if size >= int(policy.get("large_file_bytes", 10 * 1024 * 1024)):
            large.append((path, size))
    if large:
        severity = "high" if any(size >= int(policy.get("very_large_file_bytes", 50 * 1024 * 1024)) for _, size in large) else "medium"
        findings.append(make_finding(
            rule_id="CONTENTS-LARGE-TRACKED-FILES",
            category="repository-contents",
            severity=severity,
            confidence="high",
            title="Move or justify large tracked files",
            summary="Large tracked files increase clone cost and may exceed hosting or workflow constraints.",
            evidence_items=[evidence(path, f"Tracked file size: {size} bytes") for path, size in sorted(large, key=lambda x: -x[1])[:100]],
            remediation_key="contents/large-files",
            actions=["Classify each large file as source, release artifact, dataset, or accidental output.", "Move appropriate binaries to Git LFS or release storage.", "Document intentionally retained large assets."],
            acceptance=["Each large tracked file has an explicit repository-appropriate storage decision."],
            verification=["git ls-files -z | size inventory", "git count-objects -vH"],
            destructive=True,
            references=["https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github"],
        ))

    if ".gitignore" not in file_set and any(item["name"] not in {"github-actions"} for item in detect_stack(repo, files, int(policy.get("max_text_file_bytes", 1048576)))["ecosystems"]):
        findings.append(make_finding(
            rule_id="CONTENTS-MISSING-GITIGNORE",
            category="repository-contents",
            severity="low",
            confidence="medium",
            title="Add a stack-aligned .gitignore",
            summary="The repository contains a detected development stack but no tracked .gitignore.",
            evidence_items=[evidence("git ls-files", "No .gitignore found")],
            remediation_key="contents/gitignore",
            actions=["Create a minimal .gitignore derived from detected generated outputs and local tooling.", "Avoid broad patterns that hide source or configuration."],
            acceptance=["Common generated outputs are ignored without hiding required source files."],
            verification=["git status --ignored --short", "Review .gitignore patterns against tracked files."],
        ))
    return findings


def audit_worktrees_and_branches(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    dry = run(["git", "worktree", "prune", "--dry-run", "--verbose", "--expire", "now"], cwd=repo)
    output = (dry.stdout + dry.stderr).strip()
    if dry.returncode == 0 and output:
        findings.append(make_finding(
            rule_id="GIT-STALE-WORKTREE-METADATA",
            category="git",
            severity="low",
            confidence="high",
            title="Prune stale Git worktree administrative records",
            summary="Git reports stale linked-worktree administrative metadata. The dry run does not identify live worktree directories for deletion.",
            evidence_items=[evidence("git worktree prune --dry-run --verbose --expire now", line, command="git worktree prune --dry-run --verbose --expire now") for line in output.splitlines()[:100]],
            remediation_key="git/worktree-prune",
            actions=["Review the generated worktree-prune plan.", "Lock any intentionally offline worktree before pruning.", "Execute the digest-confirmed prune operation."],
            acceptance=["A fresh worktree prune dry-run reports no stale administrative entries.", "All live or intentionally offline worktrees remain registered or locked."],
            verification=["git worktree list --porcelain", "git worktree prune --dry-run --verbose --expire now"],
            destructive=True,
            references=["https://git-scm.com/docs/git-worktree"],
        ))

    gone = run(["git", "for-each-ref", "--format=%(refname:short)%00%(upstream:track)", "refs/heads"], cwd=repo)
    gone_branches: list[str] = []
    if gone.returncode == 0:
        for row in gone.stdout.splitlines():
            parts = row.split("\x00", 1)
            if len(parts) == 2 and "gone" in parts[1]:
                gone_branches.append(parts[0])
    if gone_branches:
        findings.append(make_finding(
            rule_id="GIT-GONE-UPSTREAM-BRANCHES",
            category="git",
            severity="low",
            confidence="high",
            title="Review local branches whose upstream is gone",
            summary="Local branches reference remote-tracking branches that no longer exist.",
            evidence_items=[evidence("git for-each-ref", branch) for branch in sorted(gone_branches)],
            remediation_key="git/gone-upstream-branches",
            actions=["Check each branch for unique commits and active worktrees.", "Back up or push any work that must be retained.", "Delete only branches proven obsolete."],
            acceptance=["Every gone-upstream branch is retained with rationale, republished, or safely deleted."],
            verification=["git branch -vv", "git log --cherry --oneline <upstream>...<branch>"],
            destructive=True,
        ))
    return findings


def _workflow_files(files: list[str]) -> list[str]:
    return sorted(path for path in files if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")))


def _uses_occurrences(text: str) -> list[tuple[int, str]]:
    results = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = re.search(r"\buses:\s*['\"]?([^'\"\s#]+)", line)
        if match:
            results.append((line_no, match.group(1)))
    return results


def _is_local_or_docker_action(reference: str) -> bool:
    return reference.startswith("./") or reference.startswith("docker://")


def _is_full_sha(reference: str) -> bool:
    if "@" not in reference:
        return False
    revision = reference.rsplit("@", 1)[1]
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", revision))


def _workflow_has_top_permissions(text: str) -> bool:
    return bool(re.search(r"(?m)^permissions:\s*(?:\{\}|read-all|write-all)?\s*(?:#.*)?$", text))


def audit_github_folder(repo: Path, files: list[str], stack: dict[str, Any], policy: dict[str, Any], remote: dict[str, Any] | None) -> tuple[list[Finding], list[Coverage]]:
    findings: list[Finding] = []
    coverage: list[Coverage] = []
    file_set = set(files)
    workflows = _workflow_files(files)

    yaml_available = False
    try:
        import yaml  # type: ignore
        yaml_available = True
    except Exception:
        yaml = None  # type: ignore
    if yaml_available:
        malformed = []
        for path in workflows:
            text = read_text_bounded(repo / path, int(policy.get("max_text_file_bytes", 1048576)))
            if text is None:
                continue
            try:
                yaml.safe_load(text)
            except Exception as exc:
                malformed.append((path, str(exc).splitlines()[0]))
        coverage.append(Coverage("workflow-yaml-parse", "complete", "Parsed workflows with PyYAML."))
        for path, error in malformed:
            findings.append(make_finding(
                rule_id="GHA-YAML-INVALID",
                category="github-actions",
                severity="high",
                confidence="high",
                title=f"Repair invalid workflow YAML in {path}",
                summary="The workflow cannot be parsed as YAML.",
                evidence_items=[evidence(path, error)],
                remediation_key=f"github-actions/yaml/{path}",
                actions=["Repair the YAML syntax without changing workflow intent.", "Validate the workflow with a YAML parser and action-specific linter."],
                acceptance=["The workflow parses successfully and appears in GitHub Actions."],
                verification=[f"python -c \"import yaml; yaml.safe_load(open('{path}', encoding='utf-8'))\"", f"actionlint {path}"],
            ))
    else:
        coverage.append(Coverage("workflow-yaml-parse", "degraded", "PyYAML unavailable; structural workflow checks used text-level analysis only."))

    for path in workflows:
        text = read_text_bounded(repo / path, int(policy.get("max_text_file_bytes", 1048576)))
        if text is None:
            coverage.append(Coverage(f"workflow:{path}", "degraded", "File exceeded text scan limit or was unreadable."))
            continue
        workflow_key = f"github-actions/harden/{path}"
        items: list[tuple[str, str, int | None, str, str]] = []
        if policy.get("require_workflow_permissions", True) and not _workflow_has_top_permissions(text):
            items.append(("GHA-PERMISSIONS-MISSING", "Workflow does not declare top-level permissions.", None, "high", "Add explicit least-privilege top-level permissions and job overrides only where required."))
        if re.search(r"(?m)^permissions:\s*write-all\s*$", text):
            line = next((i for i, value in enumerate(text.splitlines(), 1) if re.match(r"^permissions:\s*write-all", value)), None)
            items.append(("GHA-PERMISSIONS-WRITE-ALL", "Workflow grants write-all permissions.", line, "high", "Replace write-all with the minimum named permissions required by each job."))
        unpinned = [(line, ref) for line, ref in _uses_occurrences(text) if not _is_local_or_docker_action(ref) and not _is_full_sha(ref)]
        if policy.get("require_action_sha_pinning", True) and unpinned:
            for line, ref in unpinned:
                items.append(("GHA-ACTION-NOT-SHA-PINNED", f"Action reference is not pinned to a full commit SHA: {ref}", line, "high", "Resolve the intended trusted release to its full 40-character commit SHA and retain the release tag in a comment."))
        if policy.get("require_job_timeouts", True) and "jobs:" in text and not re.search(r"(?m)^\s+timeout-minutes:\s*\d+", text):
            items.append(("GHA-TIMEOUT-MISSING", "No job timeout-minutes declaration was found.", None, "medium", "Set bounded timeout-minutes values appropriate to each job."))
        if re.search(r"(?m)^\s*pull_request_target:\s*$", text):
            line = next((i for i, value in enumerate(text.splitlines(), 1) if re.match(r"^\s*pull_request_target:", value)), None)
            items.append(("GHA-PULL-REQUEST-TARGET", "Workflow uses pull_request_target, which executes in the base repository security context.", line, "high", "Prove that untrusted pull-request code is never checked out or executed; otherwise redesign around pull_request or a trusted two-stage workflow."))
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "run:" in line and re.search(r"\$\{\{\s*github\.event\.(issue|pull_request|comment|head_commit|discussion)", line):
                items.append(("GHA-UNTRUSTED-EXPRESSION-IN-SHELL", "Potentially untrusted event data is interpolated directly into a shell command.", line_no, "critical", "Pass the expression through an environment variable and quote it as data, or avoid shell interpretation."))
        is_deploy = bool(re.search(r"(?i)(deploy|release|publish|production)", path + "\n" + text[:1000]))
        if is_deploy and not re.search(r"(?m)^concurrency:\s*", text):
            items.append(("GHA-DEPLOY-CONCURRENCY-MISSING", "Deployment or release workflow has no top-level concurrency control.", None, "medium", "Add a stable concurrency group and choose cancellation semantics that cannot corrupt releases."))
        if items:
            findings.append(make_finding(
                rule_id="GHA-WORKFLOW-HARDENING",
                category="github-actions",
                severity=max((item[3] for item in items), key=lambda value: {"medium": 2, "high": 3, "critical": 4}[value]),
                confidence="high" if all(item[0] != "GHA-PULL-REQUEST-TARGET" for item in items) else "medium",
                title=f"Harden GitHub Actions workflow {path}",
                summary="The workflow has one or more security, reliability, or governance gaps that share a single file-level change and verification boundary.",
                evidence_items=[evidence(path, observation, line=line) for _, observation, line, _, _ in items],
                remediation_key=workflow_key,
                actions=list(dict.fromkeys(item[4] for item in items)),
                acceptance=["All external action references satisfy the repository pinning policy.", "Workflow token permissions are explicit and least-privilege.", "Every job has a bounded timeout.", "Untrusted event values are treated as data, not executable shell syntax.", "Deployment/release concurrency is explicit when applicable."],
                verification=[f"actionlint {path}", f"Review permissions, uses, timeout-minutes, event triggers, and run expressions in {path}.", "Run the workflow from a non-production test branch where safe."],
                references=["https://docs.github.com/en/actions/reference/security/secure-use"],
            ))

    visibility = (remote or {}).get("visibility")
    is_public = visibility == "PUBLIC" or visibility == "public"
    readme = _find_community_file(file_set, ["README.md", "README.rst", "README.txt", "README"])
    if not readme:
        findings.append(make_finding(
            rule_id="COMMUNITY-README-MISSING",
            category="governance",
            severity="medium",
            confidence="high",
            title="Add an evidence-backed repository README",
            summary="No recognized README exists in the repository root or supported community-file locations.",
            evidence_items=[evidence("git ls-files", "No README found")],
            remediation_key="governance/readme",
            actions=["Document purpose, supported status, exact setup, run, test, and contribution entry points using detected repository evidence."],
            acceptance=["A new contributor can identify the project purpose and reproduce the canonical validation workflow."],
            verification=["Compare README commands with manifests and CI.", "Follow setup instructions in a clean environment."],
            references=["https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories"],
        ))

    required_checks = [
        ("require_security_policy", ["SECURITY.md", "SECURITY.rst"], "COMMUNITY-SECURITY-MISSING", "Add a repository security policy", "governance/security-policy", "high"),
        ("require_contributing_guide", ["CONTRIBUTING.md", "CONTRIBUTING.rst"], "COMMUNITY-CONTRIBUTING-MISSING", "Add repository-specific contribution guidelines", "governance/contributing", "medium"),
    ]
    for policy_key, names, rule_id, title, remediation, severity in required_checks:
        if policy.get(policy_key, True) and not _find_community_file(file_set, names):
            findings.append(make_finding(
                rule_id=rule_id,
                category="governance",
                severity=severity,
                confidence="high",
                title=title,
                summary=f"No recognized {names[0]} exists in GitHub-supported repository locations.",
                evidence_items=[evidence("git ls-files", f"Missing {names[0]} in .github/, repository root, and docs/")],
                remediation_key=remediation,
                actions=[f"Create {names[0]} using repository-specific contacts, workflows, and commands.", "Cross-link it from the README where appropriate."],
                acceptance=[f"{names[0]} exists in a GitHub-recognized location and contains no placeholders."],
                verification=[f"test -f {names[0]} || test -f .github/{names[0]} || test -f docs/{names[0]}", "Review all commands and contacts against current repository evidence."],
                references=["https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions"],
            ))

    if is_public and policy.get("public_repo_require_license", True) and not _find_community_file(file_set, ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]):
        findings.append(make_finding(
            rule_id="COMMUNITY-LICENSE-MISSING",
            category="governance",
            severity="high",
            confidence="high",
            title="Choose and add an explicit repository license",
            summary="The public repository has no recognized license file.",
            evidence_items=[evidence("repository visibility", "Public repository; no license file found")],
            remediation_key="governance/license",
            actions=["Have the repository owner choose an appropriate license; do not infer legal intent.", "Add the exact unmodified license text and any required notices."],
            acceptance=["GitHub recognizes the selected license and repository documentation states the intended licensing scope."],
            verification=["Inspect the repository About/license metadata.", "Review LICENSE and notices for placeholders."],
            references=["https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-license-to-a-repository"],
        ))

    has_pr_template = any(path.casefold() in {"pull_request_template.md", ".github/pull_request_template.md", "docs/pull_request_template.md"} or path.casefold().startswith(".github/pull_request_template/") for path in files)
    if policy.get("require_pull_request_template", True) and not has_pr_template:
        findings.append(make_finding(
            rule_id="COMMUNITY-PR-TEMPLATE-MISSING",
            category="governance",
            severity="low",
            confidence="high",
            title="Add a repository-specific pull request template",
            summary="No GitHub-recognized pull request template was found.",
            evidence_items=[evidence("git ls-files", "No pull request template found")],
            remediation_key="governance/pr-template",
            actions=["Add a concise template covering intent, risk, tests, documentation, and linked issue."],
            acceptance=["New pull requests receive a useful, repository-specific template."],
            verification=["Open a draft pull request and confirm the template is prefilled."],
        ))

    issue_templates = [path for path in files if path.startswith(".github/ISSUE_TEMPLATE/") and Path(path).name.casefold() not in {"config.yml", "config.yaml"}]
    if policy.get("require_issue_templates", True) and (remote is None or remote.get("hasIssuesEnabled", True)) and not issue_templates:
        findings.append(make_finding(
            rule_id="COMMUNITY-ISSUE-TEMPLATES-MISSING",
            category="governance",
            severity="low",
            confidence="high",
            title="Add structured issue intake templates",
            summary="Issues are available or remote status is unknown, but no issue template or form was found.",
            evidence_items=[evidence(".github/ISSUE_TEMPLATE/", "No issue templates found")],
            remediation_key="governance/issue-templates",
            actions=["Create separate bug, feature, and support/security routing templates only where applicable.", "Use required fields sparingly and ensure referenced labels exist."],
            acceptance=["Issue intake captures reproducible evidence and routes non-issue requests appropriately."],
            verification=["Validate issue-form YAML.", "Open each template in GitHub's new-issue chooser."],
            references=["https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository"],
        ))

    if policy.get("require_codeowners_for_multi_contributor_repos", True):
        contributor_count = (remote or {}).get("contributor_count")
        if contributor_count and contributor_count > 1 and not _find_community_file(file_set, ["CODEOWNERS"]):
            findings.append(make_finding(
                rule_id="COMMUNITY-CODEOWNERS-MISSING",
                category="governance",
                severity="medium",
                confidence="medium",
                title="Define maintainership boundaries with CODEOWNERS",
                summary="The repository has multiple contributors but no CODEOWNERS file in a supported location.",
                evidence_items=[evidence("remote contributors", f"Contributor count: {contributor_count}"), evidence("git ls-files", "No CODEOWNERS found")],
                remediation_key="governance/codeowners",
                actions=["Map high-risk and domain-specific paths to active maintainers or teams.", "Add fallback ownership and validate patterns against the current tree."],
                acceptance=["Every critical path has an active, permission-valid owner and patterns match intended files."],
                verification=["Review CODEOWNERS rendering on GitHub.", "Open a test pull request touching representative paths."],
                references=["https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners"],
            ))

    if policy.get("require_dependabot_for_detected_ecosystems", True):
        needed = sorted({DEPENDABOT_ECOSYSTEMS[item["name"]] for item in stack["ecosystems"] if item["name"] in DEPENDABOT_ECOSYSTEMS})
        dependabot = next((path for path in files if path.casefold() in {".github/dependabot.yml", ".github/dependabot.yaml"}), None)
        if needed and not dependabot:
            findings.append(make_finding(
                rule_id="DEPENDABOT-CONFIG-MISSING",
                category="dependencies",
                severity="medium",
                confidence="high",
                title="Configure dependency update coverage for detected ecosystems",
                summary=f"No Dependabot configuration exists for detected update ecosystems: {', '.join(needed)}.",
                evidence_items=[evidence(item["evidence"][0], f"Detected ecosystem {item['name']}") for item in stack["ecosystems"] if item["name"] in DEPENDABOT_ECOSYSTEMS],
                remediation_key="dependencies/dependabot",
                actions=["Add one valid update entry per active package ecosystem and manifest directory.", "Choose a sustainable schedule, grouping policy, labels, and pull-request limit.", "Include github-actions when workflows exist."],
                acceptance=["Every active manifest directory has appropriate dependency-update coverage.", "Dependabot configuration validates and creates no duplicate update streams."],
                verification=["Validate .github/dependabot.yml against GitHub's option reference.", "Confirm dependency graph/Dependabot recognizes the configuration."],
                references=["https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference"],
            ))
        elif needed and dependabot:
            text = read_text_bounded(repo / dependabot, int(policy.get("max_text_file_bytes", 1048576))) or ""
            missing = [name for name in needed if not re.search(rf"package-ecosystem:\s*['\"]?{re.escape(name)}['\"]?", text)]
            if missing:
                findings.append(make_finding(
                    rule_id="DEPENDABOT-COVERAGE-INCOMPLETE",
                    category="dependencies",
                    severity="medium",
                    confidence="medium",
                    title="Complete Dependabot coverage for active package ecosystems",
                    summary=f"The Dependabot file does not visibly cover: {', '.join(missing)}.",
                    evidence_items=[evidence(dependabot, f"Missing package-ecosystem entries: {', '.join(missing)}")],
                    remediation_key="dependencies/dependabot",
                    actions=["Add update entries for each missing active ecosystem and all relevant manifest directories.", "Avoid duplicate overlapping entries."],
                    acceptance=["Every detected active package ecosystem is covered or has an explicit documented exception."],
                    verification=["Validate .github/dependabot.yml.", "Compare update directories with detected manifests."],
                ))
    return findings, coverage


def _github_slug_from_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    patterns = [r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", r"^([^/]+/[^/]+)$"]
    for pattern in patterns:
        match = re.search(pattern, origin)
        if match:
            return match.group(1).removesuffix(".git")
    return None


def collect_remote(repo: Path, mode: str) -> tuple[dict[str, Any] | None, list[Coverage]]:
    coverage: list[Coverage] = []
    if mode == "off":
        return None, [Coverage("github-remote", "skipped", "Remote audit disabled by caller.")]
    if not command_exists("gh"):
        if mode == "on":
            coverage.append(Coverage("github-remote", "degraded", "GitHub CLI is unavailable; remote assertions suppressed."))
        else:
            coverage.append(Coverage("github-remote", "skipped", "GitHub CLI unavailable in auto mode."))
        return None, coverage
    auth = run(["gh", "auth", "status"], cwd=repo)
    if auth.returncode != 0:
        coverage.append(Coverage("github-remote", "degraded", "GitHub CLI is not authenticated; remote assertions suppressed."))
        return None, coverage
    identity = repository_identity(repo)
    slug = _github_slug_from_origin(identity.get("origin"))
    if not slug:
        coverage.append(Coverage("github-remote", "degraded", "Origin is not a recognized GitHub repository URL."))
        return None, coverage
    try:
        data = run_json(["gh", "repo", "view", slug, "--json", "nameWithOwner,visibility,defaultBranchRef,description,homepageUrl,repositoryTopics,hasIssuesEnabled,isArchived,deleteBranchOnMerge,mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed"], cwd=repo)
    except Exception as exc:
        coverage.append(Coverage("github-remote", "degraded", f"Repository metadata unavailable: {exc}"))
        return None, coverage
    data["slug"] = slug
    data["default_branch"] = ((data.get("defaultBranchRef") or {}).get("name"))
    data["topics"] = [item.get("name") for item in ((data.get("repositoryTopics") or {}).get("nodes") or []) if item.get("name")]
    contributors = run(["gh", "api", f"repos/{slug}/contributors", "--method", "GET", "-f", "per_page=100", "-f", "anon=true"], cwd=repo)
    if contributors.returncode == 0:
        try:
            data["contributor_count"] = len(json.loads(contributors.stdout))
        except Exception:
            pass
    coverage.append(Coverage("github-remote", "complete", f"Read GitHub metadata for {slug}."))
    return data, coverage


def audit_remote(repo: Path, remote: dict[str, Any] | None, policy: dict[str, Any]) -> tuple[list[Finding], list[Coverage]]:
    if remote is None:
        return [], []
    findings: list[Finding] = []
    coverage: list[Coverage] = []
    slug = remote["slug"]
    default_branch = remote.get("default_branch")

    if not (remote.get("description") or "").strip():
        findings.append(make_finding(
            rule_id="REMOTE-DESCRIPTION-MISSING",
            category="repository-settings",
            severity="low",
            confidence="high",
            title="Add an accurate repository description",
            summary="The GitHub repository description is empty.",
            evidence_items=[evidence(f"github:{slug}", "Repository description is empty")],
            remediation_key="remote/about-metadata",
            actions=["Add a concise description derived from the README and current project scope.", "Add a homepage and topics only when supported by repository evidence."],
            acceptance=["The repository About panel accurately communicates purpose without stale claims."],
            verification=[f"gh repo view {slug} --json description,homepageUrl,repositoryTopics"],
        ))
    if not remote.get("topics"):
        findings.append(make_finding(
            rule_id="REMOTE-TOPICS-MISSING",
            category="repository-settings",
            severity="low",
            confidence="medium",
            title="Add evidence-backed repository topics",
            summary="No repository topics are configured.",
            evidence_items=[evidence(f"github:{slug}", "Repository topics list is empty")],
            remediation_key="remote/about-metadata",
            actions=["Select a small set of purpose, domain, language, and framework topics supported by the stack profile."],
            acceptance=["Topics accurately classify the repository and contain no speculative marketing terms."],
            verification=[f"gh repo view {slug} --json repositoryTopics"],
        ))
    if policy.get("recommend_delete_branch_on_merge", True) and not remote.get("deleteBranchOnMerge"):
        findings.append(make_finding(
            rule_id="REMOTE-DELETE-BRANCH-DISABLED",
            category="repository-settings",
            severity="low",
            confidence="high",
            title="Enable automatic deletion of merged head branches",
            summary="The repository does not automatically delete head branches after pull-request merges.",
            evidence_items=[evidence(f"github:{slug}", "deleteBranchOnMerge=false")],
            remediation_key="remote/merge-settings",
            actions=["Enable automatic head-branch deletion after confirming no automation depends on retained branches."],
            acceptance=["Merged pull-request branches are automatically deleted except where protected."],
            verification=[f"gh repo view {slug} --json deleteBranchOnMerge"],
        ))
    merge_methods = [name for name, key in (("merge", "mergeCommitAllowed"), ("squash", "squashMergeAllowed"), ("rebase", "rebaseMergeAllowed")) if remote.get(key)]
    if len(merge_methods) > 1:
        findings.append(make_finding(
            rule_id="REMOTE-MERGE-POLICY-AMBIGUOUS",
            category="repository-settings",
            severity="low",
            confidence="medium",
            title="Document and enforce a coherent pull-request merge policy",
            summary=f"Multiple merge methods are enabled ({', '.join(merge_methods)}) without evidence of a documented policy.",
            evidence_items=[evidence(f"github:{slug}", f"Enabled merge methods: {', '.join(merge_methods)}")],
            remediation_key="remote/merge-settings",
            actions=["Choose merge methods that match release, changelog, and history requirements.", "Document the policy and disable methods that violate it."],
            acceptance=["Enabled merge methods match the documented contribution and release workflow."],
            verification=[f"gh repo view {slug} --json mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed", "Review CONTRIBUTING.md merge policy."],
        ))

    if policy.get("require_branch_protection", True) and default_branch:
        rules = run(["gh", "api", f"repos/{slug}/rulesets", "--method", "GET", "-f", "includes_parents=true"], cwd=repo)
        has_active_ruleset = False
        if rules.returncode == 0:
            try:
                payload = json.loads(rules.stdout)
                has_active_ruleset = any(item.get("enforcement") == "active" for item in payload if isinstance(item, dict))
                coverage.append(Coverage("github-rulesets", "complete", "Repository rulesets read successfully."))
            except Exception:
                coverage.append(Coverage("github-rulesets", "degraded", "Ruleset response could not be parsed."))
        else:
            coverage.append(Coverage("github-rulesets", "degraded", "Rulesets unavailable with current token or plan."))
        protected = run(["gh", "api", f"repos/{slug}/branches/{default_branch}/protection"], cwd=repo)
        has_branch_protection = protected.returncode == 0
        if protected.returncode in {403, 404}:
            coverage.append(Coverage("github-branch-protection", "degraded" if protected.returncode == 403 else "complete", "Branch protection unavailable or absent; rulesets checked independently."))
        else:
            coverage.append(Coverage("github-branch-protection", "complete", "Default-branch protection endpoint read successfully."))
        if not has_active_ruleset and not has_branch_protection:
            findings.append(make_finding(
                rule_id="REMOTE-DEFAULT-BRANCH-UNPROTECTED",
                category="repository-settings",
                severity="high",
                confidence="medium" if rules.returncode != 0 else "high",
                title=f"Protect the default branch {default_branch}",
                summary="No active repository ruleset or legacy branch-protection response was found for the default branch. Permission or plan limitations may reduce confidence.",
                evidence_items=[evidence(f"github:{slug}", f"No visible active ruleset or protection for {default_branch}")],
                remediation_key="remote/default-branch-protection",
                actions=["Define a ruleset or branch protection requiring pull requests and appropriate status checks.", "Require reviews according to contributor count and risk.", "Limit bypasses and destructive branch operations.", "Avoid requiring checks that cannot run on all eligible pull requests."],
                acceptance=["The default branch rejects unauthorized direct pushes and enforces the project's review and verification policy."],
                verification=[f"gh api repos/{slug}/rulesets", f"gh api repos/{slug}/branches/{default_branch}/protection"],
                references=["https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets"],
            ))
    return findings, coverage


def _github_anchor(text: str) -> str:
    value = re.sub(r"[^\w\- ]", "", text.casefold(), flags=re.UNICODE)
    return re.sub(r"\s+", "-", value.strip())


def _anchors(markdown: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            raw = re.sub(r"<[^>]+>", "", match.group(1))
            anchor = _github_anchor(raw)
            index = counts[anchor]
            counts[anchor] += 1
            anchors.add(anchor if index == 0 else f"{anchor}-{index}")
        for explicit in re.findall(r"<a\s+(?:name|id)=['\"]([^'\"]+)", line, flags=re.IGNORECASE):
            anchors.add(explicit)
    return anchors


def _markdown_links(text: str) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("<!--"):
            continue
        for target in pattern.findall(line):
            results.append((line_no, target.strip("<>")))
    return results


def audit_docs(repo: Path, files: list[str], stack: dict[str, Any], policy: dict[str, Any]) -> tuple[list[Finding], list[Coverage]]:
    findings: list[Finding] = []
    coverage: list[Coverage] = []
    max_bytes = int(policy.get("max_text_file_bytes", 1048576))
    markdown = sorted(path for path in files if path.casefold().endswith((".md", ".markdown", ".mdx")))
    broken_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in markdown:
        text = read_text_bounded(repo / path, max_bytes)
        if text is None:
            coverage.append(Coverage(f"docs:{path}", "degraded", "Document exceeded scan limit or was unreadable."))
            continue
        for line_no, raw_target in _markdown_links(text):
            if re.match(r"^(?:https?|mailto|tel|data):", raw_target, flags=re.IGNORECASE):
                continue
            target = unquote(raw_target.split("?", 1)[0])
            file_part, _, anchor = target.partition("#")
            resolved = (repo / path).parent / file_part if file_part else repo / path
            if file_part and not resolved.exists():
                broken_by_doc[path].append(evidence(path, f"Broken relative link target: {raw_target}", line=line_no))
                continue
            if anchor and resolved.is_file() and resolved.suffix.casefold() in {".md", ".markdown", ".mdx"}:
                target_text = read_text_bounded(resolved, max_bytes)
                if target_text is not None and anchor not in _anchors(target_text):
                    broken_by_doc[path].append(evidence(path, f"Missing local heading anchor: {raw_target}", line=line_no))
    for path, items in broken_by_doc.items():
        findings.append(make_finding(
            rule_id="DOCS-BROKEN-LOCAL-REFERENCES",
            category="documentation",
            severity="medium",
            confidence="high",
            title=f"Repair broken local documentation references in {path}",
            summary="The document contains relative links, images, or heading anchors that do not resolve in the current repository snapshot.",
            evidence_items=items,
            remediation_key=f"docs/broken-links/{path}",
            actions=["Update each reference to the current path or anchor, or remove it when the target no longer exists.", "Preserve intentional links to generated documentation only with explicit build evidence."],
            acceptance=["Every local Markdown link, image, and anchor in the document resolves case-sensitively from the repository checkout."],
            verification=["Run repository_hygiene.py audit and confirm DOCS-BROKEN-LOCAL-REFERENCES is absent.", "Render the document and manually inspect navigation."],
        ))

    # Deterministic Node script mismatch checks in docs and workflows.
    package_scripts: dict[str, set[str]] = {}
    for manifest in stack.get("manifests", []):
        if Path(manifest["path"]).name == "package.json":
            payload = _json_file(repo, manifest["path"])
            package_scripts[str(Path(manifest["path"]).parent)] = set((payload or {}).get("scripts", {}).keys())
    if package_scripts:
        command_sources = markdown + _workflow_files(files)
        mismatches: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for path in command_sources:
            text = read_text_bounded(repo / path, max_bytes)
            if text is None:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for manager, script in re.findall(r"\b(npm|pnpm|yarn|bun)\s+(?:run\s+)?([A-Za-z0-9:_-]+)", line):
                    if script in {"install", "add", "remove", "exec", "dlx", "init", "create", "publish", "audit", "why", "list"}:
                        continue
                    candidate_boundaries = sorted(package_scripts, key=len, reverse=True)
                    boundary = next((item for item in candidate_boundaries if item != "." and path.startswith(item + "/")), ".")
                    available = package_scripts.get(boundary, set())
                    if script not in available:
                        mismatches[path].append(evidence(path, f"Documented command references missing package script '{script}' for {boundary or '.'}", line=line_no))
        for path, items in mismatches.items():
            findings.append(make_finding(
                rule_id="DOCS-COMMAND-NOT-IN-MANIFEST",
                category="documentation",
                severity="medium",
                confidence="medium",
                title=f"Align documented commands with package scripts in {path}",
                summary="The file invokes package scripts that are not defined in the nearest detected package manifest.",
                evidence_items=items,
                remediation_key=f"docs/commands/{path}",
                actions=["Determine the canonical current command from manifests and CI.", "Update documentation/automation or restore the missing script when it remains part of the supported workflow."],
                acceptance=["Every documented package script exists in the correct project boundary and executes the intended task."],
                verification=["Parse package.json scripts and compare with commands in the changed file.", "Run each corrected command in the intended project directory."],
            ))

    stale_days = int(policy.get("docs_stale_days", 180))
    latest_code = run(["git", "log", "-1", "--format=%ct", "--", ":(exclude)*.md", ":(exclude)docs/**"], cwd=repo)
    if latest_code.returncode == 0 and latest_code.stdout.strip().isdigit():
        newest_code_ts = int(latest_code.stdout.strip())
        stale_docs: list[dict[str, Any]] = []
        for path in markdown[:500]:
            last = run(["git", "log", "-1", "--format=%ct", "--", path], cwd=repo)
            if last.returncode == 0 and last.stdout.strip().isdigit():
                doc_ts = int(last.stdout.strip())
                delta_days = (newest_code_ts - doc_ts) // 86400
                if delta_days >= stale_days:
                    stale_docs.append(evidence(path, f"Last documentation change trails latest non-documentation change by {delta_days} days"))
        if stale_docs:
            findings.append(make_finding(
                rule_id="DOCS-AGE-REVIEW-SIGNAL",
                category="documentation",
                severity="low",
                confidence="low",
                title="Review aging documentation against the current repository snapshot",
                summary="Document age is not proof of rot, but these files substantially predate current implementation changes and require evidence-based review.",
                evidence_items=stale_docs[:100],
                remediation_key="docs/staleness-review",
                actions=["Assign each flagged document an owner and compare every architectural, setup, command, path, and support claim with current evidence.", "Update, archive, or explicitly affirm each document."],
                acceptance=["Each flagged document is current, intentionally historical, or removed with inbound references repaired."],
                verification=["Review git history and current manifests/CI for every flagged document.", "Re-run deterministic link and command checks."],
            ))
    coverage.append(Coverage("documentation-local-links", "complete", f"Scanned {len(markdown)} tracked Markdown documents for local references."))
    coverage.append(Coverage("documentation-external-links", "skipped", "External URL checking is disabled by default to preserve deterministic offline operation."))
    return findings, coverage


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    by_id: dict[str, Finding] = {}
    for finding in findings:
        by_id[finding.id] = finding
    return sorted(by_id.values(), key=lambda item: (-{"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[item.severity], item.category, item.title, item.id))


def run_audit(repo: Path, policy: dict[str, Any], remote_mode: str) -> dict[str, Any]:
    files = tracked_files(repo)
    max_text = int(policy.get("max_text_file_bytes", 1048576))
    stack = detect_stack(repo, files, max_text)
    remote, coverage = collect_remote(repo, remote_mode)
    findings: list[Finding] = []
    findings.extend(audit_stack(repo, files, stack))
    findings.extend(audit_repository_contents(repo, files, policy))
    findings.extend(audit_worktrees_and_branches(repo))
    gh_findings, gh_coverage = audit_github_folder(repo, files, stack, policy, remote)
    findings.extend(gh_findings)
    coverage.extend(gh_coverage)
    docs_findings, docs_coverage = audit_docs(repo, files, stack, policy)
    findings.extend(docs_findings)
    coverage.extend(docs_coverage)
    remote_findings, remote_coverage = audit_remote(repo, remote, policy)
    findings.extend(remote_findings)
    coverage.extend(remote_coverage)
    findings = deduplicate_findings(findings)
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "repository": repository_identity(repo),
        "remote": remote,
        "stack_profile": stack,
        "coverage": [item.to_dict() for item in coverage],
        "summary": {
            "tracked_files": len(files),
            "findings": len(findings),
            "actionable": sum(1 for item in findings if item.actionable),
            "by_severity": {severity: sum(1 for item in findings if item.severity == severity) for severity in ("critical", "high", "medium", "low", "info")},
        },
        "findings": [item.to_dict() for item in findings],
    }


def report_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    stack = report["stack_profile"]
    lines = [
        "# Repository Hygiene Audit",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Repository: `{report['repository']['root']}`  ",
        f"HEAD: `{report['repository'].get('head') or 'unavailable'}`",
        "",
        "## Executive summary",
        "",
        f"- Tracked files: **{summary['tracked_files']}**",
        f"- Findings: **{summary['findings']}** ({summary['actionable']} actionable)",
        f"- Severity: critical {summary['by_severity']['critical']}, high {summary['by_severity']['high']}, medium {summary['by_severity']['medium']}, low {summary['by_severity']['low']}, info {summary['by_severity']['info']}",
        "",
        "## Detected stack",
        "",
    ]
    for item in stack["ecosystems"]:
        lines.append(f"- **{item['name']}** ({item['confidence']}): " + ", ".join(f"`{path}`" for path in item["evidence"][:8]))
    if not stack["ecosystems"]:
        lines.append("- No recognized manifest-backed stack detected.")
    if stack["frameworks"]:
        lines.extend(["", "Framework signals:"])
        for item in stack["frameworks"]:
            lines.append(f"- {item['name']}: " + ", ".join(f"`{path}`" for path in item["evidence"]))
    lines.extend(["", "## Coverage", ""])
    for item in report["coverage"]:
        lines.append(f"- **{item['status']}** — `{item['check']}`: {item['detail']}")
    lines.extend(["", "## Findings", ""])
    if not report["findings"]:
        lines.append("No findings were produced by the enabled checks.")
    for finding in report["findings"]:
        lines.extend([
            f"### {finding['id']} — {finding['title']}",
            "",
            f"**Severity:** {finding['severity']} · **Confidence:** {finding['confidence']} · **Category:** {finding['category']}",
            "",
            finding["summary"],
            "",
            "Evidence:",
        ])
        for item in finding["evidence"][:20]:
            location = item["source"] + (f":{item['line']}" if item.get("line") else "")
            lines.append(f"- `{location}` — {item['observation']}")
        lines.extend(["", "Recommended actions:"])
        for action in finding["recommended_actions"]:
            lines.append(f"- [ ] {action}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

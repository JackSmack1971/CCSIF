#!/usr/bin/env python3
"""Validate a UX feature contract with no third-party dependencies.

Exit codes:
  0 valid
  2 usage, file, or path error
  3 malformed JSON
  4 schema or semantic validation failure
  5 internal validator failure
"""

from __future__ import annotations

import argparse
import json
import math
import re
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
REQUIRED_STATE_TYPES = {"idle", "loading", "success", "empty", "error", "permission", "authentication", "offline", "partial", "interrupted", "cancelled", "stale"}
PLACEHOLDER_RE = re.compile(r"(?:\bTODO\b|\bTBD\b|\[TODO(?::[^\]]*)?\]|<[^>]+>)", re.IGNORECASE)


def pointer(parts: list[str]) -> str:
    if not parts:
        return "$"
    return "$" + "".join(f"[{part}]" if part.isdigit() else f".{part}" for part in parts)


def resolve_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema reference: {ref}")
    node: Any = root
    for raw in ref[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        node = node[key]
    if not isinstance(node, dict):
        raise ValueError(f"schema reference does not resolve to an object: {ref}")
    return node


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_schema(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: list[str], errors: list[str]) -> None:
    if "$ref" in schema:
        validate_schema(instance, resolve_ref(root, schema["$ref"]), root, path, errors)
        return

    expected = schema.get("type")
    type_ok = True
    if expected == "object":
        type_ok = isinstance(instance, dict)
    elif expected == "array":
        type_ok = isinstance(instance, list)
    elif expected == "string":
        type_ok = isinstance(instance, str)
    elif expected == "number":
        type_ok = is_number(instance)
    elif expected == "boolean":
        type_ok = isinstance(instance, bool)

    if not type_ok:
        errors.append(f"{pointer(path)}: expected {expected}")
        return

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{pointer(path)}: value must be one of {schema['enum']}")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{pointer(path)}: string is shorter than {schema['minLength']} characters")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, instance) is None:
            errors.append(f"{pointer(path)}: string does not match pattern {pattern}")

    if is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{pointer(path)}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{pointer(path)}: value exceeds maximum {schema['maximum']}")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{pointer(path)}: requires at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{pointer(path)}: allows at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                validate_schema(item, item_schema, root, path + [str(index)], errors)

    if isinstance(instance, dict):
        for required in schema.get("required", []):
            if required not in instance:
                errors.append(f"{pointer(path)}: missing required property '{required}'")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{pointer(path + [key])}: unknown property")

        for key, child_schema in properties.items():
            if key in instance:
                validate_schema(instance[key], child_schema, root, path + [key], errors)


def collect_strings(value: Any, path: list[str] | None = None):
    path = path or []
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from collect_strings(item, path + [str(index)])
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from collect_strings(item, path + [key])


def duplicate_ids(items: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        item_id = item.get("id")
        if isinstance(item_id, str):
            if item_id in seen:
                duplicates.append(item_id)
            seen.add(item_id)
    return duplicates


def expected_score(candidate: dict[str, Any]) -> float:
    total = sum((float(candidate["scores"][name]) / 5.0) * weight for name, weight in WEIGHTS.items())
    return round(max(0.0, total - float(candidate["risk_penalty"])), 1)


def graph_has_cycle(dependencies: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in dependencies.get(node, []):
            if visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in dependencies)


def semantic_checks(data: dict[str, Any], repo_root: Path | None, strict: bool) -> list[str]:
    errors: list[str] = []

    if data.get("feature_id") != f"uxf-{data.get('slug', '')}":
        errors.append("$.feature_id: must equal 'uxf-' + slug")

    evidence = data.get("generated_from", {}).get("evidence", [])
    evidence_ids = {item.get("id") for item in evidence if isinstance(item, dict)}
    for duplicate in duplicate_ids(evidence):
        errors.append(f"$.generated_from.evidence: duplicate id {duplicate}")

    candidates = data.get("decision", {}).get("candidates", [])
    candidate_ids = {item.get("id") for item in candidates if isinstance(item, dict)}
    for duplicate in duplicate_ids(candidates):
        errors.append(f"$.decision.candidates: duplicate id {duplicate}")

    selected_id = data.get("decision", {}).get("selected_candidate_id")
    if selected_id not in candidate_ids:
        errors.append("$.decision.selected_candidate_id: does not reference a candidate")

    selected = [item for item in candidates if item.get("disposition") == "selected"]
    if len(selected) != 1:
        errors.append("$.decision.candidates: exactly one candidate must have disposition 'selected'")
    elif selected[0].get("id") != selected_id:
        errors.append("$.decision: selected_candidate_id must match the selected candidate")
    elif candidates:
        highest = max(float(item.get("total_score", 0)) for item in candidates)
        if float(selected[0].get("total_score", 0)) < highest:
            errors.append("$.decision: selected candidate must have the highest total_score")

    for index, candidate in enumerate(candidates):
        for ref in candidate.get("evidence_refs", []):
            if ref not in evidence_ids:
                errors.append(f"$.decision.candidates[{index}].evidence_refs: unknown evidence id {ref}")
        gates = candidate.get("minimum_gates", {})
        if candidate.get("disposition") == "selected" and not all(gates.values()):
            errors.append(f"$.decision.candidates[{index}]: selected candidate fails a minimum gate")
        try:
            expected = expected_score(candidate)
            actual = float(candidate.get("total_score"))
            if not math.isclose(expected, actual, abs_tol=0.05):
                errors.append(f"$.decision.candidates[{index}].total_score: expected {expected}, found {actual}")
        except (KeyError, TypeError, ValueError):
            pass

    for ref in data.get("problem", {}).get("evidence_refs", []):
        if ref not in evidence_ids:
            errors.append(f"$.problem.evidence_refs: unknown evidence id {ref}")

    metrics = data.get("outcomes", {}).get("metrics", [])
    primary_metrics = [metric for metric in metrics if metric.get("kind") == "primary"]
    if len(primary_metrics) != 1:
        errors.append("$.outcomes.metrics: exactly one primary metric is required")

    states = data.get("ux_design", {}).get("states", [])
    state_types = [item.get("type") for item in states if isinstance(item, dict)]
    missing_states = REQUIRED_STATE_TYPES - set(state_types)
    duplicated_states = {state for state in state_types if state_types.count(state) > 1}
    if missing_states:
        errors.append(f"$.ux_design.states: missing state types {sorted(missing_states)}")
    if duplicated_states:
        errors.append(f"$.ux_design.states: duplicate state types {sorted(duplicated_states)}")
    for index, state in enumerate(states):
        applicable = state.get("applicable")
        if applicable is True:
            for field in ("trigger", "experience", "recovery"):
                if not str(state.get(field, "")).strip():
                    errors.append(f"$.ux_design.states[{index}].{field}: required when applicable is true")
            if str(state.get("not_applicable_reason", "")).strip():
                errors.append(f"$.ux_design.states[{index}].not_applicable_reason: must be empty when applicable is true")
        elif applicable is False:
            if not str(state.get("not_applicable_reason", "")).strip():
                errors.append(f"$.ux_design.states[{index}].not_applicable_reason: required when applicable is false")

    work_items = data.get("implementation", {}).get("work_items", [])
    work_ids = {item.get("id") for item in work_items if isinstance(item, dict)}
    for duplicate in duplicate_ids(work_items):
        errors.append(f"$.implementation.work_items: duplicate id {duplicate}")

    dependencies: dict[str, list[str]] = {}
    for index, item in enumerate(work_items):
        item_id = item.get("id")
        item_dependencies = item.get("dependencies", [])
        dependencies[item_id] = item_dependencies
        if item_id in item_dependencies:
            errors.append(f"$.implementation.work_items[{index}].dependencies: self-dependency")
        for dependency in item_dependencies:
            if dependency not in work_ids:
                errors.append(f"$.implementation.work_items[{index}].dependencies: unknown work item {dependency}")

        if repo_root is not None:
            for path_index, change in enumerate(item.get("paths", [])):
                raw_path = change.get("path", "")
                candidate_path = (repo_root / raw_path).resolve()
                try:
                    candidate_path.relative_to(repo_root.resolve())
                except ValueError:
                    errors.append(f"$.implementation.work_items[{index}].paths[{path_index}].path: escapes repo root")
                    continue
                operation = change.get("operation")
                if strict and operation in {"modify", "delete"} and not candidate_path.exists():
                    errors.append(f"$.implementation.work_items[{index}].paths[{path_index}].path: path does not exist for {operation}: {raw_path}")
                if strict and operation == "create" and candidate_path.exists():
                    errors.append(f"$.implementation.work_items[{index}].paths[{path_index}].path: path already exists for create: {raw_path}")

    if graph_has_cycle(dependencies):
        errors.append("$.implementation.work_items: dependency graph contains a cycle")

    execution_order = data.get("agent_handoff", {}).get("execution_order", [])
    if set(execution_order) != work_ids or len(execution_order) != len(work_ids):
        errors.append("$.agent_handoff.execution_order: must contain every work item exactly once")
    else:
        positions = {item_id: index for index, item_id in enumerate(execution_order)}
        for item_id, item_dependencies in dependencies.items():
            for dependency in item_dependencies:
                if positions[dependency] > positions[item_id]:
                    errors.append(f"$.agent_handoff.execution_order: {dependency} must precede {item_id}")

    def ancestors(item_id: str, seen: set[str] | None = None) -> set[str]:
        seen = seen or set()
        result: set[str] = set()
        for dependency in dependencies.get(item_id, []):
            if dependency in seen:
                continue
            result.add(dependency)
            result.update(ancestors(dependency, seen | {dependency}))
        return result

    for group_index, group in enumerate(data.get("agent_handoff", {}).get("parallel_groups", [])):
        group_set = set(group)
        if len(group_set) != len(group):
            errors.append(f"$.agent_handoff.parallel_groups[{group_index}]: duplicate work item")
        for item_id in group:
            if item_id not in work_ids:
                errors.append(f"$.agent_handoff.parallel_groups[{group_index}]: unknown work item {item_id}")
            if ancestors(item_id) & group_set:
                errors.append(f"$.agent_handoff.parallel_groups[{group_index}]: contains transitively dependent work items")

    id_collections = [
        ("$.outcomes.metrics", data.get("outcomes", {}).get("metrics", [])),
        ("$.ux_design.primary_flow", data.get("ux_design", {}).get("primary_flow", [])),
        ("$.ux_design.states", states),
        ("$.acceptance_criteria", data.get("acceptance_criteria", [])),
        ("$.risks", data.get("risks", [])),
        ("$.open_questions", data.get("open_questions", [])),
    ]
    for label, collection in id_collections:
        for duplicate in duplicate_ids(collection):
            errors.append(f"{label}: duplicate id {duplicate}")

    if strict:
        if data.get("status") != "ready_for_implementation":
            errors.append("$.status: strict mode requires 'ready_for_implementation'")
        for path, value in collect_strings(data):
            if PLACEHOLDER_RE.search(value):
                errors.append(f"{pointer(path)}: placeholder text is not allowed in strict mode")
        blocking = [q.get("id") for q in data.get("open_questions", []) if q.get("blocking") is True]
        if blocking:
            errors.append(f"$.open_questions: blocking questions remain {blocking}")

    return errors


def emit(status: str, errors: list[str], path: Path, as_json: bool, exit_code: int) -> int:
    payload = {
        "status": status,
        "file": str(path),
        "error_count": len(errors),
        "errors": errors,
        "exit_code": exit_code,
    }
    if as_json:
        print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    elif errors:
        print(f"INVALID: {path}")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"VALID: {path}")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_file", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "resources" / "feature-brief.schema.json")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.feature_file.is_file():
        return emit("error", [f"feature file not found: {args.feature_file}"], args.feature_file, args.json, 2)
    if not args.schema.is_file():
        return emit("error", [f"schema file not found: {args.schema}"], args.feature_file, args.json, 2)
    if args.repo_root is not None and not args.repo_root.is_dir():
        return emit("error", [f"repo root not found: {args.repo_root}"], args.feature_file, args.json, 2)

    try:
        data = json.loads(args.feature_file.read_text(encoding="utf-8"))
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return emit("invalid_json", [f"line {exc.lineno}, column {exc.colno}: {exc.msg}"], args.feature_file, args.json, 3)
    except (OSError, UnicodeError) as exc:
        return emit("error", [str(exc)], args.feature_file, args.json, 2)

    try:
        errors: list[str] = []
        validate_schema(data, schema, schema, [], errors)
        if isinstance(data, dict):
            errors.extend(semantic_checks(data, args.repo_root, args.strict))
        errors = sorted(set(errors))
    except Exception as exc:  # Defensive boundary for machine-parseable failures.
        return emit("internal_error", [f"{type(exc).__name__}: {exc}"], args.feature_file, args.json, 5)

    if errors:
        return emit("invalid", errors, args.feature_file, args.json, 4)
    return emit("valid", [], args.feature_file, args.json, 0)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:  # Optional Graphiti backend. Local store remains the default path.
    from graphiti_core import Graphiti
    from graphiti_core.driver.neo4j_driver import Neo4jDriver
    from graphiti_core.embedder.voyage import VoyageAIEmbedder, VoyageAIEmbedderConfig
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.nodes import EpisodeType
except Exception:  # pragma: no cover - exercised only when optional deps exist.
    Graphiti = None
    Neo4jDriver = None
    VoyageAIEmbedder = None
    VoyageAIEmbedderConfig = None
    LLMConfig = None
    OpenAIGenericClient = None
    EpisodeType = None

ROOT = Path(__file__).resolve().parents[2]
TRACE_DIR = ROOT / ".claude" / "traces"
STATE_DIR = ROOT / ".claude" / "memory" / "state"
CURSOR_PATH = STATE_DIR / "retain-cursor.json"
EPISODES_PATH = STATE_DIR / "episodes.jsonl"
OBSERVATIONS_PATH = STATE_DIR / "observations.jsonl"
OPINIONS_PATH = STATE_DIR / "opinions.jsonl"

TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
FILE_RE = re.compile(r"(?:[A-Za-z]:\\\\|/)?(?:[\w.-]+[/\\\\])+[\w.-]+\.[A-Za-z0-9]+")
LEADING_VERB_RE = re.compile(
    r"^(?P<verb>added|changed|created|deleted|fixed|implemented|updated|refactored|reviewed|documented|ran|wrote|wired|configured|investigated|audited|checked|traced|verified|bootstrapped)\b",
    re.I,
)
_GRAPHITI_CLIENT = None
ENV_PATH = ROOT / ".claude" / "memory" / ".env"
NEGATION_RE = re.compile(r"\b(?:no|not|never|cannot|can't|won't|failed|broken|missing|lacks?|without|error|bug)\b", re.I)
PERSONA_PATH = ROOT / ".claude" / "rules" / "persona-profile.md"
PERSONA_DEFAULTS = {"skepticism": 0.5, "literalism": 0.5, "empathy": 0.5, "bias_strength": 0.5}
PERSONA_KEY_RE = re.compile(r"^(skepticism|literalism|empathy|bias_strength)\s*:\s*([0-9]*\.?[0-9]+)", re.I)


@dataclass
class TraceRecord:
    ts: str
    task: str | None
    skill: str | None
    outcome: str | None
    error_class: str | None
    component: str | None
    notes: str | None


@dataclass
class MemoryRecord:
    ts: str
    group_id: str
    kind: str
    text: str
    source_trace: str
    source_line: int
    entity: str | None = None
    confidence: float | None = None
    evidence_score: float | None = None
    supporting_evidence: int = 0
    contradicting_evidence: int = 0
    tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class GraphitiRuntimeStatus:
    requested: bool
    configured: bool
    connected: bool
    detail: str


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_project_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if value and value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


load_project_env()


def graphiti_requested() -> bool:
    return os.getenv("HINDSIGHT_BACKEND", "local").strip().lower() == "graphiti"


def env_value(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def parse_reference_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def build_graphiti_client():
    global _GRAPHITI_CLIENT
    if _GRAPHITI_CLIENT is not None:
        return _GRAPHITI_CLIENT
    try:
        if not graphiti_requested():
            return None
        if Graphiti is None or Neo4jDriver is None or VoyageAIEmbedder is None or LLMConfig is None or OpenAIGenericClient is None:
            return None

        uri = env_value("HINDSIGHT_GRAPHITI_URI", "NEO4J_URI")
        user = env_value("HINDSIGHT_GRAPHITI_USER", "NEO4J_USER")
        password = env_value("HINDSIGHT_GRAPHITI_PASSWORD", "NEO4J_PASSWORD")
        if not uri or not user or not password:
            return None

        api_key = env_value("HINDSIGHT_LLM_API_KEY", "OPENAI_API_KEY")
        if not api_key:
            return None

        model = env_value("HINDSIGHT_LLM_MODEL", "MODEL_NAME", default="gpt-4.1-mini")
        small_model = env_value("HINDSIGHT_LLM_SMALL_MODEL", "SMALL_MODEL_NAME", default=model)
        base_url = env_value("HINDSIGHT_LLM_BASE_URL")
        temperature = float(env_value("HINDSIGHT_LLM_TEMPERATURE", "LLM_TEMPERATURE", default="0"))
        llm_client = OpenAIGenericClient(
            config=LLMConfig(
                api_key=api_key,
                model=model,
                small_model=small_model,
                base_url=base_url,
                temperature=temperature,
            )
        )

        voyage_key = env_value("HINDSIGHT_VOYAGE_API_KEY", "VOYAGE_API_KEY")
        if not voyage_key:
            return None
        embedder = VoyageAIEmbedder(
            config=VoyageAIEmbedderConfig(
                api_key=voyage_key,
                embedding_model=env_value("HINDSIGHT_VOYAGE_EMBEDDING_MODEL", "VOYAGE_EMBEDDING_MODEL", default="voyage-3"),
                embedding_dim=int(env_value("HINDSIGHT_VOYAGE_EMBEDDING_DIM", "VOYAGE_EMBEDDING_DIM", default="1024")),
            )
        )

        database = env_value("HINDSIGHT_GRAPHITI_DATABASE", "NEO4J_DATABASE", default="neo4j")
        driver = Neo4jDriver(uri=uri, user=user, password=password, database=database)
        _GRAPHITI_CLIENT = Graphiti(graph_driver=driver, llm_client=llm_client, embedder=embedder)
        return _GRAPHITI_CLIENT
    except Exception:
        return None


def graphiti_available() -> bool:
    return build_graphiti_client() is not None


async def probe_graphiti_client(client) -> tuple[bool, str]:
    driver = getattr(client, "driver", None)
    if driver is None or not hasattr(driver, "execute_query"):
        return False, "graphiti client has no executable driver"
    await driver.execute_query("RETURN 1 AS ok")
    return True, "neo4j query succeeded"


def graphiti_status() -> GraphitiRuntimeStatus:
    if not graphiti_requested():
        return GraphitiRuntimeStatus(False, False, False, "HINDSIGHT_BACKEND is not graphiti")
    if Graphiti is None or Neo4jDriver is None or VoyageAIEmbedder is None or LLMConfig is None or OpenAIGenericClient is None:
        return GraphitiRuntimeStatus(True, False, False, "graphiti-core optional dependencies are unavailable")
    client = build_graphiti_client()
    if client is None:
        return GraphitiRuntimeStatus(True, False, False, "Graphiti client configuration is incomplete")
    try:
        connected, detail = asyncio.run(probe_graphiti_client(client))
    except Exception as exc:
        return GraphitiRuntimeStatus(True, True, False, f"{exc.__class__.__name__}: {exc}")
    return GraphitiRuntimeStatus(True, True, connected, detail)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_state()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_state()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def load_traces() -> list[tuple[Path, list[TraceRecord]]]:
    if not TRACE_DIR.exists():
        return []
    files = sorted(TRACE_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    loaded: list[tuple[Path, list[TraceRecord]]] = []
    for path in files:
        records: list[TraceRecord] = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            records.append(
                TraceRecord(
                    ts=str(item.get("ts") or ""),
                    task=item.get("task"),
                    skill=item.get("skill"),
                    outcome=item.get("outcome"),
                    error_class=item.get("error_class"),
                    component=item.get("component"),
                    notes=item.get("notes"),
                )
            )
        loaded.append((path, records))
    return loaded


def load_cursor() -> dict[str, int]:
    payload = read_json(CURSOR_PATH)
    files = payload.get("files")
    if isinstance(files, dict):
        return {str(k): int(v) for k, v in files.items() if isinstance(v, int) or str(v).isdigit()}
    return {}


def save_cursor(cursor: dict[str, int]) -> None:
    write_json(CURSOR_PATH, {"files": cursor, "updated_at": now()})


def tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {token.lower() for token in TOKEN_RE.findall(text)}


def normalize_entity(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.strip().lower().split())


def load_persona() -> dict[str, float]:
    persona = dict(PERSONA_DEFAULTS)
    if not PERSONA_PATH.exists():
        return persona
    for raw in PERSONA_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PERSONA_KEY_RE.match(raw.strip())
        if not match:
            continue
        key = match.group(1).lower()
        try:
            persona[key] = max(0.0, min(1.0, float(match.group(2))))
        except ValueError:
            continue
    return persona


def opinion_match_score(query_tokens: set[str], target: str, record: MemoryRecord) -> float:
    candidate = normalize_entity(record.entity)
    if not candidate:
        return 0.0
    if candidate == target:
        return 1.0
    candidate_tokens = tokenize(record.entity)
    if not query_tokens or not candidate_tokens:
        return 0.0
    union = query_tokens | candidate_tokens
    if not union:
        return 0.0
    return len(query_tokens & candidate_tokens) / len(union)


def find_latest_opinion(query: str, persona: dict[str, float] | None = None) -> "MemoryRecord | None":
    target = normalize_entity(query)
    if not target:
        return None
    persona = persona or load_persona()
    # literalism gates how loose an entity match may be and still count as
    # "the same opinion": 1.0 requires an exact normalized match, 0.0 accepts
    # any nonzero token overlap.
    threshold = persona.get("literalism", PERSONA_DEFAULTS["literalism"])
    query_tokens = tokenize(query)
    matches = [
        (opinion_match_score(query_tokens, target, rec), rec)
        for rec in read_all_memory()
        if rec.kind == "opinion"
    ]
    matches = [(score, rec) for score, rec in matches if score > 0.0 and score >= threshold]
    if not matches:
        return None
    return max(matches, key=lambda pair: (pair[0], pair[1].ts))[1]


def record_provenance(records: list[MemoryRecord]) -> list[str]:
    refs: set[str] = set()
    for rec in records:
        if rec.source_refs:
            refs.update(rec.source_refs)
        else:
            refs.add(f"{rec.source_trace}:{rec.source_line}")
    return sorted(refs)


def trace_source_ref(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def extract_entity(record: TraceRecord) -> str | None:
    for candidate in [record.component, record.skill, record.task, record.notes]:
        if not candidate:
            continue
        match = FILE_RE.search(candidate)
        if match:
            return match.group(0)
        if candidate:
            return candidate.split()[0][:120]
    return None


def build_experience_record(path: Path, line_no: int, record: TraceRecord) -> MemoryRecord:
    task = record.task or "the current task"
    outcome = record.outcome or "unknown"
    notes = record.notes or ""
    if outcome == "success":
        opener = "I completed"
    elif outcome == "partial":
        opener = "I partially completed"
    else:
        opener = "I attempted"
    text = f"{opener} {task}. Outcome: {outcome}."
    if notes:
        text = f"{text} Notes: {notes}."
    tags = ["experience"]
    if record.skill:
        tags.append(record.skill)
    if record.component:
        tags.append(record.component)
    return MemoryRecord(
        ts=record.ts or now(),
        group_id="ccsif:experience",
        kind="experience",
        text=text,
        source_trace=trace_source_ref(path),
        source_line=line_no,
        entity=extract_entity(record),
        confidence=1.0,
        tags=tags,
    )


def build_world_record(path: Path, line_no: int, record: TraceRecord) -> MemoryRecord:
    component = record.component or "the workspace"
    notes = record.notes or "trace summary available"
    text = f"The workspace activity touched {component}. {notes}."
    tags = ["world"]
    if record.component:
        tags.append(record.component)
    return MemoryRecord(
        ts=record.ts or now(),
        group_id="ccsif:world",
        kind="world",
        text=text,
        source_trace=trace_source_ref(path),
        source_line=line_no,
        entity=extract_entity(record),
        confidence=1.0,
        tags=tags,
    )


def build_observation_record(entity: str, records: list[MemoryRecord]) -> MemoryRecord:
    counts = Counter(rec.kind for rec in records)
    recent = records[-3:]
    summary = "; ".join(rec.text for rec in recent)
    text = (
        f"Observation for {entity}: {counts['world']} world facts, {counts['experience']} experience facts. "
        f"Recent evidence: {summary}"
    )
    return MemoryRecord(
        ts=now(),
        group_id="ccsif:observation",
        kind="observation",
        text=text,
        source_trace="derived",
        source_line=0,
        entity=entity,
        confidence=1.0,
        tags=["observation"],
        source_refs=record_provenance(records),
    )


def evidence_signal(query_tokens: set[str], record: MemoryRecord) -> float:
    text_tokens = tokenize(record.text) | tokenize(record.entity) | tokenize(" ".join(record.tags))
    overlap = len(query_tokens & text_tokens)
    if overlap == 0:
        return 0.0
    weight = float(overlap)
    if record.kind == "experience":
        weight += 0.5
    elif record.kind == "world":
        weight += 0.25
    try:
        dt = datetime.fromisoformat(record.ts.replace("Z", "+00:00"))
        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        weight *= max(0.35, 1.0 - min(age_days, 30.0) / 45.0)
    except Exception:
        pass
    if NEGATION_RE.search(record.text or ""):
        return -weight
    return weight


def summarize_evidence(query: str, evidence: list[MemoryRecord]) -> tuple[float, int, int]:
    query_tokens = tokenize(query)
    total = 0.0
    supporting = 0
    contradicting = 0
    for record in evidence:
        signal = evidence_signal(query_tokens, record)
        if signal > 0:
            supporting += 1
        elif signal < 0:
            contradicting += 1
        total += signal
    return total, supporting, contradicting


def build_opinion_record(
    query: str,
    evidence: list[MemoryRecord],
    persona: dict[str, float] | None = None,
    prior_opinion: "MemoryRecord | None" = None,
) -> MemoryRecord:
    persona = persona or load_persona()
    evidence_score, supporting, contradicting = summarize_evidence(query, evidence)
    if prior_opinion is None:
        prior_opinion = find_latest_opinion(query, persona)
    prior_confidence = prior_opinion.confidence if prior_opinion and prior_opinion.confidence is not None else 0.5
    # Skepticism dampens how much one evidence batch can move belief;
    # bias_strength controls how strongly a standing opinion resists revision.
    scaled_score = evidence_score * (1.5 - persona["skepticism"])
    learning_rate = max(0.05, 0.4 * (1.0 - persona["bias_strength"]))
    confidence = prior_confidence if scaled_score == 0 else reinforce(prior_confidence, scaled_score > 0, learning_rate)
    if supporting == 0 and contradicting == 0:
        text = f"I think {query.strip() or 'the current topic'} needs more evidence."
    else:
        text = (
            f"I think {query.strip() or 'the current topic'} is worth tracking "
            f"based on {supporting} supporting and {contradicting} contradicting evidence items."
        )
    return MemoryRecord(
        ts=now(),
        group_id="ccsif:opinion",
        kind="opinion",
        text=text,
        source_trace="derived",
        source_line=0,
        entity=normalize_entity(query) or None,
        confidence=confidence,
        evidence_score=evidence_score,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        tags=["opinion"],
        source_refs=record_provenance(evidence),
    )


def iter_new_trace_entries() -> Iterable[tuple[Path, int, TraceRecord]]:
    cursor = load_cursor()
    for path, records in load_traces():
        key = str(path.name)
        start = cursor.get(key, 0)
        for idx, record in enumerate(records[start:], start=start + 1):
            yield path, idx, record
        cursor[key] = len(records)
    save_cursor(cursor)


def read_all_memory() -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    for path in [EPISODES_PATH, OBSERVATIONS_PATH, OPINIONS_PATH]:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            records.append(MemoryRecord(**item))
    return records


def write_memory(record: MemoryRecord, path: Path) -> None:
    append_jsonl(path, asdict(record))


def clear_trace_state() -> None:
    for path in (CURSOR_PATH, EPISODES_PATH, OBSERVATIONS_PATH):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def build_episode_body(kind: str, trace: TraceRecord, source_ref: str) -> str:
    lines = [
        f"Kind: {kind}",
        f"Task: {trace.task or ''}",
        f"Skill: {trace.skill or ''}",
        f"Outcome: {trace.outcome or ''}",
        f"Error class: {trace.error_class or ''}",
        f"Component: {trace.component or ''}",
        f"Notes: {trace.notes or ''}",
        f"Source: {source_ref}",
    ]
    return "\n".join(lines).strip()


async def add_graphiti_episode(client, *, name: str, episode_body: str, source_description: str, source: str, group_id: str, reference_time: datetime) -> None:
    if EpisodeType is None:
        return
    await client.add_episode(
        name=name,
        episode_body=episode_body,
        source_description=source_description,
        reference_time=reference_time,
        source=getattr(EpisodeType, source, EpisodeType.text),
        group_id=group_id,
    )


async def graphiti_search(client, query: str, limit: int) -> list[MemoryRecord]:
    if client is None:
        return []
    try:
        edges = await client.search(
            query,
            group_ids=["ccsif:world", "ccsif:experience", "ccsif:observation", "ccsif:opinion"],
            num_results=limit,
        )
    except Exception:
        return []
    records: list[MemoryRecord] = []
    for edge in edges or []:
        fact = getattr(edge, "fact", None) or str(edge)
        valid_at = getattr(edge, "valid_at", None)
        records.append(
            MemoryRecord(
                ts=str(valid_at or now()),
                group_id="ccsif:world",
                kind="world",
                text=fact,
                source_trace="graphiti",
                source_line=0,
                entity=query.strip() or None,
                confidence=1.0,
                tags=["graphiti"],
            )
        )
    return records


def retain() -> int:
    count = 0
    client = build_graphiti_client()
    retained_keys = {(rec.kind, rec.source_trace, rec.source_line) for rec in read_all_memory()}
    for path, line_no, trace in iter_new_trace_entries():
        experience = build_experience_record(path, line_no, trace)
        world = build_world_record(path, line_no, trace)
        experience_key = (experience.kind, experience.source_trace, experience.source_line)
        world_key = (world.kind, world.source_trace, world.source_line)
        if experience_key not in retained_keys:
            write_memory(experience, EPISODES_PATH)
            retained_keys.add(experience_key)
            count += 1
        if world_key not in retained_keys:
            write_memory(world, EPISODES_PATH)
            retained_keys.add(world_key)
            count += 1
        if client is not None:
            try:
                source_ref = f"{experience.source_trace}:{line_no}"
                episode_body = build_episode_body(experience.kind, trace, source_ref)
                world_body = build_episode_body(world.kind, trace, source_ref)
                asyncio.run(
                    add_graphiti_episode(
                        client,
                        name=f"{path.stem}-{line_no}-experience",
                        episode_body=episode_body,
                        source_description=source_ref,
                        source="text",
                        group_id=experience.group_id,
                        reference_time=parse_reference_time(trace.ts),
                    )
                )
                asyncio.run(
                    add_graphiti_episode(
                        client,
                        name=f"{path.stem}-{line_no}-world",
                        episode_body=world_body,
                        source_description=source_ref,
                        source="text",
                        group_id=world.group_id,
                        reference_time=parse_reference_time(trace.ts),
                    )
                )
            except Exception:
                client = None
    print(f"retained {count} memory records")
    return 0


def bootstrap() -> int:
    save_cursor({})
    return retain()


def score_record(query_tokens: set[str], record: MemoryRecord) -> float:
    text_tokens = tokenize(record.text) | tokenize(record.entity) | tokenize(" ".join(record.tags))
    overlap = len(query_tokens & text_tokens)
    bonus = 0.0
    if record.entity and record.entity.lower() in " ".join(sorted(query_tokens)):
        bonus += 2.0
    if record.kind == "experience":
        bonus += 0.5
    if record.kind == "world":
        bonus += 0.25
    age_penalty = 0.0
    try:
        dt = datetime.fromisoformat(record.ts.replace("Z", "+00:00"))
        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        age_penalty = min(2.0, age_days / 14.0)
    except Exception:
        pass
    return overlap + bonus - age_penalty


def recall(query: str, limit: int = 6) -> int:
    print(_render_recall(query, limit))
    return 0


def _render_recall(query: str, limit: int = 6) -> str:
    client = build_graphiti_client()
    if client is not None:
        try:
            edges = asyncio.run(client.search(query, group_ids=["ccsif:world", "ccsif:experience", "ccsif:observation", "ccsif:opinion"], num_results=limit))
            if edges:
                lines = ["## HINDSIGHT Recall (Graphiti)", f"Query: {query.strip() or '(empty)'}"]
                for edge in edges:
                    fact = getattr(edge, "fact", str(edge))
                    valid_at = getattr(edge, "valid_at", None)
                    suffix = f" @ {valid_at}" if valid_at else ""
                    lines.append(f"- {fact}{suffix}")
                return "\n".join(lines)
        except Exception:
            pass

    records = read_all_memory()
    if not records:
        return "No HINDSIGHT memory available yet."
    q_tokens = tokenize(query)
    ranked = sorted(records, key=lambda rec: score_record(q_tokens, rec), reverse=True)
    picked = [rec for rec in ranked if score_record(q_tokens, rec) > 0][:limit]
    if not picked:
        picked = ranked[:limit]
    lines = ["## HINDSIGHT Recall", f"Query: {query.strip() or '(empty)'}"]
    for rec in picked:
        entity = f" [{rec.entity}]" if rec.entity else ""
        lines.append(f"- ({rec.group_id}){entity} {rec.text}")
    return "\n".join(lines)


def observe() -> int:
    client = build_graphiti_client()
    records = [rec for rec in read_all_memory() if rec.kind in {"world", "experience"}]
    by_entity: dict[str, list[MemoryRecord]] = defaultdict(list)
    for rec in records:
        key = rec.entity or rec.group_id
        by_entity[key].append(rec)
    if not by_entity:
        print("No evidence available for observation.")
        return 0
    for entity, items in sorted(by_entity.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        live_items = items
        if client is not None:
            live_items = asyncio.run(graphiti_search(client, entity, limit=12)) or items
        obs = build_observation_record(entity, live_items)
        write_memory(obs, OBSERVATIONS_PATH)
        if client is not None:
            try:
                asyncio.run(
                    add_graphiti_episode(
                        client,
                        name=f"observation-{entity[:32]}",
                        episode_body=obs.text,
                        source_description="hindsight.observe",
                        source="text",
                        group_id=obs.group_id,
                        reference_time=parse_reference_time(obs.ts),
                    )
                )
            except Exception:
                pass
    print(f"observed {len(by_entity)} entities")
    return 0


def replay() -> int:
    clear_trace_state()
    retain()
    observe()
    return 0


def reinforce(prior: float, supports: bool, learning_rate: float = 0.2) -> float:
    target = 1.0 if supports else 0.0
    return max(0.0, min(1.0, prior + learning_rate * (target - prior)))


def reinforce_cli(args: argparse.Namespace) -> int:
    updated = reinforce(args.prior, args.supports, args.learning_rate)
    print(f"{updated:.3f}")
    return 0


def reflect(query: str, limit: int = 6) -> int:
    print(_render_reflect(query, limit))
    return 0


def _render_reflect(query: str, limit: int = 6) -> str:
    records = read_all_memory()
    q_tokens = tokenize(query)
    ranked = sorted(records, key=lambda rec: score_record(q_tokens, rec), reverse=True)
    evidence = [rec for rec in ranked if score_record(q_tokens, rec) > 0][:limit]
    persona = load_persona()
    prior_opinion = find_latest_opinion(query, persona)
    opinion = build_opinion_record(query, evidence, persona=persona, prior_opinion=prior_opinion)
    write_memory(opinion, OPINIONS_PATH)
    lines = ["## HINDSIGHT Reflection", f"Query: {query.strip() or '(empty)'}", opinion.text]
    if prior_opinion is not None and prior_opinion.confidence is not None:
        lines.append(f"Confidence reinforced: {prior_opinion.confidence:.2f} -> {opinion.confidence:.2f}")
    else:
        lines.append(f"Confidence (new opinion): {opinion.confidence:.2f}")
    for rec in evidence:
        lines.append(f"- Evidence: ({rec.group_id}) {rec.text}")
    return "\n".join(lines)


def prompt_text_from_stdin() -> str:
    raw = sys.stdin.read()
    if not raw.strip():
        return ""
    try:
        payload = json.loads(raw)
    except Exception:
        return raw.strip()
    for key in ("prompt", "prompt_text", "user_prompt", "message", "content", "query"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for inner in ("text", "prompt", "content"):
                inner_value = value.get(inner)
                if isinstance(inner_value, str) and inner_value.strip():
                    return inner_value.strip()
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and Path(transcript).exists():
        try:
            last_user = ""
            for line in Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines():
                if "\"role\":\"user\"" in line:
                    last_user = line
            if last_user:
                return last_user
        except Exception:
            pass
    return ""


def self_test() -> int:
    assert math.isclose(reinforce(0.6, True), 0.68)
    assert math.isclose(reinforce(0.6, False), 0.48)
    persona = load_persona()
    assert set(PERSONA_DEFAULTS) <= set(persona)
    assert all(0.0 <= value <= 1.0 for value in persona.values())
    sample = TraceRecord(
        ts="2026-07-10T00:00:00Z",
        task="update the memory hooks",
        skill="hindsight-retain",
        outcome="success",
        error_class=None,
        component=".claude/hooks/post-tool-use.sh",
        notes="retained hook events",
    )
    exp = build_experience_record(ROOT / ".claude" / "traces" / "2026-07-10.jsonl", 1, sample)
    world = build_world_record(ROOT / ".claude" / "traces" / "2026-07-10.jsonl", 1, sample)
    assert exp.group_id == "ccsif:experience"
    assert world.group_id == "ccsif:world"
    assert "I completed" in exp.text
    assert "workspace activity touched" in world.text
    opinion = build_opinion_record("memory hooks", [exp, world])
    assert opinion.kind == "opinion"
    assert opinion.evidence_score is not None
    assert opinion.supporting_evidence >= 1
    assert opinion.source_refs == record_provenance([exp, world])
    print("self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hindsight")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("bootstrap")
    sub.add_parser("retain")
    sub.add_parser("replay")
    sub.add_parser("observe")
    sub.add_parser("self-test")
    sub.add_parser("graphiti-check")

    p_recall = sub.add_parser("recall")
    p_recall.add_argument("query", nargs="?", default="")
    p_recall.add_argument("--limit", type=int, default=6)

    p_reflect = sub.add_parser("reflect")
    p_reflect.add_argument("query", nargs="?", default="")
    p_reflect.add_argument("--limit", type=int, default=6)

    p_reinforce = sub.add_parser("reinforce")
    p_reinforce.add_argument("--prior", type=float, required=True)
    p_reinforce.add_argument("--supports", action="store_true")
    p_reinforce.add_argument("--learning-rate", type=float, default=0.2)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        return bootstrap()
    if args.command == "retain":
        return retain()
    if args.command == "replay":
        return replay()
    if args.command == "observe":
        return observe()
    if args.command == "graphiti-check":
        status = graphiti_status()
        print(json.dumps(asdict(status), indent=2, sort_keys=True))
        return 0 if status.connected else 1
    if args.command == "recall":
        query = args.query or prompt_text_from_stdin()
        print(_render_recall(query, args.limit))
        return 0
    if args.command == "reflect":
        query = args.query or prompt_text_from_stdin()
        print(_render_reflect(query, args.limit))
        return 0
    if args.command == "reinforce":
        return reinforce_cli(args)
    if args.command == "self-test":
        return self_test()
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

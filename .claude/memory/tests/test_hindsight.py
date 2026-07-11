from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hindsight


class FakeDriver:
    async def execute_query(self, query: str):
        self.query = query
        return [{"ok": 1}], None, None


class FakeGraphitiClient:
    def __init__(self):
        self.driver = FakeDriver()
        self.search = AsyncMock(return_value=[])
        self.add_episode = AsyncMock(return_value=None)


class HindsightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = patch.dict(os.environ, {"HINDSIGHT_BACKEND": "local"}, clear=False)
        self._env_patch.start()
        self._client_patch = patch.object(hindsight, "_GRAPHITI_CLIENT", None)
        self._client_patch.start()
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        hindsight.STATE_DIR = base / "state"
        hindsight.CURSOR_PATH = hindsight.STATE_DIR / "retain-cursor.json"
        hindsight.EPISODES_PATH = hindsight.STATE_DIR / "episodes.jsonl"
        hindsight.OBSERVATIONS_PATH = hindsight.STATE_DIR / "observations.jsonl"
        hindsight.OPINIONS_PATH = hindsight.STATE_DIR / "opinions.jsonl"
        hindsight.TRACE_DIR = base / "traces"
        hindsight.TRACE_DIR.mkdir(parents=True, exist_ok=True)
        self._persona_patch = patch.object(hindsight, "PERSONA_PATH", base / "no-persona-file.md")
        self._persona_patch.start()

    def write_trace(self, name: str, rows: list[dict[str, object]]) -> Path:
        path = hindsight.TRACE_DIR / name
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def tearDown(self) -> None:
        self._persona_patch.stop()
        self._client_patch.stop()
        self._env_patch.stop()
        self.tmp.cleanup()

    def test_build_opinion_record_uses_evidence_scoring(self) -> None:
        support = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:experience",
            kind="experience",
            text="I completed the memory hooks update successfully.",
            source_trace="trace.jsonl",
            source_line=1,
            entity="memory hooks",
            confidence=1.0,
            tags=["memory", "hooks"],
        )
        contradiction = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:world",
            kind="world",
            text="The memory hooks change failed in validation.",
            source_trace="trace.jsonl",
            source_line=2,
            entity="memory hooks",
            confidence=1.0,
            tags=["memory", "hooks"],
        )

        opinion = hindsight.build_opinion_record("memory hooks", [support, contradiction])

        self.assertEqual(opinion.kind, "opinion")
        self.assertEqual(opinion.supporting_evidence, 1)
        self.assertEqual(opinion.contradicting_evidence, 1)
        self.assertIsNotNone(opinion.evidence_score)
        self.assertIsNotNone(opinion.confidence)
        self.assertLess(opinion.confidence, 1.0)

    def test_graphiti_status_reports_connected_client(self) -> None:
        fake_client = FakeGraphitiClient()

        with patch.object(hindsight, "graphiti_requested", return_value=True), patch.object(
            hindsight, "Graphiti", object()
        ), patch.object(hindsight, "Neo4jDriver", object()), patch.object(
            hindsight, "VoyageAIEmbedder", object()
        ), patch.object(hindsight, "LLMConfig", object()), patch.object(
            hindsight, "OpenAIGenericClient", object()
        ), patch.object(hindsight, "build_graphiti_client", return_value=fake_client), patch.object(
            hindsight, "probe_graphiti_client", new=AsyncMock(return_value=(True, "neo4j query succeeded"))
        ):
            status = hindsight.graphiti_status()

        self.assertTrue(status.requested)
        self.assertTrue(status.configured)
        self.assertTrue(status.connected)
        self.assertIn("succeeded", status.detail)

    def test_observe_writes_local_projection(self) -> None:
        episode = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:experience",
            kind="experience",
            text="I completed the memory hooks update successfully.",
            source_trace="trace.jsonl",
            source_line=1,
            entity="memory hooks",
            confidence=1.0,
            tags=["memory", "hooks"],
        )
        hindsight.write_memory(episode, hindsight.EPISODES_PATH)

        with patch.object(hindsight, "build_graphiti_client", return_value=None):
            rc = hindsight.observe()

        self.assertEqual(rc, 0)
        self.assertTrue(hindsight.OBSERVATIONS_PATH.exists())
        rows = [json.loads(line) for line in hindsight.OBSERVATIONS_PATH.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "observation")
        self.assertEqual(rows[0]["entity"], "memory hooks")

    def test_retain_is_idempotent_and_replay_rebuilds_trace_state(self) -> None:
        self.write_trace(
            "2026-07-10.jsonl",
            [
                {
                    "ts": "2026-07-10T00:00:00Z",
                    "task": "update the memory hooks",
                    "skill": "hindsight-retain",
                    "outcome": "success",
                    "component": ".claude/hooks/post-tool-use.sh",
                    "notes": "retained hook events",
                }
            ],
        )

        self.assertEqual(hindsight.retain(), 0)
        self.assertTrue(hindsight.EPISODES_PATH.exists())
        first_pass = hindsight.EPISODES_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(first_pass), 2)

        hindsight.CURSOR_PATH.unlink()
        self.assertEqual(hindsight.retain(), 0)
        second_pass = hindsight.EPISODES_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(second_pass), 2)

        self.assertEqual(hindsight.replay(), 0)
        replayed_episodes = hindsight.EPISODES_PATH.read_text(encoding="utf-8").splitlines()
        replayed_observations = hindsight.OBSERVATIONS_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(replayed_episodes), 2)
        self.assertEqual(len(replayed_observations), 1)

    def test_local_end_to_end_flow_covers_retain_recall_observe_reflect(self) -> None:
        self.write_trace(
            "2026-07-10.jsonl",
            [
                {
                    "ts": "2026-07-10T00:00:00Z",
                    "task": "update the memory hooks",
                    "skill": "hindsight-retain",
                    "outcome": "success",
                    "component": ".claude/hooks/post-tool-use.sh",
                    "notes": "retained hook events",
                }
            ],
        )

        self.assertEqual(hindsight.retain(), 0)
        recall_output = hindsight._render_recall("memory hooks", limit=3)
        self.assertIn("HINDSIGHT Recall", recall_output)
        self.assertIn("memory hooks", recall_output)

        self.assertEqual(hindsight.observe(), 0)
        self.assertTrue(hindsight.OBSERVATIONS_PATH.exists())

        reflect_output = hindsight._render_reflect("memory hooks", limit=3)
        self.assertIn("HINDSIGHT Reflection", reflect_output)
        self.assertIn("Confidence", reflect_output)
        self.assertTrue(hindsight.OPINIONS_PATH.exists())

    def test_recall_respects_limit_and_observe_stays_neutral(self) -> None:
        self.write_trace(
            "2026-07-10.jsonl",
            [
                {
                    "ts": "2026-07-10T00:00:00Z",
                    "task": "update the memory hooks",
                    "skill": "hindsight-retain",
                    "outcome": "success",
                    "component": ".claude/hooks/post-tool-use.sh",
                    "notes": "retained hook events",
                }
            ],
        )

        self.assertEqual(hindsight.retain(), 0)
        recall_output = hindsight._render_recall("memory hooks", limit=1)
        bullets = [line for line in recall_output.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(bullets), 1)

        self.assertEqual(hindsight.observe(), 0)
        observation = json.loads(hindsight.OBSERVATIONS_PATH.read_text(encoding="utf-8").splitlines()[0])
        self.assertNotIn("I think", observation["text"])
        self.assertNotIn("persona", observation["text"].lower())

    def test_load_persona_defaults_when_file_missing(self) -> None:
        persona = hindsight.load_persona()
        self.assertEqual(persona, hindsight.PERSONA_DEFAULTS)

    def test_load_persona_parses_profile_file(self) -> None:
        hindsight.PERSONA_PATH.write_text(
            "# Persona Profile\n\nskepticism: 0.9\nliteralism: 0.2\nempathy: 0.1\nbias_strength: 0.8\n",
            encoding="utf-8",
        )

        persona = hindsight.load_persona()

        self.assertEqual(
            persona,
            {"skepticism": 0.9, "literalism": 0.2, "empathy": 0.1, "bias_strength": 0.8},
        )

    def test_opinion_confidence_reinforces_instead_of_resetting(self) -> None:
        evidence = [
            hindsight.MemoryRecord(
                ts="2026-07-10T00:00:00Z",
                group_id="ccsif:experience",
                kind="experience",
                text="I completed the memory hooks update successfully.",
                source_trace="trace.jsonl",
                source_line=1,
                entity="memory hooks",
                confidence=1.0,
                tags=["memory", "hooks"],
            )
        ]

        first = hindsight.build_opinion_record("memory hooks", evidence)
        hindsight.write_memory(first, hindsight.OPINIONS_PATH)
        second = hindsight.build_opinion_record("Memory Hooks", evidence)

        self.assertGreater(first.confidence, 0.5)
        self.assertGreater(second.confidence, first.confidence)

    def test_opinion_confidence_holds_steady_without_new_evidence(self) -> None:
        stale = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:opinion",
            kind="opinion",
            text="I think memory hooks is worth tracking.",
            source_trace="derived",
            source_line=0,
            entity="memory hooks",
            confidence=0.73,
            tags=["opinion"],
        )
        hindsight.write_memory(stale, hindsight.OPINIONS_PATH)

        unrelated_evidence = [
            hindsight.MemoryRecord(
                ts="2026-07-10T00:00:00Z",
                group_id="ccsif:world",
                kind="world",
                text="The workspace activity touched an unrelated subsystem.",
                source_trace="trace.jsonl",
                source_line=9,
                entity="unrelated subsystem",
                confidence=1.0,
                tags=["world"],
            )
        ]

        opinion = hindsight.build_opinion_record("memory hooks", unrelated_evidence)

        self.assertEqual(opinion.confidence, 0.73)

    def test_find_latest_opinion_high_literalism_requires_near_exact_match(self) -> None:
        prior = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:opinion",
            kind="opinion",
            text="I think memory hooks is worth tracking.",
            source_trace="derived",
            source_line=0,
            entity="memory hooks",
            confidence=0.73,
            tags=["opinion"],
        )
        hindsight.write_memory(prior, hindsight.OPINIONS_PATH)

        exact = hindsight.find_latest_opinion("memory hooks", {"literalism": 1.0})
        loose = hindsight.find_latest_opinion("hooks in the memory subsystem", {"literalism": 1.0})

        self.assertIsNotNone(exact)
        self.assertIsNone(loose)

    def test_find_latest_opinion_low_literalism_allows_loose_match(self) -> None:
        prior = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:opinion",
            kind="opinion",
            text="I think memory hooks is worth tracking.",
            source_trace="derived",
            source_line=0,
            entity="memory hooks",
            confidence=0.73,
            tags=["opinion"],
        )
        hindsight.write_memory(prior, hindsight.OPINIONS_PATH)

        loose = hindsight.find_latest_opinion("hooks in the memory subsystem", {"literalism": 0.3})
        too_strict = hindsight.find_latest_opinion("hooks in the memory subsystem", {"literalism": 0.5})

        self.assertIsNotNone(loose)
        self.assertEqual(loose.entity, "memory hooks")
        self.assertIsNone(too_strict)

    def test_provenance_chains_from_observation_into_opinion(self) -> None:
        episode = hindsight.MemoryRecord(
            ts="2026-07-10T00:00:00Z",
            group_id="ccsif:experience",
            kind="experience",
            text="I completed the memory hooks update successfully.",
            source_trace=".claude/traces/2026-07-10.jsonl",
            source_line=4,
            entity="memory hooks",
            confidence=1.0,
            tags=["memory", "hooks"],
        )

        observation = hindsight.build_observation_record("memory hooks", [episode])

        self.assertEqual(observation.source_refs, [".claude/traces/2026-07-10.jsonl:4"])

        opinion = hindsight.build_opinion_record("memory hooks", [observation])

        self.assertEqual(opinion.source_refs, [".claude/traces/2026-07-10.jsonl:4"])


if __name__ == "__main__":
    unittest.main()

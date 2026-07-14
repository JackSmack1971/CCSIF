from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import prereq_check  # noqa: E402


class PrereqCheckTests(unittest.TestCase):
    def test_mcp_manifest_matches_repository_local_startup_contract(self) -> None:
        prereq_check.check_mcp_manifest(require_uv=False)

    def test_package_json_exposes_deterministic_verification_scripts(self) -> None:
        data = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(data["engines"]["node"], ">=20")
        self.assertEqual(data["engines"]["python"], ">=3.11")
        self.assertIn("python .claude/scripts/prereq_check.py --mcp-smoke", data["scripts"]["verify"])
        self.assertEqual(data["scripts"]["smoke:mcp"], "python .claude/scripts/prereq_check.py --mcp-smoke")

    def test_runtime_version_files_are_discoverable(self) -> None:
        self.assertEqual((ROOT / ".python-version").read_text(encoding="utf-8").strip(), "3.11")
        self.assertEqual((ROOT / ".node-version").read_text(encoding="utf-8").strip(), "20")

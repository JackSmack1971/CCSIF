from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import ledger_append  # noqa: E402


class AppendOnlyTests(unittest.TestCase):
    def test_append_never_truncates_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            path.write_text("# Ledger\n\nexisting content that must survive\n", encoding="utf-8")
            ledger_append.append_entry("New Entry", "new body", ledger_path=path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("existing content that must survive", text)
            self.assertIn("## New Entry", text)
            self.assertIn("new body", text)

    def test_creates_file_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "ledger.md"
            ledger_append.append_entry("First Entry", "body", ledger_path=path)
            self.assertTrue(path.exists())
            self.assertIn("## First Entry", path.read_text(encoding="utf-8"))

    def test_rejects_empty_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            with self.assertRaises(ledger_append.LedgerAppendError):
                ledger_append.append_entry("   ", "body", ledger_path=path)

    def test_multiple_appends_preserve_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            ledger_append.append_entry("First", "one", ledger_path=path)
            ledger_append.append_entry("Second", "two", ledger_path=path)
            text = path.read_text(encoding="utf-8")
            self.assertLess(text.index("## First"), text.index("## Second"))

    def test_cli_main_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.md"
            code = ledger_append.main(["--heading", "CLI Entry", "--body", "cli body", "--ledger-path", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("## CLI Entry", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

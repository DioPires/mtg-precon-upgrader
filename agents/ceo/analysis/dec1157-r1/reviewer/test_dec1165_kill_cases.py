"""DEC-1165 review of PR #67 (head f5eda73): kill cases for the mutants that survive.

Copy this file into tests/ of a tree at the PR head and run:
    CI=true uv run --with pytest python -m pytest -q tests/test_dec1165_kill_cases.py
The class reuses GapSeatWriteTests's own setUp, tearDown, _run and _edit_pool, so it
runs on the class's invented cards (Removal 0 and the rest). The module binds no
TestCase but its own class, so pytest collects only the three cases below.

- K1 kills R1 (`pass` becomes `return False`) and X4 (`pass` becomes `raise`).
- K2 kills X2 (the `continue` after the `no change` line is removed).
- K3 kills R5 (no final newline), R6 (`indent=1`) and R7 (`ensure_ascii=True`).
"""
import json
import unittest

import tests.test_generate_candidate_pool as base


class Dec1165KillTests(unittest.TestCase):
    DECK_ID = base.GapSeatWriteTests.DECK_ID
    setUp = base.GapSeatWriteTests.setUp
    tearDown = base.GapSeatWriteTests.tearDown
    _run = base.GapSeatWriteTests._run
    _edit_pool = base.GapSeatWriteTests._edit_pool

    def test_file_that_is_not_valid_json_is_rewritten(self):
        """K1: a pool cut short in a write is written again, not kept and not a crash."""
        self._run()
        self.out_path.write_text('{"candidates": [\n')
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(len(pool["candidates"]), 8)

    def test_run_that_writes_nothing_prints_no_wrote_line(self):
        """K2: a skip prints the `no change` line and no `wrote` line."""
        def edit(pool):
            pool["generated_at"] = "2000-01-01T00:00:00+00:00"
        self._edit_pool(edit)
        second = self._run()
        self.assertIn(f"[{self.DECK_ID}] no change (8 candidates)", second)
        self.assertNotIn(f"[{self.DECK_ID}] wrote", second)

    def test_written_text_has_two_space_indent_utf8_and_final_newline(self):
        """K3: the file is json.dumps(indent=2, ensure_ascii=False) plus a final newline."""
        edhrec_dir = self.tmp / "no-edhrec"
        edhrec_dir.mkdir()
        source = "Invented page — Zoë"
        (edhrec_dir / f"{self.DECK_ID}.json").write_text(json.dumps(
            {"recorded_at": "2026-01-01", "source": source, "rates": {}},
        ))
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        text = self.out_path.read_text(encoding="utf-8")
        pool = json.loads(text)
        self.assertEqual(pool["edhrec_rates"]["source"], source)
        self.assertIn(source, text)
        self.assertEqual(text, json.dumps(pool, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()

"""DEC-1165 review: demo for the N item on a pool file that is valid JSON but not an object.

Not a kill case. It shows a behaviour difference: on origin/main the old guard writes
such a file (`null`, `[]`, `0`); on the PR head write_candidates calls `.pop` on it and
raises. Copy into tests/ and run:
    CI=true uv run --with pytest python -m pytest -q tests/demo_dec1165_non_object.py
"""
import unittest

import tests.test_generate_candidate_pool as base


class Dec1165NonObjectDemo(unittest.TestCase):
    DECK_ID = base.GapSeatWriteTests.DECK_ID
    setUp = base.GapSeatWriteTests.setUp
    tearDown = base.GapSeatWriteTests.tearDown
    _run = base.GapSeatWriteTests._run

    def test_valid_json_that_is_not_an_object_is_rewritten(self):
        for text in ("null\n", "[]\n", "0\n"):
            with self.subTest(text=text.strip()):
                self.out_path.write_text(text)
                self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())


if __name__ == "__main__":
    unittest.main()

"""DEC-1121 kill cases for item (c) of PR #41 (`write_metrics` in scripts/compute_deck_metrics.py).

Each test passes on the head and fails on one surviving mutant (named in its
docstring). Run from the basis tree root:
    uv run --with pytest python -m pytest -q -p no:cacheprovider /tmp/dec1078-review/kill/test_kill_dec1121_item_c.py

The fix adds both methods to WriteMetricsClockFieldTests in tests/test_write_metrics.py.
"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
tw = importlib.import_module("tests.test_write_metrics")
m = tw.m


class WriteMetricsShapeKillTests(tw.WriteMetricsClockFieldTests):
    def _seed_raw(self, doc: dict) -> None:
        self.path.write_text(json.dumps(doc, indent=2) + "\n")

    def test_file_whose_penalties_is_not_a_dict_raises_nothing(self):
        """Kills C6 (`if penalties is not None:` in place of `isinstance(penalties, dict)`)."""
        old = tw._payload()
        old["confidence_inputs"]["penalties"] = []
        self._seed_raw(old)
        self.assertTrue(m.write_metrics(tw.DECK_ID, tw._payload()))
        stored = json.loads(self.path.read_text())
        self.assertEqual(stored["confidence_inputs"]["penalties"]["candidates_age_days"], 1.0)

    def test_file_whose_confidence_inputs_is_not_a_dict_raises_nothing(self):
        """Kills C7 (`if inputs is not None` in place of `isinstance(inputs, dict)`)."""
        old = tw._payload()
        old["confidence_inputs"] = []
        self._seed_raw(old)
        self.assertTrue(m.write_metrics(tw.DECK_ID, tw._payload()))
        stored = json.loads(self.path.read_text())
        self.assertIsInstance(stored["confidence_inputs"], dict)


# The inherited tests run here too; keep only the kill cases in this file's count.
for _name in [n for n in dir(WriteMetricsShapeKillTests) if n.startswith("test_")]:
    if _name not in WriteMetricsShapeKillTests.__dict__:
        setattr(WriteMetricsShapeKillTests, _name, None)
del _name

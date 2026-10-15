"""DEC-1078 item (c) — tests for write_metrics in scripts/compute_deck_metrics.py:
the comparison leaves out the two fields that read the clock (`generated_at`
and `confidence_inputs.penalties.candidates_age_days`), and only those."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import compute_deck_metrics as m  # noqa: E402

DECK_ID = "test-deck"


def _payload(age: float | None = 1.0, generated_at: str = "2026-10-14T10:00:00+00:00") -> dict:
    return {
        "version": 1,
        "deck_id": DECK_ID,
        "generated_at": generated_at,
        "global_health": 80,
        "confidence_margin": 5,
        "confidence_inputs": {
            "default": 5,
            "penalties": {
                "role_unset_cards": 0,
                "role_unset_applied": 0,
                "candidates_missing": False,
                "candidates_age_days": age,
                "candidates_stale": False,
                "total": 0,
            },
            "bonus_floor_eligible": True,
            "role_coverage_score": 100,
        },
        "gaps": [],
    }


class WriteMetricsClockFieldTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / DECK_ID).mkdir()
        self.path = root / DECK_ID / "metrics.json"
        self._patcher = mock.patch.object(m, "DECKS_DIR", root)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmp.cleanup()

    def _seed(self, payload: dict) -> bytes:
        self.assertTrue(m.write_metrics(DECK_ID, payload))
        return self.path.read_bytes()

    def _seed_raw(self, doc: dict) -> None:
        self.path.write_text(json.dumps(doc, indent=2) + "\n")

    def test_payload_that_differs_only_in_the_clock_fields_writes_nothing(self):
        before = self._seed(_payload(age=1.0))
        new = _payload(age=2.1, generated_at="2026-10-15T12:00:00+00:00")
        self.assertFalse(m.write_metrics(DECK_ID, new))
        self.assertEqual(self.path.read_bytes(), before)

    def test_payload_that_differs_in_another_field_writes_the_new_age(self):
        self._seed(_payload(age=1.0))
        new = _payload(age=2.1)
        new["global_health"] = 81
        self.assertTrue(m.write_metrics(DECK_ID, new))
        stored = json.loads(self.path.read_text())
        self.assertEqual(stored["global_health"], 81)
        self.assertEqual(stored["confidence_inputs"]["penalties"]["candidates_age_days"], 2.1)

    def test_payload_that_differs_in_another_penalties_key_is_written(self):
        self._seed(_payload(age=1.0))
        new = _payload(age=1.0)
        new["confidence_inputs"]["penalties"]["role_unset_cards"] = 1
        self.assertTrue(m.write_metrics(DECK_ID, new))
        stored = json.loads(self.path.read_text())
        self.assertEqual(stored["confidence_inputs"]["penalties"]["role_unset_cards"], 1)

    def test_file_without_confidence_inputs_or_with_no_age_raises_nothing(self):
        bare = _payload()
        del bare["confidence_inputs"]
        self._seed(bare)
        self.assertFalse(m.write_metrics(DECK_ID, copy.deepcopy(bare)))

        self._seed(_payload(age=None))
        self.assertFalse(m.write_metrics(DECK_ID, _payload(age=None)))
        self.assertFalse(m.write_metrics(DECK_ID, _payload(age=2.1)))

    def test_age_that_crosses_the_bonus_floor_threshold_is_written(self):
        self._seed(_payload(age=29.9))
        new = _payload(age=30.1)
        new["confidence_inputs"]["bonus_floor_eligible"] = False
        self.assertTrue(m.write_metrics(DECK_ID, new))
        stored = json.loads(self.path.read_text())
        self.assertFalse(stored["confidence_inputs"]["bonus_floor_eligible"])
        self.assertEqual(stored["confidence_inputs"]["penalties"]["candidates_age_days"], 30.1)

    def test_file_whose_penalties_is_not_a_dict_raises_nothing(self):
        """Kills C6 (`if penalties is not None:` in place of `isinstance(penalties, dict)`)."""
        old = _payload()
        old["confidence_inputs"]["penalties"] = []
        self._seed_raw(old)
        self.assertTrue(m.write_metrics(DECK_ID, _payload()))
        stored = json.loads(self.path.read_text())
        self.assertEqual(stored["confidence_inputs"]["penalties"]["candidates_age_days"], 1.0)

    def test_file_whose_confidence_inputs_is_not_a_dict_raises_nothing(self):
        """Kills C7 (`if inputs is not None` in place of `isinstance(inputs, dict)`)."""
        old = _payload()
        old["confidence_inputs"] = []
        self._seed_raw(old)
        self.assertTrue(m.write_metrics(DECK_ID, _payload()))
        stored = json.loads(self.path.read_text())
        self.assertIsInstance(stored["confidence_inputs"], dict)


if __name__ == "__main__":
    unittest.main()

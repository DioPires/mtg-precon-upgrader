import importlib
import json
import unittest
from pathlib import Path


exporter = importlib.import_module("scripts.export_simulation_results")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"


class CheckedInSimulationOutputTests(unittest.TestCase):
    def test_all_checked_in_simulation_outputs_validate(self):
        expected_ids = [deck_id for deck_id, _, _ in exporter.DECKS]
        actual_ids = sorted(path.parent.name for path in COMMANDERS_DIR.glob("*/simulation.json"))

        self.assertEqual(actual_ids, sorted(expected_ids))

        for deck_id in actual_ids:
            with self.subTest(deck_id=deck_id):
                path = COMMANDERS_DIR / deck_id / "simulation.json"
                data = json.loads(path.read_text())
                self.assertTrue(exporter.validate_output(data, deck_id))

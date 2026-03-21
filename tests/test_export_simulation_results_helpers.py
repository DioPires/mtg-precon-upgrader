import importlib
import unittest
from pathlib import Path


exporter = importlib.import_module("scripts.export_simulation_results")


class ExportSimulationResultsHelperTests(unittest.TestCase):
    def test_resolve_decks_defaults_to_all(self):
        resolved = exporter.resolve_decks(None)
        self.assertEqual([deck_id for deck_id, _, _ in resolved],
                         [deck_id for deck_id, _, _ in exporter.DECKS])

    def test_resolve_decks_preserves_canonical_order(self):
        resolved = exporter.resolve_decks(["dark-dominion", "titan-convergence"])
        self.assertEqual([deck_id for deck_id, _, _ in resolved],
                         ["titan-convergence", "dark-dominion"])

    def test_output_path_for_default_location(self):
        path = exporter.output_path_for("dark-dominion", None)
        expected = exporter.PROJECT_ROOT / "data" / "commanders" / "dark-dominion" / "simulation.json"
        self.assertEqual(path, expected)

    def test_output_path_for_custom_directory(self):
        base = Path("/tmp/sim-exports")
        path = exporter.output_path_for("dark-dominion", base)
        self.assertEqual(path, base / "dark-dominion" / "simulation.json")

import importlib
import json
import types
import unittest
from unittest.mock import Mock, patch


EXPORT_CASES = [
    ("scripts.mana_simulation_gathering_shadow", "export_grixis", "gathering-shadow"),
    ("scripts.mana_simulation_eternal_agony", "export_rakdos", "eternal-agony"),
    ("scripts.mana_simulation_eternal_harvest", "export_golgari", "eternal-harvest"),
    ("scripts.mana_simulation_witherbloom_the_balancer", "export_witherbloom", "witherbloom-the-balancer"),
    ("scripts.mana_simulation_titan_convergence", "export_titan", "titan-convergence"),
    ("scripts.mana_simulation_stampede_acres", "export_stampede_acres", "stampede-acres"),
]


class SimulationJsonExportTests(unittest.TestCase):
    def test_standalone_json_export_uses_bulk_exporter(self):
        for module_name, export_fn_name, deck_id in EXPORT_CASES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                expected = {"metadata": {}, "goldfish": {}}
                metadata = {"Card": {"type_line": "Artifact"}}

                fake_exporter = types.SimpleNamespace(
                    validate_output=Mock(return_value=True),
                    **{export_fn_name: Mock(return_value=expected)},
                )

                with patch.dict("sys.modules", {"export_simulation_results": fake_exporter}):
                    result = module.export_enhanced_json(metadata)

                self.assertIs(result, expected)
                getattr(fake_exporter, export_fn_name).assert_called_once_with(metadata)
                fake_exporter.validate_output.assert_called_once_with(expected, deck_id)

    def test_standalone_json_export_rejects_invalid_bulk_output(self):
        for module_name, export_fn_name, deck_id in EXPORT_CASES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                fake_result = {"metadata": {}}
                fake_exporter = types.SimpleNamespace(validate_output=Mock(return_value=False))
                setattr(fake_exporter, export_fn_name, Mock(return_value=fake_result))

                with patch.dict("sys.modules", {"export_simulation_results": fake_exporter}):
                    with self.assertRaisesRegex(ValueError, "invalid simulation output"):
                        module.export_enhanced_json({})

                getattr(fake_exporter, export_fn_name).assert_called_once_with({})
                fake_exporter.validate_output.assert_called_once_with(fake_result, deck_id)


class SerialPool:
    """multiprocessing.Pool stand-in that maps in this process."""

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @staticmethod
    def map(fn, iterable):
        return [fn(item) for item in iterable]


class RealWrapperExportTests(unittest.TestCase):
    def test_the_stampede_acres_wrapper_exports_its_own_deck(self):
        # Through the real exporter, at 16 games of each simulation: the
        # result is stampede-acres' own, not another deck's: its commander,
        # Baylen, the Haymaker, and the combo lines the goldfish read are
        # those of stampede-acres' deck file (winConditions kind "combo").
        # The wrapper imports the exporter by its module name, which
        # scripts.export_simulation_results puts on sys.path.
        exporter_package = importlib.import_module("scripts.export_simulation_results")
        exporter = importlib.import_module("export_simulation_results")
        module = importlib.import_module("scripts.mana_simulation_stampede_acres")
        metadata = json.loads(exporter_package.METADATA_FILE.read_text())
        deck = json.loads((exporter_package.PROJECT_ROOT / "data" / "commanders" / "stampede-acres"
                           / "deck.json").read_text())
        lines = [{"pieces": w["pieces"]} for w in deck["winConditions"] if w.get("kind") == "combo"]
        with patch.object(exporter, "NUM_GAMES", 16), patch.object(exporter, "GOLDFISH_GAMES", 16), \
                patch("multiprocessing.Pool", SerialPool):
            result = module.export_enhanced_json(metadata)
        self.assertTrue(lines)
        self.assertEqual((result["commanderTiming"]["name"], result["metadata"]["numGames"],
                          result["goldfish"]["comboLines"]),
                         ("Baylen, the Haymaker", 16, lines))

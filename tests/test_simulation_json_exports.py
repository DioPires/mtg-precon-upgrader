import importlib
import types
import unittest
from unittest.mock import Mock, patch


EXPORT_CASES = [
    ("scripts.mana_simulation_gathering_shadow", "export_grixis", "gathering-shadow"),
    ("scripts.mana_simulation_eternal_agony", "export_rakdos", "eternal-agony"),
    ("scripts.mana_simulation_eternal_harvest", "export_golgari", "eternal-harvest"),
    ("scripts.mana_simulation_witherbloom_the_balancer", "export_witherbloom", "witherbloom-the-balancer"),
    ("scripts.mana_simulation_titan_convergence", "export_titan", "titan-convergence"),
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

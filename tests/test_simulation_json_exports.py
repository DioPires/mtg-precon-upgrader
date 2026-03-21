import importlib
import types
import unittest
from unittest.mock import Mock, patch


class SimulationJsonExportTests(unittest.TestCase):
    def test_standalone_json_export_uses_bulk_exporter(self):
        cases = [
            ("scripts.mana_simulation_azure_dominion", "export_mono_blue", "azure-dominion"),
            ("scripts.mana_simulation_forge_and_fury", "export_forge", "forge-and-fury"),
        ]

        for module_name, export_fn_name, deck_id in cases:
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
        cases = [
            ("scripts.mana_simulation_azure_dominion", "azure-dominion"),
            ("scripts.mana_simulation_forge_and_fury", "forge-and-fury"),
        ]

        for module_name, deck_id in cases:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                fake_result = {"metadata": {}}
                fake_exporter = types.SimpleNamespace(
                    export_mono_blue=Mock(return_value=fake_result),
                    export_forge=Mock(return_value=fake_result),
                    validate_output=Mock(return_value=False),
                )

                with patch.dict("sys.modules", {"export_simulation_results": fake_exporter}):
                    with self.assertRaisesRegex(ValueError, "invalid simulation output"):
                        module.export_enhanced_json({})

                fake_exporter.validate_output.assert_called_once_with(fake_result, deck_id)

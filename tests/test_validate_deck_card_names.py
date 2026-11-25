import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


validator = importlib.import_module("scripts.validate_deck_json")


class ValidateDeckJsonTests(unittest.TestCase):
    def test_load_scryfall_name_index_includes_face_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mirror_file = Path(tmpdir) / "scryfall-oracle.json"
            mirror_file.write_text(json.dumps([
                {
                    "name": "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun",
                    "card_faces": [
                        {"name": "Growing Rites of Itlimoc"},
                        {"name": "Itlimoc, Cradle of the Sun"},
                    ],
                }
            ]))

            names = validator.load_scryfall_name_index(mirror_file)

        self.assertEqual(
            names.resolve("Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun"),
            "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun",
        )
        self.assertEqual(
            names.resolve("Growing Rites of Itlimoc"),
            "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun",
        )
        self.assertEqual(
            names.resolve("Itlimoc, Cradle of the Sun"),
            "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun",
        )

    def test_validate_deck_json_reports_missing_and_off_deck_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_file = Path(tmpdir) / "deck.json"
            deck_file.write_text(
                json.dumps({
                    "id": "test-deck",
                    "commander": "Known Commander",
                    "decklist": [
                        {"name": "Known Spell"},
                        {"name": "Known DFC Front"},
                    ],
                    "adds": [{"name": "Known Add"}],
                    "highlights": [{"name": "Off Deck Highlight"}],
                    "synergies": [
                        {
                            "title": "Narrative slot",
                            "cards": ["any damage source"],
                        }
                    ],
                })
            )
            scryfall_names = validator.ScryfallNameIndex({
                "Known Commander": "Known Commander",
                "Known Spell": "Known Spell",
                "Known Add": "Known Add",
                "Known DFC Front": "Known DFC // Known Back",
                "Known DFC // Known Back": "Known DFC // Known Back",
                "Off Deck Highlight": "Off Deck Highlight",
            })

            issues = validator.validate_deck_json([deck_file], scryfall_names)

        self.assertEqual(
            [(issue.issue_type, issue.reference.json_path, issue.reference.name) for issue in issues],
            [
                ("not_in_decklist", "adds[0].name", "Known Add"),
                ("not_in_decklist", "highlights[0].name", "Off Deck Highlight"),
                ("missing_scryfall", "synergies[0].cards[0]", "any damage source"),
            ],
        )

    def test_validate_deck_json_reports_malformed_candidate_pins(self):
        no_key = object()
        with tempfile.TemporaryDirectory() as tmpdir:
            decks = {
                "list-pins": [
                    "Bare String Pin",
                    {"reason": "Pin without a name (DEC-996)."},
                    {"name": "  ", "reason": "Blank name (DEC-996)."},
                    {"name": "Known Spell", "reason": "Well-formed pin (DEC-996)."},
                ],
                "string-pins": "Known Spell",
                "null-pins": None,
                "no-pins": no_key,
            }
            deck_files = []
            for deck_id, pins in decks.items():
                deck = {"id": deck_id, "commander": "Known Commander", "decklist": [{"name": "Known Spell"}]}
                if pins is not no_key:
                    deck["candidate_pins"] = pins
                deck_file = Path(tmpdir) / deck_id / "deck.json"
                deck_file.parent.mkdir()
                deck_file.write_text(json.dumps(deck))
                deck_files.append(deck_file)
            scryfall_names = validator.ScryfallNameIndex({
                "Known Commander": "Known Commander",
                "Known Spell": "Known Spell",
            })

            issues = validator.validate_deck_json(deck_files, scryfall_names)

        self.assertEqual(
            [(issue.issue_type, issue.reference.deck_id, issue.reference.json_path) for issue in issues],
            [
                ("invalid_candidate_pins", "list-pins", "candidate_pins[0]"),
                ("invalid_candidate_pins", "list-pins", "candidate_pins[1]"),
                ("invalid_candidate_pins", "list-pins", "candidate_pins[2]"),
                ("invalid_candidate_pins", "null-pins", "candidate_pins"),
                ("invalid_candidate_pins", "string-pins", "candidate_pins"),
            ],
        )
        for issue in issues:
            self.assertIn(f"Deck {issue.reference.deck_id}:", issue.detail)

    def test_load_scryfall_name_index_reads_the_front_face_mana_cost(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mirror_file = Path(tmpdir) / "scryfall-oracle.json"
            mirror_file.write_text(json.dumps([
                {"name": "Walking Ballista", "mana_cost": "{X}{X}"},
                {"name": "Fire // Ice", "mana_cost": "{1}{R} // {1}{U}",
                 "card_faces": [{"name": "Fire"}, {"name": "Ice"}]},
                {"name": "Front Spell // Back Land", "mana_cost": None,
                 "card_faces": [{"name": "Front Spell", "mana_cost": "{X}{B}"},
                                {"name": "Back Land", "mana_cost": ""}]},
            ]))

            names = validator.load_scryfall_name_index(mirror_file)

        self.assertEqual(
            [names.mana_cost(name) for name in ("Walking Ballista", "Ice", "Back Land", "Unknown")],
            ["{X}{X}", "{1}{R}", "{X}{B}", ""],
        )

    def test_validate_deck_json_reports_malformed_min_x(self):
        pieces = ["Walking Ballista", "Heliod, Sun-Crowned"]
        # (label, minX, the reported json path's name or None when valid)
        cases = [
            ("valid", {"Walking Ballista": 2}, None),
            ("empty", {}, None),
            ("not one of the line's pieces", {"Hangarback Walker": 1}, "Hangarback Walker"),
            ("a piece with no {X} in its cost", {"Heliod, Sun-Crowned": 1}, "Heliod, Sun-Crowned"),
            ("zero", {"Walking Ballista": 0}, "Walking Ballista"),
            ("negative", {"Walking Ballista": -1}, "Walking Ballista"),
            ("a string", {"Walking Ballista": "2"}, "Walking Ballista"),
            ("a boolean", {"Walking Ballista": True}, "Walking Ballista"),
            ("a float", {"Walking Ballista": 2.0}, "Walking Ballista"),
            ("not a mapping", ["Walking Ballista"], "['Walking Ballista']"),
        ]
        scryfall_names = validator.ScryfallNameIndex(
            {name: name for name in ["Known Commander", "Hangarback Walker"] + pieces},
            {"Walking Ballista": "{X}{X}", "Heliod, Sun-Crowned": "{2}{W}", "Hangarback Walker": "{X}{X}"},
        )
        for label, min_x, reported in cases:
            with self.subTest(label), tempfile.TemporaryDirectory() as tmpdir:
                deck_file = Path(tmpdir) / "deck.json"
                deck_file.write_text(json.dumps({
                    "id": "test-deck",
                    "commander": "Known Commander",
                    "decklist": [{"name": name} for name in pieces + ["Hangarback Walker"]],
                    "winConditions": [
                        {"title": "No minX", "kind": "combo", "cards": pieces, "pieces": pieces},
                        {"title": "Loop", "kind": "combo", "cards": pieces, "pieces": pieces, "minX": min_x},
                    ],
                }))

                issues = validator.validate_deck_json([deck_file], scryfall_names)

                self.assertEqual(
                    [(issue.issue_type, issue.reference.json_path, issue.reference.name) for issue in issues],
                    [] if reported is None else [("invalid_min_x", "winConditions[1].minX", reported)],
                )

    @unittest.skipUnless(
        validator.MIRROR_FILE.exists(),
        "local Scryfall mirror is generated by scripts/refresh_scryfall_mirror.py",
    )
    def test_checked_in_deck_card_names_exist_in_local_scryfall_mirror(self):
        scryfall_names = validator.load_scryfall_name_index()
        missing = validator.validate_deck_json(
            validator.available_deck_paths(),
            scryfall_names,
        )

        self.assertEqual(missing, [])


class ImportTests(unittest.TestCase):
    def test_the_module_imports_in_a_new_process(self):
        """The validator puts its own folder on sys.path, so its sibling
        gate_tags_lib imports when the validator is imported or run as
        scripts.validate_deck_json from the repository root, without another
        module having done it first."""
        root = Path(validator.__file__).resolve().parent.parent
        imported = "import scripts.validate_deck_json as m; print(m.gate_tags_lib.__name__)"
        for label, args in (("import", ["-c", imported]), ("-m", ["-m", "scripts.validate_deck_json", "--help"])):
            with self.subTest(label):
                proc = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("gate_tags_lib" if label == "import" else "usage:", proc.stdout)


if __name__ == "__main__":
    unittest.main()

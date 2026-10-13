import importlib
import json
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
        with tempfile.TemporaryDirectory() as tmpdir:
            decks = {
                "list-pins": [
                    "Bare String Pin",
                    {"reason": "Pin without a name (DEC-996)."},
                    {"name": "  ", "reason": "Blank name (DEC-996)."},
                    {"name": "Known Spell", "reason": "Well-formed pin (DEC-996)."},
                ],
                "string-pins": "Known Spell",
                "no-pins": None,
            }
            deck_files = []
            for deck_id, pins in decks.items():
                deck = {"id": deck_id, "commander": "Known Commander", "decklist": [{"name": "Known Spell"}]}
                if pins is not None:
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
                ("invalid_candidate_pins", "string-pins", "candidate_pins"),
            ],
        )
        for issue in issues:
            self.assertIn(f"Deck {issue.reference.deck_id}:", issue.detail)

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


if __name__ == "__main__":
    unittest.main()

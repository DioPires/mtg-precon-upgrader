import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"


class CardMetadataCoverageTests(unittest.TestCase):
    def test_all_commander_cards_have_metadata(self):
        metadata = json.loads(METADATA_FILE.read_text())

        for deck_file in sorted(COMMANDERS_DIR.glob("*/deck.json")):
            deck = json.loads(deck_file.read_text())
            card_names = {deck["commander"]} | {card["name"] for card in deck["decklist"]}
            missing = sorted(name for name in card_names if name not in metadata)

            with self.subTest(deck_id=deck_file.parent.name):
                self.assertEqual(missing, [])

    def test_every_entry_carries_printed_power_and_toughness(self):
        """DEC-940 — printed P/T is part of the card-metadata envelope."""
        metadata = json.loads(METADATA_FILE.read_text())
        missing_keys = sorted(
            name for name, entry in metadata.items()
            if "power" not in entry or "toughness" not in entry
        )
        self.assertEqual(missing_keys, [])

        # Creatures carry a printed value (strings as Scryfall gives them, so
        # "*" survives); non-creatures carry None.
        creatures = [
            (name, entry) for name, entry in metadata.items()
            if "Creature" in entry.get("type_line", "")
        ]
        self.assertGreater(len(creatures), 500)
        # The only creatures without front-face power are DFCs whose creature
        # face is the back one (Fable of the Mirror-Breaker, Westvale Abbey).
        powerless = sorted(
            name for name, entry in creatures if entry["power"] is None)
        self.assertEqual(
            powerless,
            ["Fable of the Mirror-Breaker",
             "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki",
             "Westvale Abbey",
             "Westvale Abbey // Ormendahl, Profane Prince"])
        for name, entry in metadata.items():
            if "Creature" in entry.get("type_line", ""):
                continue
            with self.subTest(card=name):
                self.assertIsNone(entry["power"])
                self.assertIsNone(entry["toughness"])

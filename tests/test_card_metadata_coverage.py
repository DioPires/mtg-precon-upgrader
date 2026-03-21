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

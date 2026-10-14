import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
META_FILE = PROJECT_ROOT / "data" / "card-metadata.meta.json"


def _deck_card_names(deck: dict) -> set[str]:
    """Every name that scripts/fetch_card_metadata.py takes from a deck file."""
    names = {deck["commander"]} | {card["name"] for card in deck["decklist"]}
    if deck.get("partner"):
        names.add(deck["partner"])
    names.update(card["name"] for card in deck.get("adds", []))
    return names


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

    def test_every_deck_card_has_an_image(self):
        """DEC-1075 — the app builds a card's image addresses from ``image``."""
        metadata = json.loads(METADATA_FILE.read_text())

        for deck_file in sorted(COMMANDERS_DIR.glob("*/deck.json")):
            deck = json.loads(deck_file.read_text())
            without_image = sorted(
                name for name in _deck_card_names(deck)
                if not metadata.get(name, {}).get("image"))

            with self.subTest(deck_id=deck_file.parent.name):
                self.assertEqual(without_image, [])

    def test_every_entry_carries_image_and_prices(self):
        """DEC-1075 — ``image``, ``usd`` and ``eur`` are part of the envelope."""
        metadata = json.loads(METADATA_FILE.read_text())
        missing_keys = sorted(
            name for name, entry in metadata.items()
            if not {"image", "usd", "eur"} <= set(entry)
        )
        self.assertEqual(missing_keys, [])

        # ``image`` is a path under https://cards.scryfall.io/<size>/, not an
        # address; a price is a number. All three are None when Scryfall gave none.
        bad_image = sorted(
            name for name, entry in metadata.items()
            if entry["image"] is not None
            and not (isinstance(entry["image"], str) and entry["image"]
                     and "://" not in entry["image"])
        )
        self.assertEqual(bad_image, [])
        bad_price = sorted(
            name for name, entry in metadata.items()
            for price in (entry["usd"], entry["eur"])
            if price is not None
            and not (isinstance(price, (int, float)) and not isinstance(price, bool)
                     and price >= 0)
        )
        self.assertEqual(bad_price, [])

    def test_meta_file_counts_every_entry(self):
        """DEC-1075 — card-metadata.meta.json describes the run that wrote the file."""
        metadata = json.loads(METADATA_FILE.read_text())
        meta = json.loads(META_FILE.read_text())

        self.assertEqual(sorted(meta), ["count", "prices_as_of", "source"])
        self.assertEqual(meta["count"], len(metadata))
        self.assertEqual(datetime.fromisoformat(meta["prices_as_of"]).utcoffset(), timedelta(0))

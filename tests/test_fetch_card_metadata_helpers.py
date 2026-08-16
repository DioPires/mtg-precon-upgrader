import importlib
import json
import tempfile
import unittest
from pathlib import Path


fetch_metadata = importlib.import_module("scripts.fetch_card_metadata")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class FetchCardMetadataHelperTests(unittest.TestCase):
    def test_available_deck_ids_matches_deck_directories(self):
        expected = sorted(path.parent.name for path in (PROJECT_ROOT / "data" / "commanders").glob("*/deck.json"))
        self.assertEqual(fetch_metadata.available_deck_ids(), expected)

    def test_collect_card_names_for_single_deck_matches_deck_file(self):
        deck_id = "gathering-shadow"
        with open(PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json") as f:
            deck = json.load(f)

        expected = {deck["commander"]}
        if deck.get("partner"):
            expected.add(deck["partner"])
        expected.update(card["name"] for card in deck.get("adds", []))
        expected.update(card["name"] for card in deck.get("decklist", []))

        self.assertEqual(fetch_metadata.collect_card_names([deck_id]), expected)

    def test_load_existing_metadata_returns_empty_dict_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            self.assertEqual(fetch_metadata.load_existing_metadata(path), {})

    def test_load_existing_metadata_reads_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metadata.json"
            expected = {"Sol Ring": {"cmc": 1}}
            path.write_text(json.dumps(expected))
            self.assertEqual(fetch_metadata.load_existing_metadata(path), expected)

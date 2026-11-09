"""DEC-687 — fleet recount caps in scripts/check_game_changers.py.

No deck has its own Game Changer cap (the user, DEC-687, superseding DEC-369's
verdant-tide <= 1). Only the bracket cap remains: brackets 1-3 and 3+ allow at
most 3 GCs, 4-/4/4+/5 are uncapped. The recount itself still has to match.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import check_game_changers as gc  # noqa: E402

GC_NAMES = {"Alpha", "Bravo", "Charlie", "Delta"}


class FleetCapTests(unittest.TestCase):
    def _fleet(self, decks: dict[str, dict]) -> list[str]:
        """Run check_fleet over `decks` ({id: {bracket, gameChangers, cards}})."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        commanders = root / "commanders"
        for deck_id, spec in decks.items():
            (commanders / deck_id).mkdir(parents=True)
            (commanders / deck_id / "deck.json").write_text(json.dumps({
                "bracket": spec["bracket"],
                "gameChangers": spec["gameChangers"],
                "decklist": [{"name": name} for name in spec["cards"]],
            }), encoding="utf-8")
        index = root / "index.json"
        index.write_text(json.dumps({"commanders": [{"id": d} for d in decks]}), encoding="utf-8")
        with mock.patch.object(gc, "INDEX_JSON", index), mock.patch.object(gc, "COMMANDERS_DIR", commanders):
            return gc.check_fleet(GC_NAMES)

    def test_verdant_tide_has_no_cap_of_its_own(self):
        problems = self._fleet({"verdant-tide": {"bracket": "3", "gameChangers": 2, "cards": ["Alpha", "Bravo"]}})
        self.assertEqual(problems, [])

    def test_bracket_three_over_three_gcs_is_reported(self):
        problems = self._fleet({"b3-deck": {"bracket": "3+", "gameChangers": 4, "cards": ["Alpha", "Bravo", "Charlie", "Delta"]}})
        self.assertEqual(problems, ["b3-deck: 4 GCs exceeds bracket cap 3 (bracket 3+): ['Alpha', 'Bravo', 'Charlie', 'Delta']"])

    def test_bracket_four_minus_is_uncapped(self):
        problems = self._fleet({"b4-deck": {"bracket": "4-", "gameChangers": 4, "cards": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]}})
        self.assertEqual(problems, [])

    def test_stale_gamechangers_field_is_reported(self):
        problems = self._fleet({"stale": {"bracket": "4", "gameChangers": 1, "cards": ["Alpha", "Bravo"]}})
        self.assertEqual(problems, ["stale: gameChangers field 1 != recount 2 (['Alpha', 'Bravo'])"])


if __name__ == "__main__":
    unittest.main()

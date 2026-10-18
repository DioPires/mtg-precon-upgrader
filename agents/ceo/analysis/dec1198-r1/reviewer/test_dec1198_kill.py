"""DEC-1198 kill cases for the mutants of PR #81 that survive the suite, and one fault case.

Every card here is invented. The classes take the style of tests/test_auto_tag_roles.py, so a fix
round can paste them into that file as they are. ATR_ROOT names the tree whose scripts/ to import.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(os.environ.get("ATR_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(ROOT / "scripts"))

import auto_tag_roles as atr  # noqa: E402


def _card(name: str, type_line: str, oracle_text: str) -> dict:
    return {"name": name, "type_line": type_line, "oracle_text": oracle_text}


class CantripKillTests(unittest.TestCase):
    """Each part of `_is_cantrip` and `_REPEATABLE_DRAW` has a case (DEC-1198 B1)."""

    def test_draw_a_card_for_each_is_card_draw(self):  # kills X1: (?! for each) dropped
        card = _card("Tallyhorn Census", "Sorcery", "Draw a card for each creature you control.")
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_draw_at_the_beginning_of_your_upkeep_is_card_draw(self):  # kills X3: "at the beginning of" dropped
        card = _card("Dawnquill Almanac", "Enchantment", "At the beginning of your upkeep, draw a card.")
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_draw_one_card_once_is_not_card_draw(self):  # kills X4: the cantrip read takes "a card" only
        card = _card("Mistveil Nudge", "Instant", "Tap target creature.\nDraw one card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_discard_this_card_outside_reminder_text_is_not_card_draw(self):  # kills X6: "discard this" dropped
        card = _card("Tidewhisper Skiff", "Creature — Merfolk Scout", "Flying\n{1}{U}, Discard this card: Draw a card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_draw_at_the_beginning_of_the_next_upkeep_is_not_card_draw(self):  # kills X7: (?!the next end step)
        card = _card(
            "Lantern of Tomorrow",
            "Instant",
            "Tap target creature.\nDraw a card at the beginning of the next turn's upkeep.",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_target_player_draws_a_card_once_is_not_card_draw(self):  # kills X9: the cantrip read takes "draw" only
        card = _card("Quillfeather Gift", "Instant", "You gain 2 life. Target player draws a card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class DrawCountKillTests(unittest.TestCase):
    """Each count word of `_DRAW` reads card-draw (DEC-1198 B2)."""

    def test_each_count_word_reads_card_draw(self):
        for label, type_line, oracle_text in (
            ("draws", "Sorcery", "Target player draws two cards."),  # kills X10
            ("one", "Enchantment", "Whenever a creature you control dies, draw one card."),
            ("three", "Sorcery", "Draw three cards."),
            ("four", "Sorcery", "Draw four cards."),
            ("five", "Sorcery", "Draw five cards."),
            ("six", "Sorcery", "Draw six cards."),
            ("seven", "Sorcery", "Draw seven cards."),
            ("eight", "Sorcery", "Draw eight cards."),
            ("nine", "Sorcery", "Draw nine cards."),
            ("ten", "Sorcery", "Draw ten cards."),
            ("x", "Sorcery", "Draw X cards."),
            ("digits", "Sorcery", "Draw 3 cards."),
            ("that many", "Sorcery", "Sacrifice any number of artifacts, then draw that many cards."),
            ("equal to", "Sorcery", "Draw cards equal to the number of creatures you control."),  # kills X5
        ):
            with self.subTest(label=label):
                card = _card("Countless Folio", type_line, oracle_text)
                self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class ToughnessCutKillTests(unittest.TestCase):
    """Each part of `_TARGET_CREATURE_GETS` and `_POWER_CUT_KILL` has a case (DEC-1198 B3)."""

    def test_qualifier_of_more_than_twenty_characters_is_read(self):  # kills Y1: {1,40} as {1,20}
        card = _card(
            "Skybane Hex",
            "Instant",
            "Target creature an opponent controls with flying gets -3/-3 until end of turn.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_qualifier_with_a_semicolon_is_another_clause(self):  # kills Y2: ";" dropped from the qualifier
        card = _card(
            "Gloomtether Brute",
            "Creature — Ogre",
            "{2}: Tap target creature an opponent controls; this creature gets +2/-2 until end of turn.",
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_power_cut_that_then_destroys_that_creature_is_removal_spot(self):  # kills Y4: "destroy it" only
        card = _card(
            "Crushing Tide",
            "Instant",
            "Target creature gets -3/-0 until end of turn. Then if that creature's power is 0 or less, "
            "destroy that creature.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_x_power_cut_that_then_destroys_is_removal_spot(self):  # kills Y6: x dropped from the guard
        card = _card(
            "Wilting Undertow",
            "Instant",
            "Target creature gets -X/-0 until end of turn, where X is the number of cards in your hand. "
            "Then if that creature's power is 0 or less, destroy it.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_qualified_power_cut_that_then_destroys_is_removal_spot(self):  # kills Y7: the guard without the qualifier
        card = _card(
            "Brineclutch Horror",
            "Creature — Horror",
            "When this creature enters, target creature an opponent controls gets -3/-0 until end of turn. "
            "Then if that creature's power is 0 or less, destroy it.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))


class GraveyardCostFaultTests(unittest.TestCase):
    """Fault case of B4 (probe P2): it fails on the head and passes with the fix."""

    def test_draw_behind_exile_this_card_from_your_graveyard_is_not_card_draw(self):
        card = _card(
            "Ashveil Courier",
            "Creature — Spirit Scout",
            "Menace\n{2}{B}, Exile this card from your graveyard: Draw a card.",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

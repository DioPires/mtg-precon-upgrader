"""DEC-1143 — tests for the role detectors in scripts/auto_tag_roles.py.

Every card here is invented; only the oracle-text forms come from real cards.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import auto_tag_roles as atr  # noqa: E402


def _card(name: str, type_line: str, oracle_text: str) -> dict:
    return {"name": name, "type_line": type_line, "oracle_text": oracle_text}


class NamedSearchTests(unittest.TestCase):
    """A search limited to a card by its name is not a tutor."""

    def test_search_for_copies_of_itself_is_not_tutor(self):
        card = _card(
            "Gloamvale Recruit",
            "Creature — Human Soldier",
            "When this creature enters, you may search your library for any number of cards named "
            "Gloamvale Recruit, reveal them, put them into your hand, then shuffle.",
        )
        self.assertEqual(atr.classify(card), (None, 0.0))

    def test_search_for_another_named_card_is_not_tutor(self):
        card = _card(
            "Emberwing Herald",
            "Legendary Creature — Human Scout",
            "Flying\nWhen Emberwing Herald enters, you may search your library for a card named "
            "Emberwing, Sovereign of Ash, reveal it, put it into your hand, then shuffle.",
        )
        self.assertEqual(atr.classify(card), (None, 0.0))

    def test_search_for_a_creature_card_stays_tutor(self):
        # "named" elsewhere in the text does not make the search a named search.
        card = _card(
            "Pact of the Ninefold",
            "Sorcery",
            "You may exile four cards named Pact of the Ninefold from your graveyard. If you do, "
            "search your library for a creature card, reveal it, put it into your hand, then shuffle.",
        )
        self.assertEqual(atr.classify(card), ("tutor", 0.85))

    def test_named_card_or_a_card_of_a_type_stays_tutor(self):
        card = _card(
            "Forging the Vale Blade",
            "Enchantment — Saga",
            "III — Search your library for a card named Orvar, God of Battle or an Equipment card, "
            "reveal it, put it into your hand, then shuffle.",
        )
        self.assertEqual(atr.classify(card), ("tutor", 0.85))

    def test_named_search_beside_an_open_search_stays_tutor(self):
        card = _card(
            "Ilsa, Grove Warden",
            "Legendary Planeswalker — Ilsa",
            "+1: Search your library for a card named Ilsa's Chosen, put it onto the battlefield, "
            "then shuffle.\n−7: Search your library for any number of Elf creature cards, put them "
            "onto the battlefield, then shuffle.",
        )
        self.assertEqual(atr.classify(card), ("tutor", 0.85))


class GraveyardExileTests(unittest.TestCase):
    """A target that is a card in a graveyard is not removal-spot."""

    def test_exile_of_a_card_in_a_graveyard_is_not_removal_spot(self):
        for oracle_text in (
            "{5}, {T}, Sacrifice this artifact: Exile target creature card from your graveyard. "
            "Create a 1/1 white Spirit creature token with flying.",
            "{2}, {T}: Exile target artifact card from a graveyard. You gain 2 life.",
            "Whenever this creature attacks, exile target creature card with mana value 3 or less "
            "from an opponent's graveyard.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Ashen Curator", "Artifact", oracle_text)
                self.assertEqual(atr.classify(card), (None, 0.0))

    def test_exile_of_target_creature_stays_removal_spot(self):
        card = _card(
            "Dawnward Warden",
            "Instant",
            "Exile target creature. Its controller draws a card.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_graveyard_exile_beside_a_permanent_target_stays_removal_spot(self):
        card = _card(
            "Grave-Lit Purge",
            "Sorcery",
            "Exile target creature card from a graveyard.\nDestroy target artifact.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_second_target_in_a_graveyard_keeps_the_first_target(self):
        card = _card(
            "Unmake and Remake",
            "Sorcery",
            "Exile target creature and return up to one target creature card from your graveyard "
            "to your hand.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))


if __name__ == "__main__":
    unittest.main()

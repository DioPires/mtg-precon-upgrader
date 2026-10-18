"""DEC-1208 kill cases for the surviving mutants of PR #84 (review of DEC-1197).

Every card here is invented; only the oracle-text forms come from real cards.
The header below runs this file from outside the tree. A fix round takes the
classes below the line "# ---- classes ----" into tests/test_auto_tag_roles.py
as they are (that file already defines `_card` and imports `atr`).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.environ["TREE"], "scripts"))

import auto_tag_roles as atr  # noqa: E402


def _card(name: str, type_line: str, oracle_text: str) -> dict:
    return {"name": name, "type_line": type_line, "oracle_text": oracle_text}


# ---- classes ----


class AdditionalDrawCountKillTests(unittest.TestCase):
    """Each count word of the "additional" alternative of `_DRAW` reads a draw (DEC-1208, item 2)."""

    def test_each_count_word_of_an_additional_draw_reads_card_draw(self):
        for label, oracle_text in (
            ("one", "At the beginning of each player's draw step, that player draws one additional card."),
            ("three", "At the beginning of each player's draw step, that player draws three additional cards."),
            ("four", "At the beginning of each player's draw step, that player draws four additional cards."),
            ("five", "At the beginning of each player's draw step, that player draws five additional cards."),
            ("six", "At the beginning of each player's draw step, that player draws six additional cards."),
            ("seven", "At the beginning of each player's draw step, that player draws seven additional cards."),
            ("eight", "At the beginning of each player's draw step, that player draws eight additional cards."),
            ("nine", "At the beginning of each player's draw step, that player draws nine additional cards."),
            ("ten", "At the beginning of each player's draw step, that player draws ten additional cards."),
            ("x", "At the beginning of your draw step, draw X additional cards, where X is the number of Wizards "
             "you control."),
            ("digits", "At the beginning of each player's draw step, that player draws 2 additional cards."),
            ("that many", "At the beginning of your draw step, put a page counter on this artifact, then draw that "
             "many additional cards."),
        ):
            with self.subTest(label=label):
                card = _card("Brimming Lectern", "Artifact", oracle_text)
                self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class SpentCardCostKillTests(unittest.TestCase):
    """A cost that exiles this creature, or sacrifices a face by its name, spends the card (DEC-1208, item 3)."""

    def test_draw_behind_exile_this_creature_is_not_card_draw(self):
        card = _card("Gravewick Moth", "Creature — Insect", "Flying\n{1}, Exile this creature: Draw a card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_draw_behind_sacrifice_of_a_faces_name_is_not_card_draw(self):
        card = {
            "name": "Lanternwick Sentry // Lanternwick Ascended",
            "type_line": "Artifact Creature — Construct // Artifact Creature — Construct",
            "card_faces": [
                {
                    "name": "Lanternwick Sentry",
                    "type_line": "Artifact Creature — Construct",
                    "oracle_text": "{2}, Sacrifice Lanternwick Sentry: Draw a card.",
                },
                {
                    "name": "Lanternwick Ascended",
                    "type_line": "Artifact Creature — Construct",
                    "oracle_text": "Flying",
                },
            ],
        }
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class LootCountKillTests(unittest.TestCase):
    """Each count word of a loot is read, and so are "discards" and "an additional card" (DEC-1208, items 4 and 7)."""

    def test_loot_that_keeps_one_card_is_not_card_draw(self):
        for label, type_line, oracle_text in (
            ("three", "Sorcery", "Draw three cards, then discard two cards."),
            ("four", "Sorcery", "Draw four cards, then discard three cards."),
            ("five", "Sorcery", "Draw five cards, then discard four cards."),
            ("discards", "Creature — Merfolk Wizard", "{T}: Target player draws a card, then discards a card."),
            ("an additional card", "Enchantment", "At the beginning of your draw step, draw an additional card, "
             "then discard a card."),
        ):
            with self.subTest(label=label):
                card = _card("Siltreader Adept", type_line, oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")


class DiscardCostKillTests(unittest.TestCase):
    """The count of a discard cost is read (DEC-1208, item 5)."""

    def test_discard_two_to_draw_three_is_not_card_draw(self):
        card = _card(
            "Ashen Reunion", "Sorcery", "As an additional cost to cast this spell, discard two cards.\nDraw three cards."
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class DrawSubjectKillTests(unittest.TestCase):
    """Each subject of another player's draw in `_OTHER_DRAW` is read (DEC-1208, item 6)."""

    def test_each_subject_of_another_players_draw_is_not_card_draw(self):
        for label, type_line, oracle_text in (
            ("target opponent", "Sorcery", "Target opponent draws two cards."),
            ("that opponent", "Sorcery", "Choose an opponent. That opponent draws two cards."),
            ("your opponents each", "Sorcery", "Your opponents each draw two cards."),
            ("defending player", "Creature — Goblin", "Whenever this creature attacks, defending player draws a card."),
            ("each other player", "Enchantment", "At the beginning of your upkeep, each other player draws a card."),
            ("whenever a player", "Enchantment", "Whenever a player draws a card, you gain 1 life."),
            ("whenever another player", "Enchantment", "Whenever another player draws a card, you gain 1 life."),
            ("whenever enchanted player", "Enchantment — Aura Curse", "Enchant player\nWhenever enchanted player "
             "draws a card, this Aura deals 1 damage to them."),
            ("if a player would", "Enchantment", "If a player would draw two cards, that player mills two cards "
             "instead."),
            ("if another player would", "Enchantment", "If another player would draw two cards, that player mills "
             "two cards instead."),
            ("they after an opponent's step", "Enchantment", "At the beginning of each opponent's upkeep, they draw a "
             "card."),
            ("may", "Sorcery", "Target opponent may draw two cards."),
        ):
            with self.subTest(label=label):
                card = _card("Gilded Envoy", type_line, oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")


class RepeatableLootKillTests(unittest.TestCase):
    """The rummage forms and the cost read of `_draw_net` (DEC-1208, item 7)."""

    def test_rummage_forms_are_not_card_draw(self):
        for label, type_line, oracle_text in (
            ("at random", "Creature — Human Rogue", "{T}: Discard a card at random, then draw a card."),
            ("you may draw", "Creature — Human Rogue", "Whenever this creature attacks, discard a card. If you do, "
             "you may draw a card."),
            ("if they do, they", "Creature — Human Rogue", "Whenever this creature attacks, target player discards a "
             "card. If they do, they draw a card."),
            ("each player discards", "Creature — Human Rogue", "Whenever this creature attacks, each player discards "
             "a card, then draws a card."),
            ("the last colon", "Enchantment — Aura", "Enchant creature\n{4}{W}: Exile enchanted creature. Create a "
             'Blood token. (It\'s an artifact with "{1}, {T}, Discard a card, Sacrifice this token: Draw a card.")'),
        ):
            with self.subTest(label=label):
                card = _card("Hollowbrook Gambler", type_line, oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_one_shot_draw_of_an_additional_card_is_not_card_draw(self):
        card = _card(
            "Patient Tidings", "Sorcery", "At the beginning of the next turn's draw step, draw an additional card."
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_discard_outside_the_draws_own_ability_does_not_count(self):
        for label, type_line, oracle_text in (
            ("quoted cost before the draw", "Enchantment — Aura", 'Enchant creature\nEnchanted creature has "Discard '
             'a card: This creature gets +1/+0 until end of turn." At the beginning of your upkeep, draw a card.'),
            ("cost before a parenthesis", "Creature — Human Wizard", "Discard a card: This creature gains flying "
             "until end of turn. (This creature also has {T}: Draw a card.)"),
            ("cost on an earlier line", "Creature — Zombie", "{1}{B}, {T}, Discard a card: Create a 2/2 black Zombie "
             "creature token.\nTap three untapped Zombies you control: You draw a card and lose 1 life."),
            ("discard in an earlier clause", "Sorcery", "Target opponent sacrifices a creature, discards three cards, "
             "then loses 5 life. You draw three cards, then gain 5 life."),
        ):
            with self.subTest(label=label):
                card = _card("Mirrorhall Savant", type_line, oracle_text)
                self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class DrawAgainKillTests(unittest.TestCase):
    """Each word of `_DRAW_AGAIN` that `DrawAgainTests` does not hold (DEC-1208, item 7a)."""

    def test_each_further_word_gives_the_draw_again(self):
        for label, type_line, oracle_text in (
            ("gravestorm", "Sorcery", "Gravestorm (When you cast this spell, copy it for each permanent put into a "
             "graveyard from the battlefield this turn.)\nDraw a card."),
            ("replicate", "Sorcery", "Replicate {1}{U} (When you cast this spell, copy it for each time you paid its "
             "replicate cost.)\nDraw a card."),
            ("copy this spell", "Instant", "As an additional cost to cast this spell, you may sacrifice a creature. "
             "When you do, copy this spell.\nYou draw a card and lose 1 life."),
            ("enters or dies", "Creature — Spirit", "When this creature enters or dies, draw a card."),
            ("buyback", "Instant", "Buyback {3} (You may pay an additional {3} as you cast this spell. If you do, put "
             "this card into your hand as it resolves.)\nDraw a card."),
            ("cipher", "Sorcery", "Draw a card.\nCipher (Then you may exile this spell card encoded on a creature you "
             "control. Whenever that creature deals combat damage to a player, its controller may cast a copy of the "
             "encoded card without paying its mana cost.)"),
            ("harmonize", "Sorcery", "Draw a card.\nHarmonize {4}{U} (You may cast this card from your graveyard for "
             "its harmonize cost. You may tap a creature you control to reduce that cost by {X}, where X is its "
             "power. Then exile this spell.)"),
        ):
            with self.subTest(label=label):
                card = _card("Echoing Missive", type_line, oracle_text)
                self.assertEqual(atr.classify(card)[0], "card-draw")


class UpToTargetKillTests(unittest.TestCase):
    """Each count word of `_UP_TO`, the "you control" lookahead, and the bounce read in full (DEC-1208, item 8)."""

    def test_each_count_word_of_up_to_reads_removal_spot(self):
        for label in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "X", "2"):
            with self.subTest(label=label):
                card = _card("Ruinous Decree", "Sorcery", f"Destroy up to {label} target creatures.")
                self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_up_to_target_of_two_or_three_words_you_control_is_not_removal_spot(self):
        for oracle_text in (
            "Destroy up to one target nonland permanent you control.",
            "Destroy up to one target artifact or non-Vehicle you control.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Hollow Offering", "Sorcery", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_bounce_of_a_nonland_permanent_is_removal_spot(self):
        for oracle_text in (
            "Return target nonland permanent to its owner's hand.",
            "Return up to one target nonland permanent to its owner's hand.",
            "Return target creature to their owner's hand.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Tideshove Adept", "Instant", oracle_text)
                self.assertEqual(atr.classify(card), ("removal-spot", 0.8))


class ExileUpToKillTests(unittest.TestCase):
    """The returns of `_NEXT_RETURN` and the owners of `_GRAVEYARD_CARD` (DEC-1208, item 9)."""

    def test_next_sentence_return_of_it_or_those_cards_is_not_removal_spot(self):
        for oracle_text in (
            "When this creature enters, exile up to one other target creature. Return it to the battlefield under "
            "its owner's control at the beginning of the next end step.",
            "Whenever this creature attacks, exile up to two other target creatures. Return those cards to the "
            "battlefield under their owners' control at the beginning of the next end step.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Mistveil Herder", "Creature — Kithkin Wizard", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_exile_from_that_players_or_their_graveyard_is_not_removal_spot(self):
        for oracle_text in (
            "Whenever this creature deals combat damage to a player, exile up to two target creature cards from "
            "that player's graveyard.",
            "Choose target opponent. Exile up to one target creature card from their graveyard.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Gravegnaw Badger", "Creature — Badger", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")


if __name__ == "__main__":
    unittest.main()

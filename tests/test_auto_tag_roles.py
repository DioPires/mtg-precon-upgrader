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

    def test_search_for_up_to_three_copies_is_not_tutor(self):
        card = _card(
            "Brindle Skyhawk",
            "Creature — Bird",
            "Flying\nWhen this creature enters, you may search your library for up to three cards named "
            "Brindle Skyhawk, reveal them, put them into your hand, then shuffle.",
        )
        self.assertEqual(atr.classify(card), (None, 0.0))

    def test_named_search_that_ends_in_and_put_is_not_tutor(self):
        card = _card(
            "Mossgate Sentinel",
            "Creature — Elf",
            "When this creature enters, you may pay {1}{G}. If you do, search your library for a card "
            "named Mossgate Sentinel and put that card onto the battlefield. Then shuffle.",
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


class TutorRetagTests(unittest.TestCase):
    """`--retag-tutors` reads a named search as `classify` does."""

    def test_named_search_gets_no_tutor_retag(self):
        card = _card(
            "Harrowfield Lookout",
            "Creature — Human Scout",
            "When this creature enters, you may search your library for a card named Harrowfield "
            "Lookout, reveal it, put it into your hand, then shuffle.",
        )
        self.assertIsNone(atr.classify_tutor_roles(card, "utility"))

    def test_named_search_beside_an_open_search_gets_a_tutor_retag(self):
        card = _card(
            "Ilsa, Grove Warden",
            "Legendary Planeswalker — Ilsa",
            "+1: Search your library for a card named Ilsa's Chosen, put it onto the battlefield, "
            "then shuffle.\n−7: Search your library for any number of Elf creature cards, put them "
            "onto the battlefield, then shuffle.",
        )
        self.assertEqual(atr.classify_tutor_roles(card, None), ("engine", "tutor", 0.75))


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

    def test_exile_of_a_card_that_is_in_a_graveyard_is_not_removal_spot(self):
        card = _card(
            "Echo of the Fallen Hour",
            "Instant",
            "Exile target nonland card in a graveyard that was put there from the battlefield this turn.",
        )
        self.assertEqual(atr.classify(card), (None, 0.0))

    def test_exile_from_target_players_graveyard_is_not_removal_spot(self):
        card = _card(
            "Cinderveil Archivist",
            "Artifact",
            "{1}, {T}: Exile target creature card from target player's graveyard.",
        )
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

    def test_graveyard_card_after_controls_is_another_clause(self):
        # "an opponent controls" ends the target; the graveyard card belongs to the next clause.
        for oracle_text in (
            "When this creature enters, exile target creature an opponent controls, then you may "
            "return a creature card from your graveyard to your hand.",
            "When this creature enters, exile target creature an opponent controls and return a "
            "creature card from your graveyard to your hand.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Thornmere Exarch", "Creature — Elf Cleric", oracle_text)
                self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_graveyard_card_after_then_is_another_clause(self):
        # ", then" ends the target; the graveyard card belongs to the next clause.
        for oracle_text in (
            "Exile target creature, then its controller returns a creature card from their "
            "graveyard to the battlefield.",
            "Exile target creature, then you may return a creature card from your graveyard to "
            "your hand.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Gravewake Exchange", "Sorcery", oracle_text)
                self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_graveyard_card_after_you_control_is_another_clause(self):
        # "you control" ends the target too; the exile of your own creature is a sac outlet.
        card = _card(
            "Bonecall Offering",
            "Instant",
            "Exile target creature you control and return a creature card from your graveyard to your hand.",
        )
        self.assertEqual(atr.classify(card), ("utility", 0.6))

    def test_word_that_begins_with_then_does_not_end_the_target(self):
        # "then" ends the target only as a word; "Thenari" is a creature type here.
        card = _card("Ashgrave Sifting", "Instant", "Exile target creature or Thenari card from a graveyard.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")


class LandTargetTests(unittest.TestCase):
    """A target that can be only a land is land destruction, not removal-spot."""

    def test_destroy_target_land_is_not_removal_spot(self):
        card = _card("Quarry Collapse", "Sorcery", "Destroy target land.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_land_beside_another_type_stays_removal_spot(self):
        card = _card("Shattering Tremor", "Sorcery", "Destroy target artifact, enchantment, or land.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_attacking_or_blocking_creature_stays_removal_spot(self):
        # The other words of the line that lost "land".
        for name, oracle_text in (
            ("Vanguard Reprisal", "Destroy target attacking creature."),
            ("Shieldbreak Ambush", "Destroy target blocking creature."),
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card(name, "Instant", oracle_text)
                self.assertEqual(atr.classify(card), ("removal-spot", 0.85))


class BlinkTests(unittest.TestCase):
    """A target that its own sentence returns to the battlefield is not removed."""

    def test_instant_blink_of_your_creature_is_protection(self):
        card = _card(
            "Glimmerstep Rescue",
            "Instant",
            "Exile target creature you control, then return it to the battlefield under its owner's control.",
        )
        self.assertEqual(atr.classify(card), ("protection", 0.8))

    def test_blink_of_any_nonland_permanent_is_not_removal_spot(self):
        card = _card(
            "Shimmer of the Mistgate",
            "Instant",
            "Exile target nonland permanent, then return it to the battlefield tapped under its owner's control.",
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_blink_beside_a_destroy_stays_removal_spot(self):
        card = _card(
            "Edict of Dusk and Dawn",
            "Sorcery",
            "Choose one or both —\n• Destroy target creature.\n• Exile target creature you control, then "
            "return it to the battlefield under its owner's control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_return_under_your_control_of_an_opponents_creature_is_removal_spot(self):
        # The card comes back under your control: a steal, not a blink.
        card = _card(
            "Rivenmark Usurpation",
            "Instant",
            "Exile target creature an opponent controls, then return it to the battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_return_under_your_control_of_your_creature_is_protection(self):
        card = _card(
            "Hollowlight Return",
            "Instant",
            "Exile target creature you control, then return it to the battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), ("protection", 0.8))

    def test_blink_that_returns_those_cards_is_protection(self):
        card = _card(
            "Twinfold Shelter",
            "Instant",
            "Exile target artifact you control and target creature you control, then return those "
            "cards to the battlefield under their owners' control.",
        )
        self.assertEqual(atr.classify(card), ("protection", 0.8))

    def test_exile_of_your_creature_with_a_later_return_is_utility(self):
        # The return is in another sentence, so this is no blink, and the exile is a sac outlet.
        card = _card(
            "Stasis Reliquary",
            "Artifact",
            "{2}, {T}: Exile target creature you control.\nSacrifice this artifact: Return each card "
            "exiled with it to the battlefield under its owner's control.",
        )
        self.assertEqual(atr.classify(card), ("utility", 0.6))

    def test_return_to_its_owners_hand_is_not_a_blink(self):
        card = _card(
            "Banishing Rebuke",
            "Instant",
            "Exile target creature an opponent controls, then return it to its owner's hand.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_tapped_return_under_your_control_of_an_opponents_creature_is_removal_spot(self):
        card = _card(
            "Ironveil Seizure",
            "Instant",
            "Exile target creature an opponent controls, then return it to the battlefield tapped under your "
            "control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_return_under_your_control_of_a_creature_you_own_is_not_removal_spot(self):
        card = _card(
            "Kinbound Echo",
            "Instant",
            "Exile target creature you own, then return it to the battlefield under your control.",
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_you_control_after_then_does_not_name_the_target(self):
        # "each creature you control" belongs to the next clause; the target is an opponent's.
        card = _card(
            "Graftcrown Theft",
            "Sorcery",
            "Exile target creature an opponent controls, then put a +1/+1 counter on each creature you "
            "control, then return it to the battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_under_your_control_later_in_the_sentence_is_not_the_return(self):
        # The target returns under its owner's control; "under your control" is another object's.
        card = _card(
            "Tidewrack Mirage",
            "Instant",
            "Exile target creature an opponent controls, then return it to the battlefield under its owner's "
            "control and put a creature card from your hand onto the battlefield under your control.",
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_you_controlled_is_not_you_control(self):
        card = _card(
            "Oathbreak Reclaim",
            "Instant",
            "Exile target creature an opponent controls that you controlled earlier this turn, then return it "
            "to the battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_blink_after_a_trigger_clause_is_not_a_sac_outlet(self):
        card = _card(
            "Dusklatch Wardrobe",
            "Artifact",
            "At the beginning of your end step, you may exile target creature you control, then return that "
            "card to the battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), (None, 0.0))

    def test_return_under_your_control_of_a_target_list_you_control_is_not_removal_spot(self):
        # Probe P2: the commas of a target list do not end the target; ", then" does.
        for oracle_text in (
            "Exile target artifact, creature, or enchantment you control, then return it to the battlefield "
            "under your control.",
            "Exile target artifact, Thenari, or creature you control, then return it to the battlefield "
            "under your control.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Glasswake Recall", "Instant", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_you_control_before_the_target_does_not_name_the_target(self):
        card = _card(
            "Wizardsworn Seizure",
            "Instant",
            "If you control a Wizard, exile target creature an opponent controls, then return it to the "
            "battlefield under your control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_return_under_your_control_of_an_opponents_target_list_is_removal_spot(self):
        card = _card(
            "Gildthief Snare",
            "Instant",
            "Exile target artifact or creature an opponent controls, then return it to the battlefield under "
            "your control.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_blink_under_your_control_beside_a_destroy_stays_removal_spot(self):
        # The exile of your creature is a blink, not a sac outlet, so the destroy keeps removal-spot.
        card = _card(
            "Twinmark Edict",
            "Sorcery",
            "Exile target creature you control, then return it to the battlefield under your control. "
            "Destroy target artifact.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))


class UpToTargetTests(unittest.TestCase):
    """"Destroy up to N target" and "return up to N target … to its owner's hand" name a target (DEC-1197)."""

    def test_destroy_up_to_one_target_is_removal_spot(self):
        card = _card("Sunder the Gate", "Sorcery", "Destroy up to one target nonland permanent.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_bounce_up_to_one_target_is_removal_spot(self):
        card = _card("Tideshove Adept", "Instant", "Return up to one target creature to its owner's hand.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.8))

    def test_return_up_to_one_card_from_your_graveyard_is_not_removal_spot(self):
        card = _card(
            "Gravebloom Rite", "Sorcery", "Return up to one target creature card from your graveyard to your hand."
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_destroy_up_to_one_target_you_control_is_not_removal_spot(self):
        card = _card("Hollow Offering", "Sorcery", "Destroy up to one target creature you control.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")


class ExileUpToTests(unittest.TestCase):
    """"Exile up to N target" names a target, with a graveyard guard and a next-sentence guard (DEC-1197)."""

    def test_exile_up_to_one_other_target_creature_is_removal_spot(self):
        card = _card("Stillwater Warden", "Creature — Elemental", "When this creature enters, exile up to one other "
                     "target creature.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_exile_from_the_battlefield_and_or_from_graveyards_is_removal_spot(self):
        card = _card(
            "Seraph of Stillness",
            "Creature — Angel",
            "Flying\nWhen this creature enters, you may exile up to three other target creatures from the battlefield "
            "and/or creature cards from graveyards until this creature leaves the battlefield.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.85))

    def test_exile_up_to_n_cards_from_a_graveyard_is_not_removal_spot(self):
        for oracle_text in (
            "Whenever this creature attacks and isn't blocked, you may exile up to two target creature cards from "
            "defending player's graveyard.",
            "Exile up to five target creature cards from graveyards. You gain 1 life for each card exiled this way.",
            "When this creature enters, exile up to one target nonland card of each card type from your graveyard.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Gravegnaw Badger", "Creature — Badger", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_exile_up_to_one_target_that_the_next_sentence_returns_is_not_removal_spot(self):
        for oracle_text in (
            "Whenever this creature becomes tapped, exile up to one target nonland, nontoken permanent. Return that "
            "card to the battlefield under its owner's control at the beginning of the next end step.",
            "Whenever this creature attacks, exile up to one other target nonland permanent. At the beginning of the "
            "next end step, return that card to the battlefield under its owner's control.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Mistveil Herder", "Creature — Kithkin Wizard", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "removal-spot")


class ToughnessCutTests(unittest.TestCase):
    """A cut to a target creature's toughness is removal-spot, also beside a gain to power."""

    def test_gain_to_power_and_cut_to_toughness_is_removal_spot(self):
        card = _card("Rendmaw Surge", "Instant", "Target creature gets +3/-3 until end of turn.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_x_cut_to_toughness_is_removal_spot(self):
        for oracle_text in (
            "Target creature gets +X/-X until end of turn, where X is the number of cards in your hand.",
            "Target creature gets -X/-X until end of turn, where X is the number of cards in your graveyard.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Hollowing Decree", "Instant", oracle_text)
                self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_gain_to_power_without_a_cut_to_toughness_is_not_removal_spot(self):
        card = _card("Brashfire Rally", "Instant", "Target creature gets +2/-0 until end of turn.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_cut_to_power_only_is_not_removal_spot(self):
        # A cut to power stops one attack; it does not answer the creature (DEC-1184 ruling R1).
        card = _card("Dullwit Hex", "Instant", "Target creature gets -3/-0 until end of turn.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_cut_to_power_that_then_destroys_the_creature_is_removal_spot(self):
        card = _card(
            "Crushing Depths",
            "Instant",
            "Target creature gets -3/-0 until end of turn. Then if that creature's power is 0 or less, destroy it.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_cut_to_toughness_of_a_qualified_target_is_removal_spot(self):
        card = _card(
            "Gloomfang Stalker",
            "Creature — Beast Horror",
            "When this creature enters, target creature an opponent controls gets -2/-2 until end of turn.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_cut_to_toughness_of_a_target_you_control_is_not_removal_spot(self):
        card = _card("Reckless Overdrive", "Instant", "Target creature you control gets +2/-1 until end of turn.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_qualifier_with_a_comma_is_another_clause(self):
        # The cut lands only on a creature that it cannot kill; the card is a pump.
        card = _card(
            "Giantsbane Fury",
            "Instant",
            "If target creature has toughness 5 or greater, it gets +4/-4 until end of turn. Otherwise, it gets "
            "+4/-0 until end of turn.",
        )
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_cut_to_the_toughness_of_this_creature_is_not_removal_spot(self):
        card = _card("Glassback Drake", "Creature — Drake", "Flying\n{R}: This creature gets +2/-2 until end of turn.")
        self.assertNotEqual(atr.classify(card)[0], "removal-spot")

    def test_gain_of_ten_or_more_to_power_is_read(self):
        card = _card("Overreach Surge", "Instant", "Target creature gets +10/-10 until end of turn.")
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))

    def test_you_may_have_target_creature_get_is_removal_spot(self):
        card = _card(
            "Rotmire Herald",
            "Creature — Zombie",
            "When this creature dies, you may have target creature get -2/-2 until end of turn.",
        )
        self.assertEqual(atr.classify(card), ("removal-spot", 0.65))


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


class CantripTests(unittest.TestCase):
    """One draw of one card that the card gives once nets 0 cards, so it is not card-draw (DEC-478)."""

    def test_one_shot_draw_of_one_card_is_not_card_draw(self):
        for name, type_line, oracle_text in (
            ("Millwater Glance", "Instant", "Target player mills two cards.\nDraw a card."),
            ("Hearthward Scout", "Creature — Human Scout", "When this creature enters, draw a card."),
            (
                "Duneplod Beast",
                "Creature — Beast",
                "Trample\nCycling {2} ({2}, Discard this card: Draw a card.)",
            ),
            (
                "Clueward Inspector",
                "Creature — Human Detective",
                'When this creature enters, investigate. (Create a Clue token. It\'s an artifact with "{2}, '
                'Sacrifice this token: Draw a card.")',
            ),
            ("Brassleaf Trinket", "Artifact", "{1}, Sacrifice this artifact: Draw a card."),
            (
                # The cost before ":" is in reminder text: cycling of the cards in your hand.
                "Tomeshade Heron",
                "Creature — Bird Wizard",
                "Flying\nEach creature card in your hand has cycling {1}{U}. ({1}{U}, Discard that card: Draw "
                "a card.)",
            ),
            (
                "Dusktide Stall",
                "Instant",
                "Tap target creature.\nAt the beginning of the next end step, draw a card.",
            ),
        ):
            with self.subTest(name=name):
                card = _card(name, type_line, oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_repeatable_draw_or_a_draw_of_two_is_card_draw(self):
        for name, type_line, oracle_text in (
            ("Gravewatch Ledger", "Enchantment", "Whenever a creature you control dies, draw a card."),
            ("Inkwell Lens", "Artifact", "{T}: Draw a card."),
            (
                "Skyrider Courier",
                "Creature — Bird Scout",
                "Flying\nWhenever this creature attacks, choose one —\n• Draw a card.\n• You gain 2 life.",
            ),
            ("Twofold Insight", "Sorcery", "Draw two cards."),
            (
                "Echoing Augury",
                "Sorcery",
                "Draw a card.\nDraw a card at the beginning of the next turn's upkeep.",
            ),
        ):
            with self.subTest(name=name):
                card = _card(name, type_line, oracle_text)
                self.assertEqual(atr.classify(card), ("card-draw", 0.85))


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


class GraveyardCostFaultTests(unittest.TestCase):
    """Fault case of B4 (probe P2): it fails on the head and passes with the fix."""

    def test_draw_behind_exile_this_card_from_your_graveyard_is_not_card_draw(self):
        card = _card(
            "Ashveil Courier",
            "Creature — Spirit Scout",
            "Menace\n{2}{B}, Exile this card from your graveyard: Draw a card.",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class SpentCardCostTests(unittest.TestCase):
    """A cost that sacrifices the card by its name, or exiles it, spends the card: its draw is once (DEC-1197)."""

    def test_draw_behind_sacrifice_of_the_cards_own_name_is_not_card_draw(self):
        for name, oracle_text in (
            ("Cairn of Velloth", "{2}, {T}, Sacrifice Cairn of Velloth: Exile target player's graveyard. Draw a card."),
            ("Brasswing, the Tinker", "Flying\n{2}, Sacrifice Brasswing: Draw a card."),
        ):
            with self.subTest(name=name):
                card = _card(name, "Legendary Artifact", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_draw_behind_exile_this_artifact_is_not_card_draw(self):  # kills "exile this card from your graveyard"
        card = _card("Ossuary Lamp", "Artifact", "{1}, Exile this artifact: Exile all graveyards. Draw a card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_two_draws_behind_sacrifice_of_the_cards_name_are_card_draw(self):
        card = _card(
            "Quillbot",
            "Artifact Creature — Robot",
            "Flying\n{2}, Sacrifice Quillbot: Draw a card, then draw an additional card for each quest counter "
            "on Quillbot.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class SagaChapterTests(unittest.TestCase):
    """A Saga line that names two or more chapters gives its draw once for each chapter (DEC-1197)."""

    def test_draw_on_two_chapters_is_card_draw(self):
        card = _card(
            "The Tidebound Chronicle",
            "Enchantment — Saga",
            "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\n"
            "I, II — Draw a card.\nIII — Create a 2/2 blue Bird creature token with flying.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_draw_on_one_chapter_is_not_card_draw(self):
        card = _card(
            "The Ashen Ballad",
            "Enchantment — Saga",
            "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\n"
            "I — Draw a card.\nII, III — Create a 1/1 black Rat creature token.",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class AdditionalDrawTests(unittest.TestCase):
    """"Draws an additional card" is a draw (DEC-1197)."""

    def test_additional_card_at_each_draw_step_is_card_draw(self):
        for oracle_text in (
            "At the beginning of each player's draw step, that player draws an additional card.",
            "At the beginning of each player's draw step, that player draws two additional cards.",
        ):
            with self.subTest(oracle_text=oracle_text):
                card = _card("Clatterhorn Mine", "Artifact", oracle_text)
                self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class OneShotLootTests(unittest.TestCase):
    """A loot that the card gives once nets 0 cards when it discards all but one card or more (DEC-1197)."""

    def test_one_shot_loot_of_two_for_one_is_not_card_draw(self):
        card = _card("Mirewake Study", "Instant", "Draw two cards, then discard a card.")
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_one_shot_loot_of_three_for_one_is_card_draw(self):
        card = _card("Deepwell Study", "Sorcery", "Draw three cards, then discard a card.")
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_loot_on_two_saga_chapters_is_card_draw(self):
        card = _card(
            "The Sunken Almanac",
            "Enchantment — Saga",
            "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\n"
            "I, II — Draw two cards, then discard a card.\nIII — Scry 2.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class DiscardCostTests(unittest.TestCase):
    """A card discarded to cast the spell counts against its draw (DEC-1197)."""

    def test_discard_one_to_draw_two_is_not_card_draw(self):
        card = _card(
            "Restless Refrain", "Sorcery", "As an additional cost to cast this spell, discard a card.\nDraw two cards."
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_discard_one_to_draw_three_is_card_draw(self):
        card = _card(
            "Reckless Recital", "Sorcery", "As an additional cost to cast this spell, discard a card.\nDraw three cards."
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class DrawSubjectTests(unittest.TestCase):
    """Only a draw by you counts toward card-draw (DEC-1197)."""

    def test_draw_by_another_player_is_not_card_draw(self):
        for name, type_line, oracle_text in (
            ("Glimmerwake Tithe", "Enchantment", "Whenever an opponent draws a card, you gain 1 life."),
            ("Openhand Envoy", "Sorcery", "Each opponent draws a card."),
            (
                "Rotgrowth Bloom",
                "Enchantment",
                "At the beginning of your upkeep, put a growth counter on this enchantment.\nAt the beginning of "
                "each opponent's draw step, that player draws an additional card for each growth counter on this "
                "enchantment.",
            ),
        ):
            with self.subTest(name=name):
                card = _card(name, type_line, oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_your_draw_on_an_opponents_draw_is_card_draw(self):
        card = _card(
            "Thoughtpilfer Rogue",
            "Creature — Human Rogue",
            "Flash\nIf an opponent would draw a card except the first one they draw in each of their draw steps, "
            "instead that player skips that draw and you draw a card.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_you_and_target_opponent_each_draw_is_yours(self):
        card = _card("Shared Counsel", "Sorcery", "You and target opponent each draw two cards.")
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class RepeatableLootTests(unittest.TestCase):
    """A loot or rummage that discards as many cards as it draws adds no card, even when it repeats (DEC-1197)."""

    def test_repeatable_loot_or_rummage_is_not_card_draw(self):
        for name, oracle_text in (
            ("Tidecaller Adept", "{T}: Draw a card, then discard a card."),
            ("Ashfall Gambler", "Whenever this creature attacks, you may discard a card. If you do, draw a card."),
        ):
            with self.subTest(name=name):
                card = _card(name, "Creature — Human Wizard", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_repeatable_draw_behind_a_discard_cost_is_not_card_draw(self):
        for name, oracle_text in (
            ("Cinderhand Scrounger", "{1}, {T}, Discard a card: Draw a card."),
            (
                "Crimson Bloodletter",
                "Whenever this creature deals combat damage to a player, create a Blood token. (It's an artifact "
                'with "{1}, {T}, Discard a card, Sacrifice this artifact: Draw a card.")',
            ),
        ):
            with self.subTest(name=name):
                card = _card(name, "Creature — Vampire Rogue", oracle_text)
                self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_repeatable_loot_that_nets_one_card_is_card_draw(self):
        card = _card("Archive Sifter", "Creature — Human Wizard", "{T}: Draw two cards, then discard a card.")
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_discard_cost_of_another_quoted_ability_does_not_count(self):
        card = _card(
            "Scholar's Mantle",
            "Enchantment — Aura",
            'Enchant creature\nEnchanted creature has "Discard a card: This creature gets +1/+0 until end of turn." '
            'and "{T}: Draw a card."',
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

    def test_rummage_that_may_sacrifice_an_artifact_instead_is_card_draw(self):
        card = _card(
            "Scrapyard Sleuth",
            "Creature — Human Detective",
            "Whenever this creature attacks, you may sacrifice an artifact or discard a card. If you do, draw a card.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))


class DrawAgainTests(unittest.TestCase):
    """A one-shot draw that the card gives again is card-draw (DEC-1198 probe P3, DEC-1197)."""

    def test_one_shot_draw_that_the_card_gives_again_is_card_draw(self):
        for label, type_line, oracle_text in (
            ("storm", "Sorcery", "Storm (When you cast this spell, copy it for each spell cast before it this turn.)\n"
             "Draw a card."),
            ("copy it", "Sorcery", "When you cast this spell, copy it if you control a Wizard.\nDraw a card."),
            ("same mode", "Instant", "Choose two. You may choose the same mode more than once.\n• Draw a card.\n"
             "• You gain 2 life."),
            ("return this card", "Creature — Zombie", "When this creature enters, draw a card.\n{2}{B}{B}: Return this "
             "card from your graveyard to your hand."),
            ("becomes prepared", "Creature — Gorgon Wizard", "Whenever a land you control enters, this creature "
             "becomes prepared.\nYou draw a card and gain 1 life."),
            ("enters or is put into a graveyard", "Artifact", "When this artifact enters or is put into a graveyard "
             "from the battlefield, draw a card."),
            ("flashback", "Sorcery", "Draw a card.\nFlashback {2}{U} (You may cast this card from your graveyard for "
             "its flashback cost. Then exile it.)"),
            ("escape", "Instant", "Draw a card.\nEscape—{2}{U}, Exile five other cards from your graveyard. (You may "
             "cast this card from your graveyard for its escape cost.)"),
            ("investigate twice", "Enchantment", 'When this enchantment enters, investigate twice. (To investigate, '
             'create a Clue token. It\'s an artifact with "{2}, Sacrifice this token: Draw a card.")'),
        ):
            with self.subTest(label=label):
                card = _card("Twicetold Omen", type_line, oracle_text)
                self.assertEqual(atr.classify(card)[0], "card-draw")

    def test_loot_with_flashback_is_not_card_draw(self):
        card = _card(
            "Cinder Rummage",
            "Sorcery",
            "Draw a card, then discard a card.\nFlashback {2}{R} (You may cast this card from your graveyard for its "
            "flashback cost. Then exile it.)",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")

    def test_word_in_reminder_text_does_not_count(self):
        card = _card(
            "Mirefed Grub",
            "Creature — Insect",
            "Dredge 3 (If you would draw a card, you may mill three cards instead. If you do, return this card from "
            "your graveyard to your hand.)",
        )
        self.assertNotEqual(atr.classify(card)[0], "card-draw")


class ProtectionPatternTests(unittest.TestCase):
    """One case for each pattern that `_detect_protection` keeps."""

    def assertProtection(self, type_line: str, oracle_text: str) -> None:
        self.assertEqual(atr.classify(_card("Invented Ward", type_line, oracle_text)), ("protection", 0.8))

    def test_grant_to_permanents_you_control(self):
        self.assertProtection(
            "Instant", "Permanents you control gain hexproof and indestructible until end of turn."
        )

    def test_grant_to_all_of_a_creature_type(self):
        self.assertProtection("Creature — Sliver", "All Slivers have shroud.")

    def test_grant_to_a_target(self):
        self.assertProtection("Instant", "Target creature you control gains indestructible until end of turn.")

    def test_grant_by_equipment(self):
        self.assertProtection("Artifact — Equipment", "Equipped creature has hexproof and haste.\nEquip {1}")

    def test_phasing_out_your_permanents(self):
        self.assertProtection("Instant", "Any number of target nonland permanents you control phase out.")

    def test_regeneration_of_another_creature(self):
        self.assertProtection("Creature — Zombie Cleric", "{1}{B}: Regenerate target Zombie.")

    def test_umbra_armor(self):
        self.assertProtection(
            "Enchantment — Aura",
            "Enchant creature\nEnchanted creature gets +1/+1.\nUmbra armor (If enchanted creature would be "
            "destroyed, instead remove all damage from it and destroy this Aura.)",
        )

    def test_return_when_the_enchanted_creature_dies(self):
        self.assertProtection(
            "Enchantment — Aura",
            "Enchant creature you control\nWhen enchanted creature dies, return that card to the "
            "battlefield under your control.",
        )

    def test_redirect(self):
        self.assertProtection("Instant", "Change the target of target spell or ability with a single target.")

    def test_blink_of_creatures_you_control(self):
        self.assertProtection(
            "Instant",
            "Exile up to two target creatures you control, then return those cards to the battlefield "
            "under their owner's control.",
        )

    def test_damage_prevention_for_your_creatures(self):
        self.assertProtection("Enchantment", "Prevent all damage that would be dealt to creatures you control.")

    def test_enters_trigger_of_a_card_with_flash(self):
        self.assertProtection(
            "Creature — Human Knight",
            "Flash\nWhen this creature enters, target creature you control gains indestructible until end of turn.",
        )


class ProtectionExclusionTests(unittest.TestCase):
    """Forms that are not `protection`: none of them protects your permanents on another turn."""

    def assertNotProtection(self, type_line: str, oracle_text: str) -> None:
        self.assertNotEqual(atr.classify(_card("Invented Ward", type_line, oracle_text))[0], "protection")

    def test_fog(self):
        self.assertNotProtection("Instant", "Prevent all combat damage that would be dealt this turn.")

    def test_player_only_grant(self):
        self.assertNotProtection("Enchantment", "You have hexproof.")

    def test_player_grant_beside_your_creatures(self):
        self.assertNotProtection(
            "Instant", "Creatures you control get +1/+1 until end of turn, and you gain hexproof until end of turn."
        )

    def test_self_only_grant(self):
        self.assertNotProtection(
            "Legendary Creature — Wraith Noble",
            "Discard a card: Invented Ward gains indestructible until end of turn. Tap it.",
        )

    def test_blink_of_a_creature_you_do_not_control(self):
        self.assertNotProtection(
            "Instant",
            "Exile up to one target creature, then return it to the battlefield under its owner's control.",
        )

    def test_grant_during_your_turn(self):
        self.assertNotProtection("Creature — Turtle", "During your turn, creatures you control have hexproof.")

    def test_grant_on_an_attack(self):
        self.assertNotProtection(
            "Creature — Human Soldier",
            "Whenever this creature attacks, attacking creatures you control gain indestructible until end of turn.",
        )

    def test_blink_at_your_end_step(self):
        self.assertNotProtection(
            "Creature — Spirit",
            "At the beginning of your end step, exile up to one other target creature you control, then "
            "return that card to the battlefield under its owner's control.",
        )

    def test_enters_trigger_of_a_card_without_flash(self):
        self.assertNotProtection(
            "Creature — Human Knight",
            "When this creature enters, target creature you control gains indestructible until end of turn.",
        )

    def test_sorcery_grant_until_end_of_turn(self):
        self.assertNotProtection("Sorcery", "Creatures you control gain indestructible until end of turn.")

    def test_aura_that_removes_abilities(self):
        self.assertNotProtection(
            "Enchantment — Aura",
            "Enchant creature\nEnchanted creature is an Insect artifact creature with base power and toughness "
            "0/1 and has indestructible, and it loses all other abilities, card types, and creature types.",
        )

    def test_redirect_that_protects_only_the_player(self):
        self.assertNotProtection("Instant", "Change the target of target spell that targets only a player.")

    def test_aura_that_steals_the_creature(self):
        self.assertNotProtection(
            "Enchantment — Aura",
            "Enchant creature\nYou control enchanted creature.\nWhen enchanted creature dies, return that card "
            "to the battlefield under its owner's control.",
        )

    def test_keyword_of_a_token(self):
        self.assertNotProtection(
            "Creature — Human Wizard",
            'Creatures you control have "{T}: Create a 1/1 white Spirit creature token with ward {1}."',
        )

    def test_grant_that_another_player_loses(self):
        self.assertNotProtection(
            "Artifact",
            "Creatures your opponents control with hexproof can be the targets of spells and abilities you "
            "control as though they didn't have hexproof.",
        )

    def test_role_of_an_earlier_detector_stays(self):
        card = _card(
            "Invented Ward",
            "Instant",
            # Two cards: one card is a cantrip, which is not card-draw (DEC-1191).
            "Target creature you control gains hexproof until end of turn.\nDraw two cards.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))




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

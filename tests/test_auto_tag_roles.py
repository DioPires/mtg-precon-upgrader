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
            "Target creature you control gains hexproof until end of turn.\nDraw a card.",
        )
        self.assertEqual(atr.classify(card), ("card-draw", 0.85))

if __name__ == "__main__":
    unittest.main()

import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


candidate_pool = importlib.import_module("scripts.generate_candidate_pool")


class CandidatePoolScoringTests(unittest.TestCase):
    def _group_slug_archetype(self):
        return candidate_pool.compile_archetype(
            {
                "name": "Group Slug / Punisher",
                "oracle_patterns": [
                    "deals? \\d+ damage",
                    "each opponent loses \\d+ life",
                ],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )

    def _base_context(self, asymmetric_only=False):
        return {
            "archetype_ids": {"group-slug"},
            "archetype_counts": {"Group Slug / Punisher": 0},
            "asymmetric_only": asymmetric_only,
            "creature_count": 30,
            "sac_outlet_count": 4,
        }

    def test_saturated_archetype_reduces_density_breakdown(self):
        archetype = candidate_pool.compile_archetype(
            {
                "name": "Amass / Army Tokens",
                "oracle_patterns": ["\\bamass\\b", "army you control"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )
        card = {
            "name": "Test Amass Card",
            "cmc": 3,
            "type_line": "Sorcery",
            "oracle_text": "Amass Orcs 2. Army you control gains menace until end of turn.",
        }

        score, breakdown, matched = candidate_pool.score_card(
            card,
            [archetype],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context={
                "archetype_ids": {"amass-armies"},
                "archetype_counts": {"Amass / Army Tokens": 16},
                "asymmetric_only": False,
                "creature_count": 30,
                "sac_outlet_count": 4,
            },
        )

        self.assertGreater(score, 0)
        self.assertEqual(matched, ["Amass / Army Tokens"])
        self.assertEqual(breakdown["density_raw"], 40.0)
        self.assertEqual(breakdown["density"], 20.0)
        self.assertEqual(breakdown["saturation_penalty"], 20.0)

    def test_amass_token_entry_mismatch_adds_visible_penalty(self):
        archetype = candidate_pool.compile_archetype(
            {
                "name": "Tokens / Go Wide",
                "oracle_patterns": ["create (?:a |\\d+|x|that many)[^.]*token"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )
        card = {
            "name": "Redoubled Stormsinger",
            "cmc": 3,
            "type_line": "Creature — Orc Wizard",
            "oracle_text": (
                "Whenever this creature attacks, for each creature token you control "
                "that entered this turn, create a tapped and attacking token that's a copy "
                "of that token."
            ),
        }

        _score, breakdown, _matched = candidate_pool.score_card(
            card,
            [archetype],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context={
                "archetype_ids": {"amass-orcs", "amass-armies"},
                "archetype_counts": {"Tokens / Go Wide": 10},
                "asymmetric_only": False,
                "creature_count": 20,
                "sac_outlet_count": 0,
            },
        )

        self.assertEqual(breakdown["anti_synergy_penalty"], 12.0)
        self.assertEqual(
            breakdown["anti_synergy_flags"],
            [{"name": "amass-token-entry-mismatch", "penalty": 12.0}],
        )

    def test_asymmetric_only_penalizes_symmetric_punisher_templates(self):
        card = {
            "name": "Test Ankh",
            "cmc": 2,
            "type_line": "Artifact",
            "oracle_text": (
                "Whenever a land enters the battlefield, Test Ankh deals 2 damage "
                "to that land's controller."
            ),
        }

        score, breakdown, _matched = candidate_pool.score_card(
            card,
            [self._group_slug_archetype()],
            deck_avg_cmc=2,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context=self._base_context(asymmetric_only=True),
        )

        self.assertAlmostEqual(score, 30.3)
        self.assertEqual(breakdown["anti_synergy_multiplier"], 0.55)
        self.assertEqual(
            breakdown["anti_synergy_flags"],
            [
                {
                    "name": "symmetric-effect-in-asymmetric-only",
                    "multiplier": 0.55,
                    "penalty": 24.7,
                }
            ],
        )

    def test_asymmetric_only_leaves_asymmetric_punishers_unaffected(self):
        card = {
            "name": "Test Drain",
            "cmc": 2,
            "type_line": "Enchantment",
            "oracle_text": "At the beginning of your upkeep, each opponent loses 2 life.",
        }

        _score, breakdown, _matched = candidate_pool.score_card(
            card,
            [self._group_slug_archetype()],
            deck_avg_cmc=2,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context=self._base_context(asymmetric_only=True),
        )

        self.assertNotIn("anti_synergy_penalty", breakdown)
        self.assertNotIn("anti_synergy_flags", breakdown)

    def test_symmetric_punisher_is_unaffected_without_asymmetric_only(self):
        card = {
            "name": "Test Vortex",
            "cmc": 3,
            "type_line": "Enchantment",
            "oracle_text": (
                "At the beginning of each player's upkeep, Test Vortex deals 2 damage "
                "to that player."
            ),
        }

        flagged_score, _flagged_breakdown, _matched = candidate_pool.score_card(
            card,
            [self._group_slug_archetype()],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context=self._base_context(asymmetric_only=True),
        )
        unflagged_score, unflagged_breakdown, _matched = candidate_pool.score_card(
            card,
            [self._group_slug_archetype()],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context=self._base_context(asymmetric_only=False),
        )

        self.assertLess(flagged_score, unflagged_score)
        self.assertNotIn("anti_synergy_penalty", unflagged_breakdown)
        self.assertNotIn("anti_synergy_flags", unflagged_breakdown)

    def test_asymmetric_only_penalizes_global_lifegain_locks(self):
        card = {
            "name": "Test Ferocidon",
            "cmc": 3,
            "type_line": "Creature — Dinosaur",
            "oracle_text": (
                "Players can't gain life. Whenever another creature enters, "
                "this creature deals 1 damage to that creature's controller."
            ),
        }

        _score, breakdown, _matched = candidate_pool.score_card(
            card,
            [self._group_slug_archetype()],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context=self._base_context(asymmetric_only=True),
        )

        self.assertEqual(
            breakdown["anti_synergy_flags"][0]["name"],
            "symmetric-effect-in-asymmetric-only",
        )


class OrderedArchetypeWeightingTests(unittest.TestCase):
    def _archetypes(self):
        infect = candidate_pool.compile_archetype(
            {
                "name": "Infect / Poison",
                "oracle_patterns": ["\\binfect\\b", "poison counter"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )
        plus_one = candidate_pool.compile_archetype(
            {
                "name": "Plus-One Counters",
                "oracle_patterns": ["\\+1/\\+1 counter"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )
        return infect, plus_one

    def _context(self, ids):
        return {
            "archetype_ids": set(ids),
            "archetype_counts": {"Infect / Poison": 0, "Plus-One Counters": 0},
            "asymmetric_only": False,
            "creature_count": 30,
            "sac_outlet_count": 0,
        }

    def test_plus_one_counter_card_scores_lower_when_infect_is_position_one(self):
        infect, plus_one = self._archetypes()
        card = {
            "name": "Generic +1/+1 Doubler",
            "cmc": 3,
            "type_line": "Enchantment",
            "oracle_text": "If one or more +1/+1 counters would be put on a creature, twice that many +1/+1 counters are put on it instead.",
        }

        # Deck A: [infect-poison, plus-one-counters] — +1/+1 archetype is position 2 (0.5x)
        weights_a = candidate_pool.build_position_weights([infect, plus_one])
        score_a, bd_a, _ = candidate_pool.score_card(
            card, [infect, plus_one], deck_avg_cmc=3,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context({"infect-poison", "plus-one-counters"}),
            position_weights=weights_a,
        )

        # Deck B: [plus-one-counters, infect-poison] — +1/+1 archetype is position 1 (1.0x)
        weights_b = candidate_pool.build_position_weights([plus_one, infect])
        score_b, bd_b, _ = candidate_pool.score_card(
            card, [plus_one, infect], deck_avg_cmc=3,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context({"plus-one-counters", "infect-poison"}),
            position_weights=weights_b,
        )

        self.assertLess(score_a, score_b)
        self.assertEqual(bd_a["archetype_position_weights"], {"Plus-One Counters": 0.5})
        self.assertNotIn("archetype_position_weights", bd_b)

    def test_position_weights_helper_decays_with_index(self):
        self.assertEqual(candidate_pool.archetype_position_weight(0), 1.0)
        self.assertEqual(candidate_pool.archetype_position_weight(1), 0.5)
        self.assertEqual(candidate_pool.archetype_position_weight(2), 0.25)
        self.assertEqual(candidate_pool.archetype_position_weight(7), 0.25)


class QualityAwareRoleSaturationTests(unittest.TestCase):
    def _archetype(self):
        return candidate_pool.compile_archetype(
            {
                "name": "Ramp / Big Mana",
                "oracle_patterns": ["add \\{[cwubrg]\\}", "search your library for[^.]*land"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )

    def _context(self):
        return {
            "archetype_ids": {"ramp-big-mana"},
            "archetype_counts": {"Ramp / Big Mana": 0},
            "asymmetric_only": False,
            "creature_count": 30,
            "sac_outlet_count": 0,
        }

    def _ramp_card(self):
        return {
            "name": "Mediocre Rock",
            "cmc": 4,
            "type_line": "Artifact",
            "oracle_text": "{T}: Add {C}.",
            "color_identity": [],
        }

    def test_strong_roster_demotes_low_score_same_role_candidate(self):
        archetype = self._archetype()
        card = self._ramp_card()

        weights = candidate_pool.build_position_weights([archetype])
        # Score the card once to learn its un-demoted score.
        baseline, _bd, _m = candidate_pool.score_card(
            card, [archetype], deck_avg_cmc=4,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context(),
            position_weights=weights,
            role_pool=None,
        )
        self.assertGreater(baseline, 0)

        # Strong roster: many ramp cards already, median above the candidate's score.
        strong_pool = {"ramp": {"count": 12, "median": baseline + 20.0}}
        demoted_score, demoted_bd, _ = candidate_pool.score_card(
            card, [archetype], deck_avg_cmc=4,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context(),
            position_weights=weights,
            role_pool=strong_pool,
        )
        self.assertLess(demoted_score, baseline)
        self.assertIn("redundancy_below_roster_median", demoted_bd)
        self.assertEqual(demoted_bd["redundancy_below_roster_median"]["role"], "ramp")
        self.assertEqual(
            demoted_bd["redundancy_below_roster_median"]["multiplier"],
            candidate_pool.ROLE_REDUNDANCY_FLOOR,
        )

    def test_weak_roster_does_not_demote(self):
        archetype = self._archetype()
        card = self._ramp_card()
        weights = candidate_pool.build_position_weights([archetype])

        weak_pool = {"ramp": {"count": 3, "median": 80.0}}
        score, breakdown, _ = candidate_pool.score_card(
            card, [archetype], deck_avg_cmc=4,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context(),
            position_weights=weights,
            role_pool=weak_pool,
        )
        self.assertNotIn("redundancy_below_roster_median", breakdown)

    def test_above_median_candidate_not_demoted_in_saturated_bucket(self):
        archetype = self._archetype()
        card = self._ramp_card()
        weights = candidate_pool.build_position_weights([archetype])

        # Saturated count, but median below candidate score → no demote.
        rich_pool = {"ramp": {"count": 12, "median": 1.0}}
        score, breakdown, _ = candidate_pool.score_card(
            card, [archetype], deck_avg_cmc=4,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context(),
            position_weights=weights,
            role_pool=rich_pool,
        )
        self.assertNotIn("redundancy_below_roster_median", breakdown)

    def test_knobs_are_off_by_default_for_unflagged_decks(self):
        """No position_weights and no role_pool ⇒ identical behavior to pre-P10."""
        archetype = self._archetype()
        card = self._ramp_card()

        score_default, breakdown_default, _ = candidate_pool.score_card(
            card, [archetype], deck_avg_cmc=4,
            decklist_names=set(), owned=set(), game_changers=set(), bracket=4,
            context=self._context(),
        )
        self.assertNotIn("archetype_position_weights", breakdown_default)
        self.assertNotIn("redundancy_below_roster_median", breakdown_default)
        self.assertGreater(score_default, 0)


class EdhrecInclusionBoostTests(unittest.TestCase):
    """DEC-410: manually recorded EDHREC inclusion rates boost candidate scores."""

    def _archetype(self):
        return candidate_pool.compile_archetype(
            {
                "name": "Voltron",
                "oracle_patterns": ["equip\\b", "attached creature"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )

    def _context(self):
        return {
            "archetype_ids": {"voltron"},
            "archetype_counts": {"Voltron": 0},
            "asymmetric_only": False,
            "creature_count": 30,
            "sac_outlet_count": 4,
        }

    def _equipment_card(self, name="Test Blade"):
        return {
            "name": name,
            "cmc": 3,
            "type_line": "Artifact — Equipment",
            "oracle_text": "Equipped creature gets +3/+1. Equip {2}",
        }

    def _score(self, card, owned=frozenset(), edhrec_rates=None):
        return candidate_pool.score_card(
            card,
            [self._archetype()],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(owned),
            game_changers=set(),
            bracket=4,
            context=self._context(),
            edhrec_rates=edhrec_rates,
        )

    def test_no_rates_leaves_score_and_breakdown_unchanged(self):
        card = self._equipment_card()
        base_score, base_bd, _ = self._score(card)
        none_score, none_bd, _ = self._score(card, edhrec_rates={})
        self.assertEqual(base_score, none_score)
        self.assertNotIn("edhrec", base_bd)
        self.assertNotIn("edhrec", none_bd)

    def test_rate_adds_scaled_boost_and_breakdown(self):
        card = self._equipment_card()
        base_score, _bd, _ = self._score(card)
        boosted_score, boosted_bd, _ = self._score(card, edhrec_rates={"Test Blade": 43})
        self.assertAlmostEqual(boosted_score - base_score, 17.2, places=1)
        self.assertEqual(boosted_bd["edhrec"], 17.2)
        self.assertEqual(boosted_bd["edhrec_rate"], 43)

    def test_boost_caps_at_max_above_saturation_rate(self):
        card = self._equipment_card()
        base_score, _bd, _ = self._score(card)
        capped_score, capped_bd, _ = self._score(card, edhrec_rates={"Test Blade": 85})
        self.assertAlmostEqual(capped_score - base_score, candidate_pool.EDHREC_MAX, places=1)
        self.assertEqual(capped_bd["edhrec"], candidate_pool.EDHREC_MAX)

    def test_forty_percent_unowned_outranks_marginal_owned_filler(self):
        popular_unowned = self._equipment_card("Popular Blade")
        owned_filler = self._equipment_card("Owned Filler")
        unowned_score, _b1, _m1 = self._score(
            popular_unowned, edhrec_rates={"Popular Blade": 40}
        )
        owned_score, _b2, _m2 = self._score(
            owned_filler, owned={"Owned Filler"}, edhrec_rates={"Popular Blade": 40}
        )
        self.assertGreater(unowned_score, owned_score)

    def test_dfc_rate_lookup_falls_back_to_front_face(self):
        rate = candidate_pool.edhrec_rate_for(
            "Grave Researcher // Reanimate", {"Grave Researcher": 31}
        )
        self.assertEqual(rate, 31)
        self.assertIsNone(candidate_pool.edhrec_rate_for("Sol Ring", {"Other": 10}))
        self.assertIsNone(candidate_pool.edhrec_rate_for("Sol Ring", None))


class MultiplayerScalingBoostTests(unittest.TestCase):
    """DEC-477: flat tiebreaker boost for opponent-scaled trigger templates."""

    def _archetype(self):
        return candidate_pool.compile_archetype(
            {
                "name": "Group Slug",
                "oracle_patterns": ["loses? \\d+ life", "gain \\d+ life"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )

    def _card(self, name, oracle_text):
        return {
            "name": name,
            "cmc": 2,
            "type_line": "Enchantment",
            "oracle_text": oracle_text,
        }

    def _score(self, card):
        return candidate_pool.score_card(
            card,
            [self._archetype()],
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
        )

    def test_opponent_scaled_trigger_gets_flat_boost(self):
        plain = self._card("Plain Drain", "When this enchantment enters, you gain 2 life.")
        scaled = self._card(
            "Consuls Class",
            "Whenever a creature an opponent controls enters, you gain 1 life.",
        )
        plain_score, plain_bd, _ = self._score(plain)
        scaled_score, scaled_bd, _ = self._score(scaled)
        self.assertEqual(
            scaled_bd["multiplayer_scaled"], candidate_pool.MULTIPLAYER_SCALED_BOOST
        )
        self.assertNotIn("multiplayer_scaled", plain_bd)
        self.assertAlmostEqual(
            scaled_score - plain_score, candidate_pool.MULTIPLAYER_SCALED_BOOST, places=1
        )

    def test_templates_match_and_symmetric_variants_do_not(self):
        rx = candidate_pool.MULTIPLAYER_SCALED_TRIGGER
        for text in (
            "each opponent loses 2 life.",
            "at the beginning of each opponent's upkeep, that player mills a card.",
            "whenever an opponent casts a noncreature spell, draw a card.",
            "whenever a creature enters under an opponent's control, you gain 1 life.",
            "whenever a creature you don't control dies, draw a card.",
            "whenever a creature dies during an opponent's turn, draw a card.",
        ):
            self.assertTrue(rx.search(text), text)
        for text in (
            "at the beginning of each player's upkeep, that player loses 1 life.",
            "each opponent and you each sacrifice a creature.",
            "whenever this creature attacks, gain control of target creature an opponent controls.",
            "destroy target creature an opponent controls.",
        ):
            self.assertFalse(rx.search(text), text)

    def test_boost_stays_a_tiebreaker(self):
        self.assertLess(candidate_pool.MULTIPLAYER_SCALED_BOOST, 15.0)  # owned
        self.assertLess(candidate_pool.MULTIPLAYER_SCALED_BOOST, candidate_pool.EDHREC_MAX)
        self.assertLessEqual(candidate_pool.MULTIPLAYER_SCALED_BOOST, 40.0 / 8.0)  # density/8


class DecklistExclusionNormalizationTests(unittest.TestCase):
    """DEC-386: mirror indexes DFCs as 'Front // Back'; decklists use front-face names."""

    def _archetype(self):
        return candidate_pool.compile_archetype(
            {
                "name": "Reanimator",
                "oracle_patterns": ["return [^.]*creature card[^.]*graveyard[^.]*battlefield"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )

    def _dfc_card(self):
        return {
            "name": "Grave Researcher // Reanimate",
            "cmc": 3,
            "type_line": "Creature — Human Wizard // Sorcery",
            "card_faces": [
                {
                    "name": "Grave Researcher",
                    "type_line": "Creature — Human Wizard",
                    "oracle_text": "When this creature enters, mill three cards.",
                },
                {
                    "name": "Reanimate",
                    "type_line": "Sorcery",
                    "oracle_text": (
                        "Return target creature card from your graveyard to the battlefield."
                    ),
                },
            ],
        }

    def _score(self, decklist_names):
        return candidate_pool.score_card(
            self._dfc_card(),
            [self._archetype()],
            deck_avg_cmc=3,
            decklist_names=decklist_names,
            owned=set(),
            game_changers=set(),
            bracket=4,
            context={
                "archetype_ids": {"reanimator"},
                "archetype_counts": {"Reanimator": 0},
                "asymmetric_only": False,
                "creature_count": 30,
                "sac_outlet_count": 4,
            },
        )

    def test_front_face_strips_back_face(self):
        self.assertEqual(
            candidate_pool.front_face("Grave Researcher // Reanimate"), "Grave Researcher"
        )
        self.assertEqual(candidate_pool.front_face("Sol Ring"), "Sol Ring")

    def test_dfc_scores_normally_when_not_in_decklist(self):
        score, breakdown, _ = self._score(decklist_names=set())
        self.assertGreater(score, 5.0)
        self.assertFalse(breakdown["decklist_demoted"])

    def test_dfc_demoted_when_front_face_name_in_decklist(self):
        score, breakdown, _ = self._score(decklist_names={"Grave Researcher"})
        self.assertLessEqual(score, 5.0)
        self.assertTrue(breakdown["decklist_demoted"])


class PerArchetypeTypeConstraintTests(unittest.TestCase):
    """DEC-990: type_constraints gate their own archetype, not the whole deck."""

    def _archetypes(self):
        flicker = candidate_pool.compile_archetype(
            {
                "name": "ETB Value / Flicker",
                "oracle_patterns": ["exile [^.]*then return.*?to the battlefield", "when [^.]*enters"],
                "type_constraints": [],
                "staples": [],
                "anti_patterns": [],
            }
        )
        changeling = candidate_pool.compile_archetype(
            {
                "name": "Changeling Omnitype Tribal",
                "oracle_patterns": ["changeling", "of the chosen type"],
                "type_constraints": ["Creature — Shapeshifter"],
                "staples": [],
                "anti_patterns": [],
            }
        )
        return [flicker, changeling]

    def _score(self, card, archetypes):
        return candidate_pool.score_card(
            card,
            archetypes,
            deck_avg_cmc=3,
            decklist_names=set(),
            owned=set(),
            game_changers=set(),
            bracket=4,
            context={
                "archetype_ids": {"etb-flicker", "changeling-omnitype-tribal"},
                "archetype_counts": {},
                "asymmetric_only": False,
                "creature_count": 30,
                "sac_outlet_count": 0,
            },
        )

    def test_off_type_card_still_hits_unconstrained_archetype(self):
        card = {
            "name": "Flickering Hound",
            "cmc": 4,
            "type_line": "Creature — Dog",
            "oracle_text": (
                "Whenever you cast a creature spell, exile up to one other target creature "
                "you control, then return that card to the battlefield under its owner's control."
            ),
        }
        score, breakdown, matched = self._score(card, self._archetypes())
        self.assertGreater(score, 0)
        self.assertNotIn("disqualified", breakdown)
        self.assertEqual(matched, ["ETB Value / Flicker"])

    def test_on_type_card_keeps_constrained_archetype_hit(self):
        card = {
            "name": "Test Changeling Blinker",
            "cmc": 3,
            "type_line": "Creature — Shapeshifter",
            "oracle_text": (
                "Changeling\nWhen this creature enters, exile another target creature you control, "
                "then return it to the battlefield."
            ),
        }
        score, _breakdown, matched = self._score(card, self._archetypes())
        self.assertGreater(score, 0)
        self.assertCountEqual(matched, ["ETB Value / Flicker", "Changeling Omnitype Tribal"])

    def test_off_type_card_gets_no_constrained_archetype_hit(self):
        card = {
            "name": "Test Chosen-Type Lord",
            "cmc": 3,
            "type_line": "Creature — Human",
            "oracle_text": "Creatures you control of the chosen type get +1/+1.",
        }
        score, breakdown, matched = self._score(card, self._archetypes())
        self.assertEqual(score, 0.0)
        self.assertEqual(breakdown, {"disqualified": "no archetype match"})
        self.assertEqual(matched, [])


class CandidatePinTests(unittest.TestCase):
    """DEC-992: deck.json candidate_pins seat cards below the cut, flagged pinned."""

    DECK_ID = "dec992-test-deck"

    def _playbook(self):
        return {
            "archetypes": {
                "etb-flicker": {
                    "name": "ETB Value / Flicker",
                    "oracle_patterns": ["exile [^.]*then return", "when [^.]*enters"],
                    "type_constraints": [],
                    "staples": [],
                    "anti_patterns": [],
                }
            }
        }

    def _card(self, name, oracle_text, cmc=3, color_identity=("W",)):
        return {
            "name": name,
            "cmc": cmc,
            "mana_cost": "",
            "type_line": "Creature — Dog",
            "oracle_text": oracle_text,
            "color_identity": list(color_identity),
        }

    def _cards(self):
        blink = (
            "When this creature enters, exile another target creature you control, "
            "then return it to the battlefield."
        )
        return [
            self._card("Test Commander", "Vigilance"),
            self._card("Strong Blinker A", blink),
            self._card("Strong Blinker B", blink),
            self._card("Weak Blinker", "When this creature enters, you gain 1 life.", cmc=9),
            self._card("Off-Colour Blinker", blink, color_identity=("U",)),
            self._card("Vanilla Dog", "Vigilance"),
        ]

    def _generate(self, pins=None, decklist=(), limit=2):
        cards = self._cards()
        deck = {
            "commander": "Test Commander",
            "archetypes": ["etb-flicker"],
            "decklist": [{"name": n, "quantity": 1} for n in decklist],
        }
        if pins is not None:
            deck["candidate_pins"] = [{"name": n, "reason": "Test pin (DEC-992)."} for n in pins]
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = candidate_pool.generate_for_deck(
                self.DECK_ID,
                deck,
                cards,
                {c["name"]: c for c in cards},
                self._playbook(),
                owned=set(),
                game_changers=set(),
                mirror_updated_at="test",
                limit=limit,
            )
        return out, stderr.getvalue()

    def _names(self, out):
        return [c["name"] for c in out["candidates"]]

    def test_pinned_card_below_cut_is_seated_with_flag(self):
        out, _stderr = self._generate(pins=["Weak Blinker"])
        self.assertEqual(self._names(out), ["Strong Blinker A", "Strong Blinker B", "Weak Blinker"])
        self.assertEqual(out["candidate_count"], 3)
        weak = out["candidates"][2]
        self.assertIs(weak["pinned"], True)
        self.assertGreater(weak["score"], 0)
        self.assertLess(weak["score"], out["candidates"][1]["score"])
        self.assertNotIn("pinned", out["candidates"][0])
        self.assertNotIn("pinned", out["candidates"][1])

    def test_pinned_card_keeps_score_order_position(self):
        out, _stderr = self._generate(pins=["Weak Blinker"], limit=1)
        self.assertEqual(self._names(out), ["Strong Blinker A", "Weak Blinker"])

    def test_pinned_card_inside_top_n_carries_flag(self):
        out, _stderr = self._generate(pins=["Strong Blinker B"])
        self.assertEqual(self._names(out), ["Strong Blinker A", "Strong Blinker B"])
        self.assertEqual(out["candidate_count"], 2)
        self.assertNotIn("pinned", out["candidates"][0])
        self.assertIs(out["candidates"][1]["pinned"], True)

    def test_unknown_pin_is_skipped_with_warning(self):
        out, stderr = self._generate(pins=["No Such Card"])
        self.assertEqual(self._names(out), ["Strong Blinker A", "Strong Blinker B"])
        self.assertIn("'No Such Card' skipped: not in the Scryfall mirror", stderr)
        self.assertFalse(any("pinned" in c for c in out["candidates"]))

    def test_ineligible_pins_are_skipped_with_warning(self):
        cases = {
            "Off-Colour Blinker": "outside the colour identity W",
            "Vanilla Dog": "scores 0 for this deck",
            "Weak Blinker": "already in the decklist",
            "Test Commander": "is the commander",
        }
        for name, reason in cases.items():
            with self.subTest(pin=name):
                out, stderr = self._generate(pins=[name], decklist=["Weak Blinker"], limit=1)
                self.assertIn(f"{name!r} skipped: {reason}", stderr)
                self.assertEqual(self._names(out), ["Strong Blinker A"])

    def test_deck_without_pins_has_no_pinned_key(self):
        out, stderr = self._generate()
        self.assertEqual(self._names(out), ["Strong Blinker A", "Strong Blinker B"])
        self.assertEqual(out["candidate_count"], 2)
        self.assertFalse(any("pinned" in c for c in out["candidates"]))
        self.assertNotIn("candidate-pin", stderr)


class GapSeatTests(unittest.TestCase):
    """DEC-1078: a gap role with fewer than 5 pool cards gets cards of that role
    seated after the top N, flagged `seeded_for_gap`."""

    DECK_ID = "dec1078-test-deck"
    ROLE = "removal-spot"
    BLINK = (
        "When this creature enters, exile another target creature you control, "
        "then return it to the battlefield."
    )

    def _playbook(self):
        return CandidatePinTests._playbook(self)

    def _card(self, name, oracle_text, cmc=3, type_line="Creature — Dog"):
        return {
            "name": name,
            "cmc": cmc,
            "mana_cost": "",
            "type_line": type_line,
            "oracle_text": oracle_text,
            "color_identity": ["W"],
        }

    def _removal(self, name, cmc):
        """A removal-spot card that matches the archetype: scores 35 + cmc fit."""
        return self._card(name, "When this creature enters, exile target creature an opponent controls.", cmc=cmc)

    def _off_archetype(self, name, cmc=1):
        """A removal-spot card that matches no archetype: scores 0 behind the gate."""
        return self._card(name, "Exile target creature.", cmc=cmc, type_line="Instant")

    def _cards(self, head=3, head_removal=0, below_removal=7, off_archetype=()):
        cards = [self._card("Test Commander", "Vigilance")]
        cards += [self._card(f"Blinker {i}", self.BLINK) for i in range(head)]
        cards += [
            self._card(f"Head Removal {i}", self.BLINK + " Exile target creature an opponent controls.")
            for i in range(head_removal)
        ]
        # cmc 4..10: scores fall in index order, all below the blinkers' 75.
        cards += [self._removal(f"Removal {i}", 4 + i) for i in range(below_removal)]
        cards.append(self._card("Weak Blinker", "When this creature enters, you gain 1 life.", cmc=9))
        cards += [self._off_archetype(n) for n in off_archetype]
        return cards

    def _generate(self, cards, limit, gaps=(ROLE,), rates=None, decklist=()):
        deck = {
            "commander": "Test Commander",
            "archetypes": ["etb-flicker"],
            "decklist": [{"name": n, "quantity": 1} for n in decklist],
        }
        stderr = io.StringIO()
        with (
            mock.patch.object(candidate_pool, "load_gap_roles", return_value=list(gaps)),
            mock.patch.object(candidate_pool, "load_edhrec_rates", return_value=(dict(rates or {}), None)),
            contextlib.redirect_stderr(stderr),
        ):
            out = candidate_pool.generate_for_deck(
                self.DECK_ID, deck, cards, {c["name"]: c for c in cards}, self._playbook(),
                owned=set(), game_changers=set(), mirror_updated_at="test", limit=limit,
            )
        return out, stderr.getvalue()

    def _names(self, out):
        return [c["name"] for c in out["candidates"]]

    def _seats(self, out):
        return [c["name"] for c in out["candidates"] if "seeded_for_gap" in c]

    def _role_count(self, out, role=ROLE):
        return sum(1 for c in out["candidates"] if c["deck_role"] == role)

    def test_floor_is_reached_from_below_the_cut(self):
        out, stderr = self._generate(self._cards(), limit=3)
        self.assertEqual(self._seats(out), [f"Removal {i}" for i in range(5)])
        self.assertEqual(self._role_count(out), 5)
        self.assertEqual(out["candidate_count"], 8)
        self.assertNotIn("Removal 5", self._names(out))
        scores = [c["score"] for c in out["candidates"][3:]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertIn("gap-seat: removal-spot 0 -> 5 (5 below the cut, 0 from the EDHREC page)", stderr)

    def test_first_limit_cards_are_equal_with_and_without_seeding(self):
        cards = self._cards(below_removal=2, off_archetype=["Listed Removal"])
        rates = {"Listed Removal": 40.0}
        seeded, _ = self._generate(cards, limit=4, rates=rates)
        # A floor of 0 seats nothing; the gap list stays, so `mitigates_gap` matches.
        with mock.patch.object(candidate_pool, "GAP_SEAT_FLOOR", 0):
            plain, _ = self._generate(cards, limit=4, rates=rates)
        self.assertEqual(seeded["candidates"][:4], plain["candidates"][:4])
        self.assertEqual(self._names(plain), ["Blinker 0", "Blinker 1", "Blinker 2", "Removal 0"])
        # Step 1 seats Removal 1 (50.0), step 2 seats Listed Removal (46.0).
        self.assertEqual(self._names(seeded)[4:], ["Removal 1", "Listed Removal"])

    def test_first_limit_cards_stay_when_a_step_2_seat_outscores_the_cut(self):
        # The cut is Weak Blinker (40.0); Listed Removal scores 46.0 without the density term.
        cards = self._cards(below_removal=0, off_archetype=["Listed Removal"])
        out, _ = self._generate(cards, limit=4, rates={"Listed Removal": 40.0})
        self.assertEqual(
            self._names(out), ["Blinker 0", "Blinker 1", "Blinker 2", "Weak Blinker", "Listed Removal"],
        )
        self.assertEqual(out["candidates"][3]["score"], 40.0)
        self.assertEqual(out["candidates"][4]["score"], 46.0)

    def test_pair_with_five_or_more_gets_no_seat(self):
        cards = self._cards(head=0, head_removal=5, below_removal=3)
        out, stderr = self._generate(cards, limit=5)
        self.assertEqual(self._names(out), [f"Head Removal {i}" for i in range(5)])
        self.assertEqual(self._seats(out), [])
        self.assertNotIn("gap-seat", stderr)

    def test_pair_with_four_gets_one_seat(self):
        cards = self._cards(head=0, head_removal=4, below_removal=3)
        out, _ = self._generate(cards, limit=4)
        self.assertEqual(self._seats(out), ["Removal 0"])
        self.assertEqual(self._role_count(out), 5)

    def test_pair_with_too_few_cards_gets_what_there_is(self):
        cards = self._cards(below_removal=2, off_archetype=["Listed Removal", "Unlisted Removal"])
        out, stderr = self._generate(cards, limit=3, rates={"Listed Removal": 10.0})
        self.assertEqual(self._seats(out), ["Removal 0", "Removal 1", "Listed Removal"])
        self.assertEqual(self._role_count(out), 3)
        self.assertIn("gap-seat: removal-spot 0 -> 3 (2 below the cut, 1 from the EDHREC page)", stderr)

    def test_step_2_runs_only_when_step_1_leaves_the_pair_under_the_floor(self):
        cards = self._cards(below_removal=5, off_archetype=["Listed Removal"])
        out, _ = self._generate(cards, limit=3, rates={"Listed Removal": 40.0})
        self.assertEqual(self._seats(out), [f"Removal {i}" for i in range(5)])
        self.assertNotIn("Listed Removal", self._names(out))

        cards = self._cards(below_removal=4, off_archetype=["Listed Removal"])
        out, _ = self._generate(cards, limit=3, rates={"Listed Removal": 40.0})
        self.assertIn("Listed Removal", self._seats(out))
        self.assertEqual(self._role_count(out), 5)

    def test_step_2_card_must_be_on_the_edhrec_page(self):
        cards = self._cards(below_removal=0, off_archetype=["Unlisted Removal", "Listed Removal"])
        out, _ = self._generate(cards, limit=3, rates={"Listed Removal": 10.0})
        self.assertEqual(self._seats(out), ["Listed Removal"])
        listed = out["candidates"][-1]
        self.assertEqual(listed["edhrec_rate"], 10.0)
        self.assertEqual(listed["matched_archetypes"], [])
        self.assertEqual(listed["score_breakdown"]["density"], 0.0)

    def test_step_2_seats_by_edhrec_rate_then_name(self):
        names = ["Rate Low", "Rate High B", "Rate High A", "Rate Mid", "Rate Lower", "Rate Lowest"]
        rates = {"Rate Low": 5.0, "Rate High B": 30.0, "Rate High A": 30.0, "Rate Mid": 20.0,
                 "Rate Lower": 4.0, "Rate Lowest": 3.0}
        cards = self._cards(below_removal=0, off_archetype=names)
        out, _ = self._generate(cards, limit=3, rates=rates)
        self.assertEqual(
            sorted(self._seats(out)),
            sorted(["Rate High A", "Rate High B", "Rate Mid", "Rate Low", "Rate Lower"]),
        )

    def test_step_2_takes_the_highest_rate_before_the_highest_score(self):
        cards = self._cards(below_removal=4)
        cards.append(self._off_archetype("High Rate", cmc=9))  # cmc fit 5 + 15 + EDHREC 12 = 32.0
        cards.append(self._off_archetype("High Score", cmc=3))  # cmc fit 20 + 15 + EDHREC 8 = 43.0
        out, _ = self._generate(cards, limit=3, rates={"High Rate": 30.0, "High Score": 20.0})
        self.assertEqual(self._seats(out), [f"Removal {i}" for i in range(4)] + ["High Rate"])

    def test_step_2_breaks_a_rate_tie_by_name(self):
        cards = self._cards(below_removal=4, off_archetype=["Tie B", "Tie A"])
        out, _ = self._generate(cards, limit=3, rates={"Tie A": 10.0, "Tie B": 10.0})
        self.assertEqual(self._seats(out)[4:], ["Tie A"])
        self.assertNotIn("Tie B", self._names(out))

    def test_card_in_the_decklist_is_not_seated(self):
        cards = self._cards(below_removal=2, off_archetype=["Listed Removal"])
        out, _ = self._generate(
            cards, limit=3, rates={"Listed Removal": 10.0}, decklist=["Removal 0", "Listed Removal"],
        )
        self.assertEqual(self._seats(out), ["Removal 1"])

    def test_flag_names_the_role(self):
        cards = self._cards(below_removal=1, off_archetype=["Listed Removal"])
        out, _ = self._generate(cards, limit=3, rates={"Listed Removal": 10.0})
        seated = [c for c in out["candidates"] if "seeded_for_gap" in c]
        self.assertEqual([c["name"] for c in seated], ["Removal 0", "Listed Removal"])
        for entry in seated:
            self.assertEqual(entry["seeded_for_gap"], self.ROLE)
            self.assertEqual(entry["deck_role"], self.ROLE)
            self.assertEqual(entry["mitigates_gap"], self.ROLE)
        self.assertFalse(any("seeded_for_gap" in c for c in out["candidates"][:3]))

    def test_pinned_card_counts_and_is_not_seeded(self):
        cards = self._cards(below_removal=6)
        deck_pins = ["Removal 3"]
        stderr = io.StringIO()
        deck = {
            "commander": "Test Commander", "archetypes": ["etb-flicker"], "decklist": [],
            "candidate_pins": [{"name": n, "reason": "Test pin."} for n in deck_pins],
        }
        with (
            mock.patch.object(candidate_pool, "load_gap_roles", return_value=[self.ROLE]),
            contextlib.redirect_stderr(stderr),
        ):
            out = candidate_pool.generate_for_deck(
                self.DECK_ID, deck, cards, {c["name"]: c for c in cards}, self._playbook(),
                owned=set(), game_changers=set(), mirror_updated_at="test", limit=3,
            )
        self.assertEqual(self._names(out)[3:], [f"Removal {i}" for i in range(5)])
        self.assertEqual(self._seats(out), ["Removal 0", "Removal 1", "Removal 2", "Removal 4"])
        self.assertIs(out["candidates"][6]["pinned"], True)
        self.assertNotIn("seeded_for_gap", out["candidates"][6])

    def test_step_2_skips_a_listed_card_that_scores_0(self):
        """Kills A5 (step 2 appends every listed card, with no `score > 0` check).

        A Game Changer at bracket 4 gets 0 of 15 on the bracket term; cmc 11 is
        8 from the deck's 3.0, so its cmc fit is 0; an EDHREC rate of 0.0 lists it
        and adds 0. It scores 0 without the gate, so it is no seat.
        """
        cards = self._cards(below_removal=4)
        cards.append(self._off_archetype("Zero Removal", cmc=11))
        deck = {"commander": "Test Commander", "archetypes": ["etb-flicker"], "decklist": []}
        with (
            mock.patch.object(candidate_pool, "load_gap_roles", return_value=[self.ROLE]),
            mock.patch.object(candidate_pool, "load_edhrec_rates", return_value=({"Zero Removal": 0.0}, None)),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            out = candidate_pool.generate_for_deck(
                self.DECK_ID, deck, cards, {c["name"]: c for c in cards}, self._playbook(),
                owned=set(), game_changers={"Zero Removal"}, mirror_updated_at="test", limit=3,
            )
        self.assertEqual(self._seats(out), [f"Removal {i}" for i in range(4)])
        self.assertNotIn("Zero Removal", self._names(out))

    def test_step_1_skips_a_decklist_card_by_its_front_face(self):
        """Kills A7 (step 1 checks `name`, not `front_face(name)`, against the decklist).

        The mirror names a double-faced card "Front // Back"; the decklist holds
        the front face. The deck's own card scores 5 (decklist demotion) below the cut.
        """
        cards = self._cards(below_removal=2)
        cards.append(self._card(
            "Split Removal // Other Half",
            "When this creature enters, exile target creature an opponent controls.", cmc=4,
        ))
        out, _ = self._generate(cards, limit=3, decklist=["Split Removal"])
        self.assertEqual(self._seats(out), ["Removal 0", "Removal 1"])
        self.assertNotIn("Split Removal // Other Half", self._names(out))

    def test_tail_breaks_a_score_tie_by_name(self):
        """Kills A8 (the tail sorts by score only).

        Both step-2 cards cost 1 and saturate the EDHREC term (rates 60 and 55
        both give 20), so both score 50.0, as Removal 1 does. Step 2 lists them by
        rate (Tie Z first); the tail must order the tie by name.
        """
        cards = self._cards(below_removal=3, off_archetype=["Tie Z", "Tie A"])
        out, _ = self._generate(cards, limit=3, rates={"Tie Z": 60.0, "Tie A": 55.0})
        tail = out["candidates"][3:]
        self.assertEqual(
            [(c["name"], c["score"]) for c in tail],
            [("Removal 0", 52.5), ("Removal 1", 50.0), ("Tie A", 50.0), ("Tie Z", 50.0), ("Removal 2", 47.5)],
        )

    def test_step_2_seats_only_cards_of_the_gap_role(self):
        """Kills A14 (step 2 takes a gated card of any role).

        Listed Rock matches no archetype, is on the EDHREC file and reads as
        `ramp`; the gap is `removal-spot`.
        """
        cards = self._cards(below_removal=4)
        cards.append(self._card("Listed Rock", "{T}: Add {C}.", cmc=1, type_line="Artifact"))
        out, stderr = self._generate(cards, limit=3, rates={"Listed Rock": 40.0})
        self.assertEqual(self._seats(out), [f"Removal {i}" for i in range(4)])
        self.assertNotIn("Listed Rock", self._names(out))
        self.assertIn("gap-seat: removal-spot 0 -> 4 (4 below the cut, 0 from the EDHREC page)", stderr)

    def test_log_counts_only_the_cards_that_step_1_seats(self):
        """Kills A16 (`from_step1 = count`: the log counts the pool's own cards as step-1 seats)."""
        cards = self._cards(head=0, head_removal=4, below_removal=3)
        _, stderr = self._generate(cards, limit=4)
        self.assertIn("gap-seat: removal-spot 4 -> 5 (1 below the cut, 0 from the EDHREC page)", stderr)

    def test_role_listed_twice_gives_each_card_one_seat(self):
        """DEC-1121 N3: a `gaps[]` that lists a role twice seats each card once."""
        cards = self._cards(below_removal=2, off_archetype=["Listed Removal"])
        rates = {"Listed Removal": 40.0}
        once, _ = self._generate(cards, limit=3, rates=rates)
        twice, stderr = self._generate(cards, limit=3, gaps=(self.ROLE, self.ROLE), rates=rates)
        self.assertEqual(self._names(twice), self._names(once))
        self.assertEqual(self._seats(twice), ["Removal 0", "Removal 1", "Listed Removal"])
        self.assertEqual(stderr.count("gap-seat: removal-spot"), 1)


class GapSeatWriteTests(unittest.TestCase):
    """DEC-1078: main() writes a pool once, and a change of a seat writes.

    DEC-1157: a change of any field but generated_at writes.
    """

    DECK_ID = GapSeatTests.DECK_ID

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dec1078-"))
        helper = GapSeatTests()
        cards = helper._cards(below_removal=6)
        (self.tmp / "mirror.json").write_text(json.dumps(cards))
        (self.tmp / "playbook.json").write_text(json.dumps(helper._playbook()))
        deck_dir = self.tmp / "commanders" / self.DECK_ID
        deck_dir.mkdir(parents=True)
        (deck_dir / "deck.json").write_text(json.dumps({
            "commander": "Test Commander", "archetypes": ["etb-flicker"], "decklist": [],
        }))
        (deck_dir / "metrics.json").write_text(json.dumps({"gaps": [
            {"role": "removal-spot", "actual": 2, "target": 8, "score": 25},
            {"resilience_component": "protection", "score_pct": 50, "max": 25},
        ]}))
        self.out_path = deck_dir / "candidates.json"
        self.patches = [
            mock.patch.object(candidate_pool, name, self.tmp / rel)
            for name, rel in (
                ("MIRROR_FILE", "mirror.json"),
                ("MIRROR_META", "no-meta.json"),
                ("PLAYBOOK_FILE", "playbook.json"),
                ("OWNED_FILE", "no-owned.csv"),
                ("GAME_CHANGERS_FILE", "no-gc.json"),
                ("EDHREC_RATES_DIR", "no-edhrec"),
                ("COMMANDERS_DIR", "commanders"),
            )
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def _run(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = candidate_pool.main(["--deck", self.DECK_ID, "--limit", "3"])
        self.assertEqual(code, 0)
        return stderr.getvalue()

    def test_second_run_writes_no_file(self):
        first = self._run()
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", first)
        written = self.out_path.read_bytes()
        pool = json.loads(written)
        self.assertEqual(pool["deck_gaps"], ["removal-spot"])
        self.assertEqual(sum(1 for c in pool["candidates"] if c.get("seeded_for_gap")), 5)
        second = self._run()
        self.assertIn(f"[{self.DECK_ID}] no change (8 candidates)", second)
        self.assertEqual(self.out_path.read_bytes(), written)

    def test_file_that_differs_only_in_the_flag_is_rewritten(self):
        self._run()
        pool = json.loads(self.out_path.read_text())
        for entry in pool["candidates"]:
            entry.pop("seeded_for_gap", None)
        self.out_path.write_text(json.dumps(pool))
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(sum(1 for c in pool["candidates"] if c.get("seeded_for_gap")), 5)

    def test_file_whose_flag_names_another_role_is_rewritten(self):
        """Kills A23 (the write guard compares `bool(seeded_for_gap)`, not the role).

        Same names, same pins, and a flag on the same five cards, but the flag
        names another role (a pool written before a classifier change, or edited).
        """
        self._run()
        pool = json.loads(self.out_path.read_text())
        for entry in pool["candidates"]:
            if "seeded_for_gap" in entry:
                entry["seeded_for_gap"] = "removal-board"
        self.out_path.write_text(json.dumps(pool))
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(
            [c["seeded_for_gap"] for c in pool["candidates"] if "seeded_for_gap" in c], ["removal-spot"] * 5,
        )

    # DEC-1157: the guard compares the whole file apart from generated_at.

    def _edit_pool(self, edit):
        self._run()
        pool = json.loads(self.out_path.read_text())
        before = json.loads(json.dumps(pool))
        edit(pool)
        self.assertNotEqual(pool, before)
        self.out_path.write_text(json.dumps(pool, indent=2, ensure_ascii=False) + "\n")
        return before

    def test_file_that_differs_only_in_generated_at_is_not_rewritten(self):
        def edit(pool):
            pool["generated_at"] = "2000-01-01T00:00:00+00:00"
        self._edit_pool(edit)
        edited = self.out_path.read_bytes()
        self.assertIn(f"[{self.DECK_ID}] no change (8 candidates)", self._run())
        self.assertEqual(self.out_path.read_bytes(), edited)

    def test_file_that_differs_only_in_one_deck_role_is_rewritten(self):
        def edit(pool):
            pool["candidates"][0]["deck_role"] = "stale-role"
        before = self._edit_pool(edit)
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(pool["candidates"][0]["deck_role"], before["candidates"][0]["deck_role"])

    def test_file_that_differs_only_in_one_score_is_rewritten(self):
        def edit(pool):
            pool["candidates"][0]["score"] += 0.5  # the top card stays on top
        before = self._edit_pool(edit)
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(pool["candidates"][0]["score"], before["candidates"][0]["score"])

    def test_file_that_differs_only_in_role_pool_is_rewritten(self):
        def edit(pool):
            pool["role_pool"] = {"removal-spot": {"count": 1, "median": 10.0}}
        before = self._edit_pool(edit)
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(pool["role_pool"], before["role_pool"])

    def test_file_that_is_not_valid_json_is_rewritten(self):
        """K1: a pool cut short in a write is written again, not kept and not a crash."""
        self._run()
        self.out_path.write_text('{"candidates": [\n')
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        pool = json.loads(self.out_path.read_text())
        self.assertEqual(len(pool["candidates"]), 7)

    def test_run_that_writes_nothing_prints_no_wrote_line(self):
        """K2: a skip prints the `no change` line and no `wrote` line."""
        def edit(pool):
            pool["generated_at"] = "2000-01-01T00:00:00+00:00"
        self._edit_pool(edit)
        second = self._run()
        self.assertIn(f"[{self.DECK_ID}] no change (8 candidates)", second)
        self.assertNotIn(f"[{self.DECK_ID}] wrote", second)

    def test_written_text_has_two_space_indent_utf8_and_final_newline(self):
        """K3: the file is json.dumps(indent=2, ensure_ascii=False) plus a final newline."""
        edhrec_dir = self.tmp / "no-edhrec"
        edhrec_dir.mkdir()
        source = "Invented page — Zoë"
        (edhrec_dir / f"{self.DECK_ID}.json").write_text(json.dumps(
            {"recorded_at": "2026-01-01", "source": source, "rates": {}},
        ))
        self.assertIn(f"[{self.DECK_ID}] wrote 8 candidates", self._run())
        text = self.out_path.read_text(encoding="utf-8")
        pool = json.loads(text)
        self.assertEqual(pool["edhrec_rates"]["source"], source)
        self.assertIn(source, text)
        self.assertEqual(text, json.dumps(pool, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()

import importlib
import unittest


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


if __name__ == "__main__":
    unittest.main()

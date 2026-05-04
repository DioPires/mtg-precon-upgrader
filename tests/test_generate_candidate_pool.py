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


if __name__ == "__main__":
    unittest.main()

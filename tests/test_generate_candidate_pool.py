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


if __name__ == "__main__":
    unittest.main()

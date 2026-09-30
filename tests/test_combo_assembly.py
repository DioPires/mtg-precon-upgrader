"""Tests for the DEC-363 tutor/redundancy-aware comboConsistency model.

Covers the five acceptance cases from the issue:
  (a) combo-less deck -> comboConsistency floored at 50
  (b) same deck with 0 vs 5 tutors -> strictly higher assembly with tutors
  (c) 1 tutor + 2 empty slots -> ~0% assembly (the one-tutor-one-slot guard)
  (d) fast 2-card infinite (Rings+Basalt style) + tutors -> assembles high
  (e) value deck (no/weak combo) -> comboConsistency floored at 50
"""

import importlib
import random
import unittest
from unittest.mock import patch


exporter = importlib.import_module("scripts.export_simulation_results")


def meta(type_line, mana_cost="", cmc=0, oracle=""):
    return {
        "type_line": type_line,
        "mana_cost": mana_cost,
        "cmc": cmc,
        "oracle_text": oracle,
    }


# A colorless-producing land keeps the synthetic mana model trivial: every
# non-land synthetic card costs only generic mana, payable from any source.
LAND = meta("Land", oracle="{T}: Add {C}.")
ARTIFACT_1 = meta("Artifact", mana_cost="{1}", cmc=1)
FILLER = meta("Creature", mana_cost="{2}", cmc=2)
COMMANDER = meta("Legendary Creature", mana_cost="{2}", cmc=2)


def build_context(decklist, combo, metadata, deck_data, commander="Cmdr"):
    """Build a goldfish context with KEY_COMBOS patched for a synthetic deck."""
    with patch.dict(exporter.KEY_COMBOS, {"test-deck": [combo]}, clear=False):
        return exporter.build_goldfish_context(
            decklist, deck_data, metadata, commander, [], deck_id="test-deck")


def run_assembly(context, decklist, metadata, n=1500, seed=exporter.GOLDFISH_SEED):
    """Single-process seeded Monte Carlo -> combo-0 assembly% by turn."""
    random.seed(seed)
    counts = {turn: 0 for turn in range(1, exporter.NUM_TURNS + 1)}
    threshold = max(exporter.GOLDFISH_MEANINGFUL_PRESSURE_FLOOR,
                    int(round(exporter.compute_avg_cmc(decklist, metadata) * 2)))
    for _ in range(n):
        _by_turn, assembly_turn = exporter.simulate_goldfish_game(
            decklist, metadata, context, threshold)
        earliest = assembly_turn[0]
        if earliest is not None:
            for turn in range(earliest, exporter.NUM_TURNS + 1):
                counts[turn] += 1
    return {turn: counts[turn] / n * 100 for turn in counts}


def make_deck(num_tutors, num_lands=16, num_fillers=18):
    """A 2-piece artifact combo deck with a tunable number of generic tutors."""
    decklist = ["Piece A", "Piece B"]
    metadata = {"Piece A": ARTIFACT_1, "Piece B": ARTIFACT_1, "Cmdr": COMMANDER}
    deck_entries = [
        {"name": "Piece A", "primary_role": "wincon"},
        {"name": "Piece B", "primary_role": "wincon"},
    ]
    for i in range(num_tutors):
        name = f"Tutor {i}"
        decklist.append(name)
        metadata[name] = meta("Sorcery", mana_cost="{1}", cmc=1,
                              oracle="Search your library for a card, put it into your hand.")
        deck_entries.append({"name": name, "primary_role": "tutor", "tutor_targets": ["any"]})
    for i in range(num_lands):
        name = f"Land {i}"
        decklist.append(name)
        metadata[name] = LAND
        deck_entries.append({"name": name, "primary_role": "land"})
    for i in range(num_fillers):
        name = f"Filler {i}"
        decklist.append(name)
        metadata[name] = FILLER
        deck_entries.append({"name": name, "primary_role": "threat"})
    combo = {
        "name": "Two-Piece",
        "slots": [["Piece A"], ["Piece B"]],
        "requiresCommander": False,
        "description": "",
    }
    deck_data = {"decklist": deck_entries}
    return decklist, metadata, deck_data, combo


class ComboAssemblySpecTests(unittest.TestCase):
    def test_slot_lists_backcompat_from_pieces(self):
        combo = {"pieces": ["X", "Y"]}
        self.assertEqual(exporter.combo_slot_lists(combo), [["X"], ["Y"]])

    def test_slot_lists_uses_explicit_slots(self):
        combo = {"slots": [["X"], ["Y", "Z"]]}
        self.assertEqual(exporter.combo_slot_lists(combo), [["X"], ["Y", "Z"]])

    def test_assembly_line_drops_combo_with_missing_slot(self):
        with patch.dict(exporter.KEY_COMBOS, {
            "test-deck": [{"name": "C", "slots": [["X"], ["Absent"]], "requiresCommander": False}]
        }, clear=False):
            lines = exporter.build_combo_assembly_lines("test-deck", ["X"], "Cmdr")
        self.assertEqual(lines, [])

    def test_assembly_line_commander_slot_autofilled(self):
        with patch.dict(exporter.KEY_COMBOS, {
            "test-deck": [{"name": "C", "slots": [["Cmdr"], ["X"]], "requiresCommander": True}]
        }, clear=False):
            lines = exporter.build_combo_assembly_lines("test-deck", ["X"], "Cmdr")
        self.assertEqual(len(lines), 1)
        slots = lines[0]["slots"]
        self.assertTrue(slots[0]["isCommander"])
        self.assertEqual(slots[0]["members"], [])
        self.assertEqual(slots[1]["members"], ["X"])


class OneTutorOneSlotTests(unittest.TestCase):
    """Case (c): a single tutor must not fill two open slots."""

    def setUp(self):
        decklist = ["Piece A", "Piece B", "Tutor 0", "Tutor 1"] + [f"Land {i}" for i in range(5)]
        metadata = {
            "Piece A": ARTIFACT_1, "Piece B": ARTIFACT_1, "Cmdr": COMMANDER,
            "Tutor 0": meta("Sorcery", mana_cost="{1}", cmc=1, oracle="Search your library."),
            "Tutor 1": meta("Sorcery", mana_cost="{1}", cmc=1, oracle="Search your library."),
        }
        for i in range(5):
            metadata[f"Land {i}"] = LAND
        deck_data = {"decklist": [
            {"name": "Piece A", "primary_role": "wincon"},
            {"name": "Piece B", "primary_role": "wincon"},
            {"name": "Tutor 0", "primary_role": "tutor", "tutor_targets": ["any"]},
            {"name": "Tutor 1", "primary_role": "tutor", "tutor_targets": ["any"]},
        ] + [{"name": f"Land {i}", "primary_role": "land"} for i in range(5)]}
        combo = {"name": "C", "slots": [["Piece A"], ["Piece B"]],
                 "requiresCommander": False, "description": ""}
        self.ctx = build_context(decklist, combo, metadata, deck_data)
        self.line = self.ctx["assemblyLines"][0]
        self.profiles = self.ctx["profiles"]
        self.tutor_meta = self.ctx["tutorMeta"]
        # Five untapped colorless sources -> mana never the blocker.
        self.mana = [{"name": f"L{i}", "kind": "land", "manaAtoms": [frozenset({"C"})],
                      "manaActiveTurn": 1} for i in range(5)]

    def _assembled(self, hand, library):
        return exporter.combo_assembled_this_turn(
            turn=3, hand=hand, permanents=self.mana, library=library,
            assembly_line=self.line, profiles=self.profiles, tutor_meta=self.tutor_meta,
            pool=exporter.GoldfishManaPool(exporter.turn_sources(self.mana, 3)))

    def test_one_tutor_two_empty_slots_not_assembled(self):
        # 1 tutor, neither piece drawn -> cannot cover both slots.
        self.assertFalse(self._assembled(["Tutor 0"], ["Piece A", "Piece B"]))

    def test_two_tutors_two_empty_slots_assembled(self):
        self.assertTrue(self._assembled(["Tutor 0", "Tutor 1"], ["Piece A", "Piece B"]))

    def test_one_drawn_one_tutor_assembled(self):
        # Piece A in hand fills slot 1 directly; one tutor covers slot 2.
        self.assertTrue(self._assembled(["Piece A", "Tutor 0"], ["Piece B"]))

    def test_tutor_with_no_library_target_not_assembled(self):
        # Both pieces already used up (not in library) and not drawn -> tutor
        # has nothing legal to fetch.
        self.assertFalse(self._assembled(["Tutor 0", "Tutor 1"], []))


class MonteCarloAssemblyTests(unittest.TestCase):
    def test_tutors_strictly_increase_assembly(self):
        """Case (b): 0 vs 5 tutors -> strictly higher assembly."""
        dl0, md0, dd0, combo0 = make_deck(num_tutors=0)
        ctx0 = build_context(dl0, combo0, md0, dd0)
        a0 = run_assembly(ctx0, dl0, md0)

        dl5, md5, dd5, combo5 = make_deck(num_tutors=5, num_fillers=13)
        ctx5 = build_context(dl5, combo5, md5, dd5)
        a5 = run_assembly(ctx5, dl5, md5)

        self.assertGreater(a5[exporter.NUM_TURNS], a0[exporter.NUM_TURNS])

    def test_fast_two_card_combo_with_tutors_scores_high(self):
        """Case (d): cheap 2-card combo + tutors assembles in a large share of games."""
        dl, md, dd, combo = make_deck(num_tutors=5, num_fillers=13)
        ctx = build_context(dl, combo, md, dd)
        assembly = run_assembly(ctx, dl, md)
        self.assertGreater(assembly[exporter.NUM_TURNS], 50.0)


def _base_result():
    """Minimal result dict carrying only fields the health score reads."""
    return {
        "commanderTiming": {"cmc": 3, "byTurn": {"3": 60.0}},
        "mulliganStats": {"paidMulligan": 5.0, "freeMulligan": 10.0},
        "manaByTurn": {"4": {"mean": 4.0}},
        "deckComposition": {"avgCmc": 3.0},
    }


def _health(combo_assembly):
    neutral_curve = {"byTurn": {str(t): 50.0 for t in range(1, 11)}}
    return exporter.compute_deck_health_score(
        result=_base_result(),
        threat_density=neutral_curve,
        draw_reliability=neutral_curve,
        interaction_availability=neutral_curve,
        combo_assembly=combo_assembly,
        color_adequacy={"overallScore": 80.0},
        commander_dependency={"score": 20.0},
    )


class ComboConsistencyFloorTests(unittest.TestCase):
    def test_comboless_deck_floored_at_50(self):
        """Case (a): no declared combo -> comboConsistency == 50."""
        assembly = {"combos": [], "bestByTurn": {str(t): 0.0 for t in range(1, 11)}}
        health = _health(assembly)
        self.assertEqual(health["components"]["comboConsistency"], 50.0)

    def test_value_deck_dead_combo_floored_at_50(self):
        """Case (e): a declared combo that never assembles stays at the 50 floor."""
        assembly = {
            "combos": [{"name": "Never"}],
            "bestByTurn": {str(t): 0.0 for t in range(1, 11)},
        }
        health = _health(assembly)
        self.assertEqual(health["components"]["comboConsistency"], 50.0)

    def test_comboconsistency_never_below_floor(self):
        """Any nonzero assembly only ever raises the axis (>=50), never lowers it."""
        assembly = {
            "combos": [{"name": "Weak"}],
            "bestByTurn": {str(t): 5.0 for t in range(1, 11)},
        }
        health = _health(assembly)
        self.assertGreaterEqual(health["components"]["comboConsistency"], 50.0)

    def test_fast_combo_rises_above_floor(self):
        assembly = {
            "combos": [{"name": "Fast"}],
            "bestByTurn": {str(t): 90.0 for t in range(1, 11)},
        }
        health = _health(assembly)
        self.assertGreater(health["components"]["comboConsistency"], 50.0)


if __name__ == "__main__":
    unittest.main()

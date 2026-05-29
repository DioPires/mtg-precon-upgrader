"""DEC-311 — tests for win_turn_triple in scripts/compute_deck_metrics.py."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import compute_deck_metrics as m  # noqa: E402
import validate_strategy_ceiling as vsc  # noqa: E402


def _curve(values):
    """{T: (comboLethal, lethalProxy)} → goldfish.byTurn shape."""
    return {str(t): {"comboLethal": cl, "lethalProxy": lp} for t, (cl, lp) in values.items()}


def _write_sim(root: Path, deck_id: str, by_turn: dict) -> None:
    d = root / deck_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "simulation.json").write_text(json.dumps({"goldfish": {"byTurn": by_turn}}))


class WinTurnTripleTests(unittest.TestCase):
    def setUp(self):
        # Each test gets its own throwaway DECKS_DIR.
        self._tmp = Path(__file__).parent / "_tmp_win_turn"
        self._tmp.mkdir(exist_ok=True)
        # Clean previous artefacts.
        for child in self._tmp.glob("*"):
            for f in child.glob("*"):
                f.unlink()
            child.rmdir()
        self._patcher = mock.patch.object(m, "DECKS_DIR", self._tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        for child in self._tmp.glob("*"):
            for f in child.glob("*"):
                f.unlink()
            child.rmdir()
        self._tmp.rmdir()

    # ---- branching ----------------------------------------------------------

    def test_combo_style_uses_comboLethal(self):
        _write_sim(self._tmp, "d", _curve({
            1: (0, 0), 2: (5, 50), 3: (16, 60), 4: (52, 70),
            5: (60, 80), 6: (70, 90), 7: (80, 95), 8: (85, 97),
            9: (90, 98), 10: (92, 99),
        }))
        deck = {"wincon_style": "combo", "decklist": [{"wincon_style": "combo"}]}
        triple = m.win_turn_triple(deck, "d", bracket=4)
        self.assertEqual(triple["source"], "comboLethal")
        self.assertEqual(triple["best"], 3)
        self.assertEqual(triple["typical"], 4)
        self.assertEqual(triple["contested"], 5)  # B4 drag = 1

    def test_combat_style_uses_lethalProxy(self):
        _write_sim(self._tmp, "d", _curve({
            t: (0, v) for t, v in
            [(1, 0), (2, 0), (3, 0), (4, 5), (5, 16), (6, 30), (7, 55), (8, 75),
             (9, 85), (10, 92)]
        }))
        deck = {"wincon_style": "combat", "decklist": [{"wincon_style": "combat"}]}
        triple = m.win_turn_triple(deck, "d", bracket=3)
        self.assertEqual(triple["source"], "lethalProxy")
        self.assertEqual(triple["best"], 5)
        self.assertEqual(triple["typical"], 7)
        self.assertEqual(triple["contested"], 7)  # B3 drag = 0

    def test_value_incremental_uses_max(self):
        _write_sim(self._tmp, "d", _curve({
            1: (0, 0), 2: (0, 0), 3: (20, 5), 4: (30, 10), 5: (40, 20),
            6: (45, 30), 7: (48, 40), 8: (49, 55), 9: (49, 70), 10: (50, 85),
        }))
        deck = {"wincon_style": "value-incremental", "decklist": []}
        triple = m.win_turn_triple(deck, "d", bracket=4)
        self.assertEqual(triple["source"], "max")
        # CL hits 15% at T3, LP hits 50% at T8 → max curve uses both
        self.assertEqual(triple["best"], 3)
        self.assertEqual(triple["typical"], 8)
        self.assertEqual(triple["contested"], 9)

    def test_multi_kind_falls_through_to_max(self):
        """Deck declared 'combo' but cards mix combo+combat → max(CL, LP).

        This is the Zada scenario — declared combo, but the simulator's
        actual signal lands on lethalProxy. Multi-kind detection prevents
        suppression that would otherwise hide the deck's real close turn.
        """
        _write_sim(self._tmp, "d", _curve({
            t: (0, v) for t, v in
            [(1, 0), (2, 0), (3, 0), (4, 0), (5, 4), (6, 19), (7, 48),
             (8, 73), (9, 86), (10, 93)]
        }))
        deck = {
            "wincon_style": "combo",
            "decklist": [
                {"wincon_style": "combo"},
                {"wincon_style": "combat"},
            ],
        }
        triple = m.win_turn_triple(deck, "d", bracket=4)
        self.assertEqual(triple["source"], "max")
        self.assertEqual(triple["best"], 6)
        self.assertEqual(triple["typical"], 8)

    # ---- suppression rules --------------------------------------------------

    def test_missing_simulation_returns_None(self):
        deck = {"wincon_style": "combat", "decklist": []}
        self.assertIsNone(m.win_turn_triple(deck, "no-such-deck", bracket=4))

    def test_flat_zero_curve_suppresses(self):
        _write_sim(self._tmp, "d", _curve({t: (0, 0) for t in range(1, 11)}))
        deck = {"wincon_style": "combat", "decklist": []}
        self.assertIsNone(m.win_turn_triple(deck, "d", bracket=4))

    def test_typical_unreached_renders_None_and_suppresses_contested(self):
        _write_sim(self._tmp, "d", _curve({
            # Combat-style deck whose LP never hits 50% inside the window.
            t: (0, v) for t, v in
            [(1, 0), (2, 0), (3, 0), (4, 5), (5, 10), (6, 18), (7, 25),
             (8, 32), (9, 40), (10, 45)]
        }))
        deck = {"wincon_style": "combat", "decklist": []}
        triple = m.win_turn_triple(deck, "d", bracket=4)
        self.assertIsNotNone(triple)
        self.assertEqual(triple["best"], 6)
        self.assertIsNone(triple["typical"])
        self.assertIsNone(triple["contested"])

    # ---- bracket drag -------------------------------------------------------

    def test_bracket_drag_applied_to_contested(self):
        _write_sim(self._tmp, "d", _curve({
            t: (0, v) for t, v in
            [(1, 0), (2, 0), (3, 0), (4, 5), (5, 16), (6, 30), (7, 55),
             (8, 75), (9, 85), (10, 92)]
        }))
        deck = {"wincon_style": "combat", "decklist": []}
        for bracket, expected_contested in [(3, 7), (4, 8), (5, 9)]:
            triple = m.win_turn_triple(deck, "d", bracket=bracket)
            self.assertEqual(triple["typical"], 7)
            self.assertEqual(triple["contested"], expected_contested)
            self.assertEqual(triple["bracket_drag"], {3: 0, 4: 1, 5: 2}[bracket])

    # ---- DEC-309 threshold parity -------------------------------------------

    def test_best_threshold_matches_DEC_309_PAYOFF_FLOOR(self):
        """The 'Best' floor MUST match scripts/validate_strategy_ceiling.py's
        PAYOFF_FLOOR — if one moves, both must move in the same PR."""
        self.assertEqual(m.WIN_TURN_BEST_THRESHOLD, vsc.PAYOFF_FLOOR)


if __name__ == "__main__":
    unittest.main()

"""DEC-939 — tests for the turn reads in scripts/validate_strategy_ceiling.py.

The payoff reads CL@T7 / LP@T8 and the fast-payoff rule reads CL@T6, one turn
later than the original DEC-309 reads (DEC-937 moved every fast deck's lethal
curve a turn). These tests pin the turns, not the thresholds.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import validate_strategy_ceiling as vsc  # noqa: E402

# One distinct value per (turn, curve) so a wrong turn read is unmistakable.
COMBO_BY_TURN = {t: float(t) for t in range(1, 11)}
PROXY_BY_TURN = {t: float(t) * 10 for t in range(1, 11)}


def _write_deck(root: Path, deck_id: str, *, wincon_style, manaH=85, intD=120,
                combo=None, proxy=None, card_styles=()):
    combo = combo or COMBO_BY_TURN
    proxy = proxy or PROXY_BY_TURN
    d = root / deck_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "deck.json").write_text(json.dumps({
        "wincon_style": wincon_style,
        "bracket": "4",
        "decklist": [{"name": f"c{i}", "wincon_style": s} for i, s in enumerate(card_styles)],
    }))
    (d / "metrics.json").write_text(json.dumps({
        "metrics": {
            "manabase_health": {"score": manaH},
            "interaction_density": {"score": intD},
        }
    }))
    (d / "simulation.json").write_text(json.dumps({
        "goldfish": {
            "byTurn": {
                str(t): {"comboLethal": combo[t], "lethalProxy": proxy[t]}
                for t in range(1, 11)
            }
        }
    }))
    return d


class StrategyCeilingTurnReadTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)

    def test_snapshot_reads_t6_t7_combo_and_t8_proxy(self):
        d = _write_deck(self.root, "d", wincon_style="combo")
        snap = vsc.load_snapshot(d)
        self.assertEqual(snap.combo_lethal_t6, COMBO_BY_TURN[6])
        self.assertEqual(snap.combo_lethal_t7, COMBO_BY_TURN[7])
        self.assertEqual(snap.lethal_proxy_t8, PROXY_BY_TURN[8])

    def test_combo_style_payoff_is_cl_at_t7(self):
        snap = vsc.load_snapshot(_write_deck(self.root, "d", wincon_style="combo"))
        self.assertEqual(snap.payoff, (COMBO_BY_TURN[7], "CL@T7"))

    def test_combat_style_payoff_is_lp_at_t8(self):
        snap = vsc.load_snapshot(_write_deck(self.root, "d", wincon_style="combat"))
        self.assertEqual(snap.payoff, (PROXY_BY_TURN[8], "LP@T8"))

    def test_value_incremental_payoff_is_max_of_t7_t8(self):
        snap = vsc.load_snapshot(_write_deck(self.root, "d", wincon_style="value-incremental"))
        val, src = snap.payoff
        self.assertEqual(val, max(COMBO_BY_TURN[7], PROXY_BY_TURN[8]))
        self.assertEqual(src, "max(CL@T7, LP@T8)")

    def test_multi_kind_payoff_is_max_of_t7_t8(self):
        snap = vsc.load_snapshot(_write_deck(
            self.root, "d", wincon_style="combo", card_styles=("combo", "combat")))
        self.assertTrue(snap.is_multi_kind)
        self.assertEqual(snap.payoff[1], "max(CL@T7, LP@T8)")

    def test_unknown_style_payoff_is_max_of_t7_t8(self):
        snap = vsc.load_snapshot(_write_deck(self.root, "d", wincon_style="teapot"))
        val, src = snap.payoff
        self.assertEqual(val, max(COMBO_BY_TURN[7], PROXY_BY_TURN[8]))
        self.assertIn("max(CL@T7, LP@T8)", src)


class StrategyCeilingWarningTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.addCleanup(self._tmpdir.cleanup)

    def test_thresholds_unchanged(self):
        self.assertEqual(
            (vsc.SHELL_FLOOR, vsc.PAYOFF_FLOOR, vsc.FAST_PAYOFF, vsc.WEAK_SHELL),
            (80, 15.0, 50.0, 60),
        )

    def test_shell_exceeds_payoff_uses_t8_proxy(self):
        """LP@T7 below the floor but LP@T8 above it must NOT warn (hidden-legion)."""
        proxy = {t: 0.0 for t in range(1, 11)}
        proxy[7] = 13.2
        proxy[8] = 36.5
        snap = vsc.load_snapshot(_write_deck(
            self.root, "d", wincon_style="combat", manaH=85, intD=120, proxy=proxy))
        self.assertEqual(snap.shell, 85)
        self.assertEqual(vsc.evaluate(snap), [])

        proxy[8] = 13.2
        snap = vsc.load_snapshot(_write_deck(
            self.root, "e", wincon_style="combat", manaH=85, intD=120, proxy=proxy))
        self.assertEqual(len(vsc.evaluate(snap)), 1)
        self.assertIn("shell-exceeds-payoff", vsc.evaluate(snap)[0])

    def test_fast_payoff_rule_reads_cl_at_t6(self):
        """A 50%+ combo line at T6 with a weak shell warns; the same at T5 does not."""
        combo = {t: 0.0 for t in range(1, 11)}
        combo[5] = 80.0
        snap = vsc.load_snapshot(_write_deck(
            self.root, "t5-only", wincon_style="combo", manaH=55, intD=55, combo=combo))
        self.assertEqual(vsc.evaluate(snap), [])

        combo[6] = 80.0
        snap = vsc.load_snapshot(_write_deck(
            self.root, "t6", wincon_style="combo", manaH=55, intD=55, combo=combo))
        warnings = vsc.evaluate(snap)
        self.assertEqual(len(warnings), 1)
        self.assertIn("comboLethal@T6=80.0%", warnings[0])


if __name__ == "__main__":
    unittest.main()

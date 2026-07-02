"""DEC-389 — tests for global_health_normalized in scripts/compute_deck_metrics.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import compute_deck_metrics as m  # noqa: E402


def _deck(bracket: str) -> dict:
    """Synthetic deck whose role counts sit between B3 and B4 targets, so the
    bracket-aware score moves on redeclaration while the normalized one must not."""
    decklist = []
    for i in range(8):  # B3 card-draw target 8, B4 target 10
        decklist.append({"name": f"Draw {i}", "type": "Creature", "primary_role": "card-draw"})
    for i in range(6):  # B3 removal-spot target 6, B4 target 8
        decklist.append({"name": f"Kill {i}", "type": "Instant", "primary_role": "removal-spot"})
    decklist.append({"name": "Closer", "type": "Creature", "primary_role": "wincon"})
    for i in range(30):
        decklist.append({"name": "Forest", "type": "Land", "primary_role": "land", "quantity": 1})
    return {
        "commander": "Test Commander",
        "bracket": bracket,
        "wincon_style": "discrete-threats",
        "archetypes": [],
        "decklist": decklist,
    }


class GlobalHealthNormalizedTests(unittest.TestCase):
    def test_normalized_invariant_under_bracket_redeclaration(self):
        p3 = m.compute(_deck("3"), "test-deck-norm", {}, "test")
        p4 = m.compute(_deck("4"), "test-deck-norm", {}, "test")
        # Declared-bar score moves with the redeclaration...
        self.assertNotEqual(
            p3["metrics"]["role_coverage_health"]["score"],
            p4["metrics"]["role_coverage_health"]["score"],
        )
        # ...the normalized companion must not.
        self.assertEqual(p3["global_health_normalized"], p4["global_health_normalized"])
        self.assertEqual(p3["normalized"], p4["normalized"])

    def test_payload_shape(self):
        payload = m.compute(_deck("4"), "test-deck-norm", {}, "test")
        self.assertIsInstance(payload["global_health_normalized"], int)
        norm = payload["normalized"]
        self.assertEqual(norm["reference_bracket"], m.NORMALIZED_REFERENCE_BRACKET)
        self.assertEqual(
            set(norm["components"]),
            {"manabase", "role", "curve", "interaction", "cohesion", "resilience"},
        )

    def test_b3_deck_normalized_equals_global_when_no_combo(self):
        # A deck already declared at the reference bracket with no combo wincon
        # is scored against identical targets on both rulers.
        payload = m.compute(_deck("3"), "test-deck-norm", {}, "test")
        self.assertEqual(payload["global_health"], payload["global_health_normalized"])

    def test_cohesion_bracket_penalty_excluded_from_normalized(self):
        deck = _deck("3")
        deck["wincon_style"] = "combo"
        deck["decklist"][14]["wincon_style"] = "combo"  # the wincon entry
        with_penalty = m.gameplan_cohesion(deck, {}, 3)
        without_penalty = m.gameplan_cohesion(deck, {}, 3, apply_bracket_penalty=False)
        self.assertEqual(with_penalty["penalty"], 15.0)
        self.assertEqual(without_penalty["penalty"], 0.0)


if __name__ == "__main__":
    unittest.main()

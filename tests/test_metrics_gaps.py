"""DEC-1062 — tests for gaps[] in scripts/compute_deck_metrics.py: the
redundancy `target` and the join of role gaps with resilience gaps."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import compute_deck_metrics as m  # noqa: E402


def _lines_deck(wincon_style: str, lines: int) -> dict:
    return {"wincon_style": wincon_style, "winConditions": [{"name": f"Line {i}"} for i in range(lines)]}


def _protection_short_deck() -> dict:
    """B4 deck with protection at 2.5 of 4: under 70 on both the role row and
    the resilience component."""
    decklist = [
        {"name": "Shield 0", "type": "Instant", "primary_role": "protection"},
        {"name": "Shield 1", "type": "Instant", "primary_role": "protection"},
        {"name": "Body", "type": "Creature", "primary_role": "threat", "secondary_role": "protection"},
    ]
    for i in range(30):
        decklist.append({"name": "Plains", "type": "Land", "primary_role": "land", "quantity": 1})
    return {
        "commander": "Test Commander",
        "bracket": "4",
        "wincon_style": "combat",
        "archetypes": [],
        "decklist": decklist,
    }


def _named(gaps: list[dict], name: str) -> list[dict]:
    return [g for g in gaps if name in (g.get("role"), g.get("resilience_component"))]


class RedundancyTargetTests(unittest.TestCase):
    def test_component_block_carries_target(self):
        for style, floor in (("combo", 1), ("discrete-threats", 2)):
            with self.subTest(style=style):
                res, _ = m.resilience_health(_lines_deck(style, floor), 4)
                block = res["components"]["redundancy"]
                self.assertEqual(block["floor"], floor)
                self.assertEqual(block["lines"], floor)
                self.assertEqual(block["target"], floor + 2)

    def test_gap_entry_carries_target_with_lines_and_floor(self):
        _, gaps = m.resilience_health(_lines_deck("combo", 2), 4)
        (entry,) = _named(gaps, "redundancy")
        self.assertEqual(
            entry,
            {
                "resilience_component": "redundancy",
                "score_pct": 50,
                "max": 25,
                "lines": 2,
                "floor": 1,
                "target": 3,
                "wincon_style": "combo",
            },
        )

    def test_full_score_arrives_at_target_and_not_before(self):
        for style in ("combo", "discrete-threats"):
            floor = m.RESILIENCE_WINCON_LINE_FLOOR[style]
            target = floor + m.RESILIENCE_REDUNDANCY_EXTRA_LINES
            with self.subTest(style=style):
                below, _ = m.resilience_health(_lines_deck(style, target - 1), 4)
                at, at_gaps = m.resilience_health(_lines_deck(style, target), 4)
                self.assertLess(below["components"]["redundancy"]["score"], 25)
                self.assertEqual(at["components"]["redundancy"]["score"], 25)
                self.assertEqual(at["components"]["redundancy"]["target"], target)
                self.assertEqual(_named(at_gaps, "redundancy"), [])


class MergeGapsTests(unittest.TestCase):
    ROLE = {"role": "protection", "actual": 2.5, "target": 4, "score": 62}
    RESILIENCE = {"resilience_component": "protection", "score_pct": 62, "max": 25, "actual": 2.5, "target": 4}

    def test_skips_resilience_gap_with_the_role_gap_figures(self):
        self.assertEqual(m.merge_gaps([self.ROLE], [self.RESILIENCE]), [self.ROLE])

    def test_keeps_both_when_actual_differs(self):
        resilience = {**self.RESILIENCE, "actual": 2.0}
        self.assertEqual(m.merge_gaps([self.ROLE], [resilience]), [self.ROLE, resilience])

    def test_keeps_both_when_target_differs(self):
        resilience = {**self.RESILIENCE, "target": 5}
        self.assertEqual(m.merge_gaps([self.ROLE], [resilience]), [self.ROLE, resilience])

    def test_keeps_resilience_gap_with_no_role_gap_of_its_name(self):
        tutor = {"role": "tutor", "actual": 2.5, "target": 4, "score": 62}
        redundancy = {
            "resilience_component": "redundancy", "score_pct": 50, "max": 25,
            "lines": 2, "floor": 1, "target": 3, "wincon_style": "combo",
        }
        self.assertEqual(
            m.merge_gaps([tutor], [self.RESILIENCE, redundancy]),
            [tutor, self.RESILIENCE, redundancy],
        )
        self.assertEqual(m.merge_gaps([], [self.RESILIENCE]), [self.RESILIENCE])


class ComputeGapsJoinTests(unittest.TestCase):
    def test_protection_shortfall_appears_once_and_component_stays(self):
        payload = m.compute(_protection_short_deck(), "test-deck-gaps", {}, "test")
        self.assertEqual(
            _named(payload["gaps"], "protection"),
            [{"role": "protection", "actual": 2.5, "target": 4, "score": 62}],
        )
        self.assertEqual(
            payload["metrics"]["resilience_health"]["components"]["protection"],
            {"score": 15.6, "actual": 2.5, "target": 4, "max": 25},
        )

    def test_both_entries_return_when_the_tables_are_tuned_apart(self):
        with mock.patch.dict(m.RESILIENCE_PROTECTION_TARGETS, {4: 5}):
            payload = m.compute(_protection_short_deck(), "test-deck-gaps", {}, "test")
        self.assertEqual(
            _named(payload["gaps"], "protection"),
            [
                {"role": "protection", "actual": 2.5, "target": 4, "score": 62},
                {"resilience_component": "protection", "score_pct": 50, "max": 25, "actual": 2.5, "target": 5},
            ],
        )


if __name__ == "__main__":
    unittest.main()

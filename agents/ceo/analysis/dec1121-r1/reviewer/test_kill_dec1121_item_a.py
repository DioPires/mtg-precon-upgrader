"""DEC-1121 kill cases for item (a) of PR #41 (scripts/generate_candidate_pool.py).

Each test passes on the head and fails on one surviving mutant (named in its
docstring). Run from the basis tree root:
    uv run --with pytest python -m pytest -q -p no:cacheprovider /tmp/dec1078-review/kill/test_kill_dec1121_item_a.py

The fix for each B item adds the test method to tests/test_generate_candidate_pool.py:
the GapSeatTests methods go into GapSeatTests, and the write test into GapSeatWriteTests.
"""
import contextlib
import importlib
import io
import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path.cwd()))
tg = importlib.import_module("tests.test_generate_candidate_pool")
candidate_pool = tg.candidate_pool


class GapSeatKillTests(tg.GapSeatTests):
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


class GapSeatWriteKillTests(tg.GapSeatWriteTests):
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


# The inherited tests run here too; keep only the kill cases in this file's count.
for _cls in (GapSeatKillTests, GapSeatWriteKillTests):
    for _name in [n for n in dir(_cls) if n.startswith("test_")]:
        if _name not in _cls.__dict__:
            setattr(_cls, _name, None)
del _cls, _name

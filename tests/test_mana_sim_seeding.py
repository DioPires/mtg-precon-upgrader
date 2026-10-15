"""DEC-1115: the export's mana sims are seeded.

run_parallel splits the games into MANA_SIM_CHUNKS fixed chunks and seeds each
chunk inside the worker, as the goldfish does (DEC-363). Two runs on one tree
and one input then give equal exports, and the CPU count (which sets only the
worker count) does not change them. Both tests run the whole export of one deck
through a real multiprocessing pool at a small game count, so a worker that
takes two chunks in a row is part of the test.

Hidden Legion's Bloom Tender built its mana sources in set order, which follows
the string hash seed of each worker process; BloomTenderOrderTests guards the
fixed WUBRG order.
"""
import copy
import importlib
import json
import random
import unittest
from unittest.mock import patch


exporter = importlib.import_module("scripts.export_simulation_results")

# Hidden Legion is the deck of the DEC-1085 seed control.
DECK_ID = "hidden-legion"
# 100 mana-sim games and 10 goldfish games in each of the 16 chunks.
GAMES = 1_600
GOLDFISH_GAMES = 160


def export_without_date(metadata: dict) -> dict:
    """Export DECK_ID at the small game counts; drop generatedAt."""
    _name, export_fn = exporter.DECK_MAP[DECK_ID]
    with patch.object(exporter, "NUM_GAMES", GAMES), \
            patch.object(exporter, "GOLDFISH_GAMES", GOLDFISH_GAMES):
        result = copy.deepcopy(export_fn(metadata))
    result["metadata"].pop("generatedAt")
    return result


class ManaSimSeedingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(exporter.METADATA_FILE) as f:
            cls.metadata = json.load(f)

    def test_two_runs_give_equal_exports(self):
        first = export_without_date(self.metadata)
        second = export_without_date(self.metadata)
        self.assertEqual(first["metadata"]["numGames"], GAMES)
        self.assertEqual(first, second)

    def test_cpu_count_does_not_change_the_export(self):
        # 2 workers take 8 chunks each; 18 CPUs give 16 workers, one chunk each.
        with patch("os.cpu_count", return_value=2):
            two = export_without_date(self.metadata)
        with patch("os.cpu_count", return_value=18):
            eighteen = export_without_date(self.metadata)
        self.assertEqual(two, eighteen)


class BloomTenderOrderTests(unittest.TestCase):
    def test_bloom_tender_sources_follow_wubrg_order(self):
        # Set order follows the string hash seed, which differs per process.
        # With all five colors, set order matched WUBRG for 1 of 200 hash
        # seeds (0 to 199), so the old code fails this test 199 times in 200.
        sources = exporter.sim_hidden_legion.dork_sources(
            "Bloom Tender", {"colors_present": {"G", "R", "B", "U", "W"}})
        self.assertEqual(sources, [frozenset({c}) for c in "WUBRG"])
        sources = exporter.sim_hidden_legion.dork_sources(
            "Bloom Tender", {"colors_present": set()})
        self.assertEqual(sources, [frozenset({"G"})])


def draw_chunk(args):
    """Stub mana-sim chunk for run_parallel: one draw from the module-level random."""
    _decklist, _metadata, num_games = args
    return random.random(), num_games


def keep_chunks(results):
    return results


class ChunkSeedTests(unittest.TestCase):
    # M4 of the DEC-1119 review gave all 16 chunks one seed: two runs were still
    # equal, so the export tests above passed, but the export read 6,250 games
    # 16 times. A stub chunk catches it in under a second, without a deck.
    GAMES = 1_605  # not a multiple of 16: chunks 0 to 4 take one game more

    def run_stub(self, cpus):
        with patch("os.cpu_count", return_value=cpus):
            return exporter.run_parallel(draw_chunk, keep_chunks, [], {}, self.GAMES)

    def test_each_chunk_draws_from_its_own_seed(self):
        # 3 CPUs: 3 workers, each runs several chunks in a row. 18 CPUs: 16 workers.
        three, sixteen = self.run_stub(3), self.run_stub(18)
        for chunks in (three, sixteen):
            draws = [d for d, _ in chunks]
            self.assertEqual(len(chunks), exporter.MANA_SIM_CHUNKS)
            self.assertEqual(sum(n for _, n in chunks), self.GAMES)
            self.assertEqual(len(set(draws)), len(draws), "two chunks drew the same value")
        self.assertEqual(three, sixteen)


if __name__ == "__main__":
    unittest.main()

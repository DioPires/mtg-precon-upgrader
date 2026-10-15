"""DEC-1119 kill case for M4: every chunk must draw from its own seed.

M4 gives all 16 chunks the seed MANA_SIM_SEED. Two runs are then still equal,
and the CPU count still changes nothing, so the two export tests in
tests/test_mana_sim_seeding.py pass. But the 16 chunks replay the same games:
at 100,000 games the export reads 6,250 different games 16 times.

This test sends a stub chunk function through run_parallel. The stub makes one
draw from the module-level `random` and returns it with the chunk's game count.
It asserts that the 16 draws are distinct, that the chunk sizes add up to the
game count, and that 3 workers and 16 workers give the same draws in the same
order. The stub is a module-level function, so `spawn` can pickle it.
Run time is under 2 s; no deck is simulated.
"""
import importlib
import random
import unittest
from unittest.mock import patch

exporter = importlib.import_module("scripts.export_simulation_results")

GAMES = 1_605  # not a multiple of 16: chunks 0 to 4 take one game more


def draw_chunk(args):
    """Stub mana-sim chunk: one draw from the module-level random."""
    _decklist, _metadata, num_games = args
    return random.random(), num_games


def keep_chunks(results):
    return results


def run_stub(cpus):
    with patch("os.cpu_count", return_value=cpus):
        return exporter.run_parallel(draw_chunk, keep_chunks, [], {}, GAMES)


class ChunkSeedTests(unittest.TestCase):
    def test_each_chunk_draws_from_its_own_seed(self):
        # 3 CPUs: 3 workers, so each worker runs several chunks in a row.
        # 18 CPUs: 16 workers, one chunk each.
        three, sixteen = run_stub(3), run_stub(18)
        for chunks in (three, sixteen):
            draws = [d for d, _ in chunks]
            self.assertEqual(len(chunks), exporter.MANA_SIM_CHUNKS)
            self.assertEqual(sum(n for _, n in chunks), GAMES)
            self.assertEqual(len(set(draws)), len(draws), "two chunks drew the same value")
        self.assertEqual(three, sixteen)


if __name__ == "__main__":
    unittest.main()

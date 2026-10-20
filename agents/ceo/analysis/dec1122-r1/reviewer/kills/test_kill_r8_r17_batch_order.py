"""DEC-1122 kill cases for R8 and R17: the batch holds the front faces in Python's sorted order.

compute_tokens_for_deck() sorts the full names, so the pin's 13 names reach fetch_collection()
already in order. Two other orders pass the pin:
- R8 keeps the order of the full names (dict.fromkeys). It differs when a name continues its
  front face with a space and a sign below '/', as "Fire & Ice" does beside "Fire // Ice".
- R17 sorts without case. It differs for "Lord Windgrace" and "Lord of the Void".
"""
import unittest

import tests.test_scryfall_callers as callers

COLLECTION_URL = callers.COLLECTION_URL


class KillBatchOrder(unittest.TestCase):
    def run_deck(self, *names: str) -> callers.FakeScryfall:
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.write_deck("one", "Sol Ring", *names)
        fake = callers.token_fake([
            callers.make_card(name, layout="adventure" if " // " in name else "normal")
            for name in names])
        code, _ = case.run_main(fake)
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        return fake

    def test_r8_batch_sorts_the_front_faces_not_the_full_names(self):
        fake = self.run_deck("Fire // Ice", "Fire & Ice")
        self.assertEqual(fake.asked_names(), ["Fire", "Fire & Ice", "Sol Ring"])

    def test_r17_batch_sorts_by_code_point_with_case(self):
        fake = self.run_deck("Lord of the Void", "Lord Windgrace")
        self.assertEqual(fake.asked_names(), ["Lord Windgrace", "Lord of the Void", "Sol Ring"])

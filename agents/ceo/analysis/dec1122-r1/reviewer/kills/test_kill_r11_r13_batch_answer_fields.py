"""DEC-1122 kill cases for R11, R12 and R13: the batch reads its answer's fields with defaults.

The lines that read ``data`` and ``not_found`` moved out of the old try block, so PR #40
rewrites them. The head reads a missing ``data`` or ``not_found`` as an empty list, and it
asks no fuzzy lookup for a ``not_found`` entry without a name. Each case answers the batch
with a raw body (FakeScryfall.failures holds bytes).
"""
import json
import unittest

import tests.test_scryfall_callers as callers

COLLECTION_URL = callers.COLLECTION_URL


class KillBatchAnswerFields(unittest.TestCase):
    def run_answer(self, answer: dict) -> tuple[int, str, callers.FakeScryfall, list]:
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        path = case.write_deck("one", "Goblin Maker")
        fake = callers.token_fake()
        fake.failures[0] = json.dumps(answer).encode()
        code, out = case.run_main(fake)
        return code, out, fake, json.loads(path.read_text())["tokens"]

    def test_r11_answer_without_data_reads_as_no_card(self):
        code, _, fake, tokens = self.run_answer({"object": "list", "not_found": []})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])

    def test_r12_answer_without_not_found_reads_as_every_card_found(self):
        goblin_maker = callers.token_fake().by_name["Goblin Maker"]
        code, _, fake, tokens = self.run_answer({"object": "list", "data": [goblin_maker]})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, callers.GOBLIN_URL])
        self.assertEqual([t["name"] for t in tokens], ["Goblin"])

    def test_r13_not_found_entry_without_a_name_costs_no_fuzzy_lookup(self):
        code, out, fake, tokens = self.run_answer(
            {"object": "list", "data": [], "not_found": [{"set": "abc", "collector_number": "1"}]})
        self.assertEqual(code, 0)
        self.assertNotIn("Retrying", out)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])

"""DEC-1122 kill case for R1.

A read timeout, a connection reset and an incomplete answer are failed requests too: each ends
the run with the RequestFailed text, writes no deck file, exits with 1 and sends no further
request. The suite only sends a URLError, so a _request that wraps a URLError or a ValueError
only passes these three raw and the run ends on a traceback.
"""
import http.client
import unittest

import tests.test_scryfall_callers as callers

COLLECTION_URL = callers.COLLECTION_URL


class KillR1(unittest.TestCase):
    def test_timeout_reset_or_incomplete_answer_ends_the_run_at_each_request_kind(self):
        kinds = {
            "the batch": ("Sol Ring", [COLLECTION_URL]),
            "a fuzzy /cards/named": (callers.MISSPELT, [COLLECTION_URL, callers.MISSPELT_URL]),
            "the token request": ("Goblin Maker", [COLLECTION_URL, callers.GOBLIN_URL]),
            "a /cards/search": ("Orc Caller", [COLLECTION_URL, callers.ARMY_URL]),
            "an exact /cards/named": ("Crown Seeker", [COLLECTION_URL, callers.MONARCH_URL]),
        }
        failures = {
            "read timeout": (lambda: TimeoutError("The read operation timed out"),
                             "TimeoutError: The read operation timed out"),
            "connection reset": (lambda: ConnectionResetError(54, "Connection reset by peer"),
                                 "ConnectionResetError: [Errno 54] Connection reset by peer"),
            "incomplete answer": (lambda: http.client.IncompleteRead(b"{"),
                                  "IncompleteRead: IncompleteRead(1 bytes read)"),
        }
        for kind, (card, urls) in kinds.items():
            for label, (failure, text) in failures.items():
                with self.subTest(kind=kind, failure=label):
                    case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
                    case.setUp()
                    self.addCleanup(case.doCleanups)
                    first = case.write_deck("a-first", card)
                    second = case.write_deck("b-second", "Arcane Signet")
                    before = {path: path.read_text() for path in (first, second)}
                    fake = callers.token_fake([callers.make_card("Arcane Signet")])
                    fake.failures[len(urls) - 1] = failure()

                    code, out = case.run_main(fake)

                    method = "POST" if urls[-1] == COLLECTION_URL else "GET"
                    self.assertEqual(code, 1)
                    self.assertIn(
                        f"\nScryfall request failed: {method} {urls[-1]}: {text}\nNo file written.\n",
                        out)
                    self.assertEqual([s.url for s in fake.sent], urls)
                    self.assertEqual({path: path.read_text() for path in before}, before)

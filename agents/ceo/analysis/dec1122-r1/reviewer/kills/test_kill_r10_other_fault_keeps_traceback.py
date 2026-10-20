"""DEC-1122 kill case for R10.

main() reports "No file written." for a 429 or a failed request only. Any other fault, here a
deck entry without a name, leaves main() as its own exception. A main() that catches every
Exception prints the KeyError as if a request had failed and returns 1.
"""
import json
import unittest

import tests.test_scryfall_callers as callers


class KillR10(unittest.TestCase):
    def test_deck_entry_without_a_name_is_not_reported_as_a_failed_request(self):
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        path = case.write_deck("one", "Sol Ring", "Arcane Signet")
        deck = json.loads(path.read_text())
        deck["decklist"].append({"quantity": 1})
        path.write_text(json.dumps(deck))
        before = path.read_text()
        fake = callers.token_fake()

        with self.assertRaises(KeyError):
            case.run_main(fake)

        self.assertEqual(fake.sent, [])
        self.assertEqual(path.read_text(), before)

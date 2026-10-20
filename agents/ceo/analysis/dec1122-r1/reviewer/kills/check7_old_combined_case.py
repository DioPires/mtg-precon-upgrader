"""DEC-1122 check 7, reading (b): the first leg's combined RedirectCases case on the merged helper.

The first leg's case set _rate_limited, ran the 3xx case, then asserted the state of a new
process. On the merged helper that state is _rate_limited only (no _last_answer_at). A 3xx
sets no 429, and setUp() already resets at the start, so this case cannot see the reset at
the end: it passes with F5 (RedirectCases without addCleanup) too.
"""
import unittest

import tests.test_scryfall_fetch as fetch


class OldCombinedCase(unittest.TestCase):
    def test_redirect_case_resets_the_helper_state_when_it_starts_and_ends(self):
        self.addCleanup(fetch.reset_helper_state)
        fetch.scryfall_api._rate_limited = True
        result = unittest.TestResult()
        fetch.RedirectCases("test_3xx_raises_and_no_second_request_goes_out").run(result)
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertFalse(fetch.scryfall_api._rate_limited)

"""DEC-1107 F1 kill case: the 429's time in the text is truncated to the second, not rounded.

A 429 answered at 10:41:07.6Z reads "at 10:41:07Z" (and the stop ends at 10:41:37.6Z, so the
text names 10:41:38Z and 30 s). Reads the module from KILL_TREE; fake clock; a temporary
SCRYFALL_LIMIT_DIR; nothing leaves the machine.
"""
import email.message, io, os, sys, tempfile, unittest, urllib.error
from datetime import datetime, timezone
from unittest import mock

TREE = os.environ.get("KILL_TREE",
                      "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1107-review")
sys.path.insert(0, os.path.join(TREE, "scripts"))
import scryfall_limit as limit  # noqa: E402

NAMED = "https://api.scryfall.com/cards/named?exact=Sol%20Ring"
AT = datetime(2026, 10, 14, 10, 41, 7, tzinfo=timezone.utc).timestamp()


class TimeOfThe429Tests(unittest.TestCase):
    def test_429_at_a_fraction_over_one_half_names_the_second_it_came(self):
        now = {"t": AT + 0.6 - 0.05}

        def transmit():
            now["t"] += 0.05
            raise urllib.error.HTTPError(NAMED, 429, "Too Many Requests", email.message.Message(), io.BytesIO())

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.dict(os.environ, {"SCRYFALL_LIMIT_DIR": folder}), \
                mock.patch("time.time", lambda: now["t"]), mock.patch("time.monotonic", lambda: now["t"]), \
                mock.patch("time.sleep", lambda s: None):
            with self.assertRaises(limit.Stopped) as raised:
                limit.send(NAMED, transmit)
            now["t"] = AT + 7.6
            with self.assertRaises(limit.Stopped) as later:
                limit.send(NAMED, lambda: b"{}")
        print(f"\n  the 429 call: {raised.exception}\n  a call 7 s later: {later.exception}")
        self.assertEqual(str(raised.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:38Z (in 30 s). "
            "Call again after that time."))
        self.assertEqual(str(later.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:38Z (in 23 s). "
            "Call again after that time."))


if __name__ == "__main__":
    unittest.main()

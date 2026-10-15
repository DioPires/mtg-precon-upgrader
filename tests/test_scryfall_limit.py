"""DEC-1092 — one limiter for every Scryfall caller on this Mac.

scripts/scryfall_limit.py keeps the waits and the stop in one lock folder that the fetch
scripts, the card tools' server and the Archidekt server share; each server keeps a byte-for-
byte copy. Most cases use FakeScryfall's fake transport and fake clock
(tests/test_scryfall_fetch.py). CrossProcessTests run real processes on one temporary lock
folder. No case sends a live request, and no case reads or writes /tmp/scryfall-limit.
"""

import contextlib
import email.message
import email.utils
import fcntl
import hashlib
import io
import json
import multiprocessing
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tests import test_scryfall_callers as callers
from tests.test_scryfall_fetch import (
    DeckDirCase, FakeScryfall, fetch_images, fetch_metadata, make_card, scryfall_api)

limit = scryfall_api.scryfall_limit

ROOT = Path(__file__).resolve().parent.parent
SERVER_COPIES = (
    "mcp-servers/scryfall/src/scryfall_mcp/services/scryfall_limit.py",
    "mcp-servers/archidekt/src/archidekt_mcp/services/scryfall_limit.py",
)
API = "https://api.scryfall.com"
NAMED = f"{API}/cards/named?exact=Sol%20Ring"
CARD = f"{API}/cards/0c082aa8-bf7f-47f2-baf8-43ad253fd7d7"
SLOW_URLS = (NAMED, f"{API}/cards/search?q=t%3Aelf", f"{API}/cards/random",
             f"{API}/cards/collection")
FAST_URLS = (CARD, f"{CARD}/rulings", f"{API}/sets/fra", f"{API}/cards/autocomplete?q=sol")
# 2026-10-14T10:41:07Z: the time of the 429 in the brief's example.
AT_10_41_07 = datetime(2026, 10, 14, 10, 41, 7, tzinfo=timezone.utc).timestamp()
EXAMPLE = ("Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 23 s). "
           "Call again after that time.")
# The first words of the helper's text; the limiter's text follows them (DEC-1114 N5).
HELPER = "Scryfall answered HTTP 429 (too many requests): "


def answering(urls) -> FakeScryfall:
    """A FakeScryfall that answers each address in ``urls`` with an empty object."""
    fake = FakeScryfall()
    fake.pages = {url: {} for url in urls}
    return fake


def send(fake: FakeScryfall, url: str, slow=None) -> bytes:
    """One request through the limiter over the fake transport."""
    def transmit() -> bytes:
        with fake.urlopen(urllib.request.Request(url)) as resp:
            return resp.read()
    return limit.send(url, transmit, slow=slow)


def http_429(url: str = NAMED, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = email.message.Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(url, 429, "Too Many Requests", headers, io.BytesIO())


def state() -> dict:
    return json.loads((Path(limit.limit_dir()) / "state.json").read_text())


class Crash(BaseException):
    """A process that dies in the middle of a request or a write."""


class CopiesTests(unittest.TestCase):
    def test_three_copies_are_the_same_file(self):
        """Rule 9: one module, one copy in scripts/ and one in each server."""
        digests = {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ("scripts/scryfall_limit.py", *SERVER_COPIES)
        }
        self.assertEqual(len(set(digests.values())), 1, digests)

    def test_ci_starts_on_a_change_to_a_server_copy(self):
        """Rule 9: both paths lists of python-tests.yml name both server copies."""
        workflow = (ROOT / ".github" / "workflows" / "python-tests.yml").read_text()
        for path in SERVER_COPIES:
            with self.subTest(path=path):
                self.assertEqual(workflow.count(f"      - '{path}'\n"), 2)

    def test_servers_and_scripts_share_one_folder_and_one_cache(self):
        """Rule 10: .mcp.json gives both servers the scripts' default folder and one cache."""
        servers = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
        self.assertEqual(servers["scryfall"]["env"], {
            "XDG_CACHE_HOME": "/Users/dpires/.cache", "SCRYFALL_LIMIT_DIR": limit.DEFAULT_DIR})
        self.assertEqual(servers["archidekt"]["env"], {"SCRYFALL_LIMIT_DIR": limit.DEFAULT_DIR})
        self.assertEqual(limit.DEFAULT_DIR, "/tmp/scryfall-limit")


class FolderTests(unittest.TestCase):
    def test_folder_comes_from_the_environment(self):
        with mock.patch.dict("os.environ", {"SCRYFALL_LIMIT_DIR": "/somewhere/else"}):
            self.assertEqual(limit.limit_dir(), "/somewhere/else")
            os.environ["SCRYFALL_LIMIT_DIR"] = ""
            self.assertEqual(limit.limit_dir(), "/tmp/scryfall-limit")
            del os.environ["SCRYFALL_LIMIT_DIR"]
            self.assertEqual(limit.limit_dir(), "/tmp/scryfall-limit")

    def test_send_makes_the_folder_and_holds_the_lock_while_it_sends(self):
        """Rule 1: an exclusive flock on <dir>/state.lock from the read to the write."""
        fake = answering([NAMED])
        with tempfile.TemporaryDirectory() as tmp, fake.clock():
            folder = Path(tmp) / "new" / "folder"
            locked = []

            def transmit() -> bytes:
                with open(folder / "state.lock") as other:
                    try:
                        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        locked.append(False)
                    except BlockingIOError:
                        locked.append(True)
                return b"{}"

            with mock.patch.dict("os.environ", {"SCRYFALL_LIMIT_DIR": str(folder)}):
                limit.send(NAMED, transmit)
                with open(folder / "state.lock") as other:
                    # Released: a second lock is free at once.
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertEqual(sorted(p.name for p in folder.iterdir()),
                                 ["state.json", "state.lock"])
            self.assertEqual(locked, [True])


class WaitTests(unittest.TestCase):
    """Rule 2: each wait counts from the end of the last answer, from any process."""

    def test_first_request_starts_at_once(self):
        fake = answering([NAMED])
        with fake.clock():
            send(fake, NAMED)
        self.assertEqual(fake.sleeps, [])

    def test_each_class_waits_its_interval(self):
        for urls, interval in ((SLOW_URLS, 0.6), (FAST_URLS, 0.1)):
            for url in urls:
                with self.subTest(url=url):
                    fake = answering([url])
                    with fake.clock():
                        for _ in range(3):
                            send(fake, url)
                    self.assertEqual(len(fake.gaps()), 2)
                    for gap in fake.gaps():
                        self.assertAlmostEqual(gap, interval, places=9)

    def test_slow_request_waits_for_the_last_answer_of_its_class(self):
        """A /cards/:id answer between two /cards/named does not reset their 600 ms."""
        fake = answering([NAMED, CARD])
        with fake.clock():
            for url in (NAMED, CARD, NAMED):
                send(fake, url)
        first, card, second = fake.sent
        self.assertAlmostEqual(card.started - first.answered, 0.1, places=9)
        self.assertAlmostEqual(second.started - first.answered, 0.6, places=9)
        self.assertAlmostEqual(second.started - card.answered, 0.25, places=9)

    def test_slow_request_waits_100ms_after_a_late_fast_answer(self):
        """The 100 ms after any answer holds when the 600 ms have passed."""
        fake = answering([NAMED, CARD])
        with fake.clock():
            send(fake, NAMED)
            fake.now += 0.5
            send(fake, CARD)
            send(fake, NAMED)
        self.assertAlmostEqual(fake.gaps()[1], 0.1, places=9)

    def test_slow_argument_overrides_the_address(self):
        """The helper sends every request as the 2-a-second class (slow=True)."""
        for url, slow, interval in ((CARD, True, 0.6), (NAMED, False, 0.1)):
            with self.subTest(url=url, slow=slow):
                fake = answering([url])
                with fake.clock():
                    send(fake, url, slow=slow)
                    send(fake, url, slow=slow)
                self.assertAlmostEqual(fake.gaps()[0], interval, places=9)

    def test_failed_request_counts_as_an_answer(self):
        failures = ((500, urllib.error.HTTPError),
                    (urllib.error.URLError("connection refused"), urllib.error.URLError),
                    (TimeoutError("The read operation timed out"), TimeoutError))
        for failure, error in failures:
            with self.subTest(failure=failure):
                fake = answering([NAMED])
                fake.failures[0] = failure
                with fake.clock():
                    with self.assertRaises(error):
                        send(fake, NAMED)
                    self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": fake.now})
                    send(fake, NAMED)
                self.assertAlmostEqual(fake.gaps()[0], 0.6, places=9)

    def test_interrupted_request_counts_as_an_answer(self):
        fake = answering([NAMED])

        def transmit():
            fake.now += 0.25
            raise Crash()

        with fake.clock():
            with self.assertRaises(Crash):
                limit.send(NAMED, transmit)
            self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": fake.now})

    def test_wait_reads_the_times_that_another_process_wrote(self):
        fake = answering([NAMED])
        fake.state = {"last_answer": fake.now - 0.2, "last_slow_answer": fake.now - 0.2}
        with fake.clock():
            send(fake, NAMED)
        self.assertEqual(len(fake.sleeps), 1)
        self.assertAlmostEqual(fake.sleeps[0], 0.4, places=9)

    def test_wait_ends_by_the_clock_when_a_sleep_returns_early(self):
        fake = answering([NAMED])
        asked = []

        def sleep(seconds):
            asked.append(seconds)
            fake.now += seconds / 2 if len(asked) == 1 else seconds

        fake.sleep = sleep
        with fake.clock():
            send(fake, NAMED)
            send(fake, NAMED)
        self.assertEqual(len(asked), 2)
        self.assertAlmostEqual(fake.gaps()[0], 0.6, places=9)

    def test_times_are_written_after_each_answer(self):
        fake = answering([NAMED, CARD])
        with fake.clock():
            send(fake, NAMED)
            self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": fake.now})
            slow_answer = fake.now
            send(fake, CARD)
            self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": slow_answer})


class StopTests(unittest.TestCase):
    """Rules 3 and 4: a 429 stops every caller; a call during the stop fails at once."""

    def stopped_fake(self, retry_after=None) -> FakeScryfall:
        """A fake whose first request answers 429 at exactly 10:41:07Z."""
        fake = answering([NAMED, CARD])
        fake.now = AT_10_41_07 - fake.LATENCY
        fake.failures[0] = http_429(retry_after=retry_after)
        return fake

    def test_429_starts_a_30s_stop_and_is_not_retried(self):
        fake = self.stopped_fake()
        with fake.clock():
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
            self.assertEqual(state()["blocked_at"], AT_10_41_07)
            self.assertEqual(state()["blocked_until"], AT_10_41_07 + 30)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(fake.sleeps, [])
        self.assertEqual(str(raised.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 30 s). "
            "Call again after that time."))
        self.assertIsInstance(raised.exception.__cause__, urllib.error.HTTPError)

    def test_call_during_the_stop_fails_at_once_with_the_end_of_the_stop(self):
        for url in (NAMED, CARD):
            with self.subTest(url=url):
                fake = self.stopped_fake()
                with fake.clock():
                    with self.assertRaises(limit.Stopped):
                        send(fake, NAMED)
                    fake.now = AT_10_41_07 + 7
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, url)
                self.assertEqual(str(raised.exception), EXAMPLE)
                self.assertEqual(raised.exception.until, AT_10_41_07 + 30)
                self.assertEqual(len(fake.sent), 1)
                self.assertEqual(fake.sleeps, [])

    def test_request_goes_out_when_the_stop_ends(self):
        fake = self.stopped_fake()
        with fake.clock():
            with self.assertRaises(limit.Stopped):
                send(fake, NAMED)
            fake.now = AT_10_41_07 + 29.999
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
            self.assertIn("(in 1 s)", str(raised.exception))
            fake.now = AT_10_41_07 + 30
            send(fake, NAMED)
        self.assertEqual(len(fake.sent), 2)
        self.assertEqual(fake.sleeps, [])

    def test_stop_in_the_state_file_stops_this_process(self):
        """A stop that another process wrote."""
        fake = answering([NAMED])
        fake.now = AT_10_41_07 + 7
        fake.state = {"blocked_at": AT_10_41_07, "blocked_until": AT_10_41_07 + 30,
                      "last_answer": AT_10_41_07, "last_slow_answer": AT_10_41_07}
        with fake.clock():
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
        self.assertEqual(str(raised.exception), EXAMPLE)
        self.assertEqual(fake.sent, [])
        self.assertEqual(fake.sleeps, [])

    def test_stop_without_its_start_counts_as_30s_long(self):
        """A hand-written state.json that holds blocked_until alone."""
        fake = answering([NAMED])
        fake.now = AT_10_41_07 + 7
        fake.state = {"blocked_until": AT_10_41_07 + 30}
        with fake.clock():
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
            self.assertEqual(state(), {"blocked_until": AT_10_41_07 + 30})
        self.assertEqual(str(raised.exception), EXAMPLE)
        self.assertEqual(fake.sent, [])

    def test_retry_after_sets_a_longer_stop(self):
        answered = AT_10_41_07
        cases = {
            "60": 60, "10": 30, " 45 ": 45, "-5": 30, "soon": 30, "1.5": 30, "1e2": 30,
            email.utils.formatdate(answered + 90, usegmt=True): 90,
            email.utils.formatdate(answered - 90, usegmt=True): 30,
        }
        for value, length in cases.items():
            with self.subTest(retry_after=value):
                fake = self.stopped_fake(retry_after=value)
                with fake.clock():
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertEqual(state()["blocked_until"], answered + length)
                self.assertIn(f"(in {length} s)", str(raised.exception))

    def test_5xx_starts_no_stop(self):
        for code in (500, 502, 503):
            with self.subTest(code=code):
                fake = answering([NAMED])
                fake.failures[0] = code
                with fake.clock():
                    with self.assertRaises(urllib.error.HTTPError) as raised:
                        send(fake, NAMED)
                    self.assertNotIn("blocked_until", state())
                    send(fake, NAMED)
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(len(fake.sent), 2)

    def test_end_of_the_stop_is_rounded_up_to_the_second(self):
        """A 429 at 10:41:07.4Z: no request until 10:41:38Z, and the 429 call says 30 s."""
        fake = self.stopped_fake()
        fake.now += 0.4
        with fake.clock():
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
        self.assertEqual(str(raised.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:38Z (in 30 s). "
            "Call again after that time."))


class TimeOfThe429Tests(unittest.TestCase):
    def test_429_at_a_fraction_over_one_half_names_the_second_it_came(self):
        now = {"t": AT_10_41_07 + 0.6 - 0.05}

        def transmit():
            now["t"] += 0.05
            raise urllib.error.HTTPError(NAMED, 429, "Too Many Requests", email.message.Message(), io.BytesIO())

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.dict(os.environ, {"SCRYFALL_LIMIT_DIR": folder}), \
                mock.patch("time.time", lambda: now["t"]), mock.patch("time.monotonic", lambda: now["t"]), \
                mock.patch("time.sleep", lambda s: None):
            with self.assertRaises(limit.Stopped) as raised:
                limit.send(NAMED, transmit)
            now["t"] = AT_10_41_07 + 7.6
            with self.assertRaises(limit.Stopped) as later:
                limit.send(NAMED, lambda: b"{}")
        print(f"\n  the 429 call: {raised.exception}\n  a call 7 s later: {later.exception}")
        self.assertEqual(str(raised.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:38Z (in 30 s). "
            "Call again after that time."))
        self.assertEqual(str(later.exception), (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:38Z (in 23 s). "
            "Call again after that time."))


class StopTextTests(unittest.TestCase):
    def test_times_are_utc_in_any_local_zone(self):
        old = os.environ.get("TZ")
        os.environ["TZ"] = "Asia/Tokyo"
        time.tzset()
        try:
            text = str(limit.Stopped(AT_10_41_07, AT_10_41_07 + 30, AT_10_41_07 + 7))
        finally:
            if old is None:
                del os.environ["TZ"]
            else:
                os.environ["TZ"] = old
            time.tzset()
        self.assertEqual(text, EXAMPLE)


class OffsetClock(FakeScryfall):
    """time.time() reads ``offset`` seconds ahead of time.monotonic(), as on a real machine."""

    def __init__(self, cards=()):
        super().__init__(cards)
        self.offset = 1_000_000.0

    def time(self) -> float:
        return self.now + self.offset


class WallClockTests(unittest.TestCase):
    """Rule 1: the state holds wall-clock times; the sleep of one wait runs on the monotonic clock."""

    def offset_fake(self) -> OffsetClock:
        fake = OffsetClock()
        fake.pages = {NAMED: {}}
        return fake

    def test_state_holds_wall_clock_times(self):
        fake = self.offset_fake()
        with fake.clock():
            send(fake, NAMED)
            self.assertEqual(state(), {"last_answer": fake.time(), "last_slow_answer": fake.time()})

    def test_wait_reads_the_wall_clock(self):
        fake = self.offset_fake()
        fake.state = {"last_answer": fake.time() - 0.2, "last_slow_answer": fake.time() - 0.2}
        with fake.clock():
            send(fake, NAMED)
        self.assertEqual(len(fake.sleeps), 1)
        self.assertAlmostEqual(fake.sleeps[0], 0.4, places=6)

    def test_stop_reads_the_wall_clock(self):
        fake = self.offset_fake()
        fake.state = {"blocked_at": fake.time() - 5, "blocked_until": fake.time() + 25}
        with fake.clock():
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
            fake.now += 25
            send(fake, NAMED)
        self.assertIn("(in 25 s)", str(raised.exception))
        self.assertEqual(len(fake.sent), 1)

    def test_wait_ignores_a_wall_clock_step_during_the_sleep(self):
        fake = self.offset_fake()
        steps = []

        def sleep(seconds):
            if not steps:
                steps.append(seconds)
                fake.offset -= 3600
            fake.sleeps.append(seconds)
            fake.now += seconds

        fake.sleep = sleep
        with fake.clock():
            send(fake, NAMED)
            send(fake, NAMED)
        self.assertEqual(len(fake.sleeps), 1)
        self.assertAlmostEqual(fake.sleeps[0], 0.6, places=6)


class ClockStepTests(unittest.TestCase):
    """Rule 13 (DEC-1093 N6): a clock that steps back makes no wait and no stop longer."""

    STEP = 3600.0

    def test_wait_is_capped_at_its_class_interval(self):
        for url, interval in ((NAMED, 0.6), (CARD, 0.1)):
            with self.subTest(url=url):
                fake = answering([url])
                with fake.clock():
                    send(fake, url)
                    fake.now -= self.STEP
                    send(fake, url)
                    send(fake, url)
                self.assertEqual(len(fake.sleeps), 2)
                for slept in fake.sleeps:
                    self.assertAlmostEqual(slept, interval, places=9)

    def test_time_left_in_a_stop_is_capped_at_its_length(self):
        for retry_after, length in ((None, 30), ("60", 60)):
            with self.subTest(length=length):
                fake = answering([NAMED])
                fake.now = AT_10_41_07 - fake.LATENCY
                fake.failures[0] = http_429(retry_after=retry_after)
                with fake.clock():
                    with self.assertRaises(limit.Stopped):
                        send(fake, NAMED)
                    fake.now = AT_10_41_07 + 5 - self.STEP
                    stepped = fake.now
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertIn(f"(in {length} s)", str(raised.exception))
                    self.assertEqual(state()["blocked_until"], stepped + length)
                    fake.now = stepped + length - 0.5
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertIn("(in 1 s)", str(raised.exception))
                    fake.now = stepped + length
                    send(fake, NAMED)
                self.assertEqual(len(fake.sent), 2)
                # The 429's answer still reads as later than now: one wait, capped at 600 ms.
                self.assertEqual(len(fake.sleeps), 1)
                self.assertAlmostEqual(fake.sleeps[0], 0.6, places=6)

    def test_step_back_after_the_stop_has_ended_starts_no_stop(self):
        """DEC-1114 N2: a 429 at 10:41:07Z, a request 70 s after the stop's end, then the clock
        steps back 1 h. The first answer after the stop removes the stop from the state, also a
        failed answer, so the next request goes out."""
        for after in (None, 500):
            with self.subTest(answer_after_the_stop=after or "200"):
                fake = answering([NAMED])
                fake.now = AT_10_41_07 - fake.LATENCY
                fake.failures[0] = http_429()
                if after is not None:
                    fake.failures[1] = after
                with fake.clock():
                    with self.assertRaises(limit.Stopped):
                        send(fake, NAMED)
                    fake.now = AT_10_41_07 + 100
                    with contextlib.suppress(urllib.error.HTTPError):
                        send(fake, NAMED)
                    self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": fake.now})
                    fake.now -= self.STEP
                    send(fake, NAMED)
                self.assertEqual(len(fake.sent), 3)


class LongStopTests(unittest.TestCase):
    """DEC-1114 N4: no stop lasts longer than 3600 s. A longer Retry-After, or a longer stop in
    a hand-written state.json, counts as 3600 s, and the text names the capped end."""

    CAPPED = ("Scryfall answered HTTP 429 at 10:41:07Z. No request until 11:41:07Z (in {} s). "
              "Call again after that time.")

    def assert_stop_ends_at_11_41_07(self, fake: FakeScryfall):
        """In the fake's clock block: a call at 10:41:14Z, one 0.5 s before 11:41:07Z, and one
        at 11:41:07Z, which goes out."""
        fake.now = AT_10_41_07 + 7
        with self.assertRaises(limit.Stopped) as raised:
            send(fake, NAMED)
        self.assertEqual(str(raised.exception), self.CAPPED.format(3593))
        fake.now = AT_10_41_07 + 3599.5
        with self.assertRaises(limit.Stopped) as raised:
            send(fake, NAMED)
        self.assertIn("(in 1 s)", str(raised.exception))
        fake.now = AT_10_41_07 + 3600
        send(fake, NAMED)

    def test_retry_after_longer_than_3600s_counts_as_3600s(self):
        two_hours = email.utils.formatdate(AT_10_41_07 + 7200, usegmt=True)
        for value in ("3601", "99999999999999999999", "9" * 400, two_hours):
            with self.subTest(retry_after=value[:24]):
                fake = answering([NAMED])
                fake.now = AT_10_41_07 - fake.LATENCY
                fake.failures[0] = http_429(retry_after=value)
                with fake.clock():
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertEqual(state()["blocked_until"], AT_10_41_07 + 3600)
                    self.assertEqual(str(raised.exception), self.CAPPED.format(3600))
                    self.assert_stop_ends_at_11_41_07(fake)
                self.assertEqual(len(fake.sent), 2)

    def test_retry_after_up_to_3600s_is_kept(self):
        for value, length in (("3599", 3599), ("3600", 3600), ("-" + "9" * 400, 30)):
            with self.subTest(retry_after=value[:24]):
                fake = answering([NAMED])
                fake.now = AT_10_41_07 - fake.LATENCY
                fake.failures[0] = http_429(retry_after=value)
                with fake.clock():
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertEqual(state()["blocked_until"], AT_10_41_07 + length)
                self.assertIn(f"(in {length} s)", str(raised.exception))

    def test_hand_written_stop_longer_than_3600s_after_its_start(self):
        for until in (AT_10_41_07 + 3601, AT_10_41_07 + 1e20):
            with self.subTest(until=until):
                fake = answering([NAMED])
                fake.state = {"blocked_at": AT_10_41_07, "blocked_until": until}
                with fake.clock():
                    self.assert_stop_ends_at_11_41_07(fake)
                self.assertEqual(len(fake.sent), 1)

    def test_hand_written_stop_that_started_more_than_3600s_ago_has_ended(self):
        fake = answering([NAMED])
        fake.now = AT_10_41_07 + 7
        fake.state = {"blocked_at": AT_10_41_07 - 3600, "blocked_until": AT_10_41_07 + 30}
        with fake.clock():
            send(fake, NAMED)
        self.assertEqual(len(fake.sent), 1)

    def test_hand_written_stop_without_its_start_more_than_3600s_ahead(self):
        """Capped at now plus 3600 s, it counts as 30 s long and moves to start now (rule 4)."""
        for until in (AT_10_41_07 + 7 + 3601, 1e20):
            with self.subTest(until=until):
                fake = answering([NAMED])
                fake.now = AT_10_41_07 + 7
                fake.state = {"blocked_until": until}
                with fake.clock():
                    with self.assertRaises(limit.Stopped) as raised:
                        send(fake, NAMED)
                    self.assertEqual(state(), {"blocked_at": AT_10_41_07 + 7,
                                               "blocked_until": AT_10_41_07 + 37})
                    fake.now = AT_10_41_07 + 37
                    send(fake, NAMED)
                self.assertEqual(str(raised.exception), (
                    "Scryfall answered HTTP 429 at 10:41:14Z. No request until 10:41:44Z (in 30 s). "
                    "Call again after that time."))
                self.assertEqual(len(fake.sent), 1)


class StateFileTests(unittest.TestCase):
    def test_missing_or_unreadable_state_counts_as_empty(self):
        for text in (None, "", "{not json", "[1, 2]", '"last_answer"', "7",
                     '{"blocked_until": "soon", "last_answer": 1e300}',
                     '{"last_answer": null}', '{"last_slow_answer": {"a": 1}}'):
            with self.subTest(state=text):
                fake = answering([NAMED])
                with fake.clock():
                    if text is not None:
                        (Path(limit.limit_dir()) / "state.json").write_text(text)
                    send(fake, NAMED)
                    self.assertEqual(state(), {"last_answer": fake.now, "last_slow_answer": fake.now})
                self.assertEqual(fake.sleeps, [])

    def test_crash_in_a_write_keeps_the_stop(self):
        """Rule 1's change: the stop moves to the new clock through a temporary file.

        A process dies in the middle of that write: state.json still holds the old stop, and
        no temporary file stays behind.
        """
        fake = answering([NAMED])
        fake.now = AT_10_41_07 - fake.LATENCY
        fake.failures[0] = http_429()

        during = []

        def half_then_crash(obj, handle, **kwargs):
            handle.write(json.dumps(obj)[:10])
            handle.flush()
            during.append(sorted(p.name for p in Path(limit.limit_dir()).iterdir()))
            raise Crash()

        with fake.clock():
            with self.assertRaises(limit.Stopped):
                send(fake, NAMED)
            before = (Path(limit.limit_dir()) / "state.json").read_text()
            fake.now -= 3600
            with mock.patch("json.dump", half_then_crash), self.assertRaises(Crash):
                send(fake, NAMED)
            self.assertEqual((Path(limit.limit_dir()) / "state.json").read_text(), before)
            # The half-written file was a temporary file in <dir>, and it is gone.
            [names] = during
            temporary = [name for name in names if name not in ("state.json", "state.lock")]
            self.assertEqual(len(names), 3)
            self.assertRegex(temporary[0], r"^state\..+\.tmp$")
            self.assertEqual(sorted(p.name for p in Path(limit.limit_dir()).iterdir()),
                             ["state.json", "state.lock"])
            with self.assertRaises(limit.Stopped):
                send(fake, NAMED)
        self.assertEqual(len(fake.sent), 1)


class HelperTests(unittest.TestCase):
    """Rule 8: the scripts' helper sends through the same state."""

    def test_helper_429_stops_every_other_caller(self):
        fake = answering([NAMED])
        fake.now = AT_10_41_07 - fake.LATENCY
        fake.failures[0] = 429
        with fake.installed():
            with self.assertRaises(scryfall_api.ScryfallRateLimited) as helper:
                scryfall_api.request(NAMED)
            fake.now = AT_10_41_07 + 7
            with self.assertRaises(limit.Stopped) as raised:
                send(fake, NAMED)
        self.assertEqual(str(helper.exception), HELPER + (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 30 s). "
            "Call again after that time."))
        self.assertEqual(str(raised.exception), EXAMPLE)
        self.assertEqual(len(fake.sent), 1)

    def test_stop_from_another_caller_ends_the_helper(self):
        fake = answering([NAMED])
        fake.now = AT_10_41_07 + 7
        fake.state = {"blocked_at": AT_10_41_07, "blocked_until": AT_10_41_07 + 30}
        with fake.installed():
            with self.assertRaises(scryfall_api.ScryfallRateLimited) as raised:
                scryfall_api.request(NAMED)
            # From then on this process sends nothing, also after the stop.
            fake.now = AT_10_41_07 + 60
            with self.assertRaises(scryfall_api.ScryfallRateLimited) as later:
                scryfall_api.request(NAMED)
        # DEC-1114 N5: the text names the end of the stop, also at the later call.
        self.assertEqual(str(raised.exception), HELPER + EXAMPLE)
        self.assertEqual(str(later.exception), HELPER + EXAMPLE)
        self.assertIsInstance(raised.exception.__cause__, limit.Stopped)
        self.assertEqual(fake.sent, [])
        self.assertEqual(fake.sleeps, [])


class ScriptStopTests(DeckDirCase):
    """Rule 8: a stop in the state ends each script as its own 429 does: exit code 1, the
    text on screen, no file written, no request.

    DEC-1114 N5: the text names the end of a 120 s stop. N3: the two bulk-data scripts too.
    """

    TEXT = HELPER + ("Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:43:07Z "
                     "(in 113 s). Call again after that time.")

    def stopped(self, fake: FakeScryfall) -> FakeScryfall:
        """A stop of 120 s that another process's 429 started at 10:41:07Z, 7 s ago."""
        fake.now = AT_10_41_07 + 7
        fake.state = {"blocked_at": AT_10_41_07, "blocked_until": AT_10_41_07 + 120}
        return fake

    def assert_stopped(self, code, out, fake):
        self.assertEqual(code, 1)
        self.assertIn(self.TEXT, out)
        self.assertEqual(fake.sent, [])
        self.assertEqual(fake.sleeps, [])

    def test_fetch_card_metadata(self):
        self.write_deck("one", "Sol Ring")
        fake = self.stopped(FakeScryfall([make_card("Sol Ring")]))
        code, out = self.run_metadata(fake)
        self.assert_stopped(code, out, fake)
        self.assert_no_file_written()

    def test_fetch_card_images(self):
        self.write_deck("one", "Sol Ring")
        images = self.root / "images"
        fake = self.stopped(FakeScryfall([make_card("Sol Ring")]))
        out = io.StringIO()
        with fake.installed(), \
                mock.patch.object(fetch_images, "COMMANDERS_DIR", self.commanders), \
                mock.patch.object(fetch_images, "IMAGES_DIR", images), \
                contextlib.redirect_stdout(out):
            code = fetch_images.main()
        self.assert_stopped(code, out.getvalue(), fake)
        self.assertFalse(images.exists())

    def test_compute_tokens(self):
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        path = case.write_deck("one", "Goblin Maker")
        before = path.read_text()
        fake = self.stopped(callers.token_fake())
        code, out = case.run_main(fake)
        self.assert_stopped(code, out, fake)
        self.assertEqual(path.read_text(), before)

    def test_check_game_changers(self):
        fake = self.stopped(callers.gc_fake(1))
        out = io.StringIO()
        with fake.installed(), mock.patch("sys.argv", ["check_game_changers.py"]), \
                contextlib.redirect_stdout(out):
            code = callers.check_gc.main()
        self.assert_stopped(code, out.getvalue(), fake)

    def test_dump_set(self):
        case = callers.DumpSetTests("test_requests_start_600ms_after_the_last_answer")
        case.setUp()
        self.addCleanup(case.doCleanups)
        fake = self.stopped(callers.set_fake())
        code, out = case.run_main(fake)
        self.assert_stopped(code, out, fake)
        self.assertFalse(case.out_dir.exists())

    def test_format_owned_list(self):
        case = callers.FormatOwnedListTests("test_batches_start_600ms_after_the_last_answer")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.write_owned(case.owned, ["Sol Ring"])
        fake = self.stopped(FakeScryfall([make_card("Sol Ring")]))
        code, out = case.run_main(fake)
        self.assert_stopped(code, out, fake)
        self.assertFalse(case.formatted.exists())

    def test_build_price_index(self):
        case = callers.BuildPriceIndexTests("test_429_on_bulk_data_ends_the_run")
        case.setUp()
        self.addCleanup(case.doCleanups)
        fake = self.stopped(callers.bulk_fake())
        code, out = case.run_main(fake)
        self.assert_stopped(code, out, fake)
        self.assertEqual(case.written(), [])

    def test_refresh_scryfall_mirror(self):
        case = callers.RefreshScryfallMirrorTests("test_429_on_bulk_data_ends_the_run")
        case.setUp()
        self.addCleanup(case.doCleanups)
        fake = self.stopped(callers.bulk_fake())
        code, out = case.run_main(fake)
        self.assert_stopped(code, out, fake)
        self.assertEqual(case.written(), [])


# ------------------------------------------------------------- across processes
# Rule 11: real processes on one temporary lock folder, with the real clock. The functions
# below run in the child processes.

LATENCY = 0.05


def _child_sends(folder, url, count, start, results):
    """Send ``count`` requests; put (pid, start, end) of each request on ``results``."""
    os.environ["SCRYFALL_LIMIT_DIR"] = folder
    start.wait(30)
    for _ in range(count):
        def transmit() -> bytes:
            began = time.time()
            time.sleep(LATENCY)
            results.put((os.getpid(), began, time.time()))
            return b"{}"
        limit.send(url, transmit)


def _child_gets_a_429(folder, results):
    os.environ["SCRYFALL_LIMIT_DIR"] = folder

    def transmit() -> bytes:
        raise http_429()

    try:
        limit.send(NAMED, transmit)
    except limit.Stopped as e:
        results.put(e.until)


def _child_tries(folder, clock, results):
    """Send one request with time.time() at ``clock`` (None: the real clock)."""
    os.environ["SCRYFALL_LIMIT_DIR"] = folder
    sent = []
    patch = mock.patch("time.time", lambda: clock) if clock is not None else contextlib.nullcontext()
    with patch:
        try:
            limit.send(NAMED, lambda: sent.append(NAMED) or b"{}")
            results.put(("sent", len(sent), ""))
        except limit.Stopped as e:
            results.put(("stopped", len(sent), str(e)))


class CrossProcessTests(unittest.TestCase):
    """The log of each case goes to stdout (``pytest -s`` shows it)."""

    def setUp(self):
        self.context = multiprocessing.get_context("spawn")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = tmp.name

    def run_child(self, target, *args, timeout=60):
        process = self.context.Process(target=target, args=args)
        process.start()
        process.join(timeout)
        self.assertEqual(process.exitcode, 0)

    def sends_from_two_processes(self, url: str, count: int = 3) -> list:
        start, results = self.context.Event(), self.context.Queue()
        processes = [self.context.Process(target=_child_sends,
                                          args=(self.folder, url, count, start, results))
                     for _ in range(2)]
        for process in processes:
            process.start()
        start.set()
        sent = [results.get(timeout=60) for _ in range(2 * count)]
        for process in processes:
            process.join(60)
            self.assertEqual(process.exitcode, 0)
        sent.sort(key=lambda row: row[1])
        print(f"\n{url}")
        for (pid, began, ended), (_, next_began, _) in zip(sent, sent[1:] + [(0, None, 0)]):
            gap = "" if next_began is None else f"  gap to next start {next_began - ended:.4f} s"
            print(f"  pid {pid}  start {began:.4f}  end {ended:.4f}{gap}")
        return sent

    def assert_gaps(self, sent: list, interval: float):
        self.assertEqual(len({pid for pid, _, _ in sent}), 2)
        for (_, _, ended), (_, began, _) in zip(sent, sent[1:]):
            # 2 ms for the drift between the wall clock and the monotonic clock of the sleep.
            self.assertGreaterEqual(began - ended, interval - 0.002)

    def test_600ms_wait_holds_across_two_processes(self):
        self.assert_gaps(self.sends_from_two_processes(NAMED), 0.6)

    def test_100ms_wait_holds_across_two_processes(self):
        self.assert_gaps(self.sends_from_two_processes(CARD), 0.1)

    def test_429_in_one_process_stops_the_other_until_blocked_until(self):
        results = self.context.Queue()
        self.run_child(_child_gets_a_429, self.folder, results)
        until = results.get(timeout=10)
        tries = {}
        for label, clock in (("now", None), ("0.5 s before blocked_until", until - 0.5),
                             ("at blocked_until", until)):
            self.run_child(_child_tries, self.folder, clock, results)
            tries[label] = results.get(timeout=10)
        print(f"\nblocked_until {until:.4f}")
        for label, outcome in tries.items():
            print(f"  {label}: {outcome}")
        self.assertEqual(tries["now"][:2], ("stopped", 0))
        self.assertEqual(tries["0.5 s before blocked_until"],
                         ("stopped", 0, tries["0.5 s before blocked_until"][2]))
        self.assertIn("(in 1 s)", tries["0.5 s before blocked_until"][2])
        self.assertEqual(tries["at blocked_until"], ("sent", 1, ""))


class TwoThreadsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.old = os.environ.get("SCRYFALL_LIMIT_DIR")
        os.environ["SCRYFALL_LIMIT_DIR"] = tmp.name
        self.addCleanup(self.restore)

    def restore(self):
        if self.old is None:
            os.environ.pop("SCRYFALL_LIMIT_DIR", None)
        else:
            os.environ["SCRYFALL_LIMIT_DIR"] = self.old

    def sends_from_two_threads(self, url, count=3):
        sent, lock, start = [], threading.Lock(), threading.Event()

        def worker():
            start.wait(10)
            for _ in range(count):
                def transmit():
                    began = time.time()
                    time.sleep(LATENCY)
                    with lock:
                        sent.append((threading.get_ident(), began, time.time()))
                    return b"{}"
                limit.send(url, transmit)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        start.set()
        for thread in threads:
            thread.join(30)
        sent.sort(key=lambda row: row[1])
        print(f"\n{url} ({limit.__file__})")
        for (ident, began, ended), nxt in zip(sent, sent[1:] + [None]):
            gap = "" if nxt is None else f"  gap to next start {nxt[1] - ended:.4f} s"
            print(f"  thread {ident % 100000:05d}  start {began:.4f}  end {ended:.4f}{gap}")
        return sent

    def assert_gaps(self, sent, interval):
        self.assertEqual(len(sent), 6)
        self.assertEqual(len({ident for ident, _, _ in sent}), 2)
        for (_, _, ended), (_, began, _) in zip(sent, sent[1:]):
            # 2 ms for the drift between the wall clock and the monotonic clock of the sleep.
            self.assertGreaterEqual(began - ended, interval - 0.002)

    def test_600ms_wait_holds_across_two_threads(self):
        self.assert_gaps(self.sends_from_two_threads(NAMED), 0.6)

    def test_100ms_wait_holds_across_two_threads(self):
        self.assert_gaps(self.sends_from_two_threads(CARD), 0.1)


if __name__ == "__main__":
    unittest.main()

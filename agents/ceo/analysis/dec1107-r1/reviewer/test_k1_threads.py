"""DEC-1107 K1 kill case: two threads of one process keep the waits of rule 2.

The card tools run each call in asyncio.to_thread, so two calls of one server reach send()
from two threads. Each request sleeps 50 ms of real time inside transmit(); the case sorts the
requests by start and checks each gap from the end of one answer to the start of the next.
It reads the module from KILL_TREE (default: the review tree) and uses a temporary
SCRYFALL_LIMIT_DIR, so it never touches /tmp/scryfall-limit. Nothing leaves the machine.
"""

import os
import sys
import tempfile
import threading
import time
import unittest

TREE = os.environ.get("KILL_TREE",
                      "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1107-review")
sys.path.insert(0, os.path.join(TREE, "scripts"))
import scryfall_limit as limit  # noqa: E402

API = "https://api.scryfall.com"
NAMED = f"{API}/cards/named?exact=Sol%20Ring"
CARD = f"{API}/cards/0c082aa8-bf7f-47f2-baf8-43ad253fd7d7"
LATENCY = 0.05


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

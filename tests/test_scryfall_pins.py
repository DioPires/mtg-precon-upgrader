"""Cases that pin what the Scryfall callers send.

The review of PR #30 (DEC-1093) found six mutants that the other Scryfall test files let
pass. Each case here kills one of them, and its docstring names the mutant.
"""

import contextlib
import io
import shutil
import unittest
from unittest import mock

from tests.test_scryfall_fetch import (
    COLLECTION_URL, DeckDirCase, FakeResponse, FakeScryfall, fetch_images, make_card, scryfall_api)
from tests import test_scryfall_callers as callers


class HostKill(unittest.TestCase):
    def test_helper_refuses_every_host_but_api_scryfall_com(self):
        """S1: the host check accepts any host that ends with scryfall.com."""
        for url in ("https://scryfall.com/cards/collection",
                    "https://www.scryfall.com/cards/search?q=x",
                    "https://evilscryfall.com/cards/collection"):
            with self.subTest(url=url):
                fake = FakeScryfall()
                with fake.installed():
                    with self.assertRaises(ValueError):
                        scryfall_api.request(url)
                self.assertEqual(fake.sent, [])


class ResettingRead(FakeScryfall):
    """The answers to the requests in ``resets`` raise ConnectionResetError inside ``read()``."""

    def __init__(self, cards=()):
        super().__init__(cards)
        self.resets: set[int] = set()

    def urlopen(self, req, timeout=None):
        index = len(self.sent)
        answer = super().urlopen(req, timeout)
        if index not in self.resets:
            return answer

        class Resets(FakeResponse):
            def read(self):
                raise ConnectionResetError(54, "Connection reset by peer")

        return Resets(b"")


class ResetKill(DeckDirCase):
    def test_reset_inside_read_is_not_retried(self):
        """S2: ``except (URLError, OSError)`` retries a reset inside read().

        On the head a reset of the batch ends the run (exit code 1, one request, no
        download), and a reset of a download counts that download as failed (no second
        request for it).
        """
        images = self.root / "images"
        self.write_deck("one", "Sol Ring")
        for index, label in ((0, "batch"), (1, "download")):
            with self.subTest(request=label):
                shutil.rmtree(images, ignore_errors=True)
                fake = ResettingRead([make_card("Sol Ring")])
                fake.resets = {index}
                out = io.StringIO()
                with fake.installed(), \
                        mock.patch.object(fetch_images, "COMMANDERS_DIR", self.commanders), \
                        mock.patch.object(fetch_images, "IMAGES_DIR", images), \
                        contextlib.redirect_stdout(out):
                    code = fetch_images.main()
                if label == "batch":
                    self.assertEqual(code, 1)
                    self.assertIn("A batch failed: ConnectionResetError", out.getvalue())
                    self.assertEqual(len(fake.sent), 1)
                    self.assertFalse(images.exists())
                else:
                    self.assertEqual(code, 0)
                    self.assertEqual(len(fake.sent), 3)
                    self.assertNotIn("Network error", out.getvalue())
                    self.assertEqual(sorted(p.name for p in images.iterdir()), ["sol-ring-art_crop.jpg"])


def assert_gets_carry_no_body(case, fake, post_urls=()):
    """Each request that is not a /cards/collection batch goes out as a GET: no body, no Content-Type."""
    for sent in fake.sent:
        with case.subTest(url=sent.url):
            if sent.url in post_urls:
                case.assertIsNotNone(sent.body)
                continue
            case.assertIsNone(sent.body)
            case.assertNotIn("content-type", sent.headers)


class MethodKill(callers.CallerCase):
    def test_compute_tokens_sends_each_lookup_as_a_get(self):
        """R4: ``def _request(url, body={})`` turns every GET into a POST with an empty body."""
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.write_deck("one", "Goblin Maker", "Orc Caller", "Crown Seeker", callers.MISSPELT)
        fake = callers.token_fake()
        code, _ = case.run_main(fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.sent), 5)
        assert_gets_carry_no_body(self, fake, post_urls={COLLECTION_URL})

    def test_compute_tokens_batch_holds_each_front_face_once(self):
        """DEC-1098 item 2: the batch holds the full // name, each front face more than once,
        or the front faces out of order.

        Ten more cards make an unsorted batch differ from the sorted one in all but 1 of 13! orders.
        No // name costs a /cards/named?fuzzy= request.
        """
        case = callers.ComputeTokensTests("test_clean_run_writes_every_deck")
        case.setUp()
        self.addCleanup(case.doCleanups)
        fillers = [f"Card {n:02d}" for n in range(10)]
        case.write_deck(
            "one", "Sol Ring", callers.VALAKUT, "Grave Researcher", "Grave Researcher // Reanimate",
            *fillers)
        fake = callers.token_fake([
            make_card(callers.VALAKUT, layout="modal_dfc"),
            make_card("Grave Researcher // Reanimate", layout="adventure"),
            *(make_card(name) for name in fillers),
        ])
        code, _ = case.run_main(fake)
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent[0].body, {"identifiers": [
            {"name": name} for name in (*fillers, "Grave Researcher", "Sol Ring", "Valakut Awakening")]})
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])

    def test_check_game_changers_sends_each_page_as_a_get(self):
        """R7: ``scryfall_api.request(url, {})``: each page goes out as a POST."""
        fake = callers.gc_fake(2)
        with fake.installed():
            callers.check_gc.fetch_remote_gc_names()
        self.assertEqual(len(fake.sent), 2)
        assert_gets_carry_no_body(self, fake)

    def test_dump_set_sends_each_request_as_a_get(self):
        """R9: ``_get_json`` sends ``scryfall_api.request(url, {})``: each request goes out as a POST."""
        case = callers.DumpSetTests("test_requests_start_600ms_after_the_last_answer")
        case.setUp()
        self.addCleanup(case.doCleanups)
        fake = callers.set_fake()
        code, _ = case.run_main(fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.sent), 4)
        assert_gets_carry_no_body(self, fake)

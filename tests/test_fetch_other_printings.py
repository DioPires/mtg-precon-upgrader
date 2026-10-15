"""DEC-1079 — a price that the batch printing lacks comes from another printing.

Also N1 (the two writes) and N5 (the spelling that Scryfall returned) of the
DEC-1080 review. No test here sends a live request: FakeScryfall of
tests/test_scryfall_fetch.py stands in for ``urlopen`` and for the clock.
"""

import contextlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tests.test_scryfall_fetch import (
    COLLECTION_URL,
    STOP_TEXT,
    DeckDirCase,
    FakeScryfall,
    fetch_metadata,
    image_path,
    image_uris,
    make_card,
)

SEARCH_URL = "https://api.scryfall.com/cards/search"
NO_PRICES = {"usd": 0, "eur": 0}


def search_url(name: str, currency: str) -> str:
    """The search of the printings of ``name``, cheapest in ``currency`` first."""
    query = urllib.parse.urlencode({
        "q": f"oracleid:{make_card(name)['oracle_id']} game:paper",
        "unique": "prints",
        "order": currency,
        "dir": "asc",
    })
    return f"{SEARCH_URL}?{query}"


def printing(name: str, set_code: str, usd=None, eur=None, released="2020-01-01",
             games=("paper",), set_type="expansion", **prices) -> dict:
    """One printing of ``name``: its own image, its release date, its games, its set type
    and its prices."""
    card = make_card(name, usd=usd, eur=eur, set=set_code, released_at=released,
                     games=list(games), set_type=set_type,
                     image_uris=image_uris(f"front/p/p/{set_code}.jpg?1"))
    card["prices"].update(prices)
    return card


class PrintsScryfall(FakeScryfall):
    """FakeScryfall that also answers a search of a card's printings.

    ``prints`` maps an oracle id to the card's printings. As Scryfall did in the
    two live runs of DEC-1079, the answer keeps the printings with "paper" in
    ``games`` when the query holds ``game:paper``, and orders them by the
    non-foil price of ``order``, else the foil one, else the etched one. A
    printing without a key sorts as the lowest: with ``dir=asc`` the printings
    without a key come first and then the cheapest (run 2); without ``dir``
    the most expensive come first and the printings without a key last
    (run 1). It holds the first PAGE_SIZE, with ``has_more``. A search that
    matches nothing answers 404. The answer goes out as a raw body through
    ``failures``, so a case can still set a failure for a search.
    """

    PAGE_SIZE = 175

    def __init__(self, cards=(), prints=None):
        super().__init__(cards)
        self.prints = prints or {}

    def urlopen(self, req, timeout=None):
        index = len(self.sent)
        parts = urllib.parse.urlsplit(req.full_url)
        if parts.path == "/cards/search" and index not in self.failures:
            answer = self.search(urllib.parse.parse_qs(parts.query, strict_parsing=True))
            if answer is not None:
                self.failures[index] = json.dumps(answer).encode()
        return super().urlopen(req, timeout)

    def search(self, query: dict) -> dict | None:
        assert set(query) <= {"q", "unique", "order", "dir"}, query
        assert query["unique"] == ["prints"] and query.get("dir", ["asc"]) == ["asc"], query
        match = re.fullmatch(r"oracleid:(\S+)((?: game:paper)?)", query["q"][0])
        assert match, query
        order = query["order"][0]
        cards = [card for card in self.prints.get(match[1], [])
                 if not match[2] or "paper" in card["games"]]

        def key(card):
            for finish in (order, f"{order}_foil", f"{order}_etched"):
                value = card["prices"].get(finish)
                if value is not None:
                    return float(value)
            return None

        priced = sorted((card for card in cards if key(card) is not None),
                        key=key, reverse="dir" not in query)
        unpriced = [card for card in cards if key(card) is None]
        cards = unpriced + priced if "dir" in query else priced + unpriced
        page = cards[:self.PAGE_SIZE]
        if not page:
            return None
        return {"object": "list", "total_cards": len(cards),
                "has_more": len(cards) > len(page), "data": page}


class OtherPrintingRuleCases(DeckDirCase):
    """Item 2: for each currency by itself, the lowest non-foil price of a released paper printing."""

    def test_null_prices_take_the_lowest_non_foil_price_of_released_paper_printings(self):
        self.write_deck("one", "Sol Ring", "Blood Crypt")
        # The printing that the batch returns is not released yet, so it has no price.
        batch = make_card("Blood Crypt", usd=None, eur=None)
        prints = [
            printing("Blood Crypt", "trk", usd="0.01", eur="0.01", released="2999-01-01"),
            printing("Blood Crypt", "vma", usd="0.02", eur="0.02", games=("mtgo",)),
            printing("Blood Crypt", "fdn", usd_foil="0.03", eur_foil="0.03"),
            printing("Blood Crypt", "rna", usd="9.00", eur="7.50"),
            printing("Blood Crypt", "gtc", usd="8.50", eur="8.00"),
        ]
        fake = PrintsScryfall([make_card("Sol Ring"), batch], {batch["oracle_id"]: prints})

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [
            COLLECTION_URL,
            "https://api.scryfall.com/cards/search"
            "?q=oracleid%3Aoracle-blood-crypt+game%3Apaper&unique=prints&order=usd&dir=asc",
        ])
        metadata = json.loads(self.output.read_text())
        # usd from gtc, eur from rna; the image stays the batch printing's.
        self.assertEqual(
            {key: metadata["Blood Crypt"][key] for key in ("usd", "eur", "image")},
            {"usd": 8.5, "eur": 7.5, "image": image_path("Blood Crypt")})
        self.assertEqual((metadata["Sol Ring"]["usd"], metadata["Sol Ring"]["eur"]), (1.5, 1.2))
        self.assertIn(
            "    Blood Crypt: usd 8.5 from another printing; eur 7.5 from another printing\n", out)
        self.assertIn("Cached 2 cards. Prices from another printing: 1 usd, 1 eur.\n", out)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["prices_from_other_printing"], {"eur": 1, "usd": 1})

    def test_a_printing_of_the_run_date_counts_and_one_of_the_next_day_does_not(self):
        self.write_deck("one", "Refute")
        batch = make_card("Refute", usd=None, eur=None)
        prints = [
            printing("Refute", "aaa", usd="0.50", eur="0.40", released="2026-10-15"),
            printing("Refute", "bbb", usd="1.00", eur="0.90", released="2026-10-14"),
        ]
        fake = PrintsScryfall([batch], {batch["oracle_id"]: prints})

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 14, 23, 59, 59, tzinfo=tz)

        with mock.patch.object(fetch_metadata, "datetime", Clock):
            code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        entry = json.loads(self.output.read_text())["Refute"]
        self.assertEqual((entry["usd"], entry["eur"]), (1.0, 0.9))

    def test_a_price_that_the_batch_printing_has_stays(self):
        """Mocking Sprite has usd and no eur: the run asks for eur only."""
        self.write_deck("one", "Mocking Sprite")
        batch = make_card("Mocking Sprite", usd="0.32", eur=None)
        prints = [
            printing("Mocking Sprite", "aaa", usd="0.10", eur="0.20"),
            printing("Mocking Sprite", "bbb", usd="0.40", eur="0.15"),
        ]
        fake = PrintsScryfall([batch], {batch["oracle_id"]: prints})

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual(fake.api_requests()[1].url, search_url("Mocking Sprite", "eur"))
        self.assertEqual(len(fake.sent), 2)
        entry = json.loads(self.output.read_text())["Mocking Sprite"]
        self.assertEqual((entry["usd"], entry["eur"]), (0.32, 0.15))
        self.assertIn("    Mocking Sprite: eur 0.15 from another printing\n", out)
        self.assertIn("Prices from another printing: 0 usd, 1 eur.\n", out)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["prices_from_other_printing"], {"eur": 1, "usd": 0})

    def test_no_price_on_any_printing_keeps_null(self):
        """Foil only everywhere, and a card with no paper printing (Scryfall answers 404)."""
        self.write_deck("one", "Foil Only", "Arena Only")
        foil_only = make_card("Foil Only", usd=None, eur=None)
        arena_only = make_card("Arena Only", usd=None, eur=None)
        prints = {
            foil_only["oracle_id"]: [
                printing("Foil Only", "aaa", usd_foil="3.00", usd_etched="4.00", eur_foil="2.50")],
            arena_only["oracle_id"]: [
                printing("Arena Only", "bbb", usd="0.10", eur="0.10", games=("arena",))],
        }
        fake = PrintsScryfall([foil_only, arena_only], prints)

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [
            COLLECTION_URL, search_url("Arena Only", "usd"), search_url("Foil Only", "usd")])
        metadata = json.loads(self.output.read_text())
        for name in ("Foil Only", "Arena Only"):
            with self.subTest(card=name):
                self.assertEqual((metadata[name]["usd"], metadata[name]["eur"]), (None, None))
                self.assertIn(
                    f"    {name}: no released paper printing outside memorabilia has a "
                    f"non-foil usd price; no released paper printing outside memorabilia "
                    f"has a non-foil eur price\n", out)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["prices_from_other_printing"], NO_PRICES)

    def test_a_memorabilia_printing_does_not_count(self):
        """Step 3a of round 2 (Q2): the prices of Strip Mine in the first live run."""
        self.write_deck("one", "Strip Mine", "Volrath's Stronghold")
        strip_mine = make_card("Strip Mine", usd=None, eur=None)
        stronghold = make_card("Volrath's Stronghold", usd=None, eur=None)
        prints = {
            # One page with every printing: the gold-bordered ptc one is the cheapest.
            strip_mine["oracle_id"]: [
                printing("Strip Mine", "ptc", usd="10.71", eur="5.69", set_type="memorabilia"),
                printing("Strip Mine", "4bb", usd="15.49", eur="9.00"),
                printing("Strip Mine", "ren", usd="20.00", eur="6.51"),
            ],
            # Only memorabilia printings have a price.
            stronghold["oracle_id"]: [
                printing("Volrath's Stronghold", "wc98", usd="31.68", eur="24.60",
                         set_type="memorabilia"),
                printing("Volrath's Stronghold", "sth", usd_foil="200.00"),
            ],
        }
        fake = PrintsScryfall([strip_mine, stronghold], prints)

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [
            COLLECTION_URL, search_url("Strip Mine", "usd"), search_url("Volrath's Stronghold", "usd")])
        metadata = json.loads(self.output.read_text())
        self.assertEqual((metadata["Strip Mine"]["usd"], metadata["Strip Mine"]["eur"]), (15.49, 6.51))
        self.assertEqual(
            (metadata["Volrath's Stronghold"]["usd"], metadata["Volrath's Stronghold"]["eur"]),
            (None, None))
        self.assertIn(
            "    Volrath's Stronghold: no released paper printing outside memorabilia has a "
            "non-foil usd price; no released paper printing outside memorabilia has a "
            "non-foil eur price\n", out)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["prices_from_other_printing"], {"eur": 1, "usd": 1})

    def test_a_card_with_both_prices_sends_no_search(self):
        self.write_deck("one", "Sol Ring")
        fake = PrintsScryfall([make_card("Sol Ring")])

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertIn("Asking once more for the 0 cards whose printing lacks a price", out)

    def test_reversible_card_searches_by_the_oracle_id_of_its_front_face(self):
        """DEC-1112 B1: a reversible_card has no top-level oracle_id.

        As the ecl printings of run 2 do, the batch printing carries its oracle
        id and its image on each face only. The back face here has another id,
        so a search by the back face finds nothing (404) and takes no price.
        """
        self.write_deck("one", "Sol Ring", "Blood Crypt")
        batch = make_card("Blood Crypt // Blood Crypt", layout="reversible_card",
                          usd=None, eur=None)
        del batch["oracle_id"], batch["image_uris"]
        batch["card_faces"] = [
            {"name": "Blood Crypt", "oracle_id": "oracle-front",
             "image_uris": image_uris(image_path("Blood Crypt", "front"))},
            {"name": "Blood Crypt", "oracle_id": "oracle-back",
             "image_uris": image_uris(image_path("Blood Crypt", "back"))},
        ]
        fake = PrintsScryfall([make_card("Sol Ring"), batch], {"oracle-front": [
            printing("Blood Crypt", "rna", usd="9.00", eur="7.50")]})

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [
            COLLECTION_URL,
            f"{SEARCH_URL}?q=oracleid%3Aoracle-front+game%3Apaper&unique=prints&order=usd&dir=asc",
        ])
        entry = json.loads(self.output.read_text())["Blood Crypt"]
        self.assertEqual(
            (entry["usd"], entry["eur"], entry["image"]),
            (9.0, 7.5, image_path("Blood Crypt", "front")))


class OtherPrintingFailureCases(DeckDirCase):
    """A failed search ends the run as a failed batch does: no file, exit code 1."""

    def setUp(self):
        super().setUp()
        self.write_deck("one", "Blood Crypt", "Steam Vents")
        self.cards = [make_card(name, usd=None, eur=None) for name in ("Blood Crypt", "Steam Vents")]
        self.prints = {
            card["oracle_id"]: [printing(card["name"], "rna", usd="9.00", eur="7.50")]
            for card in self.cards
        }

    def test_failed_search_ends_the_run(self):
        failures = {
            "HTTP 500": 500,
            "HTTP 400": 400,
            "network error": urllib.error.URLError("connection refused"),
            "timeout": TimeoutError("timed out"),
            "not JSON": b"<html>bad gateway</html>",
            "no data list": b'{"object": "list", "has_more": false}',
            "no has_more": b'{"object": "list", "data": []}',
        }
        for label, failure in failures.items():
            with self.subTest(failure=label):
                fake = PrintsScryfall(self.cards, self.prints)
                fake.failures[1] = failure

                code, out = self.run_metadata(fake)

                self.assertNotEqual(code, 0)
                self.assertIn("The search for Blood Crypt failed", out)
                self.assertEqual(len(fake.sent), 2)
                self.assert_no_file_written()

    def test_429_on_a_search_ends_the_run(self):
        fake = PrintsScryfall(self.cards, self.prints)
        fake.failures[1] = 429

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertRegex(out, f"\n{STOP_TEXT}\nNo file written.")
        self.assertNotIn("The search for", out)
        self.assertEqual(len(fake.sent), 2)
        self.assert_no_file_written()

    def test_a_price_that_is_not_a_number_ends_the_run(self):
        """A non-foil price, and the foil price that is the sort key of a card on a page with more."""
        for key, has_more in (("usd", False), ("usd_foil", True)):
            with self.subTest(price=key):
                bad = printing("Blood Crypt", "gtc", **{"usd": None, "eur": "7.00", key: "n/a"})
                fake = PrintsScryfall(self.cards, self.prints)
                fake.failures[1] = json.dumps({"object": "list", "has_more": has_more, "data": [
                    printing("Blood Crypt", "rna", usd="9.00", eur="7.50"), bad]}).encode()

                code, out = self.run_metadata(fake)

                self.assertNotEqual(code, 0)
                self.assertIn(f"Blood Crypt: the {key} price is 'n/a', not a number", out)
                self.assert_no_file_written()


class OtherPrintingCostCases(DeckDirCase):
    """Item 3: one search for each card; a second only when the page has ``has_more``."""

    def test_one_search_per_card_and_a_second_for_a_page_with_has_more(self):
        self.write_deck("one", "Forest", "Chaos Warp", "CHAOS WARP", "Bonecrusher Giant // Stomp")
        forest = make_card("Forest", usd=None, eur=None)
        chaos_warp = make_card("Chaos Warp", usd=None, eur=None)
        giant = make_card("Bonecrusher Giant // Stomp", layout="adventure", usd=None, eur=None)
        prints = {
            # Five printings and pages of three: the cheapest eur is not on the usd page.
            forest["oracle_id"]: [
                printing("Forest", "p1", usd="0.05", eur="0.90"),
                printing("Forest", "p2", usd="0.06", eur="0.80"),
                printing("Forest", "p3", usd="0.07", eur="0.70"),
                printing("Forest", "p4", usd="0.50", eur="0.03"),
                printing("Forest", "p5", usd="0.60", eur="0.04"),
            ],
            chaos_warp["oracle_id"]: [
                printing("Chaos Warp", "c1", usd="1.00", eur="2.00"),
                printing("Chaos Warp", "c2", usd="3.00", eur="1.50"),
            ],
            giant["oracle_id"]: [
                printing("Bonecrusher Giant // Stomp", "g1", usd="0.75", eur="0.65")],
        }
        fake = PrintsScryfall([forest, chaos_warp, giant], prints)
        fake.PAGE_SIZE = 3
        # Scryfall finds "CHAOS WARP" and returns its own spelling. Each of the two names
        # gets an entry of its own: the one of "CHAOS WARP" stays under that key only.
        fake.by_name["CHAOS WARP"] = chaos_warp

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [
            COLLECTION_URL,
            search_url("Bonecrusher Giant // Stomp", "usd"),
            search_url("Chaos Warp", "usd"),
            search_url("Forest", "usd"),
            search_url("Forest", "eur"),
        ])
        for gap in fake.gaps():
            self.assertAlmostEqual(gap, 0.6, places=9)
        metadata = json.loads(self.output.read_text())
        expected = {
            "Forest": (0.05, 0.03),
            "Chaos Warp": (1.0, 1.5),
            "CHAOS WARP": (1.0, 1.5),
            "Bonecrusher Giant // Stomp": (0.75, 0.65),
            "Bonecrusher Giant": (0.75, 0.65),
        }
        self.assertEqual(
            {name: (entry["usd"], entry["eur"]) for name, entry in metadata.items()}, expected)
        self.assertNotIn("does not prove", out)
        self.assertIn("    Bonecrusher Giant // Stomp: usd 0.75 from another printing; "
                      "eur 0.65 from another printing\n", out)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["prices_from_other_printing"], {"eur": 5, "usd": 5})


class FirstPageProofCases(DeckDirCase):
    """No search reads a second page. A page with ``has_more`` gives a price only when it proves it."""

    def run_pass(self, name: str, *prints: dict, page_size: int = 2,
                 raw_page: list[dict] | None = None, has_more: bool = True):
        """The usd price that the pass gives ``name``, and the run's text. The batch has eur.

        ``raw_page`` is the page that the search answers, as it stands, with ``has_more``.
        """
        batch = make_card(name, usd=None, eur="0.05")
        fake = PrintsScryfall([batch], {batch["oracle_id"]: list(prints)})
        fake.PAGE_SIZE = page_size
        if raw_page is not None:
            fake.failures[1] = json.dumps(
                {"object": "list", "has_more": has_more, "data": raw_page}).encode()
        out = io.StringIO()
        with fake.installed(), contextlib.redirect_stdout(out):
            metadata, _ = fetch_metadata.fetch_metadata({name}, today="2026-10-14")
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, search_url(name, "usd")])
        return metadata[name]["usd"], out.getvalue()

    def test_page_of_foil_prices_with_more_after_it_proves_nothing(self):
        price, out = self.run_pass(
            "Island",
            printing("Island", "f1", usd_foil="0.01"),
            printing("Island", "f2", usd_foil="0.02"),
            printing("Island", "n1", usd="0.10"))
        self.assertIsNone(price)
        self.assertIn(
            "    Island: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_in_order_with_a_price_is_proof(self):
        """Two keys of the same value are in order."""
        price, out = self.run_pass(
            "Plains",
            printing("Plains", "f1", usd_foil="0.03"),
            printing("Plains", "n1", usd="0.03", usd_foil="0.01"),
            printing("Plains", "n3", usd="0.035"))
        self.assertEqual(price, 0.03)
        self.assertIn("    Plains: usd 0.03 from another printing\n", out)

    def test_page_of_cards_without_price_before_a_price_proves_nothing(self):
        """With ``dir=asc`` the two printings without a key fill the page; 0.10 follows it."""
        price, out = self.run_pass(
            "Mountain",
            printing("Mountain", "n1", usd="0.10"),
            printing("Mountain", "x"),
            printing("Mountain", "y"))
        self.assertIsNone(price)
        self.assertIn(
            "    Mountain: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_whose_last_card_has_no_price_proves_nothing(self):
        """The page holds the two printings without a key; a foil key follows it."""
        price, out = self.run_pass(
            "Swamp",
            printing("Swamp", "f1", usd_foil="0.10"),
            printing("Swamp", "x"),
            printing("Swamp", "y"))
        self.assertIsNone(price)
        self.assertIn(
            "    Swamp: the first page does not prove the lowest usd price: no price taken\n", out)
        self.assertNotIn("no released paper printing", out)

    def test_page_out_of_order_proves_nothing(self):
        """The order of the first live run: the most expensive first."""
        price, out = self.run_pass("Forest", raw_page=[
            printing("Forest", "a", usd="0.50"), printing("Forest", "b", usd="0.05")])
        self.assertIsNone(price)
        self.assertIn(
            "    Forest: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_with_a_card_without_price_before_a_price_is_proof(self):
        """The order of run 2: the printings without a key first."""
        price, out = self.run_pass("Wastes", raw_page=[
            printing("Wastes", "x"), printing("Wastes", "n1", usd="0.10")])
        self.assertEqual(price, 0.1)
        self.assertIn("    Wastes: usd 0.1 from another printing\n", out)

    def test_page_in_the_shape_of_run_2_gives_the_lowest_price(self):
        """Step 5a of round 3: two printings without a key, a foil-only printing at 0.01,
        then printings that count at 0.09, 0.09 and 0.15. One more follows the page."""
        price, out = self.run_pass(
            "Forest",
            printing("Forest", "c15", usd="0.15"),
            printing("Forest", "m20", usd="0.09"),
            printing("Forest", "x"),
            printing("Forest", "f1", usd_foil="0.01"),
            printing("Forest", "y"),
            printing("Forest", "dtk", usd="0.09"),
            printing("Forest", "z", usd="0.16"),
            page_size=6)
        self.assertEqual(price, 0.09)
        self.assertIn("    Forest: usd 0.09 from another printing\n", out)

    def test_page_whose_every_printing_has_no_price_proves_nothing(self):
        """Step 5b of round 3: no printing has a key, and the page has more after it.
        The page proves nothing, and no line says that the card has no price."""
        price, out = self.run_pass(
            "Plains",
            printing("Plains", "x"),
            printing("Plains", "y"),
            printing("Plains", "z"))
        self.assertIsNone(price)
        self.assertIn(
            "    Plains: the first page does not prove the lowest usd price: no price taken\n", out)
        self.assertNotIn("no released paper printing", out)

    def test_page_with_a_card_without_price_after_a_price_proves_nothing(self):
        """Step 5c of round 3: the direction of run 1, a price and then no key."""
        price, out = self.run_pass("Island", raw_page=[
            printing("Island", "n1", usd="0.10"), printing("Island", "x")])
        self.assertIsNone(price)
        self.assertIn(
            "    Island: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_with_a_card_without_price_after_a_price_of_zero_proves_nothing(self):
        """A printing without a key sorts below every key, 0.00 too, so it cannot follow one."""
        price, out = self.run_pass("Island", raw_page=[
            printing("Island", "n0", usd="0.00"), printing("Island", "x")])
        self.assertIsNone(price)
        self.assertIn(
            "    Island: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_whose_only_prices_are_memorabilia_proves_nothing(self):
        """Step 3b of round 2: the last card has a price, so a printing that counts may follow."""
        price, out = self.run_pass(
            "Island",
            printing("Island", "wc97", usd="0.10", set_type="memorabilia"),
            printing("Island", "wc98", usd="0.20", set_type="memorabilia"),
            printing("Island", "n1", usd="0.30"))
        self.assertIsNone(price)
        self.assertIn(
            "    Island: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_with_memorabilia_first_gives_the_price_of_the_card_that_counts(self):
        """Step 3c of round 2."""
        price, out = self.run_pass(
            "Plains",
            printing("Plains", "wc97", usd="0.10", set_type="memorabilia"),
            printing("Plains", "ced", usd="0.20", set_type="memorabilia"),
            printing("Plains", "n1", usd="0.30"),
            printing("Plains", "n2", usd="0.40"),
            page_size=3)
        self.assertEqual(price, 0.3)
        self.assertIn("    Plains: usd 0.3 from another printing\n", out)

    def test_page_with_memorabilia_prices_whose_last_card_has_no_price_proves_nothing(self):
        """The page of round 2's second rule: no card that counts has a price, and the last
        card has no key. With ``dir=asc`` a printing without a key cannot follow a price."""
        price, out = self.run_pass("Swamp", raw_page=[
            printing("Swamp", "olep", usd="0.10", set_type="memorabilia"),
            printing("Swamp", "x"),
            printing("Swamp", "y")])
        self.assertIsNone(price)
        self.assertIn(
            "    Swamp: the first page does not prove the lowest usd price: no price taken\n", out)
        self.assertNotIn("no released paper printing", out)

    def test_order_check_reads_the_memorabilia_cards_too(self):
        """Without the memorabilia card the page would be in order and give 0.10."""
        price, out = self.run_pass("Forest", raw_page=[
            printing("Forest", "n1", usd="0.10"),
            printing("Forest", "30a", usd="0.05", set_type="memorabilia")])
        self.assertIsNone(price)
        self.assertIn(
            "    Forest: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_page_with_every_printing_needs_no_order(self):
        price, out = self.run_pass("Thought Vessel", has_more=False, raw_page=[
            printing("Thought Vessel", "a", usd="0.50"),
            printing("Thought Vessel", "b", usd="0.05")])
        self.assertEqual(price, 0.05)
        self.assertIn("    Thought Vessel: usd 0.05 from another printing\n", out)

    def test_sort_key_is_the_non_foil_price_else_the_foil_else_the_etched_one(self):
        """Keys 0.05, 0.20 and 0.30 are in order. By the lowest price they would be 0.05, 0.20
        and 0.10; by the non-foil price only, None, 0.20 and None; with etched before foil,
        0.05, 0.20 and 0.10."""
        price, out = self.run_pass("Mind Stone", raw_page=[
            printing("Mind Stone", "a", usd_foil="0.05"),
            printing("Mind Stone", "b", usd="0.20"),
            printing("Mind Stone", "c", usd_foil="0.30", usd_etched="0.10")])
        self.assertEqual(price, 0.2)
        self.assertIn("    Mind Stone: usd 0.2 from another printing\n", out)


class AtomicWriteCases(DeckDirCase):
    """N1: each file goes to a temporary file in its folder; the meta file moves last."""

    OLD = '{"Sol Ring": {"cmc": 1.0}}'
    OLD_META = '{"count": 1}\n'

    def write(self):
        fetch_metadata.write_outputs(
            self.output, {"Sol Ring": {"cmc": 2.0}}, "2026-10-14T00:00:00+00:00", NO_PRICES)

    def assert_old_files_and_no_temp_file(self):
        self.assertEqual(self.output.read_text(), self.OLD)
        self.assertEqual(self.meta.read_text(), self.OLD_META)
        self.assertEqual(
            sorted(path.name for path in self.root.iterdir()),
            ["card-metadata.json", "card-metadata.meta.json"])

    def test_meta_file_moves_last_from_the_same_folder(self):
        self.write_deck("one", "Sol Ring")
        moves = []
        replace = os.replace

        def recording_replace(src, dst):
            # The limiter's state.json moves too (DEC-1092); keep the moves into this folder.
            if Path(dst).parent == self.root:
                moves.append((Path(src), Path(dst)))
            replace(src, dst)

        with mock.patch("os.replace", recording_replace):
            code, _ = self.run_metadata(PrintsScryfall([make_card("Sol Ring")]))

        self.assertEqual(code, 0)
        self.assertEqual(moves, [
            (self.root / "card-metadata.json.tmp", self.output),
            (self.root / "card-metadata.meta.json.tmp", self.meta),
        ])
        self.assertEqual(
            sorted(path.name for path in self.root.iterdir()),
            ["card-metadata.json", "card-metadata.meta.json", "commanders"])

    def test_write_that_fails_leaves_both_old_files(self):
        """Probe 8b: a write that stops half way, for each of the two files."""
        write_text = Path.write_text
        for failing in ("card-metadata.json.tmp", "card-metadata.meta.json.tmp"):
            with self.subTest(file=failing):
                self.output.write_text(self.OLD)
                self.meta.write_text(self.OLD_META)

                def half_write(path, text, *args, failing=failing, **kwargs):
                    if path.name != failing:
                        return write_text(path, text, *args, **kwargs)
                    write_text(path, text[: len(text) // 2], *args, **kwargs)
                    raise OSError("No space left on device")

                with mock.patch.object(Path, "write_text", half_write), \
                        self.assertRaises(OSError):
                    self.write()

                self.assert_old_files_and_no_temp_file()

    def test_first_move_that_fails_leaves_both_old_files(self):
        self.output.write_text(self.OLD)
        self.meta.write_text(self.OLD_META)

        with mock.patch("os.replace", side_effect=OSError("Read-only file system")), \
                self.assertRaises(OSError):
            self.write()

        self.assert_old_files_and_no_temp_file()


class SpellingCases(DeckDirCase):
    """N5: the line for a name that finds no card also gives the names Scryfall returned."""

    def test_deck_name_not_found_shows_the_spelling_that_scryfall_returned(self):
        self.write_deck("one", "sol ring", "Lorien Revealed")
        fake = FakeScryfall()
        fake.failures[0] = json.dumps({"object": "list", "not_found": [], "data": [
            make_card("Lórien Revealed"), make_card("Sol Ring")]}).encode()

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn(
            "  Lorien Revealed: Scryfall gave no card of that name and no not_found line for it\n"
            "  Scryfall also returned names that match no name asked: Lórien Revealed\n", out)
        self.assert_no_file_written()

    def test_failed_batch_whose_cards_all_answered_a_name_adds_no_line(self):
        self.write_deck("one", "Sol Ring", "No Image")
        no_image = make_card("No Image")
        del no_image["image_uris"]
        fake = FakeScryfall([make_card("Sol Ring"), no_image])

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("No Image: no normal image address", out)
        self.assertNotIn("match no name asked", out)
        self.assert_no_file_written()

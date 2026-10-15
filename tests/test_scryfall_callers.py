"""DEC-1076 — four more callers of Scryfall's 2-a-second methods keep the helper's rules.

scripts/compute_tokens.py, scripts/check_game_changers.py, scripts/prerelease/dump_set.py and
priv_data/format_owned_list.py send every request through scripts/scryfall_api.py:

1. a request starts 600 ms or more after the last answer arrived;
2. a 429 ends the run: no file written, the status and the end of the stop on screen,
   exit code 1 and no later request.

No test here sends a live request: FakeScryfall (tests/test_scryfall_fetch.py) stands in for
the helper's opener and for the clock.
"""

import contextlib
import csv
import gzip
import http.client
import importlib
import io
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

from tests.test_scryfall_fetch import STOP_TEXT, FakeScryfall, make_card, scryfall_api

compute_tokens = importlib.import_module("scripts.compute_tokens")
check_gc = importlib.import_module("scripts.check_game_changers")
dump_set = importlib.import_module("scripts.prerelease.dump_set")
format_owned = importlib.import_module("priv_data.format_owned_list")
build_price_index = importlib.import_module("scripts.build_price_index")
refresh_mirror = importlib.import_module("scripts.refresh_scryfall_mirror")

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.scryfall.com"
COLLECTION_URL = f"{API}/cards/collection"


class CallerCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def assert_600ms_gaps(self, fake: FakeScryfall, count: int):
        self.assertEqual(len(fake.gaps()), count)
        for gap in fake.gaps():
            self.assertAlmostEqual(gap, 0.6, places=9)

    def assert_429_text(self, out: str):
        self.assertIn("429", out)
        self.assertRegex(out, STOP_TEXT)

    def run_as_script(self, fake: FakeScryfall, path: Path, *argv: str):
        """Run ``path`` as ``__main__``; return the exit code and the screen."""
        out = io.StringIO()
        with fake.installed(), contextlib.redirect_stdout(out), \
                mock.patch.object(sys, "path", list(sys.path)), \
                mock.patch("sys.argv", [path.name, *argv]), \
                self.assertRaises(SystemExit) as raised:
            runpy.run_path(str(path), run_name="__main__")
        return raised.exception.code, out.getvalue()


# --------------------------------------------------------------- compute_tokens.py

GOBLIN_URL = f"{API}/cards/goblin-token"
ARMY_QUERY = 't:token t:army "Orcs"'
ARMY_URL = f"{API}/cards/search?q={urllib.parse.quote(ARMY_QUERY)}"
MONARCH_URL = f"{API}/cards/named?exact=The%20Monarch"
VALAKUT = "Valakut Awakening // Valakut Stoneforge"
# A name that the batch does not find, so the script asks /cards/named?fuzzy= for it.
MISSPELT = "Lim-Dul's Vault"
MISSPELT_URL = f"{API}/cards/named?fuzzy=Lim-Dul%27s%20Vault"


def token_card(name: str, type_line: str, **extra) -> dict:
    card = {"object": "card", "id": name.lower().replace(" ", "-"), "name": name,
            "type_line": type_line, "oracle_text": "", "colors": [],
            "image_uris": {"normal": f"https://cards.scryfall.io/normal/front/t/k/{name}.jpg"}}
    card.update(extra)
    return card


def token_fake(cards=()) -> FakeScryfall:
    """The cards of each request kind that compute_tokens.py sends."""
    fake = FakeScryfall([
        make_card("Sol Ring"),
        make_card("Goblin Maker", all_parts=[
            {"component": "token", "name": "Goblin", "uri": GOBLIN_URL}]),
        make_card("Orc Caller", oracle_text="Amass Orcs 2."),
        make_card("Crown Seeker", oracle_text="When this enters, you become the monarch."),
        *cards,
    ])
    fake.pages = {
        MISSPELT_URL: make_card("Lim-Dûl's Vault"),
        GOBLIN_URL: token_card("Goblin", "Token Creature — Goblin", power="1", toughness="1"),
        ARMY_URL: {"object": "list", "data": [
            token_card("Orc Army", "Token Creature — Orc Army", power="0", toughness="0")]},
        MONARCH_URL: token_card("The Monarch", "Card"),
    }
    return fake


class ComputeTokensTests(CallerCase):
    def setUp(self):
        super().setUp()
        self.commanders = self.root / "commanders"
        # fetch_named_exact keeps its answers for the whole process.
        compute_tokens.fetch_named_exact.__defaults__[0].clear()
        self.addCleanup(compute_tokens.fetch_named_exact.__defaults__[0].clear)

    def write_deck(self, deck_id: str, commander: str, *names: str) -> Path:
        path = self.commanders / deck_id / "deck.json"
        path.parent.mkdir(parents=True)
        deck = {"name": deck_id, "commander": commander, "decklist": [{"name": n} for n in names]}
        path.write_text(json.dumps(deck))
        return path

    def run_main(self, fake: FakeScryfall, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with fake.installed(), \
                mock.patch.object(compute_tokens, "COMMANDERS_DIR", self.commanders), \
                mock.patch("sys.argv", ["compute_tokens.py", *argv]), \
                contextlib.redirect_stdout(out):
            code = compute_tokens.main()
        return code, out.getvalue()

    def test_every_request_starts_600ms_after_the_last_answer(self):
        """Rule 1 over each request kind: two batches, /cards/named, a token, /cards/search."""
        fillers = [f"Card {n:03d}" for n in range(75)]
        path = self.write_deck(
            "one", "Goblin Maker", *fillers, "Orc Caller", "Crown Seeker", MISSPELT)
        fake = token_fake(make_card(name) for name in fillers)

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual(
            [s.url for s in fake.sent],
            [COLLECTION_URL, COLLECTION_URL, MISSPELT_URL, GOBLIN_URL, ARMY_URL, MONARCH_URL])
        self.assertEqual([len(s.body["identifiers"]) for s in fake.sent[:2]], [75, 4])
        self.assert_600ms_gaps(fake, 5)
        for sent in fake.sent:
            self.assertEqual(sent.headers["user-agent"], "MTGPreconUpgrader/1.0")
        tokens = json.loads(path.read_text())["tokens"]
        self.assertEqual(
            [(t["name"], t["produced_by"]) for t in tokens],
            [("Goblin", ["Goblin Maker"]), ("Orc Army", ["Orc Caller"]),
             ("The Monarch", ["Crown Seeker"])])

    def test_clean_run_writes_every_deck(self):
        first = self.write_deck("a-first", "Arcane Signet")
        second = self.write_deck("b-second", "Goblin Maker")
        fake = token_fake([make_card("Arcane Signet")])

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, COLLECTION_URL, GOBLIN_URL])
        self.assert_600ms_gaps(fake, 2)
        self.assertEqual(json.loads(first.read_text())["tokens"], [])
        self.assertEqual([t["name"] for t in json.loads(second.read_text())["tokens"]], ["Goblin"])

    def test_429_ends_the_run_at_each_request_kind(self):
        """Rule 2. The 429 answers the last request of the run, so a swallowed 429 writes files."""
        kinds = {
            "a batch": ("Sol Ring", [COLLECTION_URL]),
            "a fuzzy /cards/named": (MISSPELT, [COLLECTION_URL, MISSPELT_URL]),
            "a token": ("Goblin Maker", [COLLECTION_URL, GOBLIN_URL]),
            "a /cards/search": ("Orc Caller", [COLLECTION_URL, ARMY_URL]),
            "an exact /cards/named": ("Crown Seeker", [COLLECTION_URL, MONARCH_URL]),
        }
        for kind, (card, urls) in kinds.items():
            with self.subTest(kind=kind):
                shutil.rmtree(self.commanders, ignore_errors=True)
                compute_tokens.fetch_named_exact.__defaults__[0].clear()
                first = self.write_deck("a-first", "Arcane Signet")
                second = self.write_deck("b-second", card)
                before = {path: path.read_text() for path in (first, second)}
                fake = token_fake([make_card("Arcane Signet")])
                fake.failures[len(urls)] = 429  # the first deck sends one request

                code, out = self.run_main(fake)

                self.assertEqual(code, 1)
                self.assert_429_text(out)
                self.assertIn("No file written.", out)
                # DEC-1098: the helper's text alone, not wrapped as a failed request.
                self.assertRegex(out, f"\n{STOP_TEXT}\nNo file written.\n")
                self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, *urls])
                self.assertEqual({path: path.read_text() for path in before}, before)

    def test_script_exits_with_1_on_a_429(self):
        """The ``__main__`` block hands main()'s code to sys.exit."""
        path = self.write_deck("one", "Sol Ring")
        before = path.read_text()
        fake = token_fake()
        fake.failures[0] = 429

        # An absolute --deck path takes the place of data/commanders.
        code, out = self.run_as_script(
            fake, ROOT / "scripts" / "compute_tokens.py", "--deck", str(path.parent))

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(path.read_text(), before)

    # DEC-1098 item 1: every failed request ends the run, as a 429 does. An answer that
    # says Scryfall found no card does not.

    def test_failed_request_ends_the_run_at_each_request_kind(self):
        """The failure answers the first deck, so a run that goes on sends the second deck's
        batch and writes both files."""
        kinds = {
            "the batch": ("Sol Ring", [COLLECTION_URL]),
            "a fuzzy /cards/named": (MISSPELT, [COLLECTION_URL, MISSPELT_URL]),
            "the token request": ("Goblin Maker", [COLLECTION_URL, GOBLIN_URL]),
            "a /cards/search": ("Orc Caller", [COLLECTION_URL, ARMY_URL]),
            "an exact /cards/named": ("Crown Seeker", [COLLECTION_URL, MONARCH_URL]),
        }
        failures = {
            "HTTP 301": (301, "HTTPError: HTTP Error 301: status 301"),
            "HTTP 503": (503, "HTTPError: HTTP Error 503: status 503"),
            "network error": (urllib.error.URLError("connection refused"),
                              "URLError: <urlopen error connection refused>"),
            "not JSON": (b"<html>bad gateway</html>",
                         "JSONDecodeError: Expecting value: line 1 column 1 (char 0)"),
            # urllib wraps a failure in a URLError only while it sends the request. A
            # failure while it waits for or reads the answer reaches the script raw.
            "read timeout": (TimeoutError("The read operation timed out"),
                             "TimeoutError: The read operation timed out"),
            "connection reset": (ConnectionResetError(54, "Connection reset by peer"),
                                 "ConnectionResetError: [Errno 54] Connection reset by peer"),
            "incomplete answer": (http.client.IncompleteRead(b"{"),
                                  "IncompleteRead: IncompleteRead(1 bytes read)"),
        }
        # A 404 means "no card" only from /cards/named and /cards/search.
        failures_404 = {"HTTP 404": (404, "HTTPError: HTTP Error 404: status 404")}
        for kind, (card, urls) in kinds.items():
            kind_failures = failures
            if kind in ("the batch", "the token request"):
                kind_failures = {**failures, **failures_404}
            for label, (failure, text) in kind_failures.items():
                with self.subTest(kind=kind, failure=label):
                    shutil.rmtree(self.commanders, ignore_errors=True)
                    compute_tokens.fetch_named_exact.__defaults__[0].clear()
                    first = self.write_deck("a-first", card)
                    second = self.write_deck("b-second", "Arcane Signet")
                    before = {path: path.read_text() for path in (first, second)}
                    fake = token_fake([make_card("Arcane Signet")])
                    fake.failures[len(urls) - 1] = failure

                    code, out = self.run_main(fake)

                    method = "POST" if urls[-1] == COLLECTION_URL else "GET"
                    self.assertEqual(code, 1)
                    self.assertIn(
                        f"\nScryfall request failed: {method} {urls[-1]}: {text}\nNo file written.\n",
                        out)
                    self.assertEqual([s.url for s in fake.sent], urls)
                    self.assertEqual({path: path.read_text() for path in before}, before)

    def test_script_exits_with_1_on_a_failed_request(self):
        """The ``__main__`` block hands main()'s code to sys.exit."""
        path = self.write_deck("one", "Sol Ring")
        before = path.read_text()
        fake = token_fake()
        fake.failures[0] = 503

        code, out = self.run_as_script(
            fake, ROOT / "scripts" / "compute_tokens.py", "--deck", str(path.parent))

        self.assertEqual(code, 1)
        self.assertIn("Scryfall request failed: POST", out)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(path.read_text(), before)

    def test_deck_entry_without_a_name_is_not_reported_as_a_failed_request(self):
        """main() prints "No file written." for a 429 or a failed request only. Any other
        fault, here a deck entry without a name, leaves main() as its own exception."""
        path = self.write_deck("one", "Sol Ring", "Arcane Signet")
        deck = json.loads(path.read_text())
        deck["decklist"].append({"quantity": 1})
        path.write_text(json.dumps(deck))
        before = path.read_text()
        fake = token_fake()

        with self.assertRaises(KeyError):
            self.run_main(fake)

        self.assertEqual(fake.sent, [])
        self.assertEqual(path.read_text(), before)

    def test_not_found_entry_of_a_batch_is_asked_by_fuzzy_lookup(self):
        path = self.write_deck("one", "Sol Ring", MISSPELT)
        fake = token_fake()

        code, out = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual(fake.sent[0].body, {"identifiers": [{"name": MISSPELT}, {"name": "Sol Ring"}]})
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, MISSPELT_URL])
        self.assertIn("Retrying 1 via fuzzy named lookup...", out)
        self.assertEqual(json.loads(path.read_text())["tokens"], [])

    # The batch reads ``data`` and ``not_found`` with defaults. Scryfall's documented answer
    # holds both fields; these cases keep the reading of an answer that lacks one.

    def run_batch_answer(self, answer: dict) -> tuple[int, str, FakeScryfall, list]:
        """Answer the batch of a one-card deck with ``answer``; return the exit code, the
        screen, the fake and the deck's tokens."""
        path = self.write_deck("one", "Goblin Maker")
        fake = token_fake()
        fake.failures[0] = json.dumps(answer).encode()
        code, out = self.run_main(fake)
        return code, out, fake, json.loads(path.read_text())["tokens"]

    def test_batch_answer_without_data_reads_as_no_card(self):
        code, _, fake, tokens = self.run_batch_answer({"object": "list", "not_found": []})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])

    def test_batch_answer_without_not_found_reads_as_every_card_found(self):
        goblin_maker = token_fake().by_name["Goblin Maker"]
        code, _, fake, tokens = self.run_batch_answer({"object": "list", "data": [goblin_maker]})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, GOBLIN_URL])
        self.assertEqual([t["name"] for t in tokens], ["Goblin"])

    def test_not_found_entry_without_a_name_costs_no_fuzzy_lookup(self):
        code, out, fake, tokens = self.run_batch_answer(
            {"object": "list", "data": [], "not_found": [{"set": "abc", "collector_number": "1"}]})
        self.assertEqual(code, 0)
        self.assertNotIn("Retrying", out)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])

    def test_404_from_fuzzy_named_skips_the_card_and_the_run_goes_on(self):
        path = self.write_deck("one", "Goblin Maker", MISSPELT)
        fake = token_fake()
        fake.failures[1] = 404

        code, out = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertIn(f"      Lookup failed for {MISSPELT}: HTTP Error 404: status 404\n", out)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, MISSPELT_URL, GOBLIN_URL])
        self.assertEqual([t["name"] for t in json.loads(path.read_text())["tokens"]], ["Goblin"])

    def test_404_from_exact_named_skips_the_marker_and_the_run_goes_on(self):
        first = self.write_deck("a-first", "Crown Seeker")
        second = self.write_deck("b-second", "Goblin Maker")
        fake = token_fake()
        fake.failures[1] = 404

        code, out = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertIn("    Marker lookup failed for 'The Monarch': HTTP Error 404: status 404\n", out)
        self.assertEqual(
            [s.url for s in fake.sent], [COLLECTION_URL, MONARCH_URL, COLLECTION_URL, GOBLIN_URL])
        self.assertEqual(json.loads(first.read_text())["tokens"], [])
        self.assertEqual([t["name"] for t in json.loads(second.read_text())["tokens"]], ["Goblin"])

    def test_404_from_search_tries_the_next_query_and_the_run_goes_on(self):
        second_url = f"{API}/cards/search?q={urllib.parse.quote('t:token \"Orc Army\"')}"
        army = token_card("Orc Army", "Token Creature — Orc Army", power="0", toughness="0")
        for found in (True, False):
            with self.subTest(second_query_finds_the_army=found):
                shutil.rmtree(self.commanders, ignore_errors=True)
                compute_tokens.fetch_named_exact.__defaults__[0].clear()
                path = self.write_deck("one", "Orc Caller", "Crown Seeker")
                fake = token_fake()
                fake.failures[1] = 404
                if found:
                    fake.pages[second_url] = {"object": "list", "data": [army]}

                code, out = self.run_main(fake)

                self.assertEqual(code, 0)
                self.assertIn(
                    f"    Token search failed for '{ARMY_QUERY}': HTTP Error 404: status 404\n", out)
                self.assertEqual(
                    [s.url for s in fake.sent], [COLLECTION_URL, ARMY_URL, second_url, MONARCH_URL])
                names = [t["name"] for t in json.loads(path.read_text())["tokens"]]
                if found:
                    self.assertEqual(names, ["Orc Army", "The Monarch"])
                else:
                    self.assertIn("    Could not find Orc Army token on Scryfall\n", out)
                    self.assertEqual(names, ["The Monarch"])

    # DEC-1098 item 2: the batch holds the front face of a // name.

    def test_slash_card_goes_out_as_its_front_face_and_gets_its_tokens(self):
        westvale = "Westvale Abbey // Ormendahl, Profane Prince"
        lovestruck = "Lovestruck Beast // Heart's Desire"
        cleric_url = f"{API}/cards/human-cleric-token"
        human_url = f"{API}/cards/human-token"
        path = self.write_deck("one", "Sol Ring", westvale, lovestruck)
        fake = token_fake([
            make_card(westvale, layout="transform", all_parts=[
                {"component": "token", "name": "Human Cleric", "uri": cleric_url}]),
            make_card(lovestruck, layout="adventure", all_parts=[
                {"component": "token", "name": "Human", "uri": human_url}]),
        ])
        fake.pages[cleric_url] = token_card(
            "Human Cleric", "Token Creature — Human Cleric", power="1", toughness="1")
        fake.pages[human_url] = token_card(
            "Human", "Token Creature — Human", power="1", toughness="1")

        code, out = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual(
            fake.asked_names(), ["Lovestruck Beast", "Sol Ring", "Westvale Abbey"])
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, human_url, cleric_url])
        self.assertNotIn("fuzzy", out)
        tokens = json.loads(path.read_text())["tokens"]
        self.assertEqual(
            [(t["name"], t["produced_by"]) for t in tokens],
            [("Human", [lovestruck]), ("Human Cleric", [westvale])])

    def test_batch_sorts_the_front_faces_by_code_point(self):
        """The batch sorts the front faces, not the full names, and capitals come first.
        "Fire & Ice" sorts before "Fire // Ice" but after "Fire"; "Lord Windgrace" sorts
        before "Lord of the Void" only when case counts."""
        decks = {
            ("Fire // Ice", "Fire & Ice"): ["Fire", "Fire & Ice", "Sol Ring"],
            ("Lord of the Void", "Lord Windgrace"):
                ["Lord Windgrace", "Lord of the Void", "Sol Ring"],
        }
        for names, asked in decks.items():
            with self.subTest(names=names):
                shutil.rmtree(self.commanders, ignore_errors=True)
                self.write_deck("one", "Sol Ring", *names)
                fake = token_fake([
                    make_card(name, layout="adventure" if " // " in name else "normal")
                    for name in names])

                code, _ = self.run_main(fake)

                self.assertEqual(code, 0)
                self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
                self.assertEqual(fake.asked_names(), asked)


# --------------------------------------------------------- check_game_changers.py

GC_QUERY_URL = f"{check_gc.SCRYFALL_SEARCH}?q={urllib.parse.quote('format:commander is:gamechanger')}"


def gc_fake(pages: int) -> FakeScryfall:
    """``pages`` pages of the live search; page n holds the card "Changer n"."""
    fake = FakeScryfall()
    urls = [GC_QUERY_URL] + [f"{GC_QUERY_URL}&page={n}" for n in range(2, pages + 1)]
    for n, url in enumerate(urls):
        page = {"object": "list", "data": [{"name": f"Changer {n}"}], "has_more": False}
        if n + 1 < len(urls):
            page.update(has_more=True, next_page=urls[n + 1])
        fake.pages[url] = page
    return fake


class CheckGameChangersTests(CallerCase):
    def test_pages_start_600ms_after_the_last_answer(self):
        fake = gc_fake(3)

        with fake.installed():
            names = check_gc.fetch_remote_gc_names()

        self.assertEqual(names, {"Changer 0", "Changer 1", "Changer 2"})
        self.assertEqual(len(fake.sent), 3)
        self.assert_600ms_gaps(fake, 2)
        for sent in fake.sent:
            self.assertEqual(sent.headers["user-agent"], "MTGPreconUpgrader/1.0")

    def test_429_ends_the_run_before_the_other_checks(self):
        fake = gc_fake(3)
        fake.failures[1] = 429
        out = io.StringIO()

        with fake.installed(), mock.patch("sys.argv", ["check_game_changers.py"]), \
                contextlib.redirect_stdout(out):
            code = check_gc.main()

        self.assertEqual(code, 1)
        self.assert_429_text(out.getvalue())
        self.assertEqual(len(fake.sent), 2)
        self.assertNotIn("ts mirror", out.getvalue())

    def test_script_exits_with_1_on_a_429(self):
        fake = gc_fake(1)
        fake.failures[0] = 429

        code, out = self.run_as_script(fake, ROOT / "scripts" / "check_game_changers.py")

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertEqual(len(fake.sent), 1)


# ------------------------------------------------------------- prerelease/dump_set.py

FIXTURES = ROOT / "tests" / "fixtures" / "prerelease"
SET_URL = f"{API}/sets/fra"
SEARCH = f"{API}/cards/search?q={urllib.parse.quote('set:fra')}"
CARDS_URL = f"{SEARCH}&unique=cards&order=set&include_extras=false"
CARDS_PAGE_2 = f"{SEARCH}&unique=cards&order=set&include_extras=false&page=2"
PRINTS_URL = f"{SEARCH}&unique=prints&order=set&include_extras=false"


def set_fake() -> FakeScryfall:
    cards = json.loads((FIXTURES / "fix_all_cards.json").read_text())
    prints = json.loads((FIXTURES / "fix_all_prints.json").read_text())
    fake = FakeScryfall()
    fake.pages = {
        SET_URL: {"object": "set", "code": "fra", "name": "Fixture", "released_at": "2026-01-01",
                  "card_count": len(cards), "set_type": "expansion"},
        CARDS_URL: {"object": "list", "data": cards[:5], "has_more": True, "next_page": CARDS_PAGE_2},
        CARDS_PAGE_2: {"object": "list", "data": cards[5:], "has_more": False},
        PRINTS_URL: {"object": "list", "data": prints, "has_more": False},
    }
    return fake


class DumpSetTests(CallerCase):
    def setUp(self):
        super().setUp()
        self.out_dir = self.root / "dump"

    def run_main(self, fake: FakeScryfall) -> tuple[int, str]:
        out = io.StringIO()
        with fake.installed(), \
                mock.patch("sys.argv", ["dump_set.py", "--set", "FRA", "--out-dir", str(self.out_dir)]), \
                contextlib.redirect_stdout(out):
            code = dump_set.main()
        return code, out.getvalue()

    def test_requests_start_600ms_after_the_last_answer(self):
        fake = set_fake()

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual(
            [s.url for s in fake.sent], [SET_URL, CARDS_URL, CARDS_PAGE_2, PRINTS_URL])
        self.assert_600ms_gaps(fake, 3)
        self.assertEqual(
            sorted(p.name for p in self.out_dir.iterdir()),
            ["fra_all_cards.json", "fra_all_prints.json", "grading_sheet.txt", "set_facts.md"])
        self.assertEqual(len(json.loads((self.out_dir / "fra_all_cards.json").read_text())), 9)

    def test_429_ends_the_run_and_writes_no_file(self):
        for index in range(4):
            with self.subTest(request=index):
                fake = set_fake()
                fake.failures[index] = 429

                code, out = self.run_main(fake)

                self.assertEqual(code, 1)
                self.assert_429_text(out)
                self.assertIn("No file written.", out)
                self.assertEqual(len(fake.sent), index + 1)
                self.assertFalse(self.out_dir.exists())

    def test_script_exits_with_1_on_a_429(self):
        fake = set_fake()
        fake.failures[0] = 429

        code, out = self.run_as_script(
            fake, ROOT / "scripts" / "prerelease" / "dump_set.py",
            "--set", "fra", "--out-dir", str(self.out_dir))

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertEqual(len(fake.sent), 1)
        self.assertFalse(self.out_dir.exists())

    # DEC-1098 item 4: the text for a failed /sets/:code names the status.

    def run_failed_set_code(self, failure) -> tuple[str, FakeScryfall]:
        """Run main() with ``failure`` on /sets/:code; return the SystemExit text and the fake."""
        fake = set_fake()
        fake.failures[0] = failure
        with self.assertRaises(SystemExit) as raised:
            self.run_main(fake)
        return raised.exception.code, fake

    def test_404_on_the_set_code_says_scryfall_does_not_know_it(self):
        text, fake = self.run_failed_set_code(404)

        # A text as the exit code: Python prints it and exits with 1.
        self.assertEqual(text, "Scryfall does not know set code 'fra' (404)")
        self.assertEqual([s.url for s in fake.sent], [SET_URL])
        self.assertFalse(self.out_dir.exists())

    def test_other_status_on_the_set_code_is_printed_with_its_reason(self):
        for status, reason in ((301, "Moved Permanently"), (500, "Internal Server Error"),
                               (503, "Service Unavailable")):
            with self.subTest(status=status):
                failure = urllib.error.HTTPError(SET_URL, status, reason, {}, io.BytesIO())

                text, fake = self.run_failed_set_code(failure)

                self.assertEqual(text, f"Scryfall answered HTTP {status} {reason} for set code 'fra'")
                self.assertEqual([s.url for s in fake.sent], [SET_URL])
                self.assertFalse(self.out_dir.exists())


# ------------------------------------------------------ priv_data/format_owned_list.py


class FormatOwnedListTests(CallerCase):
    def setUp(self):
        super().setUp()
        self.owned = self.root / "Owned.csv"
        self.formatted = self.root / "owned_formatted.csv"

    def write_owned(self, path: Path, names: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Name", "Quantity"])
            writer.writerows([name, 1] for name in names)

    def run_main(self, fake: FakeScryfall) -> tuple[int, str]:
        out = io.StringIO()
        with fake.installed(), \
                mock.patch.object(format_owned, "OWNED_CSV", self.owned), \
                mock.patch.object(format_owned, "FORMATTED_CSV", self.formatted), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = format_owned.main()
        return code, out.getvalue()

    def test_batches_start_600ms_after_the_last_answer(self):
        names = [f"Card {n:03d}" for n in range(160)]
        self.write_owned(self.owned, names)
        fake = FakeScryfall(make_card(name) for name in names)

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL] * 3)
        self.assertEqual([len(s.body["identifiers"]) for s in fake.sent], [75, 75, 10])
        self.assert_600ms_gaps(fake, 2)
        for sent in fake.sent:
            self.assertEqual(sent.headers["user-agent"], "MTGPreconUpgrader/1.0")
        with self.formatted.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["name"] for row in rows], names)
        self.assertEqual({row["type_line"] for row in rows}, {"Instant"})

    def test_429_ends_the_run_without_retry(self):
        names = [f"Card {n:03d}" for n in range(160)]
        self.write_owned(self.owned, names)
        # An old file whose rows lack metadata: the run asks for every name again.
        self.write_owned(self.formatted, names)
        before = self.formatted.read_text()
        fake = FakeScryfall(make_card(name) for name in names)
        fake.failures[1] = 429

        code, out = self.run_main(fake)

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertIn("No file written.", out)
        self.assertEqual(len(fake.sent), 2)
        # The one wait before batch 2, and no backoff after the 429.
        self.assertAlmostEqual(sum(fake.sleeps), 0.6, places=9)
        self.assertEqual(self.formatted.read_text(), before)

    def test_script_exits_with_1_on_a_429(self):
        """priv_data/format_owned_list.py imports the helper from ../scripts.

        A copy of the script runs from a temporary priv_data directory, so it reads a test
        Owned.csv; the helper comes from sys.modules, the same module that the fake patches.
        """
        script = self.root / "priv_data" / "format_owned_list.py"
        script.parent.mkdir()
        shutil.copyfile(ROOT / "priv_data" / "format_owned_list.py", script)
        self.write_owned(script.parent / "Owned.csv", ["Sol Ring"])
        fake = FakeScryfall([make_card("Sol Ring")])
        fake.failures[0] = 429

        code, out = self.run_as_script(fake, script)

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertEqual(len(fake.sent), 1)
        self.assertFalse((script.parent / "owned_formatted.csv").exists())

    def test_helper_is_the_scripts_module(self):
        self.assertIs(format_owned.scryfall_api, scryfall_api)


# ------------------------------------------- build_price_index.py, refresh_scryfall_mirror.py
# DEC-1114 N3: each script sends its one GET /bulk-data through the helper. The download of the
# export from data.scryfall.io stays outside it: that host has no limit.

BULK_DATA_URL = f"{API}/bulk-data"
EXPORT_URL = "https://data.scryfall.io/oracle-cards/oracle-cards-20261015090000.jsonl.gz"


def bulk_fake() -> FakeScryfall:
    """/bulk-data names one oracle_cards export, and the export holds one card."""
    fake = FakeScryfall()
    fake.pages = {BULK_DATA_URL: {"object": "list", "data": [
        {"type": "oracle_cards", "updated_at": "2026-10-15T09:00:00.000+00:00",
         "jsonl_download_uri": EXPORT_URL}]}}
    card = make_card("Sol Ring", legalities={"commander": "legal"})
    # The body of the second request, the download.
    fake.failures[1] = gzip.compress(json.dumps(card).encode() + b"\n")
    return fake


class BulkDataCase(CallerCase):
    """One bulk-data script, its files in a temporary folder. The script prints to stderr."""

    module = None
    folder = ""  # the module's name of the folder that holds its files
    files = ()  # the module's names of its files

    def setUp(self):
        super().setUp()
        self.folder_path = self.root / "out"

    def run_main(self, fake: FakeScryfall, *argv: str) -> tuple[int, str]:
        err = io.StringIO()
        with fake.installed(), contextlib.ExitStack() as stack, contextlib.redirect_stderr(err):
            # The script names its files relative to PROJECT_ROOT.
            stack.enter_context(mock.patch.object(self.module, "PROJECT_ROOT", self.root))
            stack.enter_context(mock.patch.object(self.module, self.folder, self.folder_path))
            for name in self.files:
                path = self.folder_path / getattr(self.module, name).name
                stack.enter_context(mock.patch.object(self.module, name, path))
            code = self.module.main(list(argv))
        return code, err.getvalue()

    def written(self) -> list[str]:
        """The files under the temporary folder."""
        return sorted(p.name for p in self.root.rglob("*") if p.is_file())

    def check_bulk_data_goes_through_the_helper(self):
        """GET /bulk-data waits as the helper's requests do; the download does not wait."""
        fake = bulk_fake()
        fake.state = {"last_answer": fake.now - 0.2, "last_slow_answer": fake.now - 0.2}

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [BULK_DATA_URL, EXPORT_URL])
        bulk, export = fake.sent
        self.assertEqual(bulk.headers["user-agent"], "MTGPreconUpgrader/1.0")
        self.assertEqual(bulk.headers["accept"], "application/json")
        self.assertEqual(export.headers["user-agent"], self.module.USER_AGENT)
        self.assertEqual(len(fake.sleeps), 1)
        self.assertAlmostEqual(fake.sleeps[0], 0.4, places=9)
        self.assertEqual(self.written(), sorted(getattr(self.module, n).name for n in self.files))

    def check_429_on_bulk_data_ends_the_run(self):
        fake = bulk_fake()
        fake.failures[0] = 429

        code, out = self.run_main(fake)

        self.assertEqual(code, 1)
        self.assert_429_text(out)
        self.assertIn("No file written.", out)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(self.written(), [])


class BuildPriceIndexTests(BulkDataCase):
    module = build_price_index
    folder = "OUT_DIR"
    files = ("INDEX_FILE", "META_FILE")

    def test_bulk_data_goes_through_the_helper(self):
        self.check_bulk_data_goes_through_the_helper()
        index = json.loads((self.folder_path / "price-index.json").read_text())
        self.assertEqual(index, {"sol ring": [1.2, 1.5]})

    def test_429_on_bulk_data_ends_the_run(self):
        self.check_429_on_bulk_data_ends_the_run()

    def test_helper_is_the_scripts_module(self):
        self.assertIs(build_price_index.scryfall_api, scryfall_api)


class RefreshScryfallMirrorTests(BulkDataCase):
    module = refresh_mirror
    folder = "PRIV_DIR"
    files = ("MIRROR_FILE", "META_FILE")

    def test_bulk_data_goes_through_the_helper(self):
        self.check_bulk_data_goes_through_the_helper()
        mirror = json.loads((self.folder_path / "scryfall-oracle.json").read_text())
        self.assertEqual([card["name"] for card in mirror], ["Sol Ring"])

    def test_429_on_bulk_data_ends_the_run(self):
        self.check_429_on_bulk_data_ends_the_run()

    def test_helper_is_the_scripts_module(self):
        self.assertIs(refresh_mirror.scryfall_api, scryfall_api)


class HelperImportTests(unittest.TestCase):
    def test_each_script_finds_the_helper_by_its_own_path(self):
        """A fresh interpreter in isolated mode loads each script by its path, without running
        main(): only the script's own sys.path line can find scripts/scryfall_api.py."""
        load = (
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('caller', sys.argv[1])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "print(module.scryfall_api.__file__)\n"
        )
        for script in ("scripts/compute_tokens.py", "scripts/check_game_changers.py",
                       "scripts/prerelease/dump_set.py", "priv_data/format_owned_list.py",
                       "scripts/build_price_index.py", "scripts/refresh_scryfall_mirror.py"):
            with self.subTest(script=script):
                # -B: -I ignores PYTHONDONTWRITEBYTECODE, and the case writes no .pyc file.
                result = subprocess.run(
                    [sys.executable, "-I", "-B", "-c", load, str(ROOT / script)],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    Path(result.stdout.strip()).resolve(), ROOT / "scripts" / "scryfall_api.py")


if __name__ == "__main__":
    unittest.main()

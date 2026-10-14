"""DEC-1076 — four more callers of Scryfall's 2-a-second methods keep the helper's rules.

scripts/compute_tokens.py, scripts/check_game_changers.py, scripts/prerelease/dump_set.py and
priv_data/format_owned_list.py send every request through scripts/scryfall_api.py:

1. a request starts 600 ms or more after the last answer arrived;
2. a 429 ends the run: no file written, the status and "wait 30 seconds or more" on screen,
   exit code 1 and no later request.

No test here sends a live request: FakeScryfall (tests/test_scryfall_fetch.py) stands in for
the helper's opener and for the clock.
"""

import contextlib
import csv
import importlib
import io
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from tests.test_scryfall_fetch import FakeScryfall, make_card, scryfall_api

compute_tokens = importlib.import_module("scripts.compute_tokens")
check_gc = importlib.import_module("scripts.check_game_changers")
dump_set = importlib.import_module("scripts.prerelease.dump_set")
format_owned = importlib.import_module("priv_data.format_owned_list")

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.scryfall.com"
COLLECTION_URL = f"{API}/cards/collection"
WAIT = "wait 30 seconds or more"


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
        self.assertIn(WAIT, out)

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
VALAKUT_URL = f"{API}/cards/named?fuzzy=Valakut%20Awakening"


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
        VALAKUT_URL: make_card(VALAKUT, layout="modal_dfc"),
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
            "one", "Goblin Maker", *fillers, "Orc Caller", "Crown Seeker", VALAKUT)
        fake = token_fake(make_card(name) for name in fillers)

        code, _ = self.run_main(fake)

        self.assertEqual(code, 0)
        self.assertEqual(
            [s.url for s in fake.sent],
            [COLLECTION_URL, COLLECTION_URL, VALAKUT_URL, GOBLIN_URL, ARMY_URL, MONARCH_URL])
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
            "a fuzzy /cards/named": (VALAKUT, [COLLECTION_URL, VALAKUT_URL]),
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
                       "scripts/prerelease/dump_set.py", "priv_data/format_owned_list.py"):
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, "-I", "-c", load, str(ROOT / script)],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    Path(result.stdout.strip()).resolve(), ROOT / "scripts" / "scryfall_api.py")


if __name__ == "__main__":
    unittest.main()

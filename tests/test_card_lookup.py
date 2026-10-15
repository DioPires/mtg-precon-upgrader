"""DEC-1124 — scripts/card_lookup.py reads the oracle mirror first and sends a miss through the helper.

1. A name in the mirror prints from the mirror and sends no request.
2. A name that the mirror lacks sends one /cards/named?exact= request through
   scripts/scryfall_api.py, so two requests keep the 600 ms wait.
3. A 404 prints "not found" and the run goes on; a 429 ends the run with exit code 1.
4. A worktree without a mirror reads the main worktree's copy.

No test here sends a live request: FakeScryfall (tests/test_scryfall_fetch.py) stands in for
the helper's opener and for the clock. Each case writes its own mirror in a temporary folder.
"""

import contextlib
import importlib
import io
import json
import runpy
import subprocess
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from tests.test_scryfall_fetch import FakeScryfall, make_card, scryfall_api

card_lookup = importlib.import_module("scripts.card_lookup")

SCRIPT = Path(card_lookup.__file__).resolve()
NAMED_URL = "https://api.scryfall.com/cards/named"
SEARCH_URL = "https://api.scryfall.com/cards/search"
UPDATED_AT = "2026-10-08T09:01:59.811+00:00"
WAIT = "wait 30 seconds or more"
KEYS = ["name", "mana_cost", "cmc", "type_line", "oracle_text", "power", "toughness",
        "loyalty", "defense", "color_identity", "legalities", "card_faces", "source"]

# Mirror entries as scripts/refresh_scryfall_mirror.py trims them.
MIRROR_CARDS = [
    {"name": "Sol Ring", "mana_cost": "{1}", "cmc": 1.0, "type_line": "Artifact",
     "oracle_text": "{T}: Add {C}{C}.", "colors": [], "color_identity": [],
     "legalities": {"commander": "legal", "legacy": "banned"}},
    {"name": "Lórien Revealed", "mana_cost": "{3}{U}{U}", "cmc": 5.0, "type_line": "Sorcery",
     "oracle_text": "Draw three cards.", "colors": ["U"], "color_identity": ["U"],
     "legalities": {"commander": "legal"}},
    {"name": "Fire // Ice", "mana_cost": "{1}{R} // {1}{U}", "cmc": 4.0,
     "type_line": "Instant // Instant", "colors": ["R", "U"], "color_identity": ["R", "U"],
     "legalities": {"commander": "legal"},
     "card_faces": [
         {"name": "Fire", "mana_cost": "{1}{R}", "type_line": "Instant",
          "oracle_text": "Fire deals 2 damage divided as you choose among one or two targets."},
         {"name": "Ice", "mana_cost": "{1}{U}", "type_line": "Instant",
          "oracle_text": "Tap target permanent.\nDraw a card."}]},
    {"name": "Delver of Secrets // Insectile Aberration", "cmc": 1.0,
     "type_line": "Creature — Human Wizard // Creature — Human Insect",
     "color_identity": ["U"], "legalities": {"commander": "legal"},
     "card_faces": [
         {"name": "Delver of Secrets", "mana_cost": "{U}", "type_line": "Creature — Human Wizard",
          "oracle_text": "Transform text.", "colors": ["U"], "power": "1", "toughness": "1"},
         {"name": "Insectile Aberration", "mana_cost": "", "type_line": "Creature — Human Insect",
          "oracle_text": "Flying", "colors": ["U"], "power": "3", "toughness": "2"}]},
]


def write_mirror(root: Path, cards=MIRROR_CARDS) -> None:
    """The mirror and its meta file under ``root``/priv_data, as the refresh script writes them."""
    priv = root / "priv_data"
    priv.mkdir(parents=True)
    (priv / "scryfall-oracle.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    (priv / "scryfall-oracle.meta.json").write_text(json.dumps({"scryfall_updated_at": UPDATED_AT}))


def git(*args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


def objects(out: str) -> list[dict]:
    """The JSON objects on the screen, one for each line that starts with ``{``."""
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


class LookupCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "repo"
        write_mirror(self.root)

    def run_lookup(self, fake: FakeScryfall, *argv: str, root: Path | None = None):
        """Run main() with PROJECT_ROOT at ``root``; return the exit code, stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        with fake.installed(), \
                mock.patch.object(card_lookup, "PROJECT_ROOT", root or self.root), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = card_lookup.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def named_urls(self, fake: FakeScryfall) -> list[str]:
        return [s.url for s in fake.sent if urllib.parse.urlsplit(s.url).path == "/cards/named"]

    def make_worktree(self, with_main_mirror: bool) -> Path:
        """A repository with a linked worktree; git ignores neither tree's mirror here, and
        the worktree has none. Returns the worktree's path."""
        main = self.tmp / "main"
        main.mkdir()
        git("-C", str(main), "init", "-q")
        git("-C", str(main), "commit", "-q", "--allow-empty", "-m", "init")
        worktree = main / "wt-dec1124"
        git("-C", str(main), "worktree", "add", "-q", "--detach", str(worktree))
        if with_main_mirror:
            write_mirror(main)
        self.assertFalse((worktree / "priv_data").exists())
        return worktree


class MirrorCases(LookupCase):
    def test_name_in_the_mirror_prints_from_the_mirror_with_no_request(self):
        """a. A mirror hit prints every field and sends 0 requests."""
        fake = FakeScryfall()
        code, out, err = self.run_lookup(fake, "Sol Ring")
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent, [])
        self.assertEqual(err, "")
        [card] = objects(out)
        self.assertEqual(list(card), KEYS)
        self.assertEqual(card, {
            "name": "Sol Ring", "mana_cost": "{1}", "cmc": 1.0, "type_line": "Artifact",
            "oracle_text": "{T}: Add {C}{C}.", "power": None, "toughness": None,
            "loyalty": None, "defense": None, "color_identity": [],
            "legalities": {"commander": "legal"}, "card_faces": None,
            "source": f"mirror {UPDATED_AT}",
        })

    def test_case_and_accents_match(self):
        """b. "lorien revealed" and "LORIEN REVEALED" find "Lórien Revealed"."""
        fake = FakeScryfall()
        code, out, _ = self.run_lookup(fake, "lorien revealed", "LÓRIEN REVEALED", "LORIEN REVEALED")
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent, [])
        self.assertEqual([c["name"] for c in objects(out)], ["Lórien Revealed"] * 3)

    def test_front_face_finds_its_two_part_card(self):
        """b. A front-face name and a full name find the "A // B" card, with its faces."""
        fake = FakeScryfall()
        code, out, _ = self.run_lookup(fake, "fire", "Fire // Ice", "delver of secrets")
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent, [])
        fire, fire_full, delver = objects(out)
        self.assertEqual(fire["name"], "Fire // Ice")
        self.assertEqual(fire, fire_full)
        self.assertEqual([face["name"] for face in fire["card_faces"]], ["Fire", "Ice"])
        self.assertEqual(delver["name"], "Delver of Secrets // Insectile Aberration")
        self.assertIsNone(delver["mana_cost"])
        self.assertEqual(delver["card_faces"][0]["mana_cost"], "{U}")
        self.assertEqual(delver["card_faces"][1]["power"], "3")

    def test_mirror_without_meta_file_still_prints(self):
        fake = FakeScryfall()
        (self.root / "priv_data" / "scryfall-oracle.meta.json").unlink()
        code, out, _ = self.run_lookup(fake, "Sol Ring")
        self.assertEqual(code, 0)
        self.assertEqual(objects(out)[0]["source"], "mirror unknown")
        self.assertEqual(fake.sent, [])


class ApiCases(LookupCase):
    def test_missing_name_sends_one_named_exact_request(self):
        """c. A name that the mirror lacks sends exactly 1 /cards/named?exact= request."""
        fake = FakeScryfall([make_card("Brand New Card")])
        code, out, _ = self.run_lookup(fake, "Brand New Card")
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [f"{NAMED_URL}?exact=Brand%20New%20Card"])
        [card] = objects(out)
        self.assertEqual(list(card), KEYS)
        self.assertEqual(card["name"], "Brand New Card")
        self.assertEqual(card["oracle_text"], "Text of Brand New Card.")
        self.assertEqual(card["source"], "api")

    def test_two_missing_names_keep_the_600ms_wait(self):
        """c. The second request starts 600 ms after the first answer, through the helper."""
        fake = FakeScryfall([make_card("First New Card"), make_card("Second New Card")])
        code, out, _ = self.run_lookup(fake, "First New Card", "Sol Ring", "Second New Card")
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.sent), 2)
        self.assertEqual(len(fake.gaps()), 1)
        self.assertAlmostEqual(fake.gaps()[0], 0.6, places=9)
        self.assertEqual([c["source"] for c in objects(out)], ["api", f"mirror {UPDATED_AT}", "api"])

    def test_api_flag_sends_one_request_for_a_name_in_the_mirror(self):
        """c. --api skips the mirror."""
        fake = FakeScryfall([make_card("Sol Ring")])
        code, out, _ = self.run_lookup(fake, "--api", "Sol Ring")
        self.assertEqual(code, 0)
        self.assertEqual(self.named_urls(fake), [f"{NAMED_URL}?exact=Sol%20Ring"])
        self.assertEqual(objects(out)[0]["source"], "api")

    def test_404_prints_not_found_and_the_next_name_still_prints(self):
        """d. A 404 prints "not found: NAME", the next names print, and the exit code is 2."""
        fake = FakeScryfall([make_card("Brand New Card")])
        code, out, _ = self.run_lookup(fake, "No Such Card", "Brand New Card", "Sol Ring")
        self.assertEqual(code, 2)
        lines = out.splitlines()
        self.assertEqual(lines[0], "not found: No Such Card")
        self.assertEqual([c["name"] for c in objects(out)], ["Brand New Card", "Sol Ring"])
        self.assertEqual(len(fake.sent), 2)

    def test_429_on_the_first_of_three_missing_names_ends_the_run(self):
        """e. Exit code 1, the helper's text, 1 request and no later call of the helper."""
        fake = FakeScryfall([make_card("Second New Card"), make_card("Third New Card")])
        fake.failures[0] = 429
        with mock.patch.object(scryfall_api, "request", wraps=scryfall_api.request) as spy:
            code, out, _ = self.run_lookup(
                fake, "First New Card", "Second New Card", "Third New Card")
        self.assertEqual(code, 1)
        self.assertIn("429", out)
        self.assertIn(WAIT, out)
        self.assertEqual(out.count(WAIT), 1)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(spy.call_count, 1)
        self.assertNotIn("Second New Card", out)
        self.assertNotIn("Third New Card", out)

    def test_stop_of_another_process_sends_nothing_and_ends_the_run(self):
        """A stop that another process's 429 started in the shared state: no request, exit 1."""
        fake = FakeScryfall()
        fake.state = {"blocked_at": fake.now - 5, "blocked_until": fake.now + 25}
        code, out, _ = self.run_lookup(fake, "First New Card", "Second New Card")
        self.assertEqual(code, 1)
        self.assertIn(WAIT, out)
        self.assertEqual(fake.sent, [])

    def test_other_failed_request_ends_the_run(self):
        fake = FakeScryfall([make_card("Second New Card")])
        fake.failures[0] = 500
        code, out, _ = self.run_lookup(fake, "First New Card", "Second New Card")
        self.assertEqual(code, 1)
        self.assertIn("Scryfall request failed: HTTP Error 500", out)
        self.assertEqual(len(fake.sent), 1)

    def test_two_part_name_goes_out_as_its_front_face(self):
        """Scryfall finds an "A // B" card by its front face; the full name must match."""
        fake = FakeScryfall([make_card("Brand New // Card Back")])
        code, out, _ = self.run_lookup(fake, "Brand New // Card Back", "Brand New // Other Back")
        self.assertEqual(code, 2)
        self.assertEqual(self.named_urls(fake), [f"{NAMED_URL}?exact=Brand%20New"] * 2)
        self.assertEqual([c["name"] for c in objects(out)], ["Brand New // Card Back"])
        self.assertIn("not found: Brand New // Other Back", out)

    def test_script_exits_with_main_code(self):
        """The __main__ block hands main()'s code to sys.exit: 1 on a 429."""
        fake = FakeScryfall()
        fake.failures[0] = 429
        out = io.StringIO()
        with fake.installed(), contextlib.redirect_stdout(out), \
                mock.patch("sys.argv", [str(SCRIPT), "--api", "First New Card", "Second New Card"]), \
                self.assertRaises(SystemExit) as raised:
            runpy.run_path(str(SCRIPT), run_name="__main__")
        self.assertEqual(raised.exception.code, 1)
        self.assertIn(WAIT, out.getvalue())
        self.assertEqual(len(fake.sent), 1)


class SearchCases(LookupCase):
    QUERY = "o:proliferate id<=bg"

    def search_url(self) -> str:
        return f"{SEARCH_URL}?q={urllib.parse.quote(self.QUERY)}"

    def test_search_sends_one_request_to_cards_search(self):
        """f. --search sends 1 request and prints total_cards and the first page."""
        # A transform card has no top-level mana_cost; its faces carry the costs.
        delver = make_card("Delver of Secrets // Insectile Aberration", layout="transform",
                           type_line="Creature — Human Wizard // Creature — Human Insect")
        del delver["mana_cost"]
        delver["card_faces"][0]["mana_cost"] = "{U}"
        delver["card_faces"][1]["mana_cost"] = ""
        fake = FakeScryfall()
        fake.pages[self.search_url()] = {
            "object": "list", "total_cards": 245, "has_more": True,
            "data": [make_card("Sol Ring", mana_cost="{1}", type_line="Artifact"), delver],
        }
        code, out, _ = self.run_lookup(fake, "--search", self.QUERY)
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.sent), 1)
        parts = urllib.parse.urlsplit(fake.sent[0].url)
        self.assertEqual(parts.path, "/cards/search")
        self.assertEqual(urllib.parse.parse_qs(parts.query), {"q": [self.QUERY]})
        self.assertEqual(out.splitlines(), [
            "total_cards: 245",
            "Sol Ring | {1} | Artifact",
            ("Delver of Secrets // Insectile Aberration | {U} //  | "
             "Creature — Human Wizard // Creature — Human Insect"),
        ])

    def test_search_that_finds_nothing_exits_with_2(self):
        fake = FakeScryfall()
        code, out, _ = self.run_lookup(fake, "--search", self.QUERY)
        self.assertEqual(code, 2)
        self.assertEqual(out.splitlines(), ["total_cards: 0"])
        self.assertEqual(len(fake.sent), 1)

    def test_search_429_ends_the_run(self):
        fake = FakeScryfall()
        fake.failures[0] = 429
        code, out, _ = self.run_lookup(fake, "--search", self.QUERY)
        self.assertEqual(code, 1)
        self.assertIn(WAIT, out)
        self.assertEqual(len(fake.sent), 1)

    def test_names_and_search_together_are_refused(self):
        fake = FakeScryfall()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(io.StringIO()):
            self.run_lookup(fake, "--search", self.QUERY, "Sol Ring")
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(fake.sent, [])


class WorktreeCases(LookupCase):
    def test_worktree_without_mirror_reads_the_main_worktree_copy(self):
        """g. The script reads the mirror of the parent of ``git rev-parse --git-common-dir``."""
        worktree = self.make_worktree(with_main_mirror=True)
        fake = FakeScryfall()
        code, out, err = self.run_lookup(fake, "Sol Ring", "lorien revealed", root=worktree)
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent, [])
        self.assertEqual(err, "")
        self.assertEqual([c["source"] for c in objects(out)], [f"mirror {UPDATED_AT}"] * 2)

    def test_main_worktree_reads_its_own_copy(self):
        worktree = self.make_worktree(with_main_mirror=True)
        fake = FakeScryfall()
        code, _, _ = self.run_lookup(fake, "Sol Ring", root=worktree.parent)
        self.assertEqual(code, 0)
        self.assertEqual(fake.sent, [])

    def test_without_any_mirror_every_name_goes_to_scryfall(self):
        """g. With neither mirror: one warning on stderr, one request for each name."""
        worktree = self.make_worktree(with_main_mirror=False)
        fake = FakeScryfall([make_card("Sol Ring"), make_card("Lórien Revealed")])
        code, out, err = self.run_lookup(fake, "Sol Ring", "Lórien Revealed", root=worktree)
        self.assertEqual(code, 0)
        self.assertEqual(self.named_urls(fake), [
            f"{NAMED_URL}?exact=Sol%20Ring",
            f"{NAMED_URL}?exact=L%C3%B3rien%20Revealed",
        ])
        self.assertAlmostEqual(fake.gaps()[0], 0.6, places=9)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("warning: no priv_data/scryfall-oracle.json", err)
        self.assertEqual([c["source"] for c in objects(out)], ["api", "api"])

    def test_folder_outside_a_repository_without_mirror_goes_to_scryfall(self):
        fake = FakeScryfall([make_card("Sol Ring")])
        outside = self.tmp / "not-a-repo"
        outside.mkdir()
        with mock.patch.dict("os.environ", {"GIT_CEILING_DIRECTORIES": str(self.tmp)}):
            code, _, err = self.run_lookup(fake, "Sol Ring", root=outside)
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.sent), 1)
        self.assertIn("warning", err)


if __name__ == "__main__":
    unittest.main()

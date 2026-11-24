"""scripts/sync_spellbook_combos.py replaces its cached export only with a download that passes
the scan: a readable gzip holding one JSON object whose "variants" list holds objects of the
expected shape, at least 1000 of them scanned and kept.

Each case runs a copy of the script as __main__ in a temporary project folder, so every path
that the script derives from its own location (priv_data/spellbook/, data/spellbook/,
data/commanders/) lies in that folder. urllib.request.urlopen answers with the case's bytes:
no case sends a request. The folder holds a matcher index and two decks' spellbook-combos.json
with old content, so a case can tell whether the run rewrote them; the decks' files, the matcher
index and its sidecar record the corpus that write_cache's meta file names, as after a full run.
"""

import contextlib
import copy
import gzip
import io
import json
import os
import runpy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
VARIANTS_URL = "https://json.commanderspellbook.com/variants.json.gz"
OLD_TIMESTAMP = "2026-11-01T00:00:00Z"
NEW_TIMESTAMP = "2026-11-20T00:00:00Z"
CACHE_NAMES = ["spellbook.meta.json", "variants.json.gz"]
OLD_MATCHER_INDEX = b'{"meta": {"corpusVersion": "2026-11-01T00:00:00Z"}, "note": "old matcher index"}'
OLD_DECK_COMBOS = b'{"meta": {"corpusVersion": "2026-11-01T00:00:00Z"}, "note": "old deck file"}'
OLD_SIDECAR = b'{"corpusVersion": "2026-11-01T00:00:00Z"}'
OLDER_TIMESTAMP = "2026-10-01T00:00:00Z"
NOT_GZIP = b"<html><body>502 Bad Gateway</body></html>"
# A readable gzip with the header fields of the corpus that the meta file names, whose
# variants list breaks off inside its first variant.
BROKEN_AFTER_HEADER = gzip.compress(
    b'{"timestamp": "2026-11-01T00:00:00Z", "version": "5.0", "variants": [{"id": ', mtime=0)
REQUIREMENT = {"quantity": 1, "template": {"id": 7, "name": "a sacrifice outlet",
                                           "scryfallQuery": "o:sacrifice"}}
FEATURE = {"feature": {"id": 3, "name": "Infinite mana"}}
DROP = object()  # in a wrong-shape case: remove the field


def variant(n: int) -> dict:
    """A variant that the scan keeps (OK, commander-legal, one card), with every field this
    run reads."""
    return {"id": f"{n}-{n + 1}", "status": "OK", "spoiler": False,
            "legalities": {"commander": True},
            "uses": [{"card": {"id": n, "name": f"Card {n}", "oracleId": f"oracle-{n}"},
                      "mustBeCommander": False, "quantity": 1, "zoneLocations": ["B"]}],
            "requires": [], "produces": [], "identity": "C", "bracketTag": "E",
            "manaNeeded": "", "manaValueNeeded": 0, "easyPrerequisites": "",
            "notablePrerequisites": "", "description": "", "notes": "",
            "prices": {"tcgplayer": "1.00"}, "popularity": 0}


def export_text(timestamp: str, variants: list[dict], aliases: bool = True,
                header_last: bool = False, version: str = "5.0") -> str:
    """An export's JSON. The real export ends with an "aliases" list after its variants;
    ``header_last`` puts "timestamp" and "version" after both lists."""
    header = {"timestamp": timestamp, "version": version}
    body = {} if header_last else dict(header)
    body["variants"] = variants
    if aliases:
        body["aliases"] = [{"id": "0-1-2", "variant": None}]
    if header_last:
        body.update(header)
    return json.dumps(body)


def export(timestamp: str, variants: list[dict], aliases: bool = True) -> bytes:
    return gzip.compress(export_text(timestamp, variants, aliases).encode(), mtime=0)


def good(timestamp: str, count: int = 1000, aliases: bool = True) -> bytes:
    return export(timestamp, [variant(n) for n in range(count)], aliases)


def gz(text: str) -> bytes:
    return gzip.compress(text.encode(), mtime=0)


def changed_export() -> bytes:
    """The export of the corpus that the meta file names, with other bytes: variant 5 now uses
    Card 1, which both decks run, so a rebuild from it gives each deck the combo 5-6."""
    variants = [variant(n) for n in range(1000)]
    variants[5]["uses"][0]["card"].update(id=1, name="Card 1", oracleId="oracle-1")
    return export(OLD_TIMESTAMP, variants)


class SyncSpellbookCombosTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "sync_spellbook_combos.py", self.root / "scripts")
        self.matcher_index = self.root / "data" / "spellbook" / "matcher-index.json"
        self.matcher_index.parent.mkdir(parents=True)
        self.matcher_index.write_bytes(OLD_MATCHER_INDEX)
        self.sidecar = self.matcher_index.with_name("matcher-index.meta.json")
        self.sidecar.write_bytes(OLD_SIDECAR)
        self.deck_combos = {}
        for deck_id, commander in (("deck-a", "Card 0"), ("deck-b", "Card 2")):
            deck = self.root / "data" / "commanders" / deck_id
            deck.mkdir(parents=True)
            (deck / "deck.json").write_text(
                json.dumps({"commander": commander, "decklist": [{"name": "Card 1"}]}))
            self.deck_combos[deck_id] = deck / "spellbook-combos.json"
            self.deck_combos[deck_id].write_bytes(OLD_DECK_COMBOS)
        self.priv = self.root / "priv_data" / "spellbook"
        self.raw = self.priv / "variants.json.gz"
        self.meta = self.priv / "spellbook.meta.json"
        self.sent = []

    def write_cache(self, raw: bytes | None = None):
        """The cached export (by default the last good download) and the meta file of the run
        that read it."""
        self.priv.mkdir(parents=True, exist_ok=True)
        self.raw.write_bytes(good(OLD_TIMESTAMP) if raw is None else raw)
        self.write_meta()

    def write_meta(self):
        self.priv.mkdir(parents=True, exist_ok=True)
        self.meta.write_text(json.dumps({"corpus_timestamp": OLD_TIMESTAMP}))

    def reset_derivatives(self):
        """The decks' files, the matcher index and its sidecar as the fixture made them (on the
        old corpus)."""
        for deck_file in self.deck_combos.values():
            deck_file.write_bytes(OLD_DECK_COMBOS)
        self.matcher_index.write_bytes(OLD_MATCHER_INDEX)
        self.sidecar.write_bytes(OLD_SIDECAR)

    def snapshot(self) -> dict:
        """Each path under the project folder but scripts/: a link's target, a file's bytes, or
        None for a folder. Links to folders are not followed."""
        return {
            p.relative_to(self.root).as_posix():
                p.readlink() if p.is_symlink() else p.read_bytes() if p.is_file() else None
            for p in sorted(self.root.rglob("*"))
            if p.relative_to(self.root).parts[0] != "scripts"
        }

    def corpus_of(self, path: Path) -> str:
        return json.loads(path.read_text())["meta"]["corpusVersion"]

    def run_script(self, body: bytes, *argv: str) -> tuple[int, str]:
        """Run the copied script; the download answers with ``body``. Returns the exit code
        and the screen (the script prints to stderr)."""
        def urlopen(req, timeout=None):
            self.sent.append(req.full_url)
            return io.BytesIO(body)

        script = self.root / "scripts" / "sync_spellbook_combos.py"
        err = io.StringIO()
        with mock.patch("urllib.request.urlopen", urlopen), \
                mock.patch("sys.argv", [script.name, *argv]), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            runpy.run_path(str(script), run_name="__main__")
        return raised.exception.code, err.getvalue()

    def check_bad_download(self, body: bytes, problem: str, *argv: str):
        """The run exits 2 and names the problem; the cached export, the meta file and the
        derivative files are byte-identical, and no temporary file is left."""
        self.write_cache()
        before = self.snapshot()
        self.sent.clear()

        code, out = self.run_script(body, *argv)

        self.assertEqual(code, 2)
        self.assertIn(problem, out)
        self.assertIn("Corpus left unchanged (degrade to 'corpus stale').\n", out)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.sent, [VARIANTS_URL])

    # ------------------------------------------------------------------ good downloads

    def test_good_download_replaces_the_cached_export(self):
        self.write_cache()
        body = good(NEW_TIMESTAMP)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.raw.read_bytes(), body)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["corpus_timestamp"], NEW_TIMESTAMP)
        self.assertEqual(meta["variant_count"], 1000)
        self.assertEqual(sorted(p.name for p in self.priv.iterdir()), CACHE_NAMES)
        self.assertEqual(self.corpus_of(self.matcher_index), NEW_TIMESTAMP)
        self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), NEW_TIMESTAMP)
        self.assertEqual(self.corpus_of(self.deck_combos["deck-b"]), NEW_TIMESTAMP)

    def test_header_string_that_says_variants(self):
        """A header member whose value is the text "variants" is a header member like any
        other."""
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        self.write_cache()

        code, out = self.run_script(gz('{"exportName": "variants", ' + text[1:]))

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], NEW_TIMESTAMP)

    def test_timestamp_and_version_after_the_list(self):
        """"timestamp" and "version" may sit after the variants list."""
        self.write_cache()
        body = gz(export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)], header_last=True))

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], NEW_TIMESTAMP)
        meta = json.loads(self.matcher_index.read_text())["meta"]
        self.assertEqual((meta["corpusVersion"], meta["spellbookApiVersion"]), (NEW_TIMESTAMP, "5.0"))

    def test_version_after_the_list(self):
        """The version (here 7.3.0, the other tests' 5.0) is the export's own, wherever it
        sits."""
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)], version="7.3.0")
        moved = text.replace('"version": "7.3.0", ', "").replace('"aliases"', '"version": "7.3.0", "aliases"')
        self.assertNotEqual(moved, text)
        self.write_cache()

        code, _ = self.run_script(gz(moved))

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.matcher_index.read_text())["meta"]["spellbookApiVersion"], "7.3.0")
        self.assertEqual(json.loads(self.meta.read_text())["spellbook_version"], "7.3.0")

    def test_current_corpus_named_after_the_list_is_scanned(self):
        """With the timestamp after the list, the run cannot know the corpus is current before
        the scan: an identical download is scanned, then changes nothing (the cached file is
        not rewritten, and neither are the derivative files)."""
        body = gz(export_text(OLD_TIMESTAMP, [variant(n) for n in range(1000)], header_last=True))
        self.write_cache(raw=body)
        before = self.snapshot()
        identity = (self.raw.stat().st_ino, self.raw.stat().st_mtime_ns)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertIn("  scanned 1,000; kept 1,000", out)
        self.assertTrue(out.endswith(
            f"Corpus current ({OLD_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))
        self.assertEqual((self.raw.stat().st_ino, self.raw.stat().st_mtime_ns), identity)
        self.assertEqual(self.snapshot(), before)

    def test_offline_run_on_a_current_corpus_named_after_the_list(self):
        body = gz(export_text(OLD_TIMESTAMP, [variant(n) for n in range(1000)], header_last=True))
        self.write_cache(raw=body)
        before = self.snapshot()

        code, out = self.run_script(NOT_GZIP, "--offline")

        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [])
        self.assertTrue(out.endswith(
            f"Corpus current ({OLD_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))
        self.assertNotIn("replaced", out)
        self.assertEqual(self.snapshot(), before)

    def check_rebuilt_from(self, body: bytes, out: str):
        """The download is the cache now, and the run rebuilt the derivative files and wrote
        the meta file from it."""
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.raw.read_bytes(), body)
        self.assertNotEqual(self.matcher_index.read_bytes(), OLD_MATCHER_INDEX)
        self.assertEqual(self.corpus_of(self.matcher_index), OLD_TIMESTAMP)
        for deck_file in self.deck_combos.values():
            self.assertNotEqual(deck_file.read_bytes(), OLD_DECK_COMBOS)
            self.assertEqual(self.corpus_of(deck_file), OLD_TIMESTAMP)
        meta = json.loads(self.meta.read_text())
        self.assertEqual((meta["corpus_timestamp"], meta["variant_count"]), (OLD_TIMESTAMP, 1000))

    def test_current_corpus_named_after_the_list_without_a_cache(self):
        self.write_meta()
        body = gz(export_text(OLD_TIMESTAMP, [variant(n) for n in range(1000)], header_last=True))

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.check_rebuilt_from(body, out)

    def test_current_corpus_named_after_the_list_over_a_corrupt_cache(self):
        self.write_cache(raw=b"junk")
        body = gz(export_text(OLD_TIMESTAMP, [variant(n) for n in range(1000)], header_last=True))

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.check_rebuilt_from(body, out)

    def test_same_timestamp_with_other_bytes_rebuilds(self):
        """The download keeps the cached corpus's timestamp but variant 5 now uses Card 1,
        which deck-a runs: the run rebuilds, and deck-a gains that combo."""
        self.write_cache()
        body = changed_export()

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.check_rebuilt_from(body, out)
        included = json.loads(self.deck_combos["deck-a"].read_text())["included"]
        self.assertEqual([combo["id"] for combo in included], ["0-1", "1-2", "5-6"])

    def test_spoilers_and_commander_illegal_variants_are_not_kept(self):
        """Variant 0 (Card 0, deck-a's commander) is a spoiler and variant 1 (Card 1, in both
        decks) is not commander-legal: neither is kept or matched."""
        variants = [variant(n) for n in range(1002)]
        variants[0]["spoiler"] = True
        variants[1]["legalities"]["commander"] = False
        self.write_cache()

        code, _ = self.run_script(export(NEW_TIMESTAMP, variants))

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.meta.read_text())["variant_count"], 1000)
        index_ids = [row["id"] for row in json.loads(self.matcher_index.read_text())["variants"]]
        self.assertNotIn("0-1", index_ids)
        self.assertNotIn("1-2", index_ids)
        for deck_file in self.deck_combos.values():
            combos = json.loads(deck_file.read_text())
            ids = [c["id"] for c in combos["included"] + combos["nearMisses"]]
            self.assertNotIn("0-1", ids)
            self.assertNotIn("1-2", ids)
        self.assertEqual([c["id"] for c in json.loads(self.deck_combos["deck-b"].read_text())["included"]],
                         ["2-3"])

    def test_two_downloads_use_two_temporary_files(self):
        """Each run's download gets a temporary name of its own in the export's folder."""
        self.write_cache()
        moved = []
        real_replace = os.replace

        def replace(src, dst):
            if Path(dst).name == "variants.json.gz":
                moved.append(Path(src))
            return real_replace(src, dst)

        with mock.patch("os.replace", replace):
            for count in (1000, 1001):
                self.assertEqual(self.run_script(good(NEW_TIMESTAMP, count=count))[0], 0)

        self.assertEqual(len(moved), 2)
        self.assertNotEqual(moved[0].name, moved[1].name)
        for path in moved:
            self.assertEqual(path.parent.resolve(), self.priv.resolve())
            self.assertTrue(path.name.startswith("variants.json.gz.") and path.name.endswith(".tmp"))

    def test_nullable_fields_of_the_real_export(self):
        """The real export has null popularities and null template queries: a null popularity
        is written as 0, a null query as null."""
        variants = [variant(n) for n in range(1000)]
        variants[0]["popularity"] = None
        variants[1]["popularity"] = 9
        variants[11]["requires"] = [{"quantity": 1, "template": {
            "id": 7, "name": "a sacrifice outlet", "scryfallQuery": None}}]
        self.write_cache()

        code, out = self.run_script(export(NEW_TIMESTAMP, variants))

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        index = json.loads(self.matcher_index.read_text())
        self.assertEqual(index["templates"], {"7": {"n": "a sacrifice outlet", "q": None}})
        self.assertEqual([row["pop"] for row in index["variants"] if row["id"] == "0-1"], [0])
        included = json.loads(self.deck_combos["deck-a"].read_text())["included"]
        self.assertEqual([(c["id"], c["popularity"]) for c in included], [("1-2", 9), ("0-1", 0)])

    def test_matching_against_a_deck(self):
        """deck-c: commander Card 3, with Card 4 and the front face of a double-faced card in
        its list. Included: a combo of its own cards (the base variants 3-4 and 4-5), one whose
        piece must be the commander and is (cmd-1), one with the double-faced card by its full
        name (dfc-1). Near-misses, at most two unmet and at least half present and popularity
        1 or more: one card missing (near-1), one template required (tpl-1). Left out: one
        card missing at popularity 0 (pop0-1), Card 4 where only the commander may serve
        (notcmd-1, nothing present), and one card present of three (half-1: two unmet, one
        present, less than halfway)."""
        deck = self.root / "data" / "commanders" / "deck-c"
        deck.mkdir()
        (deck / "deck.json").write_text(json.dumps(
            {"commander": "Card 3", "decklist": [{"name": "Card 4"}, {"name": "Front Face"}]}))

        def special(variant_id, *cards, popularity=0, requires=(), produces=()):
            v = variant(0)
            v.update(id=variant_id, popularity=popularity, requires=list(requires), produces=list(produces))
            v["uses"] = [{"card": {"id": card_id, "name": name, "oracleId": f"oracle-{card_id}"},
                          "mustBeCommander": must, "quantity": 1, "zoneLocations": ["B"]}
                         for card_id, name, must in cards]
            return v

        variants = [variant(n) for n in range(1000)] + [
            special("cmd-1", (3, "Card 3", True)),
            special("dfc-1", (9001, "Front Face // Back Face", False), (4, "Card 4", False),
                    produces=[copy.deepcopy(FEATURE)]),
            special("near-1", (4, "Card 4", False), (999, "Card 999", False), popularity=5),
            special("tpl-1", (4, "Card 4", False), popularity=5, requires=[copy.deepcopy(REQUIREMENT)]),
            special("pop0-1", (4, "Card 4", False), (998, "Card 998", False)),
            special("notcmd-1", (4, "Card 4", True)),
            special("half-1", (4, "Card 4", False), (997, "Card 997", False),
                    (996, "Card 996", False), popularity=5),
        ]
        self.write_cache()

        code, _ = self.run_script(export(NEW_TIMESTAMP, variants))

        self.assertEqual(code, 0)
        combos = json.loads((deck / "spellbook-combos.json").read_text())
        self.assertEqual([c["id"] for c in combos["included"]], ["3-4", "4-5", "cmd-1", "dfc-1"])
        self.assertEqual(
            [(c["id"], c["distance"], c["missing"]) for c in combos["nearMisses"]],
            [("near-1", 1, {"cards": ["Card 999"], "templates": []}),
             ("tpl-1", 1, {"cards": [], "templates": [
                 {"name": "a sacrifice outlet", "query": "o:sacrifice"}]})])
        self.assertEqual(json.loads(self.matcher_index.read_text())["features"], {"3": "Infinite mana"})

    def test_emit_details_writes_the_shards(self):
        """--emit-details writes every kept variant into the shard files and removes an old
        shard. The shard of an id is h % 256 in two hex digits, where h starts at 0 and takes
        h * 131 + ord(character) for each character: "0-1" gives 48, 6333, 829672 and shard
        e8 (829672 = 3240 * 256 + 232); "1-2" gives 49, 6464, 846834 and shard f2
        (846834 = 3307 * 256 + 242)."""
        details = self.root / "data" / "spellbook" / "details"
        details.mkdir()
        (details / "zz.json").write_text("{}")
        self.write_cache()

        code, _ = self.run_script(good(NEW_TIMESTAMP), "--emit-details")

        self.assertEqual(code, 0)
        self.assertNotIn("zz.json", [p.name for p in details.iterdir()])
        ids = sorted(row["id"] for shard in details.iterdir()
                     for row in json.loads(shard.read_text())["variants"])
        self.assertEqual(ids, sorted(f"{n}-{n + 1}" for n in range(1000)))
        for variant_id, shard in (("0-1", "e8"), ("1-2", "f2")):
            rows = json.loads((details / f"{shard}.json").read_text())["variants"]
            self.assertIn(variant_id, [row["id"] for row in rows])

    def test_deck_that_does_not_exist(self):
        """An unknown --deck is warned about; no other deck's file is rebuilt."""
        self.write_cache()

        code, out = self.run_script(good(NEW_TIMESTAMP), "--deck", "deck-z")

        self.assertEqual(code, 0)
        self.assertIn("  WARN: deck-z is not the name of a deck folder (one holding a deck.json) "
                      "under data/commanders/; skipping.\n", out)
        self.assertFalse((self.root / "data" / "commanders" / "deck-z").exists())
        for deck_file in self.deck_combos.values():
            self.assertEqual(deck_file.read_bytes(), OLD_DECK_COMBOS)

    def test_deck_given_as_a_path(self):
        """--deck ./deck-b names a path, not a deck folder's name: it is warned about and
        skipped, and no deck's file changes."""
        self.write_cache()

        code, out = self.run_script(self.raw.read_bytes(), "--deck", "./deck-b")

        self.assertEqual(code, 0)
        self.assertIn("  WARN: ./deck-b is not the name of a deck folder (one holding a deck.json) "
                      "under data/commanders/; skipping.\n", out)
        for deck_file in self.deck_combos.values():
            self.assertEqual(deck_file.read_bytes(), OLD_DECK_COMBOS)

    def test_meta_file_that_records_no_corpus(self):
        """A meta file holding JSON null, or one whose bytes are not UTF-8 (its timestamp
        readable all the same), records no corpus: a default run and an --offline --force run
        rebuild instead of stopping on it."""
        for label, content in (("null", b"null"),
                               ("not UTF-8", b'{"corpus_timestamp": "2026-11-01T00:00:00Z", "x": "\xff"}')):
            for argv in ((), ("--offline", "--force")):
                with self.subTest(label, argv=argv):
                    self.write_cache()
                    self.reset_derivatives()
                    self.meta.write_bytes(content)
                    body = self.raw.read_bytes()

                    code, out = self.run_script(body, *argv)

                    self.assertEqual(code, 0)
                    self.check_rebuilt_from(body, out)

    def test_offline_without_a_cache(self):
        before = self.snapshot()

        code, out = self.run_script(NOT_GZIP, "--offline")

        self.assertEqual(code, 1)
        self.assertIn("variants.json.gz absent and --offline set.", out)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.snapshot(), before)

    def test_unreadable_meta_file_rebuilds(self):
        """A meta file that is not JSON names no corpus: the run rebuilds and rewrites it."""
        self.write_cache()
        self.meta.write_text("{")

        code, out = self.run_script(self.raw.read_bytes())

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)
        self.assertEqual(self.corpus_of(self.matcher_index), OLD_TIMESTAMP)
        included = json.loads(self.deck_combos["deck-a"].read_text())["included"]
        self.assertEqual([c["id"] for c in included], ["0-1", "1-2"])

    def stop_run(self, error: type, body: bytes, *argv: str, patch=contextlib.nullcontext()):
        """Run the copied script under ``patch``; the download answers with ``body`` and the run
        must stop with ``error`` (not an exit)."""
        script = self.root / "scripts" / "sync_spellbook_combos.py"
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: io.BytesIO(body)), \
                mock.patch("sys.argv", [script.name, *argv]), patch, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(error):
            runpy.run_path(str(script), run_name="__main__")

    def stop_on_deck(self, deck_id: str, body: bytes, *argv: str):
        """A run that stops on the deck's broken deck.json (after the matcher index and the
        files of the decks before it are written); the deck.json is then repaired."""
        deck_json = self.root / "data" / "commanders" / deck_id / "deck.json"
        good_deck = deck_json.read_text()
        deck_json.write_text("{")
        self.stop_run(json.JSONDecodeError, body, *argv)
        deck_json.write_text(good_deck)

    def included_ids(self, deck_id: str) -> list[str]:
        return [c["id"] for c in json.loads(self.deck_combos[deck_id].read_text())["included"]]

    def test_interrupted_rebuild_is_redone(self):
        """A same-timestamp download with other bytes (variant 5 now uses Card 1) replaces the
        cache, then the rebuild stops on deck-b's broken deck.json. Once the file is fixed, a
        default run rebuilds: the meta file no longer calls the half-built files current."""
        self.write_cache()
        body = changed_export()
        self.stop_on_deck("deck-b", body)
        self.assertEqual(self.raw.read_bytes(), body)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])

    def test_interrupted_offline_force_run_is_redone(self):
        """The cached export changed under the same timestamp after the derivative files were
        built (variant 5 now uses Card 1), and the --offline --force run that rebuilds from it
        stops on deck-a's broken deck.json, before any deck's file. A default run (the same
        bytes downloaded) and an --offline run each rebuild every deck: both gain the combo
        5-6."""
        body = changed_export()
        for argv in ((), ("--offline",)):
            with self.subTest(argv=argv):
                self.write_cache(raw=body)
                self.reset_derivatives()
                self.stop_on_deck("deck-a", NOT_GZIP, "--offline", "--force")
                self.assertFalse(self.meta.exists())
                self.assertEqual(self.deck_combos["deck-a"].read_bytes(), OLD_DECK_COMBOS)

                code, out = self.run_script(body, *argv)

                self.assertEqual(code, 0)
                self.assertTrue(out.endswith("Done.\n"))
                self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
                self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])

    def test_deck_run_stopped_right_after_replacing_the_cache_is_redone(self):
        """A --deck deck-b run downloads the export with other bytes under the same timestamp
        (variant 5 now uses Card 1) and is stopped (Ctrl-C) right after it replaced the cached
        export, before the rebuild. The next default run (the same bytes) rebuilds every deck:
        no meta file is left to call the old files current."""
        self.write_cache()
        body = changed_export()
        real_replace = os.replace

        def replace(src, dst):
            real_replace(src, dst)
            if Path(dst).name == "variants.json.gz":
                raise KeyboardInterrupt

        self.stop_run(KeyboardInterrupt, body, "--deck", "deck-b", patch=mock.patch("os.replace", replace))
        self.assertEqual(self.raw.read_bytes(), body)
        self.assertEqual(self.deck_combos["deck-b"].read_bytes(), OLD_DECK_COMBOS)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])

    def test_failure_while_writing_the_matcher_index(self):
        """An --offline --force run from a cached export that changed under the same timestamp:
        the disk fills half-way through the matcher index. The old index is whole and no meta
        file is left; the next default run rebuilds every deck and leaves no temporary file."""
        body = changed_export()
        self.write_cache(raw=body)
        real_write_text = Path.write_text

        def write_text(path, data, *args, **kwargs):
            if path.name.startswith("matcher-index.json"):
                real_write_text(path, data[:len(data) // 2], *args, **kwargs)
                raise OSError(28, "No space left on device")
            return real_write_text(path, data, *args, **kwargs)

        self.stop_run(OSError, NOT_GZIP, "--offline", "--force",
                      patch=mock.patch.object(Path, "write_text", write_text))
        self.assertEqual(self.matcher_index.read_bytes(), OLD_MATCHER_INDEX)
        self.assertFalse(self.meta.exists())

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.corpus_of(self.matcher_index), OLD_TIMESTAMP)
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])
        self.assertEqual(sorted(p.name for p in self.matcher_index.parent.iterdir()),
                         ["matcher-index.json", "matcher-index.meta.json"])

    def test_1000_kept_of_1001_scanned(self):
        variants = [variant(n) for n in range(1001)]
        variants[0]["status"] = "DRAFT"
        self.write_cache()

        code, _ = self.run_script(export(NEW_TIMESTAMP, variants))

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.meta.read_text())["variant_count"], 1000)

    def test_byte_identical_download_keeps_the_cache(self):
        """A download equal to the cached export of the current corpus changes nothing and
        is not scanned: the cached file is the same file, not a rewrite."""
        self.write_cache()
        before = self.snapshot()
        identity = (self.raw.stat().st_ino, self.raw.stat().st_mtime_ns)

        code, out = self.run_script(self.raw.read_bytes())

        self.assertEqual(code, 0)
        self.assertIn(f"Corpus current ({OLD_TIMESTAMP}); derivatives up to date.", out)
        self.assertNotIn("Extracting", out)
        self.assertEqual((self.raw.stat().st_ino, self.raw.stat().st_mtime_ns), identity)
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_cache_is_repaired_by_a_current_download(self):
        """The cached export is junk and the meta file names the corpus of the download: the
        download passes the scan, replaces the cache, and the run rebuilds."""
        self.write_cache(raw=b"junk")
        body = good(OLD_TIMESTAMP)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertIn("  scanned 1,000; kept 1,000", out)
        self.check_rebuilt_from(body, out)

    def test_unreadable_cache_is_repaired_by_a_current_download(self):
        """A cached export that cannot be read counts as different from the download."""
        self.write_cache()
        body = self.raw.read_bytes()
        self.raw.chmod(0)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.check_rebuilt_from(body, out)

    def test_current_download_without_a_cache_is_scanned(self):
        """With no cached export, a download of the corpus that the meta file names becomes
        the cache only through the scan, and the run rebuilds."""
        self.write_meta()
        body = good(OLD_TIMESTAMP, aliases=False)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertIn("  scanned 1,000; kept 1,000", out)
        self.check_rebuilt_from(body, out)

    def test_leftover_temporary_file_of_another_run_is_left_alone(self):
        """variants.json.gz.tmp, the one name every run used before, may belong to a run still
        going: a good run neither publishes nor removes it."""
        self.write_cache()
        leftover = self.priv / "variants.json.gz.tmp"
        leftover.write_bytes(b"half of another run's download")
        body = good(NEW_TIMESTAMP)

        code, _ = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in self.priv.iterdir()),
                         ["spellbook.meta.json", "variants.json.gz", "variants.json.gz.tmp"])
        self.assertEqual(leftover.read_bytes(), b"half of another run's download")
        self.assertEqual(self.raw.read_bytes(), body)

    # ------------------------------------------------------------------ the documented flags

    def test_offline_force_rebuilds_from_the_cache(self):
        self.write_cache()
        cached = self.raw.read_bytes()

        code, out = self.run_script(NOT_GZIP, "--offline", "--force")

        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [])
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.raw.read_bytes(), cached)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["corpus_timestamp"], OLD_TIMESTAMP)
        self.assertEqual(meta["variant_count"], 1000)
        self.assertEqual(self.corpus_of(self.matcher_index), OLD_TIMESTAMP)
        self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), OLD_TIMESTAMP)
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2"])

    def test_deck_run_with_a_good_newer_download(self):
        """--deck deck-b: deck-b (commander Card 2, Card 1 in its list) gets the two combos
        of its two cards; deck-a's file is not touched, and the run names it as left on the
        old corpus. The meta file names the new corpus."""
        self.write_cache()
        body = good(NEW_TIMESTAMP)

        code, out = self.run_script(body, "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  decks whose spellbook-combos.json is not on this run's corpus (2026-11-20T00:00:00Z):\n"
            "    deck-a                           2026-11-01T00:00:00Z\n"
            "  to put every deck on it: uv run python scripts/sync_spellbook_combos.py --offline --force\n"
            "  then, for each deck whose included[] set changed: "
            "uv run python scripts/build_tier_b_candidates.py --deck ID\n"
            "Done.\n"))
        self.assertEqual(self.raw.read_bytes(), body)
        combos = json.loads(self.deck_combos["deck-b"].read_text())
        self.assertEqual(combos["meta"]["corpusVersion"], NEW_TIMESTAMP)
        self.assertEqual([combo["id"] for combo in combos["included"]], ["1-2", "2-3"])
        self.assertEqual(self.deck_combos["deck-a"].read_bytes(), OLD_DECK_COMBOS)
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], NEW_TIMESTAMP)

    def test_deck_run_on_the_current_corpus(self):
        """--deck rebuilds the named deck's file even when the corpus is current; the other
        deck's file is not touched, and the run says every deck is on its corpus and prints
        neither command. It writes the meta file again: the export's corpus and version, 1000
        variants over 999 cards (variant 5 reuses Card 1)."""
        self.write_cache(raw=changed_export())

        code, out = self.run_script(self.raw.read_bytes(), "--deck", "deck-a")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  every deck's spellbook-combos.json is on this run's corpus (2026-11-01T00:00:00Z).\n"
            "Done.\n"))
        self.assertNotIn("--offline --force", out)
        self.assertNotIn("build_tier_b_candidates", out)
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
        self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), OLD_TIMESTAMP)
        self.assertEqual(self.deck_combos["deck-b"].read_bytes(), OLD_DECK_COMBOS)
        meta = json.loads(self.meta.read_text())
        self.assertEqual({key: meta[key] for key in (
            "corpus_timestamp", "spellbook_version", "variant_count", "card_count", "source")}, {
            "corpus_timestamp": OLD_TIMESTAMP, "spellbook_version": "5.0",
            "variant_count": 1000, "card_count": 999, "source": VARIANTS_URL})

    def test_same_deck_named_twice(self):
        """--deck deck-b --deck deck-b rebuilds deck-b once: one row in the report."""
        self.write_cache()

        code, out = self.run_script(self.raw.read_bytes(), "--deck", "deck-b", "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertEqual([line for line in out.splitlines() if line.startswith("    deck-b ")],
                         ["    deck-b                              2 /    0 /     0"])

    def test_deck_run_in_a_tree_without_a_meta_file(self):
        """A new worktree: no meta file of its own, and every deck's file, the matcher index and
        its sidecar record the cached export's corpus. --deck deck-b (offline, and online with the
        cached bytes downloaded) rebuilds deck-b only, names no deck and writes the meta file;
        the next default run is up to date."""
        for argv in (("--offline", "--deck", "deck-b"), ("--deck", "deck-b")):
            with self.subTest(argv=argv):
                self.write_cache()
                self.reset_derivatives()
                self.meta.unlink()
                body = self.raw.read_bytes()

                code, out = self.run_script(body, *argv)

                self.assertEqual(code, 0)
                self.assertTrue(out.endswith(
                    "  every deck's spellbook-combos.json is on this run's corpus (2026-11-01T00:00:00Z).\n"
                    "Done.\n"))
                self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)
                self.assertEqual(self.deck_combos["deck-a"].read_bytes(), OLD_DECK_COMBOS)
                self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3"])

                code, out = self.run_script(body)

                self.assertEqual(code, 0)
                self.assertTrue(out.endswith(
                    f"Corpus current ({OLD_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))

    def test_deck_run_in_a_new_tree_over_an_older_cached_export(self):
        """A new worktree whose cached export is older than the deck files it checked out, and
        no meta file: --deck deck-b downloads the export of the files' corpus, names no deck
        and writes the meta file; the download is the cache now. (Adopted from the round-2
        review.)"""
        self.write_cache(raw=good(OLDER_TIMESTAMP))
        self.meta.unlink()
        body = good(OLD_TIMESTAMP)

        code, out = self.run_script(body, "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  every deck's spellbook-combos.json is on this run's corpus (2026-11-01T00:00:00Z).\n"
            "Done.\n"), out[-300:])
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)
        self.assertEqual(self.raw.read_bytes(), body)

    def test_named_deck_newer_stops_the_run(self):
        """The deck a --deck run would rebuild records a newer corpus than the cached export: the
        run exits 1, names that deck's file and its corpus, and changes nothing. (Adopted from the
        round-2 review.)"""
        self.write_cache()
        self.deck_combos["deck-b"].write_bytes(b'{"meta": {"corpusVersion": "2026-11-20T00:00:00Z"}}')
        before = self.snapshot()

        code, out = self.run_script(NOT_GZIP, "--offline", "--deck", "deck-b")

        self.assertEqual(code, 1)
        self.assertIn(
            "ERROR: these files record a newer corpus than the cached export's (2026-11-01T00:00:00Z):\n"
            "    data/commanders/deck-b/spellbook-combos.json  2026-11-20T00:00:00Z\n"
            "No cache, meta", out)
        self.assertEqual(self.snapshot(), before)

    def test_equal_instants_in_other_forms_are_not_newer(self):
        """deck-a records the export's instant in another form (+00:00, or with zero fractions):
        not newer, so an --offline run rebuilds it onto the export's own form. Half a second
        later is newer: the run exits 1. (Adopted from the round-2 review.)"""
        for recorded in ("2026-11-01T00:00:00+00:00", "2026-11-01T00:00:00.000000Z"):
            with self.subTest(recorded):
                self.write_cache()
                self.reset_derivatives()
                self.deck_combos["deck-a"].write_text(json.dumps({"meta": {"corpusVersion": recorded}}))
                code, _ = self.run_script(NOT_GZIP, "--offline")
                self.assertEqual(code, 0)
                self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), OLD_TIMESTAMP)
        self.write_cache()
        self.reset_derivatives()
        self.deck_combos["deck-a"].write_text(json.dumps({"meta": {"corpusVersion": "2026-11-01T00:00:00.5Z"}}))
        self.assertEqual(self.run_script(NOT_GZIP, "--offline")[0], 1)

    def test_later_instant_whose_text_sorts_earlier_is_newer(self):
        """deck-a records 2026-10-31T23:30:00-01:00, which is 2026-11-01T00:30:00Z: half an hour
        after the cached export's corpus although its text sorts before it. The run exits 1 and
        names it."""
        self.write_cache()
        self.deck_combos["deck-a"].write_bytes(b'{"meta": {"corpusVersion": "2026-10-31T23:30:00-01:00"}}')
        before = self.snapshot()

        code, out = self.run_script(NOT_GZIP, "--offline")

        self.assertEqual(code, 1)
        self.assertIn("    data/commanders/deck-a/spellbook-combos.json  2026-10-31T23:30:00-01:00\n", out)
        self.assertEqual(self.snapshot(), before)

    def test_every_newer_file_is_named(self):
        """Both decks' files, the matcher index and its sidecar record a newer corpus: the
        refusal names all four."""
        self.write_cache()
        for deck_file in self.deck_combos.values():
            deck_file.write_bytes(b'{"meta": {"corpusVersion": "2026-11-20T00:00:00Z"}}')
        self.matcher_index.write_bytes(b'{"meta": {"corpusVersion": "2026-11-21T00:00:00Z"}}')
        self.sidecar.write_bytes(b'{"corpusVersion": "2026-11-22T00:00:00Z"}')

        code, out = self.run_script(NOT_GZIP, "--offline")

        self.assertEqual(code, 1)
        self.assertIn(
            "ERROR: these files record a newer corpus than the cached export's (2026-11-01T00:00:00Z):\n"
            "    data/commanders/deck-a/spellbook-combos.json  2026-11-20T00:00:00Z\n"
            "    data/commanders/deck-b/spellbook-combos.json  2026-11-20T00:00:00Z\n"
            "    data/spellbook/matcher-index.json  2026-11-21T00:00:00Z\n"
            "    data/spellbook/matcher-index.meta.json  2026-11-22T00:00:00Z\n", out)

    def test_deck_run_that_kept_the_export_names_a_deck_on_another_corpus(self):
        """The meta file names the cached export's corpus but deck-a's file records an older one
        (a merge brought it in). --deck deck-b with the same bytes downloaded names deck-a and
        writes the meta file; the next default run rebuilds deck-a."""
        self.write_cache()
        self.deck_combos["deck-a"].write_bytes(b'{"meta": {"corpusVersion": "2026-10-01T00:00:00Z"}}')

        code, out = self.run_script(self.raw.read_bytes(), "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  decks whose spellbook-combos.json is not on this run's corpus (2026-11-01T00:00:00Z):\n"
            "    deck-a                           2026-10-01T00:00:00Z\n"
            "  to put every deck on it: uv run python scripts/sync_spellbook_combos.py --offline --force\n"
            "  then, for each deck whose included[] set changed: "
            "uv run python scripts/build_tier_b_candidates.py --deck ID\n"
            "Done.\n"))
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)

        code, out = self.run_script(self.raw.read_bytes())

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), OLD_TIMESTAMP)

    def test_deck_run_that_replaced_the_export_under_the_same_timestamp(self):
        """--deck deck-b downloads the export with other bytes under the timestamp the meta file
        names (variant 5 now uses Card 1): only deck-b is built from it. The run names deck-a as
        unverified and writes no meta file. deck-b's list then gains Card 4; the next default run
        (the same bytes) rebuilds every deck from the installed export and its current list and
        writes the meta file; the run after it is up to date."""
        self.write_cache()
        body = changed_export()

        code, out = self.run_script(body, "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  this checkout's meta file named this corpus (2026-11-01T00:00:00Z), but this run could "
            "not match the export it installed to the cached one (missing, unreadable or other "
            "bytes), so it cannot tell which of these decks' files were built from the one it "
            "installed:\n"
            "    deck-a                           matching timestamp, export unverified\n"
            "  to put every deck on it: uv run python scripts/sync_spellbook_combos.py --offline --force\n"
            "  then, for each deck whose included[] set changed: "
            "uv run python scripts/build_tier_b_candidates.py --deck ID\n"
            "  no meta file written: run once without --deck next; that run rebuilds every deck.\n"
            "Done.\n"))
        self.assertFalse(self.meta.exists())
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])
        self.assertEqual(self.deck_combos["deck-a"].read_bytes(), OLD_DECK_COMBOS)
        deck_b = self.root / "data" / "commanders" / "deck-b" / "deck.json"
        deck_b.write_text(json.dumps({"commander": "Card 2", "decklist": [{"name": "Card 1"}, {"name": "Card 4"}]}))

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "4-5", "5-6"])
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)

        code, out = self.run_script(body)

        self.assertTrue(out.endswith(
            f"Corpus current ({OLD_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))

    def test_reissue_through_a_deck_run_naming_every_deck(self):
        """The same reissued export through --deck deck-a --deck deck-b: every deck is rebuilt
        from it, so the run is a full rebuild: it writes the meta file and says every deck is on
        its corpus."""
        self.write_cache()

        code, out = self.run_script(changed_export(), "--deck", "deck-a", "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  every deck's spellbook-combos.json is on this run's corpus (2026-11-01T00:00:00Z).\n"
            "Done.\n"))
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], OLD_TIMESTAMP)
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2", "5-6"])
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "5-6"])

    def test_second_deck_run_after_a_reissue_rebuilds_its_deck(self):
        """After the --deck deck-b run on a reissued export, deck-b's list gains Card 4; a second
        --deck deck-b run (offline) rebuilds deck-b from that list: it now includes 4-5."""
        self.write_cache()
        self.assertEqual(self.run_script(changed_export(), "--deck", "deck-b")[0], 0)
        deck_b = self.root / "data" / "commanders" / "deck-b" / "deck.json"
        deck_b.write_text(json.dumps({"commander": "Card 2", "decklist": [{"name": "Card 1"}, {"name": "Card 4"}]}))

        code, out = self.run_script(NOT_GZIP, "--offline", "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.included_ids("deck-b"), ["1-2", "2-3", "4-5", "5-6"])

    def test_deck_run_names_every_deck_off_its_corpus(self):
        """After --deck deck-b on a newer corpus, the run names deck-a (old corpus), deck-c (no
        file), deck-d (a file that is not JSON), and as no record, though each would be read as
        later than the run's corpus: deck-e (a time without a timezone), deck-f (an offset of
        +00:99), deck-g (seven fractional digits), deck-h (a fullwidth T between the date and the
        time), deck-i (a lone surrogate there), deck-j (hour 24, which Python 3.14 reads as the
        next midnight), deck-k (an offset of +00:60), deck-l (a space between the date and the
        time), deck-m (an offset with seconds) and deck-n (a lowercase t); notes/ holds no
        deck.json and is no deck. The command it prints then puts every deck on the new corpus
        without a request, and a --deck run after that says every deck is on its corpus."""
        commanders = self.root / "data" / "commanders"
        unread = {"deck-e": "2026-11-25T00:00:00", "deck-f": "2026-11-25T00:00:00+00:99",
                  "deck-g": "2026-11-25T00:00:00.1234567Z", "deck-h": "2026-11-25Ｔ00:00:00Z",
                  "deck-i": "2026-11-25\ud80000:00:00Z", "deck-j": "2026-11-25T24:00:00Z",
                  "deck-k": "2026-11-25T00:00:00+00:60", "deck-l": "2026-11-25 00:00:00Z",
                  "deck-m": "2026-11-25T00:00:00+00:00:00", "deck-n": "2026-11-25t00:00:00Z"}
        for deck_id in ("deck-c", "deck-d", *unread):
            (commanders / deck_id).mkdir()
            (commanders / deck_id / "deck.json").write_text(
                json.dumps({"commander": "Card 7", "decklist": []}))
        (commanders / "deck-d" / "spellbook-combos.json").write_text("{")
        for deck_id, recorded in unread.items():
            (commanders / deck_id / "spellbook-combos.json").write_text(
                json.dumps({"meta": {"corpusVersion": recorded}}))
        (commanders / "notes").mkdir()
        self.write_cache()

        code, out = self.run_script(good(NEW_TIMESTAMP), "--deck", "deck-b")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  decks whose spellbook-combos.json is not on this run's corpus (2026-11-20T00:00:00Z):\n"
            "    deck-a                           2026-11-01T00:00:00Z\n"
            "    deck-c                           no corpus recorded\n"
            "    deck-d                           no corpus recorded\n"
            "    deck-e                           no corpus recorded\n"
            "    deck-f                           no corpus recorded\n"
            "    deck-g                           no corpus recorded\n"
            "    deck-h                           no corpus recorded\n"
            "    deck-i                           no corpus recorded\n"
            "    deck-j                           no corpus recorded\n"
            "    deck-k                           no corpus recorded\n"
            "    deck-l                           no corpus recorded\n"
            "    deck-m                           no corpus recorded\n"
            "    deck-n                           no corpus recorded\n"
            "  to put every deck on it: uv run python scripts/sync_spellbook_combos.py --offline --force\n"
            "  then, for each deck whose included[] set changed: "
            "uv run python scripts/build_tier_b_candidates.py --deck ID\n"
            "Done.\n"), out[-1400:])

        code, out = self.run_script(NOT_GZIP, "--offline", "--force")

        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [VARIANTS_URL])
        for deck_id in ("deck-a", "deck-b", "deck-c", "deck-d", *unread):
            self.assertEqual(self.corpus_of(commanders / deck_id / "spellbook-combos.json"), NEW_TIMESTAMP)
        self.assertFalse((commanders / "notes" / "spellbook-combos.json").exists())

        code, out = self.run_script(NOT_GZIP, "--offline", "--deck", "deck-c")

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "  every deck's spellbook-combos.json is on this run's corpus (2026-11-20T00:00:00Z).\n"
            "Done.\n"))

    def test_deck_off_the_corpus_makes_the_fleet_stale(self):
        """The meta file, the cached export, the matcher index and its sidecar are current, but
        deck-a's spellbook-combos.json records an older corpus, is missing, is not JSON, holds
        [] or {}, is nested too deep to read, holds NaN (not strict JSON), or records a time
        without a timezone (later, were it read as UTC) or a value that is not a time: each
        counts as no record or another corpus, and a default run (the cached bytes downloaded)
        and an --offline run each rebuild every deck."""
        for label, content in (("older corpus", b'{"meta": {"corpusVersion": "2026-10-01T00:00:00Z"}}'),
                               ("missing", None), ("not JSON", b"{"), ("[]", b"[]"), ("{}", b"{}"),
                               ("nested too deep", b"[" * 100000 + b"]" * 100000),
                               ("NaN", b'{"meta": {"corpusVersion": "2026-11-01T00:00:00Z"}, "x": NaN}'),
                               ("no timezone", b'{"meta": {"corpusVersion": "2026-11-20T00:00:00"}}'),
                               ("not a time", b'{"meta": {"corpusVersion": "old deck file"}}')):
            for argv in ((), ("--offline",)):
                with self.subTest(label, argv=argv):
                    self.write_cache()
                    self.reset_derivatives()
                    if content is None:
                        self.deck_combos["deck-a"].unlink()
                    else:
                        self.deck_combos["deck-a"].write_bytes(content)
                    body = self.raw.read_bytes()

                    code, out = self.run_script(body, *argv)

                    self.assertEqual(code, 0)
                    self.check_rebuilt_from(body, out)

    def test_matcher_index_off_the_corpus_makes_the_fleet_stale(self):
        """Everything else current, the matcher index or its sidecar records an older corpus or
        is missing (deck files committed with the index's diff discarded): a default run and an
        --offline run each rebuild every deck, the index and the sidecar."""
        cases = (("sidecar older", self.sidecar, b'{"corpusVersion": "2026-10-01T00:00:00Z"}'),
                 ("sidecar missing", self.sidecar, None),
                 ("index older", self.matcher_index, b'{"meta": {"corpusVersion": "2026-10-01T00:00:00Z"}}'),
                 ("index missing", self.matcher_index, None))
        for label, path, content in cases:
            for argv in ((), ("--offline",)):
                with self.subTest(label, argv=argv):
                    self.write_cache()
                    self.reset_derivatives()
                    if content is None:
                        path.unlink()
                    else:
                        path.write_bytes(content)
                    body = self.raw.read_bytes()

                    code, out = self.run_script(body, *argv)

                    self.assertEqual(code, 0)
                    self.check_rebuilt_from(body, out)
                    self.assertEqual(json.loads(self.sidecar.read_text())["corpusVersion"], OLD_TIMESTAMP)

    def test_newer_files_stop_every_run(self):
        """deck-a's file, the matcher index or its sidecar records a newer corpus (2026-11-20)
        than the cached export (2026-11-01). --offline, --offline --force, --offline --deck
        deck-b, and a default and a --deck deck-b run whose download (other bytes, also
        2026-11-01) is older each exit 1, name the newer file, and change nothing."""
        newer_files = (
            ("deck file", self.deck_combos["deck-a"], b'{"meta": {"corpusVersion": "2026-11-20T00:00:00Z"}}',
             "data/commanders/deck-a/spellbook-combos.json"),
            ("matcher index", self.matcher_index, b'{"meta": {"corpusVersion": "2026-11-20T00:00:00Z"}}',
             "data/spellbook/matcher-index.json"),
            ("sidecar", self.sidecar, b'{"corpusVersion": "2026-11-20T00:00:00Z"}',
             "data/spellbook/matcher-index.meta.json"))
        offline_end = ("No cache, meta or derivative file changed: no run moves a derivative file to "
                       "an older corpus. Run without --offline to download the newest export.\n")
        online_end = ("No cache, meta or derivative file changed: no run moves a derivative file to "
                      "an older corpus. Spellbook served an export older than these files: run again "
                      "without --offline once it serves the newest.\n")
        for label, path, content, name in newer_files:
            for argv, source, end in (
                    (("--offline",), "the cached export's", offline_end),
                    (("--offline", "--force"), "the cached export's", offline_end),
                    (("--offline", "--deck", "deck-b"), "the cached export's", offline_end),
                    ((), "the download's", online_end),
                    (("--deck", "deck-b"), "the download's", online_end)):
                with self.subTest(label, argv=argv):
                    self.write_cache()
                    self.reset_derivatives()
                    path.write_bytes(content)
                    before = self.snapshot()

                    code, out = self.run_script(good(OLD_TIMESTAMP, aliases=False), *argv)

                    self.assertEqual(code, 1)
                    self.assertTrue(out.endswith(
                        f"ERROR: these files record a newer corpus than {source} (2026-11-01T00:00:00Z):\n"
                        f"    {name}  2026-11-20T00:00:00Z\n" + end), out[-400:])
                    self.assertEqual(self.snapshot(), before)

    def test_export_timestamp_that_cannot_be_ordered(self):
        """An export whose timestamp is not of the export's form is refused as a schema error
        before anything changes: no timezone, not a timestamp, an offset of +00:99 (which
        datetime.fromisoformat reads as +01:39), seven fractional digits (which it cuts to six),
        a fullwidth T or a lone surrogate between the date and the time (which it accepts as a
        separator; the surrogate cannot be written to a file), and hour 24 (which Python 3.14
        reads as the next midnight)."""
        for timestamp in ("2026-11-20T00:00:00", "last Tuesday", "2026-11-20T00:00:00+00:99",
                          "2026-11-20T00:00:00.1234567Z", "2026-11-20Ｔ00:00:00Z",
                          "2026-11-20\ud80000:00:00Z", "2026-11-20T24:00:00Z"):
            with self.subTest(timestamp):
                self.reset_derivatives()
                self.check_bad_download(
                    gz(export_text(timestamp, [variant(n) for n in range(1000)])),
                    f"export timestamp {timestamp!r} is not a timestamp of the export's form "
                    "(YYYY-MM-DDTHH:MM:SS in ASCII digits, an optional fraction of 1 to 6 digits, "
                    "then Z or an offset ±HH:MM) — cannot order the corpus.")

    def test_fleet_left_behind_by_a_deck_run_is_rebuilt(self):
        """--deck deck-b on a newer corpus leaves deck-a on the old one. The next default run
        (the same download) rebuilds deck-a instead of calling the fleet up to date; the run
        after it is up to date."""
        self.write_cache()
        body = good(NEW_TIMESTAMP)
        self.assertEqual(self.run_script(body, "--deck", "deck-b")[0], 0)
        self.assertEqual(self.deck_combos["deck-a"].read_bytes(), OLD_DECK_COMBOS)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertEqual(self.corpus_of(self.deck_combos["deck-a"]), NEW_TIMESTAMP)
        self.assertEqual(self.included_ids("deck-a"), ["0-1", "1-2"])

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            f"Corpus current ({NEW_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))

    def test_different_download_over_a_linked_export(self):
        """The cache links to another checkout's export and the download has other bytes (a
        newer corpus): the link becomes this checkout's own file holding the download; the
        other checkout's export is the same file with the same bytes and modification time."""
        self.write_cache()
        other = self.root / "main" / "priv_data" / "spellbook" / "variants.json.gz"
        other.parent.mkdir(parents=True)
        self.raw.rename(other)
        self.raw.symlink_to(other)
        old_bytes = other.read_bytes()
        identity = (other.stat().st_ino, other.stat().st_mtime_ns)
        body = good(NEW_TIMESTAMP)

        code, out = self.run_script(body)

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("Done.\n"))
        self.assertFalse(self.raw.is_symlink())
        self.assertEqual(self.raw.read_bytes(), body)
        self.assertEqual(other.read_bytes(), old_bytes)
        self.assertEqual((other.stat().st_ino, other.stat().st_mtime_ns), identity)

    def test_identical_download_leaves_a_linked_cache_alone(self):
        """The cache links to another checkout's export: an identical download through an
        online --deck run and an online --force run, both rebuilding, leaves the link a link
        and its target the same file."""
        self.write_cache()
        other = self.root / "main" / "priv_data" / "spellbook" / "variants.json.gz"
        other.parent.mkdir(parents=True)
        self.raw.rename(other)
        self.raw.symlink_to(other)
        identity = (other.stat().st_ino, other.stat().st_mtime_ns)

        for argv in (("--deck", "deck-a"), ("--force",)):
            with self.subTest(argv=argv):
                code, out = self.run_script(other.read_bytes(), *argv)

                self.assertEqual(code, 0)
                self.assertTrue(out.endswith("Done.\n"))
                self.assertTrue(self.raw.is_symlink())
                self.assertEqual(self.raw.readlink(), other)
                self.assertEqual((other.stat().st_ino, other.stat().st_mtime_ns), identity)

    def test_deck_run_with_a_bad_download(self):
        self.check_bad_download(NOT_GZIP, "the download is not a readable gzip export",
                                "--deck", "deck-a")

    # ------------------------------------------------------------------ refused before a request

    def check_meta_elsewhere(self, target: Path):
        """The run is refused before any request, naming where the meta file leads."""
        before = self.snapshot()

        code, out = self.run_script(good(NEW_TIMESTAMP))

        self.assertEqual(code, 1)
        meta = self.root.resolve() / "priv_data" / "spellbook" / "spellbook.meta.json"
        self.assertIn(f"{meta} leads to {target}.", out)
        self.assertIn("priv_data/spellbook/ must be a real folder of this checkout (inside a "
                      "real priv_data/) holding variants.json.gz (its own copy, or a link to "
                      "another checkout's) and no linked meta file: remove the meta link (or "
                      "replace the linked folder by such a real one), then run once with "
                      "--offline --force and no --deck", out)
        self.assertIn("rebuilds every deck's file from that export without a download and writes "
                      "this checkout's own meta file (if this checkout's files record a newer "
                      "corpus than that export, it refuses and changes nothing: then run with "
                      "--force and without --offline, which downloads the newest export). No file "
                      "written.", out)
        self.assertIn("The meta file records the corpus of the last run that wrote it, in this "
                      "checkout; a run here checks it against this checkout's cached export and "
                      "derivative files", out)
        self.assertNotIn("vouch", out)
        self.assertNotIn("copy the linked one", out)
        self.assertNotIn("holds only a link", out)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.snapshot(), before)

    def test_linked_meta_file_is_refused(self):
        self.write_cache()
        other = self.root / "main" / "priv_data" / "spellbook" / "spellbook.meta.json"
        other.parent.mkdir(parents=True)
        self.meta.rename(other)
        self.meta.symlink_to(other)
        self.check_meta_elsewhere(
            self.root.resolve() / "main" / "priv_data" / "spellbook" / "spellbook.meta.json")

    def test_linked_spellbook_folder_is_refused(self):
        main = self.root / "main" / "priv_data" / "spellbook"
        main.mkdir(parents=True)
        (main / "variants.json.gz").write_bytes(good(OLD_TIMESTAMP))
        (main / "spellbook.meta.json").write_text(json.dumps({"corpus_timestamp": OLD_TIMESTAMP}))
        self.priv.parent.mkdir()
        self.priv.symlink_to(main)
        self.check_meta_elsewhere(
            self.root.resolve() / "main" / "priv_data" / "spellbook" / "spellbook.meta.json")

    def test_linked_priv_data_folder_is_refused(self):
        main = self.root / "main" / "priv_data"
        (main / "spellbook").mkdir(parents=True)
        (main / "spellbook" / "variants.json.gz").write_bytes(good(OLD_TIMESTAMP))
        (main / "spellbook" / "spellbook.meta.json").write_text(
            json.dumps({"corpus_timestamp": OLD_TIMESTAMP}))
        (self.root / "priv_data").symlink_to(main)
        self.check_meta_elsewhere(
            self.root.resolve() / "main" / "priv_data" / "spellbook" / "spellbook.meta.json")

    # ------------------------------------------------------------------ bad downloads

    def test_download_that_is_not_gzip(self):
        self.check_bad_download(NOT_GZIP, "the download is not a readable gzip export")

    def test_truncated_gzip(self):
        whole = good(NEW_TIMESTAMP)
        self.check_bad_download(whole[:len(whole) // 2],
                                "the download is not a readable gzip export")

    def test_corrupted_deflate_bytes(self):
        """Bytes overwritten in the middle (the CRC check fails), and a first deflate block of
        the reserved type 3 (zlib refuses it)."""
        whole = good(NEW_TIMESTAMP)
        for label, index, value in (("middle", len(whole) // 2, b"\xff" * 8),
                                    ("block type", 10, b"\xff")):
            with self.subTest(label):
                body = bytearray(whole)
                body[index:index + len(value)] = value
                self.check_bad_download(bytes(body), "the download is not a readable gzip export")

    def test_gzip_of_invalid_utf8(self):
        self.check_bad_download(gzip.compress(b'{"timestamp": "\xff\xfe"}', mtime=0),
                                "the download is not a readable gzip export")

    def test_gzip_without_a_variants_key(self):
        self.check_bad_download(gz('{"timestamp": "2026-11-20T00:00:00Z", "data": []}'),
                                "export has no top-level 'variants' key")

    def test_variants_key_without_a_list(self):
        self.check_bad_download(
            gz('{"timestamp": "2026-11-20T00:00:00Z", "version": "5.0", "variants": {"0-1": {}}}'),
            "the top-level 'variants' key is not followed by a list")

    def test_export_cut_off_after_enough_variants(self):
        """A complete gzip whose JSON stops inside the variants list after 1,100 complete
        variants."""
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1200)])
        cut = text[:text.index('{"id": "1100-1101"')]
        self.check_bad_download(gz(cut), "the export is cut off")

    def test_gzipped_html_page(self):
        """The usual error answer: an HTML page, gzipped like the export."""
        self.check_bad_download(gz("<!doctype html><html><body>502 Bad Gateway</body></html>"),
                                "the export is not a JSON object")

    def test_empty_variants_list(self):
        self.check_bad_download(
            gz('{"timestamp": "2026-11-20T00:00:00Z", "version": "5.0", "variants": []}'),
            "only 0 variants scanned")

    def test_member_without_a_name_or_a_colon(self):
        for label, text in (
                ("no name", '{"timestamp": "2026-11-20T00:00:00Z", 5: 1, "variants": []}'),
                ("no colon", '{"timestamp" "2026-11-20T00:00:00Z", "variants": []}')):
            with self.subTest(label):
                self.check_bad_download(gz(text), "the export is not valid JSON: no member name")

    def test_export_cut_off_right_after_a_member(self):
        self.check_bad_download(gz('{"timestamp": "2026-11-20T00:00:00Z"'), "the export is cut off")

    def test_two_members_without_a_comma(self):
        self.check_bad_download(
            gz('{"timestamp": "2026-11-20T00:00:00Z" "version": "5.0", "variants": []}'),
            "the export is not valid JSON: expected ',' or '}'")

    def test_export_cut_off_right_after_a_variant(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        self.check_bad_download(gz(text[:text.index(', {"id": "500-501"')]), "the export is cut off")

    def test_two_variants_without_a_comma(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        broken = text.replace('}, {"id": "500-501"', '} {"id": "500-501"')
        self.assertNotEqual(broken, text)
        self.check_bad_download(gz(broken), "the export is not valid JSON: expected ',' or ']'")

    def test_export_without_a_timestamp(self):
        body = {"version": "5.0", "variants": [variant(n) for n in range(1000)], "aliases": []}
        self.check_bad_download(gz(json.dumps(body)), "export has no 'timestamp'")

    def test_two_held_downloads_keep_their_own_bytes(self):
        """Two runs at once: both downloads sit in their temporary files before either is put
        in place, and each keeps its own bytes."""
        self.write_cache()
        module = runpy.run_path(str(self.root / "scripts" / "sync_spellbook_combos.py"))
        held = []
        for body in (good(OLD_TIMESTAMP), good(NEW_TIMESTAMP)):
            with mock.patch("urllib.request.urlopen",
                            lambda req, timeout=None, body=body: io.BytesIO(body)), \
                    contextlib.redirect_stderr(io.StringIO()):
                held.append((module["download_corpus"](), body))

        self.assertNotEqual(held[0][0], held[1][0])
        for path, body in held:
            self.assertEqual(path.parent.resolve(), self.priv.resolve())
            self.assertEqual(path.read_bytes(), body)

    def test_recovery_from_a_linked_spellbook_folder(self):
        """The refusal's advice, followed after a refused --deck run: the linked folder is
        replaced by a real priv_data/spellbook/ holding a link to the other checkout's
        variants.json.gz, and one run with --offline --force and no --deck rebuilds every
        deck's file from the linked export, sends no request and writes this checkout's own
        meta file. The next default run on the same export then changes nothing."""
        main = self.root / "main" / "priv_data" / "spellbook"
        main.mkdir(parents=True)
        (main / "variants.json.gz").write_bytes(good(NEW_TIMESTAMP))
        (main / "spellbook.meta.json").write_text(json.dumps({"corpus_timestamp": NEW_TIMESTAMP}))
        self.priv.parent.mkdir()
        self.priv.symlink_to(main)
        self.assertEqual(self.run_script(good(NEW_TIMESTAMP), "--deck", "deck-b")[0], 1)

        self.priv.unlink()
        self.priv.mkdir()
        self.raw.symlink_to(main / "variants.json.gz")
        code, out = self.run_script(NOT_GZIP, "--offline", "--force")

        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [])
        self.assertTrue(self.raw.is_symlink())
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], NEW_TIMESTAMP)
        self.assertEqual(self.corpus_of(self.matcher_index), NEW_TIMESTAMP)
        for deck_file in self.deck_combos.values():
            self.assertEqual(self.corpus_of(deck_file), NEW_TIMESTAMP)
        self.assertEqual(json.loads((main / "spellbook.meta.json").read_text()),
                         {"corpus_timestamp": NEW_TIMESTAMP})

        code, out = self.run_script(good(NEW_TIMESTAMP))

        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            f"Corpus current ({NEW_TIMESTAMP}); derivatives up to date. Use --force to rebuild.\n"))
        self.assertTrue(self.raw.is_symlink())

    def test_recovery_from_a_linked_meta_file(self):
        """Only the meta file is linked, and this checkout's variants.json.gz is its own file:
        removing the meta link and one run with --offline --force and no --deck rebuild every
        deck's file from the local export and write this checkout's own meta file; the other
        checkout's meta file is untouched."""
        self.write_cache(raw=good(NEW_TIMESTAMP))
        local_export = self.raw.read_bytes()
        other = self.root / "main" / "priv_data" / "spellbook" / "spellbook.meta.json"
        other.parent.mkdir(parents=True)
        other.write_text(json.dumps({"corpus_timestamp": OLD_TIMESTAMP}))
        self.meta.unlink()
        self.meta.symlink_to(other)
        self.assertEqual(self.run_script(good(NEW_TIMESTAMP))[0], 1)

        self.meta.unlink()
        code, out = self.run_script(NOT_GZIP, "--offline", "--force")

        self.assertEqual(code, 0)
        self.assertEqual(self.sent, [])
        self.assertTrue(out.endswith("Done.\n"))
        self.assertFalse(self.meta.is_symlink())
        self.assertEqual(json.loads(self.meta.read_text())["corpus_timestamp"], NEW_TIMESTAMP)
        self.assertEqual(self.raw.read_bytes(), local_export)
        self.assertEqual(self.corpus_of(self.matcher_index), NEW_TIMESTAMP)
        for deck_file in self.deck_combos.values():
            self.assertEqual(self.corpus_of(deck_file), NEW_TIMESTAMP)
        self.assertEqual(json.loads(other.read_text()), {"corpus_timestamp": OLD_TIMESTAMP})

    def test_export_cut_off_inside_the_members_after_the_list(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        self.check_bad_download(gz(text[:text.index('"variant": null')]), "the export is cut off")

    def test_trailing_comma_in_the_variants_list(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        broken = text.replace('}], "aliases"', '},], "aliases"')
        self.assertNotEqual(broken, text)
        self.check_bad_download(gz(broken), "the export is not valid JSON: Expecting value")

    def test_variant_without_its_opening_brace(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1001)])
        broken = text.replace('{"id": "500-501"', '"id": "500-501"')
        self.assertNotEqual(broken, text)
        self.check_bad_download(gz(broken), "entry 501 of the variants list is not an object")

    def test_scalar_in_the_variants_list(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        broken = text.replace('{"id": "500-501"', '42, {"id": "500-501"')
        self.check_bad_download(gz(broken), "entry 501 of the variants list is not an object")

    def test_export_with_text_after_its_end(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)]) + ' {"more": 1}'
        self.check_bad_download(gz(text), "the export has text after its closing brace")

    def test_variant_that_is_not_json(self):
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)])
        broken = text.replace('"id": "500-501", "status": "OK"', '"id": "500-501", "status": OK')
        self.assertNotEqual(broken, text)
        self.check_bad_download(gz(broken), "the export is not valid JSON: Expecting value")

    def test_too_few_variants(self):
        self.check_bad_download(good(NEW_TIMESTAMP, count=999), "only 999 variants scanned")

    def test_every_variant_filtered_out(self):
        """A renamed status value: every variant is scanned and none is kept."""
        variants = [dict(variant(n), status="VERIFIED") for n in range(1000)]
        self.check_bad_download(export(NEW_TIMESTAMP, variants), "only 0 of 1000 variants kept")

    def test_999_kept_of_1000_scanned(self):
        variants = [variant(n) for n in range(1000)]
        variants[0]["status"] = "DRAFT"
        self.check_bad_download(export(NEW_TIMESTAMP, variants), "only 999 of 1000 variants kept")

    def test_variants_of_the_wrong_shape(self):
        """Each field this run reads, missing or with another type than the real export has:
        the run names the variant and its place in the list."""
        def at(path, value):
            """Set (or with DROP, remove) the field at ``path`` in variant 500."""
            def mutate(v):
                *parents, key = path
                for step in parents:
                    v = v[step]
                if value is DROP:
                    del v[key]
                else:
                    v[key] = value
            return mutate

        name = "variant '500-501'"
        deep = "1.00"  # a price nested 550 objects deep
        for _ in range(550):
            deep = {"x": deep}
        use, card = ("uses", 0), ("uses", 0, "card")
        template, feature = ("requires", 0, "template"), ("produces", 0, "feature")
        cases = [
            (("status",), ["OK"], f"{name} has no string 'status'"),
            (("spoiler",), "no", f"{name} has no boolean 'spoiler'"),
            (("spoiler",), DROP, f"{name} has no boolean 'spoiler'"),
            (("legalities",), None, f"{name} has no 'legalities' object"),
            (("legalities", "commander"), "false", f"{name} has no boolean commander legality"),
            (("id",), DROP, "variant None has no string 'id'"),
            (("id",), 500, "variant 500 has no string 'id'"),
            (("id",), "", "variant '' has no string 'id'"),
            (("uses",), DROP, f"{name} has no 'uses' list of objects"),
            (("uses",), ["Card 500"], f"{name} has no 'uses' list of objects"),
            ((*use, "card"), "Card 500", f"{name} has a use with no 'card' object"),
            ((*card, "id"), "500", f"{name} has a use whose card has no integer 'id'"),
            ((*card, "id"), True, f"{name} has a use whose card has no integer 'id'"),
            ((*card, "name"), 500, f"{name} has a use whose card has no 'name'"),
            ((*card, "name"), "", f"{name} has a use whose card has no 'name'"),
            ((*card, "oracleId"), 5, f"{name} has a use whose card has no string 'oracleId'"),
            ((*use, "mustBeCommander"), "yes", f"{name} has a use with no boolean 'mustBeCommander'"),
            ((*use, "mustBeCommander"), DROP, f"{name} has a use with no boolean 'mustBeCommander'"),
            ((*use, "quantity"), "1", f"{name} has a use with no whole-number 'quantity'"),
            ((*use, "quantity"), 1.5, f"{name} has a use with no whole-number 'quantity'"),
            ((*use, "zoneLocations"), "B", f"{name} has a use with no 'zoneLocations' list of strings"),
            ((*use, "zoneLocations"), ["B", 5], f"{name} has a use with no 'zoneLocations' list of strings"),
            (("requires",), DROP, f"{name} has no 'requires' list of objects"),
            (("requires",), ["a sacrifice outlet"], f"{name} has no 'requires' list of objects"),
            (("requires", 0, "template"), "a sacrifice outlet",
             f"{name} has a 'requires' entry with no 'template' object"),
            (("requires", 0, "template"), None, f"{name} has a 'requires' entry with no 'template' object"),
            (("requires", 0, "quantity"), "1", f"{name} has a 'requires' entry with no whole-number 'quantity'"),
            ((*template, "id"), DROP, f"{name} has a template with no integer 'id'"),
            ((*template, "id"), "7", f"{name} has a template with no integer 'id'"),
            ((*template, "name"), 5, f"{name} has a template with no string 'name'"),
            ((*template, "scryfallQuery"), 5, f"{name} has a template with no string or null 'scryfallQuery'"),
            (("produces",), DROP, f"{name} has no 'produces' list of objects"),
            (("produces",), "Infinite mana", f"{name} has no 'produces' list of objects"),
            (("produces", 0, "feature"), "Infinite mana", f"{name} has a 'produces' entry with no 'feature' object"),
            ((*feature, "id"), DROP, f"{name} has a feature with no integer 'id'"),
            ((*feature, "id"), "3", f"{name} has a feature with no integer 'id'"),
            ((*feature, "name"), 5, f"{name} has a feature with no string 'name'"),
            (("description",), 5, f"{name} has no string 'description'"),
            (("notes",), None, f"{name} has no string 'notes'"),
            (("identity",), 5, f"{name} has no string 'identity'"),
            (("manaNeeded",), DROP, f"{name} has no string 'manaNeeded'"),
            (("easyPrerequisites",), 5, f"{name} has no string 'easyPrerequisites'"),
            (("notablePrerequisites",), ["ramp"], f"{name} has no string 'notablePrerequisites'"),
            (("bracketTag",), ["C"], f"{name} has no string 'bracketTag'"),
            (("manaValueNeeded",), "2", f"{name} has no integer 'manaValueNeeded'"),
            (("manaValueNeeded",), DROP, f"{name} has no integer 'manaValueNeeded'"),
            (("prices",), "cheap", f"{name} has no 'prices' object of strings"),
            (("prices",), {"cardkingdom": 1.5}, f"{name} has no 'prices' object of strings"),
            (("prices",), {"tcg": deep}, f"{name} has no 'prices' object of strings"),
            (("prices",), DROP, f"{name} has no 'prices' object of strings"),
            (("popularity",), "high", f"{name} has no integer or null 'popularity'"),
            (("popularity",), True, f"{name} has no integer or null 'popularity'"),
            (("popularity",), DROP, f"{name} has no integer or null 'popularity'"),
            # A deletion row for every required path that has none above.
            (("status",), DROP, f"{name} has no string 'status'"),
            (("legalities",), DROP, f"{name} has no 'legalities' object"),
            (("legalities", "commander"), DROP, f"{name} has no boolean commander legality"),
            (("uses",), [], f"{name} has no 'uses' list of objects"),
            ((*use, "card"), DROP, f"{name} has a use with no 'card' object"),
            ((*card, "id"), DROP, f"{name} has a use whose card has no integer 'id'"),
            ((*card, "name"), DROP, f"{name} has a use whose card has no 'name'"),
            ((*card, "oracleId"), DROP, f"{name} has a use whose card has no string 'oracleId'"),
            ((*use, "quantity"), DROP, f"{name} has a use with no whole-number 'quantity'"),
            ((*use, "zoneLocations"), DROP, f"{name} has a use with no 'zoneLocations' list of strings"),
            (("requires", 0, "template"), DROP, f"{name} has a 'requires' entry with no 'template' object"),
            (("requires", 0, "quantity"), DROP,
             f"{name} has a 'requires' entry with no whole-number 'quantity'"),
            ((*template, "name"), DROP, f"{name} has a template with no string 'name'"),
            ((*template, "scryfallQuery"), DROP,
             f"{name} has a template with no string or null 'scryfallQuery'"),
            (("produces", 0, "feature"), DROP, f"{name} has a 'produces' entry with no 'feature' object"),
            ((*feature, "name"), DROP, f"{name} has a feature with no string 'name'"),
            (("description",), DROP, f"{name} has no string 'description'"),
            (("notes",), DROP, f"{name} has no string 'notes'"),
            (("identity",), DROP, f"{name} has no string 'identity'"),
            (("easyPrerequisites",), DROP, f"{name} has no string 'easyPrerequisites'"),
            (("notablePrerequisites",), DROP, f"{name} has no string 'notablePrerequisites'"),
            (("bracketTag",), DROP, f"{name} has no string 'bracketTag'"),
        ]
        for path, value, problem in cases:
            with self.subTest(path=".".join(map(str, path)), value=value):
                variants = [variant(n) for n in range(1000)]
                variants[500]["requires"] = [copy.deepcopy(REQUIREMENT)]
                variants[500]["produces"] = [copy.deepcopy(FEATURE)]
                at(path, value)(variants[500])
                self.check_bad_download(export(NEW_TIMESTAMP, variants),
                                        f"{problem} (position 501 in the variants list)")

    def test_numbers_that_are_not_json_or_not_finite(self):
        """NaN, Infinity and -Infinity are not JSON; 1e400 is JSON but reads as infinity."""
        variants = [variant(n) for n in range(1000)]
        variants[500]["popularity"] = 77
        text = export_text(NEW_TIMESTAMP, variants)
        for token, problem in (
                ("NaN", "the export holds NaN, which is not a JSON number"),
                ("Infinity", "the export holds Infinity, which is not a JSON number"),
                ("-Infinity", "the export holds -Infinity, which is not a JSON number"),
                ("1e400", "variant '500-501' has no integer or null 'popularity'")):
            with self.subTest(token):
                broken = text.replace('"popularity": 77', f'"popularity": {token}')
                self.assertNotEqual(broken, text)
                self.check_bad_download(gz(broken), problem)

    def test_text_that_cannot_be_written(self):
        """A string the run reads holding a lone surrogate (the JSON escape \\ud800, or the low
        half \\udc00) cannot be written as UTF-8: the export's version, a card name, a zone and a
        price's key are each refused in the scan of a download newer than the cache, before the
        meta file is removed or the cache replaced; under --emit-details the detail shard already
        written stays in place."""
        def broken(mutate) -> bytes:
            variants = [variant(n) for n in range(1000)]
            mutate(variants[500])
            return export(NEW_TIMESTAMP, variants)

        shard = self.root / "data" / "spellbook" / "details" / "e8.json"
        shard.parent.mkdir()
        in_variant = "variant '500-501' has text that cannot be written as UTF-8 (a lone surrogate) in"
        card_name = f"{in_variant} 'name' (position 501 in the variants list)."
        cases = (
            ("version", gz(export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)],
                                       version="5.0\ud800")),
             "export version '5.0\\ud800' has text that cannot be written as UTF-8 (a lone surrogate).", ()),
            ("card name", broken(lambda v: v["uses"][0]["card"].update(name="Card \ud800")), card_name, ()),
            ("card name, low surrogate", broken(lambda v: v["uses"][0]["card"].update(name="Card \udc00")),
             card_name, ()),
            ("card name, --emit-details", broken(lambda v: v["uses"][0]["card"].update(name="Card \ud800")),
             card_name, ("--emit-details",)),
            ("zone", broken(lambda v: v["uses"][0].update(zoneLocations=["B", "\ud800"])),
             f"{in_variant} 'zoneLocations' (position 501 in the variants list).", ()),
            ("price key", broken(lambda v: v.update(prices={"tcg\ud800": "1.00"})),
             f"{in_variant} 'prices' (position 501 in the variants list).", ()))
        for label, body, problem, argv in cases:
            with self.subTest(label):
                self.reset_derivatives()
                shard.write_text('{"variants": [{"id": "0-1", "note": "old shard"}]}')
                self.check_bad_download(body, problem, *argv)
                self.assertEqual(shard.read_text(), '{"variants": [{"id": "0-1", "note": "old shard"}]}')

    def test_writable_text_beyond_ascii(self):
        """Text that is not ASCII but can be written as UTF-8 is kept: an accented card name and a
        feature name holding an astral character, which the export writes as a surrogate-pair
        escape (\\ud83d\\ude00). Variant joetun-1 uses Card 1, which both decks run, and Jötun Grunt:
        a near-miss for deck-a, written to its file and to the matcher index as UTF-8."""
        extra = variant(0)
        extra.update(id="joetun-1", popularity=5,
                     produces=[{"feature": {"id": 9, "name": "Infinite \U0001F600 tokens"}}])
        extra["uses"].append({"card": {"id": 2001, "name": "Jötun Grunt", "oracleId": "oracle-2001"},
                              "mustBeCommander": False, "quantity": 1, "zoneLocations": ["B"]})
        extra["uses"][0]["card"].update(id=1, name="Card 1", oracleId="oracle-1")
        text = export_text(NEW_TIMESTAMP, [variant(n) for n in range(1000)] + [extra])
        self.assertIn("\\ud83d\\ude00", text)
        self.write_cache()

        code, out = self.run_script(gz(text))

        self.assertEqual(code, 0, out[-400:])
        index = json.loads(self.matcher_index.read_text(encoding="utf-8"))
        self.assertEqual(index["cards"]["2001"]["n"], "Jötun Grunt")
        self.assertEqual(index["features"]["9"], "Infinite \U0001F600 tokens")
        self.assertIn("Infinite \U0001F600 tokens".encode(), self.matcher_index.read_bytes())
        near = [c for c in json.loads(self.deck_combos["deck-a"].read_text(encoding="utf-8"))["nearMisses"]
                if c["id"] == "joetun-1"]
        self.assertEqual([(c["missing"]["cards"], c["produces"]) for c in near],
                         [(["Jötun Grunt"], ["Infinite \U0001F600 tokens"])])

    def test_failed_write_of_the_download_leaves_no_file(self):
        """The disk fills while the download is written to its temporary file: the error
        propagates, and the cache, the meta file and the derivative files are unchanged, with
        no temporary file left."""
        self.write_cache()
        before = self.snapshot()
        real_fdopen = os.fdopen

        class FullDisk:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.handle.close()
                return False

            def write(self, data):
                raise OSError(28, "No space left on device")

        script = self.root / "scripts" / "sync_spellbook_combos.py"
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: io.BytesIO(NOT_GZIP)), \
                mock.patch("os.fdopen", lambda fd, *a, **k: FullDisk(real_fdopen(fd, *a, **k))), \
                mock.patch("sys.argv", [script.name]), contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(OSError):
            runpy.run_path(str(script), run_name="__main__")

        self.assertEqual(self.snapshot(), before)

    def test_failed_progress_message_leaves_no_file(self):
        """The screen fails on the "downloaded" line (a closed pipe): the download's temporary
        file is removed all the same."""
        self.write_cache()
        before = self.snapshot()

        class ClosedPipe(io.StringIO):
            def write(self, text):
                if "downloaded" in text:
                    raise BrokenPipeError(32, "Broken pipe")
                return super().write(text)

        script = self.root / "scripts" / "sync_spellbook_combos.py"
        with mock.patch("urllib.request.urlopen", lambda req, timeout=None: io.BytesIO(NOT_GZIP)), \
                mock.patch("sys.argv", [script.name]), contextlib.redirect_stderr(ClosedPipe()), \
                self.assertRaises(BrokenPipeError):
            runpy.run_path(str(script), run_name="__main__")

        self.assertEqual(self.snapshot(), before)

    def test_first_bad_download_leaves_no_export(self):
        """With no cached export yet, a bad download leaves no file in priv_data/spellbook/."""
        before = self.snapshot()

        code, out = self.run_script(NOT_GZIP)

        self.assertEqual(code, 2)
        self.assertIn("the download is not a readable gzip export", out)
        self.assertEqual(list(self.priv.iterdir()), [])
        after = self.snapshot()
        del after["priv_data"], after["priv_data/spellbook"]
        self.assertEqual(after, before)

    # ------------------------------------------------------------------ the current corpus

    def test_current_broken_download_keeps_the_cached_export(self):
        """A download of the corpus that the meta file names, broken after its header, differs
        from the cached export: it is scanned, fails, and none of it reaches the cache."""
        self.check_bad_download(BROKEN_AFTER_HEADER, "the export is cut off")

    def test_current_broken_download_without_a_cache(self):
        """With no cached export, a download of the corpus that the meta file names but broken
        after its header fails the scan and leaves no export."""
        self.write_meta()
        before = self.snapshot()

        code, out = self.run_script(BROKEN_AFTER_HEADER)

        self.assertEqual(code, 2)
        self.assertIn("the export is cut off", out)
        self.assertIn("Corpus left unchanged (degrade to 'corpus stale').\n", out)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()

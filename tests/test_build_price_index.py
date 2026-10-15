"""DEC-1086 — the price index takes a missing price from another printing.

scripts/build_price_index.py reads Scryfall's oracle_cards export (one printing
for each card) and its default_cards export (every printing). For each currency
by itself, a card keeps the non-foil price of its oracle_cards printing; when
that printing has none, it takes the lowest non-foil price among its printings
that count: "paper" in ``games``, released on or before the date of the
default_cards export, and not memorabilia. This is the rule of
data/card-metadata.json (DEC-1079, DEC-1112 R4).

No test here sends a request: the exports sit in a temporary folder, and
FakeScryfall (tests/test_scryfall_fetch.py) stands in for the helper's opener,
for ``urlopen`` and for the clock. A socket guard fails every connect.
"""

import contextlib
import gzip
import importlib
import io
import json
import os
import re
import socket
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from tests.test_scryfall_fetch import FakeScryfall, Sent, scryfall_api

bpi = importlib.import_module("scripts.build_price_index")

BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
ORACLE_URI = "https://data.scryfall.io/oracle-cards/oracle-cards-20261015090112.jsonl.gz"
DEFAULT_URI = "https://data.scryfall.io/default-cards/default-cards-20261015092040.jsonl.gz"
ORACLE_AT = "2026-10-15T09:01:12.402+00:00"
DEFAULT_AT = "2026-10-15T09:20:40.117+00:00"
EXPORT_DATE = "2026-10-15"
DAY_AFTER = "2026-10-16"


def _no_connect(*args, **kwargs):
    raise AssertionError(f"test_build_price_index sent a request: connect{args[1:]}")


_SOCKET_GUARD = contextlib.ExitStack()


def setUpModule():
    for name in ("connect", "connect_ex"):
        _SOCKET_GUARD.enter_context(mock.patch.object(socket.socket, name, _no_connect))
    _SOCKET_GUARD.enter_context(mock.patch.object(socket, "create_connection", _no_connect))


def tearDownModule():
    _SOCKET_GUARD.close()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def card(name: str, eur=None, usd=None, legal=True, **extra) -> dict:
    """An oracle_cards entry: the card's one printing, with string prices as Scryfall gives them."""
    c = {
        "object": "card",
        "name": name,
        "oracle_id": "oid-" + slug(name),
        "legalities": {"commander": "legal" if legal else "not_legal"},
        "prices": {
            "usd": usd, "usd_foil": None, "usd_etched": None,
            "eur": eur, "eur_foil": None, "tix": None,
        },
    }
    c.update(extra)
    return c


def printing(name: str, set_code: str, eur=None, usd=None, released="2020-01-01",
             games=("paper", "mtgo"), set_type="expansion", **prices) -> dict:
    """One default_cards printing of ``name``."""
    p = card(name, eur, usd, id=f"{slug(name)}-{set_code}", set=set_code,
             released_at=released, games=list(games), set_type=set_type)
    p["prices"].update(prices)
    return p


def bulk_data(oracle_at=ORACLE_AT, default_at=DEFAULT_AT) -> dict:
    """A /bulk-data answer with the entries that Scryfall lists."""
    def entry(kind, uri, at):
        return {"object": "bulk_data", "type": kind, "updated_at": at,
                "download_uri": uri.replace(".jsonl.gz", ".json"), "jsonl_download_uri": uri}
    return {"object": "list", "has_more": False, "data": [
        entry("oracle_cards", ORACLE_URI, oracle_at),
        entry("unique_artwork", ORACLE_URI.replace("oracle", "unique-artwork"), oracle_at),
        entry("default_cards", DEFAULT_URI, default_at),
        entry("all_cards", DEFAULT_URI.replace("default", "all"), default_at),
    ]}


def jsonl(cards) -> bytes:
    """Cards as JSON Lines, with a blank last line as a reader must skip."""
    return "".join(json.dumps(c) + "\n" for c in cards).encode() + b"\n"


class IndexCase(unittest.TestCase):
    """A temporary project root, so no case reads or writes data/spellbook."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        out = self.root / "data" / "spellbook"
        self.index_file = out / "price-index.json"
        self.meta_file = out / "price-index.meta.json"
        for name, value in {"PROJECT_ROOT": self.root, "OUT_DIR": out,
                            "INDEX_FILE": self.index_file, "META_FILE": self.meta_file}.items():
            patcher = mock.patch.object(bpi, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.src = self.root / "src"
        self.src.mkdir()

    def write_sources(self, oracle_cards, printings, bulk=None, gz=True) -> list[str]:
        """Write both exports and the /bulk-data answer; return the local arguments."""
        oracle = self.src / ("oracle.jsonl.gz" if gz else "oracle.jsonl")
        default = self.src / "default.jsonl"
        raw = jsonl(oracle_cards)
        oracle.write_bytes(gzip.compress(raw) if gz else raw)
        default.write_bytes(jsonl(printings))
        bulk_file = self.src / "bulk-data.json"
        bulk_file.write_text(json.dumps(bulk or bulk_data()))
        return ["--bulk-data", str(bulk_file), "--oracle-source", str(oracle),
                "--default-source", str(default)]

    def run_main(self, argv) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = bpi.main(argv)
        return code, err.getvalue()

    def build(self, oracle_cards, printings, **kwargs) -> tuple[dict, dict]:
        """Run the script on local sources; return the index and the meta file."""
        code, err = self.run_main(self.write_sources(oracle_cards, printings, **kwargs))
        self.assertEqual(code, 0, err)
        return json.loads(self.index_file.read_text()), json.loads(self.meta_file.read_text())


class FillTests(IndexCase):
    def test_own_price_stays_when_another_printing_is_cheaper(self):
        """Step 1: the oracle_cards printing's price stays, also above a cheaper printing."""
        own = card("Wayfarer's Bauble", eur="4.10", usd="5.79")
        index, meta = self.build([own], [
            printing("Wayfarer's Bauble", "cmm", eur="4.10", usd="5.79"),
            printing("Wayfarer's Bauble", "m21", eur="0.20", usd="0.31"),
        ])
        self.assertEqual(index, {"wayfarer s bauble": [4.1, 5.79]})
        self.assertEqual((meta["pricedEurFromOtherPrinting"], meta["pricedUsdFromOtherPrinting"]),
                         (0, 0))

    def test_missing_price_takes_the_lowest_counted_price_for_each_currency(self):
        """Step 2, currency by currency: a price that the printing has stays, and each
        missing one takes the lowest of its own currency, from any printing."""
        index, meta = self.build([
            card("Blood Crypt", usd="12.00"),
            card("Fellwar Stone", eur="0.90"),
            card("Mind Stone"),
        ], [
            printing("Blood Crypt", "rna", eur="9.50", usd="0.50"),
            printing("Blood Crypt", "dis", eur="8.00"),
            printing("Blood Crypt", "rvr", eur="11.00", usd="0.40"),
            printing("Fellwar Stone", "drk", eur="3.00", usd="2.25"),
            printing("Fellwar Stone", "c16", eur="0.10", usd="1.75"),
            printing("Fellwar Stone", "mic", usd="1.80"),
            printing("Mind Stone", "wth", eur="0.70", usd="0.95"),
            printing("Mind Stone", "c21", eur="0.25"),
            printing("Mind Stone", "dmc", usd="0.33", eur="0.60"),
        ])
        self.assertEqual(index, {
            "blood crypt": [8.0, 12.0],
            "fellwar stone": [0.9, 1.75],
            "mind stone": [0.25, 0.33],
        })
        self.assertEqual((meta["pricedEurFromOtherPrinting"], meta["pricedUsdFromOtherPrinting"]),
                         (2, 2))

    def test_only_cards_that_lack_a_price_are_read_from_default_cards(self):
        """The fill keeps only the oracle ids that it needs (the Mac is shared)."""
        calls = []
        real = bpi.lowest_prices

        def lowest_prices(path, wanted, export_date):
            lowest = real(path, wanted, export_date)
            calls.append((set(wanted), set(lowest), export_date))
            return lowest

        with mock.patch.object(bpi, "lowest_prices", lowest_prices):
            self.build([
                card("Sol Ring", eur="1.49", usd="1.56"),
                card("Blood Crypt", usd="12.00"),
                card("Mind Stone"),
                card("Arena Card"),
            ], [
                printing("Sol Ring", "lea", eur="900.00", usd="1000.00"),
                printing("Blood Crypt", "rna", eur="9.50"),
                printing("Mind Stone", "wth", eur="0.70", usd="0.95"),
                printing("Arena Card", "y25", eur="0.01", games=("arena",)),
            ])
        self.assertEqual(calls, [(
            {"oid-blood-crypt", "oid-mind-stone", "oid-arena-card"},
            {"oid-blood-crypt", "oid-mind-stone"},
            EXPORT_DATE,
        )])

    def test_printings_that_do_not_count(self):
        """A memorabilia printing, a printing with no "paper" in games and a printing
        released after the export's date give no price; one released on that date does."""
        index, meta = self.build([
            card("Memorabilia Card"), card("Online Card"), card("New Card"), card("Arena Card"),
        ], [
            printing("Memorabilia Card", "30a", eur="0.01", usd="0.01", set_type="memorabilia"),
            printing("Memorabilia Card", "lea", eur="0.90", usd="0.80"),
            printing("Online Card", "prm", eur="0.01", usd="0.01", games=("mtgo", "arena")),
            printing("Online Card", "ema", eur="0.90", usd="0.80", games=("mtgo", "paper")),
            printing("New Card", "fra", eur="0.01", usd="0.01", released=DAY_AFTER),
            printing("New Card", "spg", eur="0.50", usd="0.40", released=EXPORT_DATE),
            printing("New Card", "dom", eur="0.90", usd="0.80"),
            printing("Arena Card", "y25", eur="0.01", usd="0.01", games=("arena",)),
        ])
        self.assertEqual(index, {
            "memorabilia card": [0.9, 0.8],
            "online card": [0.9, 0.8],
            "new card": [0.5, 0.4],
        })
        self.assertEqual((meta["keyCount"], meta["pricedEurFromOtherPrinting"],
                          meta["pricedUsdFromOtherPrinting"]), (3, 3, 3))

    def test_export_date_comes_from_the_default_cards_entry(self):
        """The date is the default_cards export's own, not the oracle_cards export's."""
        oracle_cards = [card("New Card")]
        printings = [printing("New Card", "fra", eur="0.50", released=EXPORT_DATE)]
        index, _ = self.build(oracle_cards, printings,
                              bulk=bulk_data(oracle_at="2026-10-14T23:59:00.000+00:00"))
        self.assertEqual(index, {"new card": [0.5, None]})
        index, _ = self.build(oracle_cards, printings,
                              bulk=bulk_data(default_at="2026-10-14T23:59:00.000+00:00"))
        self.assertEqual(index, {})

    def test_foil_and_etched_prices_never_count(self):
        """Neither the oracle_cards printing's nor another printing's foil or etched price."""
        index, _ = self.build([
            card("Lotus Petal", eur_foil="0.05", usd_foil="0.05"),
            card("Commodore Guff", eur_foil="3.00", usd_foil="2.50"),
        ], [
            printing("Lotus Petal", "tmp", eur_foil="0.02", usd_foil="0.02", usd_etched="0.02"),
            printing("Lotus Petal", "mm2", eur="2.00", usd="3.00"),
            printing("Commodore Guff", "moc", eur_foil="3.00", usd_foil="2.50"),
            printing("Commodore Guff", "pmoc", usd_etched="1.00", eur_foil="1.00"),
        ])
        self.assertEqual(index, {"lotus petal": [2.0, 3.0]})

    def test_reversible_printing_joins_by_its_front_face_oracle_id(self):
        """A reversible_card printing carries its oracle id on each face only (DEC-1112 B1)."""
        def reversible(name, set_code, front, back, **prices):
            p = printing(name, set_code, **prices)
            p["layout"] = "reversible_card"
            del p["oracle_id"]
            p["card_faces"] = [{"name": name, "oracle_id": front},
                               {"name": name, "oracle_id": back}]
            return p
        oracle_reversible = card("Pandemonium", layout="reversible_card")
        del oracle_reversible["oracle_id"]
        oracle_reversible["card_faces"] = [{"name": "Pandemonium", "oracle_id": "oid-pandemonium"}]
        index, _ = self.build([card("Agate Instigator"), card("Refute"), oracle_reversible], [
            reversible("Agate Instigator", "sld", "oid-agate-instigator", "oid-refute",
                       eur="0.40", usd="0.45"),
            reversible("Pandemonium", "sld", "oid-pandemonium", "oid-refute", eur="1.10"),
        ])
        self.assertEqual(index, {"agate instigator": [0.4, 0.45], "pandemonium": [1.1, None]})

    def test_card_with_no_counted_price_gets_no_row(self):
        """No row for a card without a price on any printing that counts, nor for a card
        that is not Commander-legal, nor for a printing without an oracle id."""
        stray = printing("Stray Token", "tsld", eur="0.10")
        del stray["oracle_id"]
        orphan = card("Orphan")
        del orphan["oracle_id"]
        index, meta = self.build([
            card("Mocking Sprite"), card("Banned Card", eur="2.00", legal=False), orphan,
        ], [
            printing("Mocking Sprite", "30a", eur="0.10", set_type="memorabilia"),
            printing("Mocking Sprite", "dsk"),
            stray,
        ])
        self.assertEqual(index, {})
        self.assertEqual((meta["keyCount"], meta["pricedEur"], meta["pricedUsd"]), (0, 0, 0))


class NameKeyTests(IndexCase):
    def test_name_keys_and_their_order_do_not_change(self):
        """Full names claim their key first, then the //-faces fill what is left,
        first-wins in the export's order (DEC-553). A card that gains a price claims
        its own full name before a face alias of another card."""
        index, meta = self.build([
            card("Fire // Ice", eur="0.30", usd="0.25"),
            card("Grave Researcher // Reanimate", eur="1.00", usd="1.10"),
            card("Ice", eur="9.00"),
            card("Lim-Dûl's Vault", eur="0.80", usd="1.00"),
            card("Lim-Dul's Vault", eur="5.00", usd="5.00"),
            card("Reanimate"),
        ], [
            printing("Reanimate", "tmp", eur="2.40", usd="2.10"),
        ])
        self.assertEqual(index, {
            "fire ice": [0.3, 0.25],
            "fire": [0.3, 0.25],
            "ice": [9.0, None],
            "grave researcher reanimate": [1.0, 1.1],
            "grave researcher": [1.0, 1.1],
            "reanimate": [2.4, 2.1],
            "lim dul s vault": [0.8, 1.0],
        })
        self.assertEqual(list(json.loads(self.index_file.read_text())), sorted(index))
        self.assertEqual((meta["pricedEurFromOtherPrinting"], meta["pricedUsdFromOtherPrinting"]),
                         (1, 1))

    def test_face_aliases_of_a_filled_card_count_as_from_another_printing(self):
        """The meta counts keys, as keyCount does: a filled // card fills each of its keys."""
        index, meta = self.build([card("Fire // Ice", usd="0.25")],
                                 [printing("Fire // Ice", "mh2", eur="0.30")])
        self.assertEqual(index, {"fire ice": [0.3, 0.25], "fire": [0.3, 0.25],
                                 "ice": [0.3, 0.25]})
        self.assertEqual((meta["keyCount"], meta["pricedEur"], meta["pricedUsd"],
                          meta["pricedEurFromOtherPrinting"], meta["pricedUsdFromOtherPrinting"]),
                         (3, 3, 3, 3, 0))


class MetaAndWriteTests(IndexCase):
    def test_meta_file_names_both_exports_and_the_counts(self):
        _, meta = self.build([
            card("Sol Ring", eur="1.49", usd="1.56"),
            card("Ashnod's Altar", eur="3.00"),
            card("Exotic Orchard", usd="0.50"),
            card("Commodore Guff"),
        ], [
            printing("Ashnod's Altar", "ema", eur="2.50"),
            printing("Exotic Orchard", "con", eur="0.35", usd="0.60"),
        ], gz=False)
        generated = meta.pop("generatedAt")
        self.assertRegex(generated, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")
        note = meta.pop("note")
        self.assertIn("lowest", note)
        self.assertIn("memorabilia", note)
        self.assertEqual(meta, {
            "schema": "combo-lab-price-index",
            "source": "scryfall-bulk-oracle-cards+default-cards",
            "sourceUrl": ORACLE_URI,
            "scryfall_updated_at": ORACLE_AT,
            "defaultCardsUrl": DEFAULT_URI,
            "default_cards_updated_at": DEFAULT_AT,
            "currencies": ["eur", "usd"],
            "keyCount": 3,
            "pricedEur": 3,
            "pricedUsd": 2,
            "pricedEurFromOtherPrinting": 1,
            "pricedUsdFromOtherPrinting": 0,
        })
        self.assertTrue(self.meta_file.read_text().endswith("}\n"))
        self.assertEqual(
            self.index_file.read_text(),
            '{"ashnod s altar":[3.0,null],"exotic orchard":[0.35,0.5],"sol ring":[1.49,1.56]}')

    def test_index_moves_first_and_the_meta_file_last(self):
        moves = []
        real_replace = os.replace

        def record(src, dst):
            moves.append((Path(src).name, Path(dst)))
            real_replace(src, dst)

        with mock.patch.object(bpi.os, "replace", record):
            self.build([card("Sol Ring", eur="1.49")], [])
        self.assertEqual(moves, [("price-index.json.tmp", self.index_file),
                                 ("price-index.meta.json.tmp", self.meta_file)])
        self.assertEqual(sorted(p.name for p in self.index_file.parent.iterdir()),
                         ["price-index.json", "price-index.meta.json"])

    def old_files(self) -> dict[Path, str]:
        self.index_file.parent.mkdir(parents=True)
        old = {self.index_file: '{"old":[1.0,1.0]}', self.meta_file: '{"old": true}\n'}
        for path, text in old.items():
            path.write_text(text)
        return old

    def assert_old_files_stay(self, old: dict[Path, str]):
        for path, text in old.items():
            self.assertEqual(path.read_text(), text)
        self.assertEqual(sorted(p.name for p in self.index_file.parent.iterdir()),
                         ["price-index.json", "price-index.meta.json"])

    def test_write_that_fails_leaves_both_old_files(self):
        """The meta file's temporary write fails: both old files stay, no .tmp stays."""
        old = self.old_files()
        real_write = Path.write_text

        def write(path, text, *args, **kwargs):
            if path.name == "price-index.meta.json.tmp":
                raise OSError("disk full")
            return real_write(path, text, *args, **kwargs)

        with mock.patch.object(Path, "write_text", write), self.assertRaises(OSError):
            self.build([card("Sol Ring", eur="1.49")], [])
        self.assert_old_files_stay(old)

    def test_first_move_that_fails_leaves_both_old_files(self):
        old = self.old_files()
        with mock.patch.object(bpi.os, "replace", side_effect=OSError("busy")), \
                self.assertRaises(OSError):
            self.build([card("Sol Ring", eur="1.49")], [])
        self.assert_old_files_stay(old)


class ArgumentTests(IndexCase):
    def test_local_arguments_go_together(self):
        args = self.write_sources([card("Sol Ring", eur="1.49")], [])
        for drop in ("--bulk-data", "--oracle-source", "--default-source"):
            i = args.index(drop)
            with self.subTest(drop=drop), contextlib.redirect_stderr(io.StringIO()) as err, \
                    self.assertRaises(SystemExit) as raised:
                bpi.main(args[:i] + args[i + 2:])
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("go together", err.getvalue())
        self.assertFalse(self.index_file.exists())

    def test_an_entry_without_a_json_lines_address_ends_the_run(self):
        bulk = bulk_data()
        del bulk["data"][2]["jsonl_download_uri"]
        with self.assertRaisesRegex(RuntimeError, "default_cards entry exposes no JSON Lines"):
            self.build([card("Sol Ring", eur="1.49")], [], bulk=bulk)
        self.assertFalse(self.index_file.exists())

    def test_a_missing_export_entry_ends_the_run(self):
        bulk = bulk_data()
        del bulk["data"][2]
        with self.assertRaisesRegex(RuntimeError, "No default_cards entry"):
            self.build([card("Sol Ring", eur="1.49")], [], bulk=bulk)
        self.assertFalse(self.index_file.exists())


class StreamOnly(io.BytesIO):
    """A download that a reader must take in parts: a read of the whole body fails."""

    def read(self, size=-1):
        if size is None or size < 0:
            raise AssertionError("the download was read whole")
        return super().read(size)


class LinesOnly(io.StringIO):
    """An open export that a reader must take one line at a time."""

    def read(self, *args):
        raise AssertionError("the export was read whole")

    def readlines(self, *args):
        raise AssertionError("the export was read whole")


class StreamTests(IndexCase):
    def test_exports_are_read_one_line_at_a_time(self):
        """iter_cards holds one line: it yields each card before it reads the next line."""
        path = self.src / "lazy.jsonl.gz"
        path.write_bytes(gzip.compress(b'{"name": "A"}\n{not json\n'))
        cards = bpi.iter_cards(path)
        self.assertEqual(next(cards), {"name": "A"})
        with self.assertRaises(json.JSONDecodeError):
            next(cards)
        text = '{"name": "A"}\n\n{"name": "B"}\n'
        with mock.patch.object(bpi.gzip, "open", lambda *args, **kwargs: LinesOnly(text)):
            self.assertEqual(list(bpi.iter_cards(path)), [{"name": "A"}, {"name": "B"}])


class BulkScryfall(FakeScryfall):
    """FakeScryfall that answers /bulk-data and serves the two exports from
    data.scryfall.io as a stream that a reader takes in parts."""

    def __init__(self, oracle_cards, printings, bulk=None):
        super().__init__()
        self.bulk = bulk or bulk_data()
        self.pages[BULK_DATA_URL] = self.bulk
        self.files = {ORACLE_URI: gzip.compress(jsonl(oracle_cards)),
                      DEFAULT_URI: gzip.compress(jsonl(printings))}

    def urlopen(self, req, timeout=None):
        if urllib.parse.urlsplit(req.full_url).hostname != "data.scryfall.io":
            return super().urlopen(req, timeout)
        headers = {key.lower(): value for key, value in req.header_items()}
        self.sent.append(Sent(self.now, self.now, req.full_url, None, headers))
        return StreamOnly(self.files[req.full_url])


class LiveRunTests(IndexCase):
    ORACLE = [card("Sol Ring", eur="1.49", usd="1.56"), card("Blood Crypt")]
    PRINTS = [printing("Blood Crypt", "rna", eur="9.50", usd="10.00"),
              printing("Blood Crypt", "dis", eur="8.00")]

    def run_live(self, fake: FakeScryfall, *argv: str) -> tuple[int, str]:
        with fake.installed():
            return self.run_main(list(argv))

    def test_live_run_sends_bulk_data_through_the_helper_and_keeps_the_downloads(self):
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        folder = self.root / "live"
        code, err = self.run_live(fake, "--download-dir", str(folder))
        self.assertEqual(code, 0, err)
        self.assertEqual([s.url for s in fake.sent], [BULK_DATA_URL, ORACLE_URI, DEFAULT_URI])
        self.assertEqual(fake.sent[0].headers["user-agent"], scryfall_api.USER_AGENT)
        self.assertEqual(fake.sent[1].headers["user-agent"], bpi.USER_AGENT)
        saved = {p.name: p.read_bytes() for p in folder.iterdir()}
        self.assertEqual(saved, {
            "bulk-data.json": json.dumps(fake.bulk).encode(),
            "oracle-cards-20261015090112.jsonl.gz": fake.files[ORACLE_URI],
            "default-cards-20261015092040.jsonl.gz": fake.files[DEFAULT_URI],
        })
        index = self.index_file.read_text()
        meta = json.loads(self.meta_file.read_text())
        self.assertEqual(json.loads(index), {"blood crypt": [8.0, 10.0], "sol ring": [1.49, 1.56]})
        self.assertEqual((meta["scryfall_updated_at"], meta["default_cards_updated_at"]),
                         (ORACLE_AT, DEFAULT_AT))
        for line in (f"Downloading {ORACLE_URI}...", f"Downloading {DEFAULT_URI}...",
                     "2 commander-legal cards; 1 lack a price. Reading the printings "
                     "released on or before 2026-10-15...",
                     "(0.0 MB, 2 keys; eur 2 / usd 2; from another printing eur 1 / usd 1)."):
            self.assertIn(line, err)

        # The saved files rebuild the same files with no request.
        self.index_file.unlink()
        code, err = self.run_main([
            "--bulk-data", str(folder / "bulk-data.json"),
            "--oracle-source", str(folder / "oracle-cards-20261015090112.jsonl.gz"),
            "--default-source", str(folder / "default-cards-20261015092040.jsonl.gz")])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.index_file.read_text(), index)
        again = json.loads(self.meta_file.read_text())
        self.assertEqual({**again, "generatedAt": None}, {**meta, "generatedAt": None})

    def test_live_run_without_a_download_folder_removes_its_downloads(self):
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        folders = []
        real = bpi.download

        def download(uri, folder):
            folders.append(folder)
            self.assertTrue((folder / "bulk-data.json").exists())
            return real(uri, folder)

        with mock.patch.object(bpi, "download", download):
            code, err = self.run_live(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(folders), 2)
        self.assertEqual(folders[0], folders[1])
        self.assertFalse(folders[0].exists())
        self.assertEqual(json.loads(self.index_file.read_text())["blood crypt"], [8.0, 10.0])

    def current_meta(self, oracle_at=ORACLE_AT, default_at=DEFAULT_AT) -> dict[Path, str]:
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        files = {self.index_file: '{"old":[1.0,1.0]}',
                 self.meta_file: json.dumps({"scryfall_updated_at": oracle_at,
                                             "default_cards_updated_at": default_at})}
        for path, text in files.items():
            path.write_text(text)
        return files

    def test_current_index_downloads_nothing(self):
        files = self.current_meta()
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        code, err = self.run_live(fake)
        self.assertEqual(code, 0, err)
        self.assertIn("is current", err)
        self.assertEqual([s.url for s in fake.sent], [BULK_DATA_URL])
        for path, text in files.items():
            self.assertEqual(path.read_text(), text)

    def test_the_current_check_reads_both_exports_times(self):
        for case, (oracle_at, default_at) in {
            "a new oracle_cards export": ("2026-10-14T09:00:00.000+00:00", DEFAULT_AT),
            "a new default_cards export": (ORACLE_AT, "2026-10-14T09:00:00.000+00:00"),
        }.items():
            with self.subTest(case):
                self.current_meta(oracle_at, default_at)
                fake = BulkScryfall(self.ORACLE, self.PRINTS)
                code, err = self.run_live(fake)
                self.assertEqual(code, 0, err)
                self.assertEqual([s.url for s in fake.sent],
                                 [BULK_DATA_URL, ORACLE_URI, DEFAULT_URI])
                self.assertEqual(json.loads(self.meta_file.read_text())["scryfall_updated_at"],
                                 ORACLE_AT)

    def test_force_rebuilds_a_current_index(self):
        self.current_meta()
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        code, err = self.run_live(fake, "--force")
        self.assertEqual(code, 0, err)
        self.assertEqual([s.url for s in fake.sent], [BULK_DATA_URL, ORACLE_URI, DEFAULT_URI])
        self.assertIn("blood crypt", json.loads(self.index_file.read_text()))

    def test_unreadable_meta_file_counts_as_not_current(self):
        self.index_file.parent.mkdir(parents=True)
        self.index_file.write_text("{}")
        self.meta_file.write_text("{not json")
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        code, err = self.run_live(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.sent), 3)

    def test_meta_file_without_index_counts_as_not_current(self):
        self.current_meta()
        self.index_file.unlink()
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        code, err = self.run_live(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.sent), 3)

    def test_429_on_bulk_data_ends_the_run(self):
        old = {self.index_file: "{}", self.meta_file: "{}"}
        self.index_file.parent.mkdir(parents=True)
        for path, text in old.items():
            path.write_text(text)
        fake = BulkScryfall(self.ORACLE, self.PRINTS)
        fake.failures[0] = 429
        folder = self.root / "live"
        code, err = self.run_live(fake, "--force", "--download-dir", str(folder))
        self.assertEqual(code, 1)
        self.assertIn("429", err)
        self.assertIn("wait 30 seconds or more", err)
        self.assertIn("No file written.", err)
        self.assertEqual([s.url for s in fake.sent], [BULK_DATA_URL])
        self.assertFalse(folder.exists())
        for path, text in old.items():
            self.assertEqual(path.read_text(), text)


class SocketGuardTests(unittest.TestCase):
    def test_guard_fails_a_connect(self):
        with self.assertRaises(AssertionError):
            socket.create_connection(("127.0.0.1", 9))
        with socket.socket() as s, self.assertRaises(AssertionError):
            s.connect(("127.0.0.1", 9))


if __name__ == "__main__":
    unittest.main()

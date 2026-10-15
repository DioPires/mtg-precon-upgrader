"""DEC-1140 kill cases for PR #55 (head 66920a3): one case for each survivor that stands.

Copy to tests/test_dec1140_kill_cases.py and run it with tests/test_build_price_index.py.
Each case passes on the head and fails on its mutant (item 6 d of the brief):

  K-S1  test_local_run_always_rebuilds                         S1
  K-S3  test_a_later_export_of_the_same_day_is_not_current     S3
  K-N4  test_a_claimed_full_name_keeps_its_own_counts          N4
  K-N5  test_a_claimed_full_name_still_gives_its_face_aliases  N5
  K-N6  test_each_download_has_a_timeout                       N6
  K-N7  test_a_download_replaces_a_leftover_file               N7
  K-N8  test_download_folder_is_made_with_its_parents          N8
  K-I4  test_exports_read_as_utf8_whatever_the_locale          I4
  K-I5  test_an_export_with_cr_line_ends_reads_one_card_a_line I5

No case sends a request: the cases use the module's FakeScryfall and a socket guard.
"""

import contextlib
import gzip
import json
import socket
import unittest
import urllib.parse
from unittest import mock

import tests.test_build_price_index as t

bpi = t.bpi

_SOCKET_GUARD = contextlib.ExitStack()


def setUpModule():
    for name in ("connect", "connect_ex"):
        _SOCKET_GUARD.enter_context(mock.patch.object(socket.socket, name, t._no_connect))
    _SOCKET_GUARD.enter_context(mock.patch.object(socket, "create_connection", t._no_connect))


def tearDownModule():
    _SOCKET_GUARD.close()


ORACLE = [t.card("Sol Ring", eur="1.49", usd="1.56"), t.card("Blood Crypt")]
PRINTS = [t.printing("Blood Crypt", "rna", eur="9.50", usd="10.00"),
          t.printing("Blood Crypt", "dis", eur="8.00")]
ORACLE_FILE = "oracle-cards-20261015090112.jsonl.gz"
DEFAULT_FILE = "default-cards-20261015092040.jsonl.gz"


class KillCases(t.IndexCase):
    def run_live(self, fake, *argv):
        with fake.installed():
            return self.run_main(list(argv))

    def current_meta(self, oracle_at=t.ORACLE_AT, default_at=t.DEFAULT_AT):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text('{"old":[1.0,1.0]}')
        self.meta_file.write_text(json.dumps({"scryfall_updated_at": oracle_at,
                                              "default_cards_updated_at": default_at}))

    # K-S1
    def test_local_run_always_rebuilds(self):
        """A run on saved files rebuilds, also when the meta file names the same two exports."""
        args = self.write_sources([t.card("Sol Ring", eur="1.49", usd="1.56")], [])
        self.current_meta()
        code, err = self.run_main(args)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.index_file.read_text()), {"sol ring": [1.49, 1.56]})
        self.assertIn("generatedAt", json.loads(self.meta_file.read_text()))

    # K-S3
    def test_a_later_export_of_the_same_day_is_not_current(self):
        """The current check compares whole times: a second export of one day is new."""
        for case, (oracle_at, default_at) in {
            "an earlier oracle_cards export of the same day":
                ("2026-10-15T01:00:00.000+00:00", t.DEFAULT_AT),
            "an earlier default_cards export of the same day":
                (t.ORACLE_AT, "2026-10-15T01:00:00.000+00:00"),
        }.items():
            with self.subTest(case):
                self.current_meta(oracle_at, default_at)
                fake = t.BulkScryfall(ORACLE, PRINTS)
                code, err = self.run_live(fake)
                self.assertEqual(code, 0, err)
                self.assertEqual([s.url for s in fake.sent],
                                 [t.BULK_DATA_URL, t.ORACLE_URI, t.DEFAULT_URI])
                self.assertEqual(json.loads(self.index_file.read_text()),
                                 {"blood crypt": [8.0, 10.0], "sol ring": [1.49, 1.56]})

    # K-N4
    def test_a_claimed_full_name_keeps_its_own_counts(self):
        """Two cards with one full-name key: the key's row and its counts come from the
        first card, also when the second card's price would come from another printing."""
        index, meta = self.build(
            [t.card("Lim-Dûl's Vault", eur="0.80", usd="1.00"), t.card("Lim-Dul's Vault")],
            [t.printing("Lim-Dul's Vault", "all", eur="5.00", usd="5.00")])
        self.assertEqual(index, {"lim dul s vault": [0.8, 1.0]})
        self.assertEqual((meta["pricedEurFromOtherPrinting"], meta["pricedUsdFromOtherPrinting"]),
                         (0, 0))

    # K-N5
    def test_a_claimed_full_name_still_gives_its_face_aliases(self):
        """A // card whose full-name key another card claimed still fills its free face keys."""
        index, _ = self.build([t.card("Fire Ice", eur="5.00"),
                               t.card("Fire // Ice", eur="0.30", usd="0.25")], [])
        self.assertEqual(index, {"fire ice": [5.0, None], "fire": [0.3, 0.25],
                                 "ice": [0.3, 0.25]})

    # K-N6
    def test_each_download_has_a_timeout(self):
        """A stalled download must end the run, so each download gives urlopen a timeout."""
        fake = t.BulkScryfall(ORACLE, PRINTS)
        timeouts = []
        real = fake.urlopen

        def urlopen(req, timeout=None):
            if urllib.parse.urlsplit(req.full_url).hostname == "data.scryfall.io":
                timeouts.append(timeout)
            return real(req, timeout)

        fake.urlopen = urlopen
        code, err = self.run_live(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(timeouts), 2)
        for timeout in timeouts:
            self.assertIsInstance(timeout, (int, float))
            self.assertGreater(timeout, 0)

    # K-N7
    def test_a_download_replaces_a_leftover_file(self):
        """A file of the export's name in --download-dir (a killed run's part) is replaced."""
        folder = self.root / "live"
        folder.mkdir()
        (folder / ORACLE_FILE).write_bytes(b"part of a killed run's download")
        fake = t.BulkScryfall(ORACLE, PRINTS)
        code, err = self.run_live(fake, "--download-dir", str(folder))
        self.assertEqual(code, 0, err)
        self.assertEqual((folder / ORACLE_FILE).read_bytes(), fake.files[t.ORACLE_URI])
        self.assertEqual(json.loads(self.index_file.read_text())["blood crypt"], [8.0, 10.0])

    # K-N8
    def test_download_folder_is_made_with_its_parents(self):
        folder = self.root / "scratch" / "live"
        fake = t.BulkScryfall(ORACLE, PRINTS)
        code, err = self.run_live(fake, "--download-dir", str(folder))
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["bulk-data.json", DEFAULT_FILE, ORACLE_FILE])

    # K-I4
    def test_exports_read_as_utf8_whatever_the_locale(self):
        """A text-mode open without an encoding takes the locale's. Under a Latin-1
        locale (LC_ALL=en_US.ISO8859-1) a name with an accent must still read right."""
        real_open = gzip.open

        def latin1_locale_open(filename, mode="rb", compresslevel=9, encoding=None,
                               errors=None, newline=None):
            if "t" in mode and encoding is None:
                encoding = "latin-1"
            return real_open(filename, mode, compresslevel, encoding, errors, newline)

        path = self.src / "names.jsonl.gz"
        path.write_bytes(gzip.compress(
            json.dumps({"name": "Lim-Dûl's Vault"}, ensure_ascii=False).encode() + b"\n"))
        with mock.patch.object(bpi.gzip, "open", latin1_locale_open):
            self.assertEqual(list(bpi.iter_cards(path)), [{"name": "Lim-Dûl's Vault"}])

    # K-I5
    def test_an_export_with_cr_line_ends_reads_one_card_a_line(self):
        path = self.src / "cr.jsonl.gz"
        path.write_bytes(gzip.compress(b'{"name": "A"}\r{"name": "B"}\r'))
        self.assertEqual(list(bpi.iter_cards(path)), [{"name": "A"}, {"name": "B"}])


if __name__ == "__main__":
    unittest.main()

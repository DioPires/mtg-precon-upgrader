"""DEC-1075 — the fetch scripts keep Scryfall's limits.

No test here sends a live request: FakeScryfall stands in for ``urlopen`` and
for the clock.
"""

import contextlib
import importlib
import io
import json
import re
import tempfile
import unittest
import urllib.error
import urllib.parse
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


fetch_metadata = importlib.import_module("scripts.fetch_card_metadata")
fetch_images = importlib.import_module("scripts.fetch_card_images")
# The module object that both scripts import.
scryfall_api = fetch_metadata.scryfall_api

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
STAMP = "1700000000"

Sent = namedtuple("Sent", "started answered url body headers")


def image_uris(path: str) -> dict:
    """Scryfall's ``image_uris`` for one image path."""
    uris = {
        size: f"https://cards.scryfall.io/{size}/{path}"
        for size in ("small", "normal", "large", "art_crop", "border_crop")
    }
    uris["png"] = f"https://cards.scryfall.io/png/{path.replace('.jpg', '.png')}"
    return uris


def image_path(name: str, side: str = "front") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{side}/a/b/{slug}.jpg?{STAMP}"


def make_card(name: str, layout: str = "normal", usd="1.50", eur="1.20", **extra) -> dict:
    """A Scryfall card object with the fields that the scripts read."""
    card = {
        "object": "card",
        "name": name,
        "layout": layout,
        "type_line": "Instant",
        "cmc": 1.0,
        "mana_cost": "{U}",
        "colors": ["U"],
        "oracle_text": f"Text of {name}.",
        "prices": {
            "usd": usd, "usd_foil": None, "usd_etched": None,
            "eur": eur, "eur_foil": None, "tix": None,
        },
    }
    faces = name.split(" // ")
    if layout in ("transform", "modal_dfc"):
        # Scryfall gives these layouts no top-level image_uris.
        card["card_faces"] = [
            {"name": faces[0], "image_uris": image_uris(image_path(name, "front"))},
            {"name": faces[1], "image_uris": image_uris(image_path(name, "back"))},
        ]
    else:
        card["image_uris"] = image_uris(image_path(name))
        if len(faces) > 1:
            card["card_faces"] = [{"name": face} for face in faces]
    card.update(extra)
    return card


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeScryfall:
    """A fake ``urlopen`` and a fake clock for both Scryfall hosts.

    Each answer takes LATENCY seconds of fake time, so a case can tell "600 ms
    after the last answer" from "600 ms after the last request start".

    The API answers as Scryfall does (DEC-1072, live reading 1): it finds a
    card by its full name when that name has no ``//``, or by its front face,
    and it does not find a full ``//`` name.
    """

    LATENCY = 0.25

    def __init__(self, cards=()):
        self.now = 50_000.0
        self.by_name = {card["name"].split(" // ")[0]: card for card in cards}
        self.sent: list[Sent] = []
        self.sleeps: list[float] = []
        # Request index -> an HTTP status, an exception or a raw body.
        self.failures: dict[int, object] = {}

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def urlopen(self, req, timeout=None):
        index = len(self.sent)
        started = self.now
        self.now += self.LATENCY
        url = req.full_url
        body = json.loads(req.data) if req.data else None
        headers = {key.lower(): value for key, value in req.header_items()}
        self.sent.append(Sent(started, self.now, url, body, headers))

        failure = self.failures.get(index)
        if isinstance(failure, int):
            raise urllib.error.HTTPError(url, failure, f"status {failure}", {}, io.BytesIO())
        if isinstance(failure, Exception):
            raise failure
        if isinstance(failure, bytes):
            return FakeResponse(failure)

        parts = urllib.parse.urlsplit(url)
        if parts.hostname == "cards.scryfall.io":
            return FakeResponse(b"image bytes")
        if parts.path == "/cards/collection":
            data, not_found = [], []
            for identifier in body["identifiers"]:
                card = self.by_name.get(identifier["name"])
                if card is None:
                    not_found.append(identifier)
                else:
                    data.append(card)
            answer = {"object": "list", "not_found": not_found, "data": data}
            return FakeResponse(json.dumps(answer).encode())
        if parts.path == "/cards/named":
            exact = urllib.parse.parse_qs(parts.query)["exact"][0]
            card = self.by_name.get(exact)
            if card is not None:
                return FakeResponse(json.dumps(card).encode())
        raise urllib.error.HTTPError(url, 404, "status 404", {}, io.BytesIO())

    def installed(self) -> contextlib.ExitStack:
        """Patch ``urlopen`` and the clock everywhere, and reset the helper's state."""
        scryfall_api._last_answer_at = None
        scryfall_api._rate_limited = False
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch("urllib.request.urlopen", self.urlopen))
        stack.enter_context(mock.patch("time.monotonic", self.monotonic))
        stack.enter_context(mock.patch("time.sleep", self.sleep))
        return stack

    def api_requests(self) -> list[Sent]:
        return [s for s in self.sent if urllib.parse.urlsplit(s.url).hostname == "api.scryfall.com"]

    def asked_names(self) -> list[str]:
        """Every name of every /cards/collection body, in order."""
        return [
            identifier["name"]
            for s in self.sent if s.url == COLLECTION_URL
            for identifier in s.body["identifiers"]
        ]

    def gaps(self) -> list[float]:
        """Seconds from each API answer to the start of the next API request."""
        sent = self.api_requests()
        return [later.started - earlier.answered for earlier, later in zip(sent, sent[1:])]


class DeckDirCase(unittest.TestCase):
    """A temporary data directory with deck files and an output path."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.commanders = self.root / "commanders"
        self.output = self.root / "card-metadata.json"
        self.meta = self.root / "card-metadata.meta.json"

    def write_deck(self, deck_id: str, commander: str, *names: str) -> None:
        deck_dir = self.commanders / deck_id
        deck_dir.mkdir(parents=True)
        deck = {"commander": commander, "decklist": [{"name": name} for name in names]}
        (deck_dir / "deck.json").write_text(json.dumps(deck))

    def run_metadata(self, fake: FakeScryfall, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with fake.installed(), \
                mock.patch.object(fetch_metadata, "COMMANDERS_DIR", self.commanders), \
                contextlib.redirect_stdout(out):
            code = fetch_metadata.main(["--output-file", str(self.output), *argv])
        return code, out.getvalue()

    def assert_no_file_written(self):
        self.assertFalse(self.output.exists())
        self.assertFalse(self.meta.exists())


class ScryfallApiTests(unittest.TestCase):
    """Rule 1 and rule 2 at the helper."""

    def test_first_request_starts_at_once(self):
        fake = FakeScryfall()
        with fake.installed():
            scryfall_api.request(COLLECTION_URL, {"identifiers": []})
        self.assertEqual(fake.sleeps, [])
        self.assertEqual(len(fake.sent), 1)

    def test_request_starts_600ms_after_the_last_answer(self):
        fake = FakeScryfall()
        with fake.installed():
            for _ in range(4):
                scryfall_api.request(COLLECTION_URL, {"identifiers": []})
        self.assertEqual(len(fake.gaps()), 3)
        for gap in fake.gaps():
            self.assertAlmostEqual(gap, 0.6, places=9)

    def test_no_wait_when_600ms_have_passed(self):
        fake = FakeScryfall()
        with fake.installed():
            scryfall_api.request(COLLECTION_URL, {"identifiers": []})
            fake.now += 0.6
            scryfall_api.request(COLLECTION_URL, {"identifiers": []})
        self.assertEqual(fake.sleeps, [])

    def test_request_waits_after_a_failed_answer_too(self):
        fake = FakeScryfall()
        fake.failures[0] = 500
        with fake.installed():
            with self.assertRaises(urllib.error.HTTPError):
                scryfall_api.request(COLLECTION_URL, {"identifiers": []})
            scryfall_api.request(COLLECTION_URL, {"identifiers": []})
        self.assertAlmostEqual(fake.gaps()[0], 0.6, places=9)

    def test_request_sends_user_agent_and_accept(self):
        fake = FakeScryfall()
        with fake.installed():
            scryfall_api.request(COLLECTION_URL, {"identifiers": [{"name": "Sol Ring"}]})
            with self.assertRaises(urllib.error.HTTPError):
                scryfall_api.request("https://api.scryfall.com/cards/unknown")
        post, get = fake.sent
        for sent in (post, get):
            self.assertEqual(sent.headers["user-agent"], "MTGPreconUpgrader/1.0")
            self.assertEqual(sent.headers["accept"], "application/json")
        self.assertEqual(post.headers["content-type"], "application/json")
        self.assertEqual(post.body, {"identifiers": [{"name": "Sol Ring"}]})
        self.assertIsNone(get.body)

    def test_429_raises_and_no_later_request_goes_out(self):
        fake = FakeScryfall()
        fake.failures[0] = 429
        with fake.installed():
            with self.assertRaises(scryfall_api.ScryfallRateLimited) as raised:
                scryfall_api.request(COLLECTION_URL, {"identifiers": []})
            with self.assertRaises(scryfall_api.ScryfallRateLimited):
                scryfall_api.request(COLLECTION_URL, {"identifiers": []})
        self.assertEqual(len(fake.sent), 1)
        self.assertIn("429", str(raised.exception))
        self.assertIn("wait 30 seconds or more", str(raised.exception))

    def test_request_refuses_another_host(self):
        fake = FakeScryfall()
        with fake.installed():
            with self.assertRaises(ValueError):
                scryfall_api.request("https://cards.scryfall.io/normal/front/a/b/x.jpg")
        self.assertEqual(fake.sent, [])


class FetchCardMetadataRunTests(DeckDirCase):
    def test_batches_start_600ms_after_the_last_answer(self):
        """Rule 1 over three batches of the real size."""
        names = [f"Card {n:03d}" for n in range(160)]
        self.write_deck("big", *names)
        fake = FakeScryfall(make_card(name) for name in names)

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL] * 3)
        self.assertEqual([len(s.body["identifiers"]) for s in fake.sent], [75, 75, 10])
        self.assertEqual(sorted(fake.asked_names()), names)
        self.assertEqual(len(fake.gaps()), 2)
        for gap in fake.gaps():
            self.assertAlmostEqual(gap, 0.6, places=9)
        for sent in fake.sent:
            self.assertEqual(sent.headers["user-agent"], "MTGPreconUpgrader/1.0")
            self.assertEqual(sent.headers["accept"], "application/json")

    def test_429_ends_the_run(self):
        """Rule 2: no file, the status and the wait on screen, exit code not 0, no later request."""
        names = [f"Card {n:03d}" for n in range(300)]
        self.write_deck("big", *names)
        fake = FakeScryfall(make_card(name) for name in names)
        fake.failures[1] = 429

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("429", out)
        self.assertIn("wait 30 seconds or more", out)
        self.assertEqual(len(fake.sent), 2)
        self.assert_no_file_written()

    def test_429_leaves_an_old_file_as_it_was(self):
        self.write_deck("one", "Sol Ring")
        self.output.write_text('{"Sol Ring": {"cmc": 1.0}}')
        fake = FakeScryfall([make_card("Sol Ring")])
        fake.failures[0] = 429

        code, _ = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertEqual(self.output.read_text(), '{"Sol Ring": {"cmc": 1.0}}')
        self.assertFalse(self.meta.exists())

    def test_failed_batch_ends_the_run(self):
        """Rule 3: the same end for every kind of failed batch."""
        names = [f"Card {n:03d}" for n in range(300)]
        self.write_deck("big", *names)
        failures = {
            "HTTP 500": 500,
            "network error": urllib.error.URLError("connection refused"),
            "timeout": TimeoutError("timed out"),
            "not JSON": b"<html>bad gateway</html>",
            "no data list": b'{"object": "error", "status": 400}',
        }
        for label, failure in failures.items():
            with self.subTest(failure=label):
                fake = FakeScryfall(make_card(name) for name in names)
                fake.failures[1] = failure

                code, out = self.run_metadata(fake)

                self.assertNotEqual(code, 0)
                self.assertIn("Batch 2/4 failed", out)
                self.assertEqual(len(fake.sent), 2)
                self.assert_no_file_written()
        # The status is on screen.
        self.assertIn("500", self._out_for(names, 500))

    def _out_for(self, names, failure) -> str:
        fake = FakeScryfall(make_card(name) for name in names)
        fake.failures[0] = failure
        return self.run_metadata(fake)[1]

    def test_slash_name_goes_out_as_its_front_face(self):
        """Rule 4: the front face in the body, no /cards/named address, three keys stored."""
        self.write_deck("one", "Sol Ring", "Bonecrusher Giant // Stomp", "Valakut Awakening")
        fake = FakeScryfall([
            make_card("Sol Ring"),
            make_card("Bonecrusher Giant // Stomp", layout="adventure"),
            make_card("Valakut Awakening // Valakut Stoneforge", layout="modal_dfc"),
        ])

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertEqual(fake.asked_names(), ["Bonecrusher Giant", "Sol Ring", "Valakut Awakening"])
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        metadata = json.loads(self.output.read_text())
        self.assertEqual(sorted(metadata), [
            "Bonecrusher Giant",
            "Bonecrusher Giant // Stomp",
            "Sol Ring",
            "Valakut Awakening",
            "Valakut Awakening // Valakut Stoneforge",
        ])
        self.assertEqual(metadata["Bonecrusher Giant"], metadata["Bonecrusher Giant // Stomp"])
        self.assertEqual(
            metadata["Valakut Awakening"], metadata["Valakut Awakening // Valakut Stoneforge"])
        self.assertEqual(
            metadata["Bonecrusher Giant // Stomp"]["image"], image_path("Bonecrusher Giant // Stomp"))

    def test_full_name_answers_before_front_face(self):
        """"Brainstorm" is a card and also the second part of another card."""
        self.write_deck("one", "Brainstorm", "Harmonized Trio // Brainstorm")
        fake = FakeScryfall([
            make_card("Harmonized Trio // Brainstorm", layout="prepare"),
            make_card("Brainstorm"),
        ])

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        metadata = json.loads(self.output.read_text())
        self.assertEqual(metadata["Brainstorm"]["image"], image_path("Brainstorm"))
        self.assertEqual(
            metadata["Harmonized Trio"]["image"], image_path("Harmonized Trio // Brainstorm"))

    def test_deck_card_not_found_ends_the_run(self):
        """Rule 5, a name that a deck file names."""
        names = [f"Card {n:03d}" for n in range(200)]
        self.write_deck("big", *names)
        missing = names[3]
        fake = FakeScryfall(make_card(name) for name in names if name != missing)

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn(missing, out)
        self.assertEqual(len(fake.sent), 1)
        self.assert_no_file_written()

    def test_deck_card_of_an_unselected_deck_not_found_ends_the_run(self):
        self.write_deck("one", "Sol Ring")
        self.write_deck("two", "Gone Card")
        old = {"Gone Card": {"cmc": 2.0, "type_line": "Artifact"}}
        self.output.write_text(json.dumps(old))
        fake = FakeScryfall([make_card("Sol Ring")])

        code, out = self.run_metadata(fake, "--deck", "one")

        self.assertNotEqual(code, 0)
        self.assertIn("Gone Card", out)
        self.assertEqual(json.loads(self.output.read_text()), old)

    def test_other_name_not_found_keeps_its_old_entry_without_image_and_prices(self):
        """Rule 5, a name that no deck file names."""
        self.write_deck("one", "Sol Ring")
        old_entry = {
            "cmc": 2.0, "colors": [], "mana_cost": "{2}", "oracle_text": "Old text.",
            "power": None, "toughness": None, "type_line": "Artifact",
            "image": "front/o/l/old.jpg?1", "usd": 9.99, "eur": 8.88,
        }
        self.output.write_text(json.dumps({"Gone Card": old_entry}))
        fake = FakeScryfall([make_card("Sol Ring")])

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertIn("Gone Card", out)
        metadata = json.loads(self.output.read_text())
        self.assertEqual(sorted(metadata), ["Gone Card", "Sol Ring"])
        self.assertEqual(
            metadata["Gone Card"], {**old_entry, "image": None, "usd": None, "eur": None})

    def test_slash_name_with_another_second_part_is_not_found(self):
        """The front face found a card, but not the card that the name asks for."""
        self.write_deck("one", "Sol Ring")
        old = {"Dusk // Night": {"cmc": 4.0, "type_line": "Sorcery // Sorcery"}}
        self.output.write_text(json.dumps(old))
        fake = FakeScryfall([make_card("Sol Ring"), make_card("Dusk // Dawn", layout="split")])

        code, out = self.run_metadata(fake)

        self.assertEqual(code, 0)
        self.assertIn("Dusk // Night", out)
        metadata = json.loads(self.output.read_text())
        self.assertEqual(sorted(metadata), ["Dusk // Night", "Sol Ring"])
        self.assertIsNone(metadata["Dusk // Night"]["image"])

    def test_entry_gains_image_usd_and_eur(self):
        """Rule 6: the path with its ``?`` part, prices as numbers, no foil fallback."""
        self.write_deck("one", "Sol Ring", "Foil Only", "No Price")
        foil_only = make_card("Foil Only", usd=None, eur=None)
        foil_only["prices"].update(usd_foil="3.00", usd_etched="4.00", eur_foil="2.50")
        fake = FakeScryfall([
            make_card("Sol Ring", usd="1.50", eur="0.07"),
            foil_only,
            make_card("No Price", prices={}),
        ])

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        metadata = json.loads(self.output.read_text())
        self.assertEqual(metadata["Sol Ring"]["image"], f"front/a/b/sol-ring.jpg?{STAMP}")
        self.assertEqual(metadata["Sol Ring"]["usd"], 1.5)
        self.assertEqual(metadata["Sol Ring"]["eur"], 0.07)
        for name in ("Foil Only", "No Price"):
            self.assertIsNone(metadata[name]["usd"])
            self.assertIsNone(metadata[name]["eur"])
        for entry in metadata.values():
            self.assertLessEqual({"image", "usd", "eur"}, set(entry))

    def test_card_whose_size_address_differs_ends_the_run(self):
        """Rule 6: one path must serve small, normal, large and art_crop."""
        names = [f"Card {n:03d}" for n in range(200)]
        self.write_deck("big", *names)
        odd = names[5]
        for size in ("large", "small", "art_crop"):
            with self.subTest(size=size):
                cards = {name: make_card(name) for name in names}
                cards[odd]["image_uris"][size] = (
                    f"https://cards.scryfall.io/{size}/front/z/z/other.jpg?{STAMP}")
                fake = FakeScryfall(cards.values())

                code, out = self.run_metadata(fake)

                self.assertNotEqual(code, 0)
                self.assertIn(odd, out)
                self.assertIn(size, out)
                self.assertEqual(len(fake.sent), 1)
                self.assert_no_file_written()

    def test_card_without_a_normal_image_address_ends_the_run(self):
        self.write_deck("one", "Sol Ring", "No Image", "Other Host")
        no_image = make_card("No Image")
        del no_image["image_uris"]
        other_host = make_card("Other Host")
        other_host["image_uris"]["normal"] = "https://example.com/normal/front/a/b/x.jpg"
        fake = FakeScryfall([make_card("Sol Ring"), no_image, other_host])

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("No Image", out)
        self.assertIn("Other Host", out)
        self.assert_no_file_written()

    def test_transform_and_modal_dfc_take_the_image_from_the_front_face(self):
        transform = "Westvale Abbey // Ormendahl, Profane Prince"
        modal = "Valakut Awakening // Valakut Stoneforge"
        self.write_deck("one", "Sol Ring", transform, modal)
        fake = FakeScryfall([
            make_card("Sol Ring"),
            make_card(transform, layout="transform"),
            make_card(modal, layout="modal_dfc"),
        ])

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        metadata = json.loads(self.output.read_text())
        for name in (transform, modal):
            self.assertEqual(metadata[name]["image"], image_path(name, "front"))
            self.assertEqual(metadata[name.split(" // ")[0]]["image"], image_path(name, "front"))

    def test_dfc_whose_front_face_breaks_the_path_check_ends_the_run(self):
        name = "Westvale Abbey // Ormendahl, Profane Prince"
        self.write_deck("one", name)
        card = make_card(name, layout="transform")
        card["card_faces"][0]["image_uris"]["large"] = card["card_faces"][1]["image_uris"]["large"]
        fake = FakeScryfall([card])

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn(name, out)
        self.assert_no_file_written()

    def test_deck_run_asks_for_every_name_in_the_file(self):
        """Rule 7: a --deck run prices the selected deck and every name of the file."""
        self.write_deck("one", "Sol Ring", "Arcane Signet")
        self.write_deck("two", "Counterspell")
        old = {
            name: {"type_line": "Old", "image": "front/o/l/old.jpg?1", "usd": 99.0, "eur": 99.0}
            for name in ("Counterspell", "Old Extra", "Dusk // Dawn", "Dusk")
        }
        self.output.write_text(json.dumps(old))
        fake = FakeScryfall([
            make_card("Sol Ring"), make_card("Arcane Signet"), make_card("Counterspell"),
            make_card("Old Extra"), make_card("Dusk // Dawn", layout="split"),
        ])

        code, _ = self.run_metadata(fake, "--deck", "one")

        self.assertEqual(code, 0)
        self.assertEqual(
            fake.asked_names(),
            ["Arcane Signet", "Counterspell", "Dusk", "Old Extra", "Sol Ring"])
        metadata = json.loads(self.output.read_text())
        self.assertEqual(
            sorted(metadata),
            ["Arcane Signet", "Counterspell", "Dusk", "Dusk // Dawn", "Old Extra", "Sol Ring"])
        for name, entry in metadata.items():
            with self.subTest(card=name):
                self.assertEqual(entry["usd"], 1.5)
                self.assertEqual(entry["eur"], 1.2)
                self.assertEqual(entry["type_line"], "Instant")
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["count"], 6)

    def test_run_that_lacks_a_name_writes_no_file(self):
        """The last guard before the write: every name asked for has an entry."""
        self.write_deck("one", "Sol Ring", "Arcane Signet")
        fake = FakeScryfall([make_card("Sol Ring"), make_card("Arcane Signet")])

        with mock.patch.object(
                fetch_metadata, "fetch_metadata", return_value={"Sol Ring": {"cmc": 1.0}}):
            code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("Arcane Signet", out)
        self.assert_no_file_written()

    def test_meta_file_holds_the_time_of_the_first_request_the_count_and_the_source(self):
        self.write_deck("one", "Sol Ring", "Bonecrusher Giant // Stomp")
        fake = FakeScryfall([
            make_card("Sol Ring"), make_card("Bonecrusher Giant // Stomp", layout="adventure")])

        before = datetime.now(timezone.utc).replace(microsecond=0)
        code, _ = self.run_metadata(fake)
        after = datetime.now(timezone.utc)

        self.assertEqual(code, 0)
        meta = json.loads(self.meta.read_text())
        self.assertEqual(sorted(meta), ["count", "prices_as_of", "source"])
        self.assertEqual(meta["count"], 3)
        self.assertEqual(meta["count"], len(json.loads(self.output.read_text())))
        self.assertEqual(meta["source"], "scryfall-cards-collection")
        self.assertTrue(meta["prices_as_of"].endswith("+00:00"))
        self.assertTrue(before <= datetime.fromisoformat(meta["prices_as_of"]) <= after)


class FetchCardImagesRunTests(DeckDirCase):
    def setUp(self):
        super().setUp()
        self.images = self.root / "images"

    def run_images(self, fake: FakeScryfall) -> tuple[int, str]:
        out = io.StringIO()
        with fake.installed(), \
                mock.patch.object(fetch_images, "COMMANDERS_DIR", self.commanders), \
                mock.patch.object(fetch_images, "IMAGES_DIR", self.images), \
                contextlib.redirect_stdout(out):
            code = fetch_images.main()
        return code, out.getvalue()

    def downloads(self, fake: FakeScryfall) -> list[Sent]:
        return [s for s in fake.sent if s.url.startswith("https://cards.scryfall.io/")]

    def test_batches_start_600ms_after_the_last_answer_and_downloads_keep_75ms(self):
        names = [f"Card {n:03d}" for n in range(160)]
        self.write_deck("big", *names)
        fake = FakeScryfall(make_card(name) for name in names)

        code, _ = self.run_images(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.api_requests()], [COLLECTION_URL] * 3)
        for gap in fake.gaps():
            self.assertAlmostEqual(gap, 0.6, places=9)
        downloads = self.downloads(fake)
        self.assertEqual(len(downloads), 320)
        for earlier, later in zip(downloads, downloads[1:]):
            self.assertAlmostEqual(later.started - earlier.answered, 0.075, places=9)
        self.assertEqual(len(list(self.images.iterdir())), 320)

    def test_429_on_a_batch_ends_the_run_without_retry_or_download(self):
        names = [f"Card {n:03d}" for n in range(160)]
        self.write_deck("big", *names)
        fake = FakeScryfall(make_card(name) for name in names)
        fake.failures[1] = 429

        code, out = self.run_images(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("429", out)
        self.assertIn("wait 30 seconds or more", out)
        self.assertEqual(len(fake.sent), 2)
        # The one wait before batch 2, and no backoff after the 429.
        self.assertAlmostEqual(sum(fake.sleeps), 0.6, places=9)
        self.assertFalse(self.images.exists())

    def test_5xx_on_a_batch_is_retried_through_the_helper(self):
        self.write_deck("one", "Sol Ring")
        fake = FakeScryfall([make_card("Sol Ring")])
        fake.failures[0] = 503

        code, _ = self.run_images(fake)

        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.api_requests()], [COLLECTION_URL] * 2)
        self.assertGreaterEqual(fake.gaps()[0], 0.6)
        self.assertEqual(len(self.downloads(fake)), 2)

    def test_batch_that_keeps_failing_ends_the_run_without_download(self):
        self.write_deck("one", "Sol Ring")
        fake = FakeScryfall([make_card("Sol Ring")])
        fake.failures = {index: 503 for index in range(fetch_images.MAX_RETRIES)}

        code, out = self.run_images(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("503", out)
        self.assertEqual(len(fake.sent), fetch_images.MAX_RETRIES)
        for gap in fake.gaps():
            self.assertGreaterEqual(gap, 0.6)
        self.assertFalse(self.images.exists())

    def test_429_on_a_download_ends_the_run(self):
        self.write_deck("one", "Sol Ring", "Arcane Signet")
        fake = FakeScryfall([make_card("Sol Ring"), make_card("Arcane Signet")])
        fake.failures[2] = 429  # the second download

        code, out = self.run_images(fake)

        self.assertNotEqual(code, 0)
        self.assertIn("429", out)
        self.assertEqual(len(fake.sent), 3)
        self.assertEqual(len(list(self.images.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()

"""DEC-1092 — the publish tool resolves cards through the shared limiter.

Fake stands in for urllib.request.urlopen and for the clocks. Each case has its own
SCRYFALL_LIMIT_DIR (conftest.py) and a new ArchidektClient. No case sends a live request.
"""

import contextlib
import email.message
import io
import json
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from archidekt_mcp.server import mcp
from archidekt_mcp.services.client import ArchidektClient, ScryfallError, ScryfallStopped
from archidekt_mcp.tools import decks

SCRYFALL = "https://api.scryfall.com"
COLLECTION = f"{SCRYFALL}/cards/collection"
# 2026-10-14T10:41:07Z: the time of the 429 in the brief's example.
AT = datetime(2026, 10, 14, 10, 41, 7, tzinfo=timezone.utc).timestamp()
EXAMPLE = ("Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 23 s). "
           "Call again after that time.")
COMMANDER = "Kíli the Resourceful"


def card(name: str) -> dict:
    return {"object": "card", "id": f"id-{name}", "name": name, "type_line": "Artifact"}


def named_url(name: str) -> str:
    return f"{SCRYFALL}/cards/named?exact={urllib.parse.quote(name)}"


class Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Fake:
    """A fake urlopen and a fake clock.

    Scryfall finds a card by its name when the name has no //, or by its front face; it
    answers not_found for a full // name. ``pages`` answers other addresses.
    """

    def __init__(self, *cards):
        self.now = AT + 1000
        self.latency = 0.25
        self.cards = {c["name"].split(" // ")[0]: c for c in cards}
        self.pages = {}
        self.statuses = {}  # request index -> HTTP status
        self.sent = []  # (started, answered, url, method, body, headers, timeout)
        self.sleeps = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def urlopen(self, req, timeout=None):
        index = len(self.sent)
        started = self.now
        self.now += self.latency
        body = json.loads(req.data) if req.data else None
        headers = {key.lower(): value for key, value in req.header_items()}
        self.sent.append((started, self.now, req.full_url, req.get_method(), body, headers, timeout))
        if index in self.statuses:
            raise urllib.error.HTTPError(req.full_url, self.statuses[index], "error",
                                         email.message.Message(), io.BytesIO(b"{}"))
        if req.full_url in self.pages:
            return Response(json.dumps(self.pages[req.full_url]).encode())
        parts = urllib.parse.urlsplit(req.full_url)
        if parts.path == "/cards/collection":
            found = [self.cards[i["name"]] for i in body["identifiers"] if i["name"] in self.cards]
            missing = [i for i in body["identifiers"] if i["name"] not in self.cards]
            return Response(json.dumps({"object": "list", "data": found, "not_found": missing}).encode())
        if parts.path == "/cards/named":
            found = self.cards.get(urllib.parse.parse_qs(parts.query)["exact"][0])
            if found is not None:
                return Response(json.dumps(found).encode())
        raise urllib.error.HTTPError(req.full_url, 404, "error", email.message.Message(),
                                     io.BytesIO(b"{}"))

    @contextlib.contextmanager
    def installed(self):
        with patch("urllib.request.urlopen", self.urlopen), patch("time.time", self.time), \
                patch("time.monotonic", self.time), patch("time.sleep", self.sleep):
            yield self

    def urls(self) -> list[str]:
        return [s[2] for s in self.sent]

    def gaps(self) -> list[float]:
        return [later[0] - earlier[1] for earlier, later in zip(self.sent, self.sent[1:])]


def deck(*names: str) -> dict:
    return {"name": "Test Deck", "commander": COMMANDER,
            "decklist": [{"name": n, "type": "Artifact"} for n in (COMMANDER, *names)]}


@pytest.fixture
def client():
    """A new client (an empty card cache) for each case."""
    fresh = ArchidektClient()
    with patch.object(decks, "_client", fresh):
        yield fresh


@pytest.fixture
def stop(limit_dir):
    """A stop that another process's 429 wrote at 10:41:07Z."""
    limit_dir.mkdir(parents=True, exist_ok=True)
    (limit_dir / "state.json").write_text(json.dumps(
        {"blocked_at": AT, "blocked_until": AT + 30, "last_answer": AT, "last_slow_answer": AT}))


async def publish(deck_data: dict):
    with patch.object(decks, "_load_deck_json", lambda deck_id: deck_data):
        return await decks.publish_deck("test-deck", dry_run=True)


def in_stop() -> Fake:
    fake = Fake()
    fake.now = AT + 7
    return fake


# ------------------------------------------------------------------ the batch


@pytest.mark.asyncio
async def test_slash_name_goes_into_the_batch_as_its_front_face(client):
    """Rule 6: each front face once, in the deck's order; every name finds its card."""
    names = ["Sol Ring", "Bonecrusher Giant // Stomp", "Grave Researcher",
             "Grave Researcher // Reanimate"]
    fake = Fake(card(COMMANDER), card("Sol Ring"), card("Bonecrusher Giant // Stomp"),
                card("Grave Researcher // Reanimate"))
    with fake.installed():
        result = await publish(deck(*names))
    assert result.errors == []
    assert result.card_count == 5
    [(_, _, url, method, body, headers, timeout)] = fake.sent
    assert (url, method, timeout) == (COLLECTION, "POST", 30)
    assert body == {"identifiers": [{"name": n} for n in (
        COMMANDER, "Sol Ring", "Bonecrusher Giant", "Grave Researcher")]}
    assert headers == {"accept": "application/json", "user-agent": "TheGrimoire-MCP/1.0",
                       "content-type": "application/json"}


@pytest.mark.asyncio
async def test_name_that_scryfall_does_not_know_is_still_not_found(client):
    """A 404 on /cards/named stays "not found"; the lookup waits 600 ms after the batch."""
    fake = Fake(card(COMMANDER))
    with fake.installed():
        result = await publish(deck("Gone Card"))
    assert result.errors == ["Could not resolve: Gone Card"]
    assert fake.urls() == [COLLECTION, named_url("Gone Card")]
    assert fake.gaps() == pytest.approx([0.6])
    _, _, _, method, body, headers, timeout = fake.sent[1]
    assert (method, body, timeout) == ("GET", None, 30)
    assert headers == {"accept": "application/json", "user-agent": "TheGrimoire-MCP/1.0"}


@pytest.mark.asyncio
async def test_lookup_of_a_not_found_name_returns_its_card(client):
    fake = Fake(card(COMMANDER))
    fake.pages[named_url("Odd Card")] = card("Odd Card")
    with fake.installed():
        result = await publish(deck("Odd Card"))
    assert result.errors == []
    assert result.card_count == 2


@pytest.mark.asyncio
async def test_5xx_gets_one_retry_under_the_same_waits(client):
    fake = Fake(card(COMMANDER))
    fake.statuses[0] = 503
    with fake.installed():
        result = await publish(deck())
    assert result.errors == []
    assert fake.urls() == [COLLECTION, COLLECTION]
    assert fake.gaps() == pytest.approx([0.6])


@pytest.mark.asyncio
async def test_second_5xx_or_a_4xx_ends_the_resolve(client):
    for statuses, count in (({0: 500, 1: 502}, 2), ({0: 400}, 1)):
        fake = Fake(card(COMMANDER))
        fake.statuses = statuses
        with fake.installed():
            result = await publish(deck())
        last = statuses[count - 1]
        assert result.deck_id == "error"
        assert result.errors == [f"Bulk resolve failed: HTTP {last}: {COLLECTION}"]
        assert fake.urls() == [COLLECTION] * count


# ------------------------------------------------------------------ a 429 and a stop


@pytest.mark.asyncio
async def test_429_on_the_batch_is_the_stop(client, limit_dir):
    fake = Fake(card(COMMANDER))
    fake.now = AT - fake.latency
    fake.statuses[0] = 429
    with fake.installed():
        with pytest.raises(ScryfallStopped) as raised:
            await publish(deck("Sol Ring"))
    assert str(raised.value) == (
        "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 30 s). "
        "Call again after that time.")
    assert fake.urls() == [COLLECTION]
    assert fake.sleeps == []
    assert json.loads((limit_dir / "state.json").read_text())["blocked_until"] == AT + 30


@pytest.mark.asyncio
async def test_not_found_loop_ends_at_the_first_stop(client):
    """Rule 6: no "Not found on Scryfall", and no name goes out after the 429."""
    fake = Fake(card(COMMANDER))
    fake.statuses[1] = 429
    with fake.installed():
        with pytest.raises(ScryfallStopped, match=r"\(in 30 s\)") as raised:
            await publish(deck("Gone A", "Gone B", "Gone C"))
    assert "Not found" not in str(raised.value)
    assert fake.urls() == [COLLECTION, named_url("Gone A")]


@pytest.mark.asyncio
async def test_publish_during_a_stop_fails_at_once(client, stop):
    """Rule 4, the cache empty: the error names the end of the stop; nothing goes out."""
    fake = in_stop()
    with fake.installed():
        with pytest.raises(ScryfallStopped) as raised:
            await publish(deck("Sol Ring"))
    assert str(raised.value) == EXAMPLE
    assert fake.sent == []
    assert fake.sleeps == []


@pytest.mark.asyncio
async def test_publish_with_every_card_in_the_cache_runs_during_a_stop(client, stop):
    """Rule 4, the cache full: the result, and nothing goes out."""
    client._scryfall_cache.update({name: card(name) for name in (COMMANDER, "Sol Ring")})
    fake = in_stop()
    with fake.installed():
        result = await publish(deck("Sol Ring"))
    assert result.errors == []
    assert result.card_count == 2
    assert fake.sent == []


def test_stop_is_a_tool_error_and_not_a_scryfall_error():
    assert issubclass(ScryfallStopped, ToolError)
    assert not issubclass(ScryfallStopped, ScryfallError)


@pytest.mark.asyncio
async def test_agent_reads_the_stop_as_the_tool_error(client, stop):
    """Through the MCP protocol: the tool result is an error whose text is the stop, as is."""
    fake = in_stop()
    with fake.installed(), patch.object(decks, "_load_deck_json", lambda deck_id: deck("Sol Ring")):
        async with Client(mcp) as mcp_client:
            result = await mcp_client.call_tool_mcp(
                "archidekt_publish_deck", {"deck_id": "test-deck", "dry_run": True})
    # MCP SDK 1.x (the live servers) names the field isError; 2.x names it is_error.
    assert result.is_error if hasattr(result, "is_error") else result.isError
    assert [part.text for part in result.content] == [EXAMPLE]
    assert fake.sent == []


@pytest.mark.asyncio
async def test_sync_all_sends_nothing_during_a_stop(client, stop):
    fake = in_stop()
    index = [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}]
    with fake.installed(), patch.object(decks, "_load_index", lambda: index), \
            patch.object(decks, "_load_deck_json", lambda deck_id: deck("Sol Ring")):
        result = await decks.sync_all(dry_run=True)
    assert result.errors == 2
    assert [r.error for r in result.results] == [EXAMPLE, EXAMPLE]
    assert fake.sent == []


# ------------------------------------------------------------------ Archidekt's own wait


def test_archidekt_requests_start_100ms_apart(client):
    fake = Fake()
    fake.latency = 0.02
    fake.pages = {f"https://archidekt.com/api/decks/{n}/": {"id": n} for n in (1, 2)}
    with fake.installed():
        client.get_deck(1)
        client.get_deck(2)
    assert fake.sleeps == pytest.approx([0.08])
    assert fake.sent[1][0] - fake.sent[0][0] == pytest.approx(0.1)

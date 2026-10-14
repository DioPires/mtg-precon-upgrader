"""DEC-1092 — the card tools send through the shared limiter (services/scryfall_limit.py).

Fake stands in for urllib.request.urlopen and for the clocks. Each case has its own
SCRYFALL_LIMIT_DIR (conftest.py) and its own cache file. No case sends a live request.
"""

import contextlib
import email.message
import io
import json
import multiprocessing
import sqlite3
import threading
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client

from scryfall_mcp.models import CardResult, RulingsResult, SearchResults
from scryfall_mcp.server import mcp
from scryfall_mcp.services import client as client_module
from scryfall_mcp.services.cache import Cache
from scryfall_mcp.services.client import ScryfallRateLimitError
from scryfall_mcp.tools import cards, collection, rulings

API = "https://api.scryfall.com"
CARD_ID = "0c082aa8-bf7f-47f2-baf8-43ad253fd7d7"
# 2026-10-14T10:41:07Z: the time of the 429 in the brief's example.
AT = datetime(2026, 10, 14, 10, 41, 7, tzinfo=timezone.utc).timestamp()
EXAMPLE = ("Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 23 s). "
           "Call again after that time.")


def card(name: str) -> dict:
    return {"object": "card", "id": f"id-{name}", "name": name, "type_line": "Artifact",
            "mana_cost": "{1}", "cmc": 1.0, "oracle_text": f"Text of {name}.", "set": "cmm"}


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
    """A fake urlopen for api.scryfall.com and a fake clock.

    ``answers`` maps an address to a JSON object or to an HTTP status. A POST to
    /cards/collection finds each name in ``cards``. Each answer takes LATENCY of fake time.
    """

    LATENCY = 0.25

    def __init__(self, answers=None, cards_by_name=None):
        self.now = AT + 1000
        self.answers = answers or {}
        self.cards = cards_by_name or {}
        self.sent = []  # (started, answered, url, method, body, timeout)
        self.sleeps = []
        self.statuses = {}  # request index -> HTTP status

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def urlopen(self, req, timeout=None):
        index = len(self.sent)
        started = self.now
        self.now += self.LATENCY
        body = json.loads(req.data) if req.data else None
        self.sent.append((started, self.now, req.full_url, req.get_method(), body, timeout))
        answer = self.statuses.get(index, self.answers.get(req.full_url))
        if urllib.parse.urlsplit(req.full_url).path == "/cards/collection" and index not in self.statuses:
            found = [self.cards[i["name"]] for i in body["identifiers"] if i["name"] in self.cards]
            missing = [i for i in body["identifiers"] if i["name"] not in self.cards]
            answer = {"object": "list", "data": found, "not_found": missing}
        if isinstance(answer, int) or answer is None:
            raise urllib.error.HTTPError(req.full_url, answer or 404, "error",
                                         email.message.Message(), io.BytesIO(b"{}"))
        return Response(json.dumps(answer).encode())

    @contextlib.contextmanager
    def installed(self):
        with patch("urllib.request.urlopen", self.urlopen), patch("time.time", self.time), \
                patch("time.monotonic", self.time), patch("time.sleep", self.sleep):
            yield self

    def gaps(self) -> list[float]:
        return [later[0] - earlier[1] for earlier, later in zip(self.sent, self.sent[1:])]


@pytest.fixture
def cache(tmp_path):
    """One empty cache file for the three tool modules."""
    db = Cache(db_path=tmp_path / "cards.db")
    with patch.object(cards, "_cache", db), patch.object(collection, "_cache", db), \
            patch.object(rulings, "_cache", db):
        yield db
    db.close()


@pytest.fixture
def stop(limit_dir):
    """A stop that another process's 429 wrote at 10:41:07Z."""
    limit_dir.mkdir(parents=True, exist_ok=True)
    (limit_dir / "state.json").write_text(json.dumps(
        {"blocked_at": AT, "blocked_until": AT + 30, "last_answer": AT, "last_slow_answer": AT}))


def in_stop() -> Fake:
    fake = Fake()
    fake.now = AT + 7
    return fake


# ------------------------------------------------------------------ one client


def test_one_client_for_the_server_process():
    """Rule 5: the three tool modules send through one client."""
    assert cards._client is client_module.client
    assert collection._client is client_module.client
    assert rulings._client is client_module.client


def test_rate_limit_error_is_a_tool_error():
    from fastmcp.exceptions import ToolError
    assert issubclass(ScryfallRateLimitError, ToolError)


# ------------------------------------------------------------------ waits


@pytest.mark.asyncio
async def test_card_by_name_waits_600ms_and_card_by_id_100ms(cache):
    fake = Fake(answers={
        f"{API}/cards/named?fuzzy=Sol%20Ring": card("Sol Ring"),
        f"{API}/cards/named?fuzzy=Arcane%20Signet": card("Arcane Signet"),
        f"{API}/cards/{CARD_ID}": card("Mind Stone"),
        f"{API}/cards/{CARD_ID}/rulings": {"object": "list", "data": []},
    })
    with fake.installed():
        await cards.card_by_name("Sol Ring")
        await cards.card_by_name("Arcane Signet")
        await cards.card_by_id(CARD_ID)
        await rulings.rulings_lookup(CARD_ID)
    assert fake.gaps() == pytest.approx([0.6, 0.1, 0.1])
    for started, answered, url, method, body, timeout in fake.sent:
        assert (method, body, timeout) == ("GET", None, 30)


@pytest.mark.asyncio
async def test_collection_batch_goes_out_as_a_post(cache):
    fake = Fake(cards_by_name={"Sol Ring": card("Sol Ring")})
    with fake.installed():
        result = await collection.collection_lookup(["Sol Ring", "Gone Card"])
    assert [c.name for c in result.found] == ["Sol Ring"]
    assert result.not_found == ["Gone Card"]
    [(_, _, url, method, body, timeout)] = fake.sent
    assert (url, method, timeout) == (f"{API}/cards/collection", "POST", 30)
    assert body == {"identifiers": [{"name": "Sol Ring"}, {"name": "Gone Card"}]}


# ------------------------------------------------------------------ a 429


@pytest.mark.asyncio
async def test_429_stops_the_call_and_every_later_call(cache, limit_dir):
    fake = Fake()
    fake.now = AT - Fake.LATENCY
    fake.statuses[0] = 429
    with fake.installed():
        with pytest.raises(ScryfallRateLimitError) as raised:
            await cards.card_by_name("Sol Ring")
        assert str(raised.value) == (
            "Scryfall answered HTTP 429 at 10:41:07Z. No request until 10:41:37Z (in 30 s). "
            "Call again after that time.")
        fake.now = AT + 7
        with pytest.raises(ScryfallRateLimitError, match=r"\(in 23 s\)"):
            await cards.card_by_id(CARD_ID)
    assert len(fake.sent) == 1
    assert fake.sleeps == []
    assert json.loads((limit_dir / "state.json").read_text())["blocked_until"] == AT + 30


@pytest.mark.asyncio
async def test_search_returns_no_partial_pages(cache):
    query = urllib.parse.quote("t:artifact")
    page_1 = f"{API}/cards/search?q={query}&order=name&page=1"
    fake = Fake(answers={page_1: {"object": "list", "total_cards": 4, "has_more": True,
                                  "data": [card("A"), card("B")]}})
    fake.statuses[1] = 429
    with fake.installed():
        with pytest.raises(ScryfallRateLimitError, match=r"\(in 30 s\)"):
            await cards.search("t:artifact", max_results=4)
    assert [s[2] for s in fake.sent] == [page_1, f"{API}/cards/search?q={query}&order=name&page=2"]
    assert cache.get(Cache.make_key("cards/search", {"q": "t:artifact", "order": "name", "max": 4})) is None


@pytest.mark.asyncio
async def test_collection_returns_no_partial_result(cache):
    names = [f"Card {n:02d}" for n in range(76)]
    fake = Fake(cards_by_name={name: card(name) for name in names})
    fake.statuses[1] = 429
    with fake.installed():
        with pytest.raises(ScryfallRateLimitError, match=r"\(in 30 s\)"):
            await collection.collection_lookup(names)
    assert [len(s[4]["identifiers"]) for s in fake.sent] == [75, 1]


# ------------------------------------------------------------------ a call during a stop
# Rule 11: each tool of rule 4, with the cache full (the result) and empty (the error).

FULL = {"name": "Sol Ring", "mana_cost": "{1}", "cmc": 1.0, "type_line": "Artifact",
        "oracle_text": "Add {C}{C}.", "colors": [], "color_identity": [], "set_code": "cmm",
        "scryfall_uri": "", "legalities": {}, "keywords": [], "scryfall_id": CARD_ID}


def fill(cache: Cache, tool: str) -> None:
    if tool == "card_by_name":
        cache.set(Cache.make_key("cards/named", {"name": "Sol Ring", "exact": False}), FULL, 60)
    elif tool == "card_by_id":
        cache.set(Cache.make_key(f"cards/{CARD_ID}", ""), FULL, 60)
    elif tool == "search":
        result = SearchResults(total_cards=1, results=[CardResult(**FULL)])
        cache.set(Cache.make_key("cards/search", {"q": "sol", "order": "name", "max": 20}),
                  result.model_dump(), 60)
    elif tool == "collection":
        for name in ("Sol Ring", "Arcane Signet"):
            cache.set(Cache.make_key("cards/named", {"name": name, "exact": True}),
                      {**FULL, "name": name}, 60)
    elif tool == "rulings":
        cache.set(Cache.make_key(f"cards/{CARD_ID}/rulings", ""),
                  RulingsResult(card_name="Sol Ring", rulings=[]).model_dump(), 60)


CALLS = {
    "card_by_name": lambda: cards.card_by_name("Sol Ring"),
    "card_by_id": lambda: cards.card_by_id(CARD_ID),
    "search": lambda: cards.search("sol"),
    "collection": lambda: collection.collection_lookup(["Sol Ring", "Arcane Signet"]),
    "rulings": lambda: rulings.rulings_lookup(CARD_ID, "Sol Ring"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(CALLS))
async def test_call_during_a_stop_with_the_cache_full_returns_the_result(tool, cache, stop):
    fill(cache, tool)
    fake = in_stop()
    with fake.installed():
        result = await CALLS[tool]()
    assert result is not None
    assert fake.sent == []
    assert fake.sleeps == []


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(CALLS))
async def test_call_during_a_stop_with_the_cache_empty_fails_at_once(tool, cache, stop):
    fake = in_stop()
    with fake.installed():
        with pytest.raises(ScryfallRateLimitError) as raised:
            await CALLS[tool]()
    assert str(raised.value) == EXAMPLE
    assert fake.sent == []
    assert fake.sleeps == []


@pytest.mark.asyncio
async def test_collection_with_part_of_the_cache_fails_during_a_stop(cache, stop):
    fill(cache, "collection")
    fake = in_stop()
    with fake.installed():
        with pytest.raises(ScryfallRateLimitError, match=r"\(in 23 s\)"):
            await collection.collection_lookup(["Sol Ring", "Arcane Signet", "Mind Stone"])
    assert fake.sent == []


TOOL_ARGS = {
    "scryfall_card_by_name": {"name": "Sol Ring"},
    "scryfall_card_by_id": {"scryfall_id": CARD_ID},
    "scryfall_search": {"query": "sol"},
    "scryfall_collection": {"card_names": ["Sol Ring"]},
    "scryfall_rulings": {"scryfall_id": CARD_ID},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(TOOL_ARGS))
async def test_agent_reads_the_stop_as_the_tool_error(tool, cache, stop):
    """Through the MCP protocol: the tool result is an error whose text is the stop, as is."""
    fake = in_stop()
    with fake.installed():
        async with Client(mcp) as client:
            result = await client.call_tool_mcp(tool, TOOL_ARGS[tool])
    # MCP SDK 1.x (the live servers) names the field isError; 2.x names it is_error.
    assert result.is_error if hasattr(result, "is_error") else result.isError
    assert [part.text for part in result.content] == [EXAMPLE]
    assert fake.sent == []


# ------------------------------------------------------------------ the shared cache
# Rule 10: every session's server writes one SQLite file.


def test_cache_uses_wal_and_a_busy_timeout(tmp_path):
    db = Cache(db_path=tmp_path / "cards.db")
    try:
        assert db._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30_000
    finally:
        db.close()


def test_cache_opens_while_another_connection_holds_a_write_lock(tmp_path):
    """The switch to WAL answers "database is locked" at once under another writer's lock.

    Two servers that open a new file at once meet it (14 of 30 such opens failed in a trial
    before the fix). The cache opens anyway and waits for the lock in its first write.
    """
    path = tmp_path / "cards.db"
    other = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    other.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)")
    other.execute("BEGIN IMMEDIATE")
    release = threading.Timer(0.3, other.execute, args=("COMMIT",))
    release.start()
    db = Cache(db_path=path)
    try:
        db.set("k", {"v": 1}, ttl=60)
        assert db.get("k") == {"v": 1}
    finally:
        release.join()
        db.close()
        other.close()


def _write_and_read(path, prefix, other, count, start, results):
    start.wait(30)
    db = Cache(db_path=Path(path))
    for n in range(count):
        db.set(f"{prefix}{n}", {"n": n}, ttl=600)
    # Read the other process's keys until all of them are there.
    seen = 0
    for _ in range(2000):
        seen = sum(db.get(f"{other}{n}") == {"n": n} for n in range(count))
        if seen == count:
            break
    db.close()
    results.put((prefix, seen))


def test_two_processes_write_and_read_one_database(tmp_path):
    context = multiprocessing.get_context("spawn")
    path = str(tmp_path / "cards.db")
    start, results = context.Event(), context.Queue()
    processes = [context.Process(target=_write_and_read, args=(path, mine, other, 200, start, results))
                 for mine, other in (("a", "b"), ("b", "a"))]
    for process in processes:
        process.start()
    start.set()
    seen = dict(results.get(timeout=60) for _ in processes)
    for process in processes:
        process.join(60)
        assert process.exitcode == 0
    print(f"\nkeys that each process read from the other: {seen}")
    assert seen == {"a": 200, "b": 200}
    db = Cache(db_path=Path(path))
    try:
        assert all(db.get(f"{p}{n}") == {"n": n} for p in "ab" for n in range(200))
    finally:
        db.close()

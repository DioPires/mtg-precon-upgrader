"""Tests for Scryfall MCP server — mocked HTTP, no live API calls."""

import json
import sqlite3
import tempfile
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from scryfall_mcp.models import CardResult, CollectionResult, RulingsResult, SearchResults
from scryfall_mcp.services.cache import Cache
from scryfall_mcp.services.client import (
    CardNotFoundError,
    ScryfallClient,
    ScryfallMaintenanceError,
    ScryfallRateLimitError,
    ScryfallTimeoutError,
)


# -- Fixtures --

LIGHTNING_BOLT = {
    "id": "f29ba16f-c8fb-42fe-aabf-87089cb214a7",
    "name": "Lightning Bolt",
    "mana_cost": "{R}",
    "cmc": 1.0,
    "type_line": "Instant",
    "oracle_text": "Lightning Bolt deals 3 damage to any target.",
    "colors": ["R"],
    "color_identity": ["R"],
    "set": "2xm",
    "image_uris": {"normal": "https://cards.scryfall.io/normal/front/e/3/bolt.jpg"},
    "scryfall_uri": "https://scryfall.com/card/2xm/117/lightning-bolt",
    "legalities": {"commander": "legal", "standard": "not_legal"},
    "keywords": [],
}

DFC_CARD = {
    "id": "dfc-uuid-123",
    "name": "Delver of Secrets // Insectile Aberration",
    "mana_cost": "{U}",
    "cmc": 1.0,
    "type_line": "Creature — Human Wizard // Creature — Human Insect",
    "colors": ["U"],
    "color_identity": ["U"],
    "set": "mid",
    "image_uris": None,
    "scryfall_uri": "https://scryfall.com/card/mid/47/delver-of-secrets",
    "legalities": {"commander": "legal"},
    "keywords": ["Transform"],
    "card_faces": [
        {
            "name": "Delver of Secrets",
            "oracle_text": "At the beginning of your upkeep, look at the top card of your library. You may reveal that card. If an instant or sorcery card is revealed this way, transform Delver of Secrets.",
            "power": "1",
            "toughness": "1",
        },
        {
            "name": "Insectile Aberration",
            "oracle_text": "Flying",
            "power": "3",
            "toughness": "2",
        },
    ],
}


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def cache(cache_dir):
    db = cache_dir / "test.db"
    c = Cache(db_path=db)
    yield c
    c.close()


# -- Cache Tests --


class TestCache:
    def test_set_and_get(self, cache):
        cache.set("k1", {"foo": "bar"}, ttl=60)
        assert cache.get("k1") == {"foo": "bar"}

    def test_expired_entry_returns_none(self, cache):
        cache.set("k2", "val", ttl=0)
        time.sleep(0.01)
        assert cache.get("k2") is None

    def test_make_key_deterministic(self):
        k1 = Cache.make_key("cards/named", {"name": "Bolt", "exact": True})
        k2 = Cache.make_key("cards/named", {"name": "Bolt", "exact": True})
        assert k1 == k2

    def test_make_key_varies_on_params(self):
        k1 = Cache.make_key("cards/named", {"name": "Bolt", "exact": True})
        k2 = Cache.make_key("cards/named", {"name": "Bolt", "exact": False})
        assert k1 != k2


# -- Client Tests --


def _mock_urlopen(response_data, status=200):
    """Create a mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestClient:
    def test_card_by_name_fuzzy(self):
        client = ScryfallClient()
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(LIGHTNING_BOLT)):
            result = client.card_by_name("Lightning Bolt")
        assert result["name"] == "Lightning Bolt"

    def test_card_by_name_exact(self):
        client = ScryfallClient()
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(LIGHTNING_BOLT)):
            result = client.card_by_name("Lightning Bolt", exact=True)
        assert result["name"] == "Lightning Bolt"

    def test_dfc_name_strips_for_fuzzy(self):
        client = ScryfallClient()
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(DFC_CARD)) as mock_open:
            result = client.card_by_name("Delver of Secrets // Insectile Aberration")
            # Should use front face name only for fuzzy
            call_url = mock_open.call_args[0][0].full_url
            assert "Delver+of+Secrets" in call_url or "Delver%20of%20Secrets" in call_url
            assert "Insectile" not in call_url

    def test_404_raises_card_not_found(self):
        client = ScryfallClient()
        error_body = json.dumps({"details": 'Did you mean "Lightning Bolt"?'}).encode()
        http_error = urllib.error.HTTPError(
            "url", 404, "Not Found", {}, MagicMock(read=MagicMock(return_value=error_body))
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(CardNotFoundError, match="Lightning Bolt"):
                client.card_by_name("Lihgtning Bolt", exact=True)

    def test_429_raises_without_retry(self):
        """DEC-1092: nothing retries a 429; the error names the end of the stop."""
        client = ScryfallClient()
        error_body = json.dumps({}).encode()
        http_error = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, MagicMock(read=MagicMock(return_value=error_body))
        )
        with patch("urllib.request.urlopen", side_effect=http_error) as urlopen:
            with patch("time.sleep") as sleep:
                with pytest.raises(ScryfallRateLimitError, match=r"No request until .* \(in 30 s\)"):
                    client.card_by_name("Sol Ring")
        assert urlopen.call_count == 1
        sleep.assert_not_called()

    def test_503_raises_maintenance(self):
        client = ScryfallClient()
        error_body = json.dumps({"details": "Scryfall is down for maintenance"}).encode()
        http_error = urllib.error.HTTPError(
            "url", 503, "Service Unavailable", {}, MagicMock(read=MagicMock(return_value=error_body))
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with pytest.raises(ScryfallMaintenanceError):
                client.card_by_name("Sol Ring")

    def test_timeout_raises_timeout_error(self):
        client = ScryfallClient()
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(ScryfallTimeoutError):
                client.card_by_name("Sol Ring")


# -- Model Tests --


class TestModels:
    def test_card_result_basic(self):
        card = CardResult(**{
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "cmc": 1.0,
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "colors": ["R"],
            "color_identity": ["R"],
            "set_code": "2xm",
            "scryfall_uri": "https://scryfall.com/card/2xm/117",
            "legalities": {"commander": "legal"},
            "keywords": [],
        })
        assert card.name == "Lightning Bolt"
        assert card.cmc == 1.0

    def test_dfc_oracle_text_merge(self):
        card = CardResult(**{
            "name": "Delver of Secrets // Insectile Aberration",
            "card_faces": [
                {"oracle_text": "Look at top card. Transform."},
                {"oracle_text": "Flying"},
            ],
        })
        assert card.oracle_text == "Look at top card. Transform. // Flying"
        assert card.card_faces is not None
        assert len(card.card_faces) == 2

    def test_no_dfc_keeps_oracle_text(self):
        card = CardResult(**{
            "name": "Lightning Bolt",
            "oracle_text": "Deals 3 damage.",
        })
        assert card.oracle_text == "Deals 3 damage."
        assert card.card_faces is None

    def test_dfc_does_not_override_existing_oracle_text(self):
        card = CardResult(**{
            "name": "Test Card",
            "oracle_text": "Already set.",
            "card_faces": [
                {"oracle_text": "Face 1"},
                {"oracle_text": "Face 2"},
            ],
        })
        assert card.oracle_text == "Already set."


# -- Collection Tests --


class TestCollectionBatching:
    def test_76_cards_makes_2_calls(self):
        """76 cards should produce 2 API calls (75 + 1)."""
        client = ScryfallClient()
        names = [f"Card {i}" for i in range(76)]

        call_count = 0

        def mock_collection(identifiers):
            nonlocal call_count
            call_count += 1
            return {
                "data": [
                    {**LIGHTNING_BOLT, "name": ident["name"]}
                    for ident in identifiers
                ],
                "not_found": [],
            }

        client.collection = mock_collection

        # Manually batch like collection_lookup does
        from scryfall_mcp.config import COLLECTION_BATCH_SIZE
        batches = [names[i:i + COLLECTION_BATCH_SIZE] for i in range(0, len(names), COLLECTION_BATCH_SIZE)]
        for batch in batches:
            client.collection([{"name": n} for n in batch])

        assert call_count == 2
        assert len(batches[0]) == 75
        assert len(batches[1]) == 1


# -- Async Tool Tests --


@pytest.mark.asyncio
class TestAsyncTools:
    async def test_card_by_name_returns_card_result(self):
        from scryfall_mcp.tools import cards

        with patch.object(cards, "_client") as mock_client, \
             patch.object(cards, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.card_by_name.return_value = LIGHTNING_BOLT

            result = await cards.card_by_name("Lightning Bolt")
            assert isinstance(result, CardResult)
            assert result.name == "Lightning Bolt"
            mock_cache.set.assert_called_once()

    async def test_card_by_name_uses_cache(self):
        from scryfall_mcp.tools import cards

        cached_data = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "cmc": 1.0,
            "type_line": "Instant",
            "oracle_text": "Deals 3.",
            "colors": ["R"],
            "color_identity": ["R"],
            "set_code": "2xm",
            "scryfall_uri": "https://scryfall.com/card/2xm/117",
            "legalities": {},
            "keywords": [],
        }

        with patch.object(cards, "_client") as mock_client, \
             patch.object(cards, "_cache") as mock_cache:
            mock_cache.get.return_value = cached_data

            result = await cards.card_by_name("Lightning Bolt")
            assert result.name == "Lightning Bolt"
            mock_client.card_by_name.assert_not_called()

    async def test_search_returns_search_results(self):
        from scryfall_mcp.tools import cards

        search_response = {
            "total_cards": 1,
            "has_more": False,
            "data": [LIGHTNING_BOLT],
        }

        with patch.object(cards, "_client") as mock_client, \
             patch.object(cards, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.search.return_value = search_response

            result = await cards.search("lightning bolt")
            assert isinstance(result, SearchResults)
            assert result.total_cards == 1
            assert result.results[0].name == "Lightning Bolt"

    async def test_collection_partial_results(self):
        from scryfall_mcp.tools import collection

        collection_response = {
            "data": [LIGHTNING_BOLT],
            "not_found": [{"name": "FakeCard"}],
        }

        with patch.object(collection, "_client") as mock_client, \
             patch.object(collection, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.collection.return_value = collection_response

            result = await collection.collection_lookup(["Lightning Bolt", "FakeCard"])
            assert isinstance(result, CollectionResult)
            assert len(result.found) == 1
            assert result.not_found == ["FakeCard"]

    async def test_rulings_returns_rulings_result(self):
        from scryfall_mcp.tools import rulings

        rulings_response = {
            "data": [
                {
                    "source": "wotc",
                    "published_at": "2020-01-01",
                    "comment": "Test ruling.",
                }
            ]
        }

        with patch.object(rulings, "_client") as mock_client, \
             patch.object(rulings, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.rulings.return_value = rulings_response

            result = await rulings.rulings_lookup("some-uuid", "Lightning Bolt")
            assert isinstance(result, RulingsResult)
            assert result.card_name == "Lightning Bolt"
            assert len(result.rulings) == 1
            assert result.rulings[0].comment == "Test ruling."


# -- KEEP_FIELDS Filtering Test --


class TestKeepFieldsFiltering:
    def test_filter_excludes_extra_fields(self):
        from scryfall_mcp.tools.cards import _filter_card

        raw = {
            **LIGHTNING_BOLT,
            "prices": {"usd": "0.50"},
            "artist": "Christopher Rush",
            "collector_number": "117",
            "rarity": "uncommon",
        }
        filtered = _filter_card(raw)
        assert "prices" not in filtered
        assert "artist" not in filtered
        assert "collector_number" not in filtered
        assert "rarity" not in filtered
        assert filtered["name"] == "Lightning Bolt"

    def test_card_faces_preserved(self):
        from scryfall_mcp.tools.cards import _filter_card

        filtered = _filter_card(DFC_CARD)
        assert filtered["card_faces"] is not None
        assert len(filtered["card_faces"]) == 2

    def test_card_faces_absent_when_not_dfc(self):
        from scryfall_mcp.tools.cards import _filter_card

        filtered = _filter_card(LIGHTNING_BOLT)
        assert filtered["card_faces"] is None


# -- MCP Smoke Test --


@pytest.mark.asyncio
class TestMCPSmoke:
    async def test_server_lists_tools(self):
        """Verify all expected tools are registered."""
        from scryfall_mcp.server import mcp

        # FastMCP exposes tool names
        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "scryfall_card_by_name",
            "scryfall_search",
            "scryfall_collection",
            "scryfall_card_by_id",
            "scryfall_rulings",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

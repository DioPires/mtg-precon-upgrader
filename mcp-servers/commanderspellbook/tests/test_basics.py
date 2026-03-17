"""Tests for Commander Spellbook MCP server — mocked HTTP, no live API calls."""

import json
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commanderspellbook_mcp.models import (
    AlmostIncludedResult,
    ComboResult,
    FindCombosResponse,
)
from commanderspellbook_mcp.services.cache import Cache
from commanderspellbook_mcp.services.client import (
    ComboLookupError,
    SpellbookClient,
    SpellbookRateLimitError,
    SpellbookTimeoutError,
)


# -- Fixtures --

SAMPLE_COMBO_RAW = {
    "id": "628-2292--5",
    "status": "OK",
    "identity": "B",
    "bracketTag": "E",
    "description": "Sacrifice a persist creature to Viscera Seer. Undying and persist return it.",
    "manaNeeded": "",
    "easyPrerequisites": "",
    "notablePrerequisites": "",
    "notes": "",
    "uses": [
        {
            "card": {
                "id": 628,
                "name": "Mikaeus, the Unhallowed",
                "oracleId": "abc",
                "typeLine": "Legendary Creature",
            },
            "quantity": 1,
            "zoneLocations": ["B"],
            "battlefieldCardState": "",
            "mustBeCommander": False,
        },
        {
            "card": {
                "id": 2292,
                "name": "Viscera Seer",
                "oracleId": "def",
                "typeLine": "Creature",
            },
            "quantity": 1,
            "zoneLocations": ["B"],
            "battlefieldCardState": "",
            "mustBeCommander": False,
        },
    ],
    "requires": [
        {
            "template": {
                "id": 5,
                "name": "Persist Creature",
                "scryfallQuery": "keyword:persist t:creature",
            },
            "quantity": 1,
            "zoneLocations": ["B"],
        }
    ],
    "produces": [
        {"feature": {"id": 3, "name": "Infinite LTB"}, "quantity": 1},
        {"feature": {"id": 4, "name": "Infinite ETB"}, "quantity": 1},
        {"feature": {"id": 7, "name": "Infinite death triggers"}, "quantity": 1},
    ],
    "prices": {"tcgplayer": "30.50"},
    "legalities": {},
}

SAMPLE_ALMOST_RAW = {
    **SAMPLE_COMBO_RAW,
    "id": "628-2034--5",
    "uses": [
        {
            "card": {"id": 628, "name": "Mikaeus, the Unhallowed"},
            "quantity": 1,
            "zoneLocations": ["B"],
            "battlefieldCardState": "",
            "mustBeCommander": False,
        },
        {
            "card": {"id": 2034, "name": "Ashnod's Altar"},
            "quantity": 1,
            "zoneLocations": ["B"],
            "battlefieldCardState": "",
            "mustBeCommander": False,
        },
    ],
}

SAMPLE_API_RESPONSE = {
    "count": None,
    "next": None,
    "previous": None,
    "results": {
        "identity": "BG",
        "included": [SAMPLE_COMBO_RAW],
        "includedByChangingCommanders": [],
        "almostIncluded": [SAMPLE_ALMOST_RAW],
        "almostIncludedByAddingColors": [],
        "almostIncludedByChangingCommanders": [],
        "almostIncludedByAddingColorsAndChangingCommanders": [],
    },
}

SAMPLE_DECKLIST = [
    "Meren of Clan Nel Toth",
    "Mikaeus, the Unhallowed",
    "Viscera Seer",
    "Blood Artist",
]


@pytest.fixture
def cache(tmp_path):
    db = tmp_path / "test.db"
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
        k1 = Cache.make_key(["Sol Ring", "Lightning Bolt"])
        k2 = Cache.make_key(["Sol Ring", "Lightning Bolt"])
        assert k1 == k2

    def test_make_key_order_insensitive(self):
        k1 = Cache.make_key(["Sol Ring", "Lightning Bolt"])
        k2 = Cache.make_key(["Lightning Bolt", "Sol Ring"])
        assert k1 == k2

    def test_make_key_case_insensitive(self):
        k1 = Cache.make_key(["Sol Ring"])
        k2 = Cache.make_key(["sol ring"])
        assert k1 == k2

    def test_make_key_varies_on_cards(self):
        k1 = Cache.make_key(["Sol Ring"])
        k2 = Cache.make_key(["Lightning Bolt"])
        assert k1 != k2


# -- Client Tests --


def _mock_urlopen(response_data):
    """Create a mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestClient:
    def test_find_my_combos_sends_text_plain(self):
        client = SpellbookClient()
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_API_RESPONSE)) as mock_open:
            client.find_my_combos(["Sol Ring", "Lightning Bolt"])
            req = mock_open.call_args[0][0]
            assert req.get_header("Content-type") == "text/plain"
            assert req.data == b"Sol Ring\nLightning Bolt"

    def test_find_my_combos_returns_dict(self):
        client = SpellbookClient()
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(SAMPLE_API_RESPONSE)):
            result = client.find_my_combos(SAMPLE_DECKLIST)
        assert "results" in result
        assert "included" in result["results"]

    def test_429_retries_then_raises(self):
        client = SpellbookClient()
        error_body = json.dumps({}).encode()
        http_error = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, MagicMock(read=MagicMock(return_value=error_body))
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with patch("time.sleep"):
                with pytest.raises(SpellbookRateLimitError):
                    client.find_my_combos(SAMPLE_DECKLIST)

    def test_500_retries_then_raises(self):
        client = SpellbookClient()
        error_body = json.dumps({}).encode()
        http_error = urllib.error.HTTPError(
            "url", 500, "Internal Server Error", {}, MagicMock(read=MagicMock(return_value=error_body))
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            with patch("time.sleep"):
                with pytest.raises(ComboLookupError, match="Server error 500"):
                    client.find_my_combos(SAMPLE_DECKLIST)

    def test_timeout_raises_timeout_error(self):
        client = SpellbookClient()
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(SpellbookTimeoutError):
                client.find_my_combos(SAMPLE_DECKLIST)


# -- Model Tests --


class TestModels:
    def test_combo_result_basic(self):
        combo = ComboResult(
            id="628-2292--5",
            url="https://commanderspellbook.com/combo/628-2292--5/",
            cards=[],
            produces=["Infinite ETB"],
        )
        assert combo.id == "628-2292--5"
        assert "commanderspellbook.com" in combo.url

    def test_find_combos_response(self):
        resp = FindCombosResponse(
            identity="BG",
            included=[],
            almost_included=[],
        )
        assert resp.identity == "BG"

    def test_almost_included_result(self):
        combo = ComboResult(
            id="test",
            url="https://commanderspellbook.com/combo/test/",
            cards=[],
            produces=[],
        )
        result = AlmostIncludedResult(
            combo=combo,
            missing_cards=["Ashnod's Altar"],
            missing_templates=["Persist Creature"],
        )
        assert result.missing_cards == ["Ashnod's Altar"]


# -- Tool Tests --


@pytest.mark.asyncio
class TestAsyncTools:
    async def test_find_combos_returns_response(self):
        from commanderspellbook_mcp.tools import combos

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.find_my_combos.return_value = SAMPLE_API_RESPONSE

            result = await combos.find_combos(SAMPLE_DECKLIST)
            assert isinstance(result, FindCombosResponse)
            assert result.identity == "BG"
            assert len(result.included) == 1
            assert result.included[0].id == "628-2292--5"
            mock_cache.set.assert_called_once()

    async def test_find_combos_uses_cache(self):
        from commanderspellbook_mcp.tools import combos

        cached_data = FindCombosResponse(
            identity="BG",
            included=[],
            almost_included=[],
        ).model_dump()

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = cached_data

            result = await combos.find_combos(SAMPLE_DECKLIST)
            assert result.identity == "BG"
            mock_client.find_my_combos.assert_not_called()

    async def test_almost_included_computes_missing_cards(self):
        from commanderspellbook_mcp.tools import combos

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.find_my_combos.return_value = SAMPLE_API_RESPONSE

            result = await combos.find_combos(SAMPLE_DECKLIST)
            assert len(result.almost_included) == 1
            almost = result.almost_included[0]
            assert "Ashnod's Altar" in almost.missing_cards
            assert "Mikaeus, the Unhallowed" not in almost.missing_cards
            assert "Persist Creature" in almost.missing_templates

    async def test_included_combo_parses_produces(self):
        from commanderspellbook_mcp.tools import combos

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.find_my_combos.return_value = SAMPLE_API_RESPONSE

            result = await combos.find_combos(SAMPLE_DECKLIST)
            combo = result.included[0]
            assert "Infinite LTB" in combo.produces
            assert "Infinite ETB" in combo.produces
            assert "Infinite death triggers" in combo.produces

    async def test_included_combo_parses_cards(self):
        from commanderspellbook_mcp.tools import combos

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.find_my_combos.return_value = SAMPLE_API_RESPONSE

            result = await combos.find_combos(SAMPLE_DECKLIST)
            combo = result.included[0]
            card_names = [c.name for c in combo.cards]
            assert "Mikaeus, the Unhallowed" in card_names
            assert "Viscera Seer" in card_names

    async def test_combo_url_computed(self):
        from commanderspellbook_mcp.tools import combos

        with patch.object(combos, "_client") as mock_client, \
             patch.object(combos, "_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_client.find_my_combos.return_value = SAMPLE_API_RESPONSE

            result = await combos.find_combos(SAMPLE_DECKLIST)
            assert result.included[0].url == "https://commanderspellbook.com/combo/628-2292--5/"


# -- MCP Smoke Test --


@pytest.mark.asyncio
class TestMCPSmoke:
    async def test_server_lists_tools(self):
        """Verify the expected tool is registered."""
        from commanderspellbook_mcp.server import mcp

        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        assert "commanderspellbook_find_combos" in tool_names

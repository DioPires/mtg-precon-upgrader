"""Synchronous Scryfall HTTP client. Every request goes through the shared limiter."""

import json
import urllib.parse
import urllib.request

from fastmcp.exceptions import ToolError

from ..config import BASE_URL, USER_AGENT
from . import scryfall_limit


class CardNotFoundError(Exception):
    """Card not found (404). Message includes Scryfall's suggestion if available."""


class ScryfallRateLimitError(ToolError):
    """Scryfall answered 429, to this call or to another caller on this Mac (DEC-1092).

    A ToolError, so the agent reads the message as it stands: the time of the 429 and the
    end of the stop.
    """


class ScryfallMaintenanceError(Exception):
    """Scryfall is down for maintenance (503)."""


class ScryfallTimeoutError(Exception):
    """Network timeout connecting to Scryfall."""


class ScryfallClient:
    """Sync HTTP client for Scryfall API. It keeps no clock: scryfall_limit holds the waits."""

    def _request(self, url: str, data: bytes | None = None, method: str = "GET") -> dict:
        """Make an HTTP request through the shared limiter. Nothing retries a 429."""
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if data is not None:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        def transmit() -> dict:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())

        try:
            return scryfall_limit.send(url, transmit)
        except scryfall_limit.Stopped as e:
            raise ScryfallRateLimitError(str(e)) from e
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.loads(e.read())
            except Exception:
                pass

            if e.code == 404:
                details = body.get("details", "")
                raise CardNotFoundError(details or f"Not found: {url}") from e
            elif e.code == 503:
                raise ScryfallMaintenanceError(body.get("details", "Scryfall maintenance")) from e
            else:
                raise
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                raise ScryfallTimeoutError(f"Timeout: {url}") from e
            raise
        except TimeoutError as e:
            raise ScryfallTimeoutError(f"Timeout: {url}") from e

    def card_by_name(self, name: str, exact: bool = False) -> dict:
        """Fetch a card by name.

        For DFC names containing ' // ', strips to front face for fuzzy lookup.
        """
        lookup_name = name
        if not exact and " // " in name:
            lookup_name = name.split(" // ")[0]

        param = "exact" if exact else "fuzzy"
        encoded = urllib.parse.quote(lookup_name)
        url = f"{BASE_URL}/cards/named?{param}={encoded}"
        return self._request(url)

    def search(self, query: str, order: str = "name", page: int = 1) -> dict:
        """Search cards via Scryfall search syntax."""
        encoded = urllib.parse.quote(query)
        url = f"{BASE_URL}/cards/search?q={encoded}&order={order}&page={page}"
        return self._request(url)

    def card_by_id(self, scryfall_id: str) -> dict:
        """Fetch a card by Scryfall UUID."""
        url = f"{BASE_URL}/cards/{scryfall_id}"
        return self._request(url)

    def collection(self, identifiers: list[dict]) -> dict:
        """Bulk lookup via POST /cards/collection. Max 75 per call."""
        url = f"{BASE_URL}/cards/collection"
        body = json.dumps({"identifiers": identifiers}).encode()
        return self._request(url, data=body, method="POST")

    def rulings(self, scryfall_id: str) -> dict:
        """Fetch rulings for a card by Scryfall UUID."""
        url = f"{BASE_URL}/cards/{scryfall_id}/rulings"
        return self._request(url)


# One client for each server process (DEC-1092): every tool module sends through it.
client = ScryfallClient()

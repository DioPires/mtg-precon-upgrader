"""Synchronous Scryfall HTTP client with rate limiting and retry."""

import json
import time
import urllib.parse
import urllib.request
from http.client import HTTPResponse
from typing import Any

from ..config import BASE_URL, COLLECTION_BATCH_SIZE, RATE_LIMIT_MS, USER_AGENT


class CardNotFoundError(Exception):
    """Card not found (404). Message includes Scryfall's suggestion if available."""


class ScryfallRateLimitError(Exception):
    """Rate limit exceeded after retry exhaustion (429)."""


class ScryfallMaintenanceError(Exception):
    """Scryfall is down for maintenance (503)."""


class ScryfallTimeoutError(Exception):
    """Network timeout connecting to Scryfall."""


class ScryfallClient:
    """Sync HTTP client for Scryfall API."""

    def __init__(self):
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        now = time.monotonic()
        elapsed_ms = (now - self._last_request_time) * 1000
        if elapsed_ms < RATE_LIMIT_MS:
            time.sleep((RATE_LIMIT_MS - elapsed_ms) / 1000)
        self._last_request_time = time.monotonic()

    def _request(self, url: str, data: bytes | None = None, method: str = "GET") -> dict:
        """Make an HTTP request with rate limiting and retry on 429."""
        self._rate_limit()

        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if data is not None:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        backoff_delays = [1, 2, 4]
        last_error: Exception | None = None

        for attempt in range(1 + len(backoff_delays)):
            try:
                resp: HTTPResponse = urllib.request.urlopen(req, timeout=30)
                return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                body = {}
                try:
                    body = json.loads(e.read())
                except Exception:
                    pass

                if e.code == 404:
                    details = body.get("details", "")
                    raise CardNotFoundError(details or f"Not found: {url}") from e
                elif e.code == 429:
                    if attempt < len(backoff_delays):
                        time.sleep(backoff_delays[attempt])
                        self._rate_limit()
                        continue
                    raise ScryfallRateLimitError("Rate limit exceeded after retries") from e
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

        raise last_error or ScryfallRateLimitError("Exhausted retries")

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

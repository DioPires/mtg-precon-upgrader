"""Synchronous Commander Spellbook HTTP client with rate limiting and retry."""

import json
import time
import urllib.request
from http.client import HTTPResponse

from ..config import BASE_URL, RATE_LIMIT_MS, USER_AGENT


class ComboLookupError(Exception):
    """General error from Commander Spellbook API."""


class SpellbookRateLimitError(Exception):
    """Rate limit exceeded after retry exhaustion (429)."""


class SpellbookTimeoutError(Exception):
    """Network timeout connecting to Commander Spellbook."""


class SpellbookClient:
    """Sync HTTP client for Commander Spellbook API."""

    def __init__(self):
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        now = time.monotonic()
        elapsed_ms = (now - self._last_request_time) * 1000
        if elapsed_ms < RATE_LIMIT_MS:
            time.sleep((RATE_LIMIT_MS - elapsed_ms) / 1000)
        self._last_request_time = time.monotonic()

    def find_my_combos(self, decklist: list[str]) -> dict:
        """POST decklist to find-my-combos endpoint.

        Args:
            decklist: List of card names (one per entry).

        Returns:
            Raw JSON response dict with results.included and results.almostIncluded.
        """
        body = "\n".join(decklist).encode("utf-8")
        url = f"{BASE_URL}/find-my-combos"

        headers = {
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        backoff_delays = [1, 2, 4]

        for attempt in range(1 + len(backoff_delays)):
            self._rate_limit()
            try:
                resp: HTTPResponse = urllib.request.urlopen(req, timeout=30)
                return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt < len(backoff_delays):
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise SpellbookRateLimitError(
                        "Rate limit exceeded after retries"
                    ) from e
                elif e.code >= 500:
                    if attempt < len(backoff_delays):
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise ComboLookupError(
                        f"Server error {e.code} after retries"
                    ) from e
                else:
                    raise ComboLookupError(f"HTTP {e.code}: {url}") from e
            except urllib.error.URLError as e:
                if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                    raise SpellbookTimeoutError(f"Timeout: {url}") from e
                raise
            except TimeoutError as e:
                raise SpellbookTimeoutError(f"Timeout: {url}") from e

        raise SpellbookRateLimitError("Exhausted retries")

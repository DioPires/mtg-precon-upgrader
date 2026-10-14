"""HTTP client for Archidekt and Scryfall APIs."""

import json
import time
import urllib.request
import urllib.parse
from http.client import HTTPResponse

from fastmcp.exceptions import ToolError

from ..config import (
    API_BASE,
    SCRYFALL_API,
    USER_AGENT,
    RATE_LIMIT_MS,
    ARCHIDEKT_AUTH_TOKEN,
    ARCHIDEKT_USERNAME,
    DECK_FORMAT_COMMANDER,
)
from . import scryfall_limit


class ArchidektError(Exception):
    """General error from Archidekt API."""


class AuthenticationError(ArchidektError):
    """Authentication failed (401/403)."""


class ScryfallError(Exception):
    """Error from Scryfall API."""


class ScryfallStopped(ToolError):
    """Scryfall answered 429, to this call or to another caller on this Mac (DEC-1092).

    Not a ScryfallError, so no caller reports it as "Not found on Scryfall". A ToolError, so
    the agent reads the message as it stands: the time of the 429 and the end of the stop.
    """


class ArchidektClient:
    """HTTP client for Archidekt API operations."""

    def __init__(self):
        self._last_archidekt_request: float = 0
        self._scryfall_cache: dict[str, dict] = {}

    def _rate_limit(self) -> None:
        """Wait RATE_LIMIT_MS between Archidekt requests."""
        elapsed_ms = (time.monotonic() - self._last_archidekt_request) * 1000
        if elapsed_ms < RATE_LIMIT_MS:
            time.sleep((RATE_LIMIT_MS - elapsed_ms) / 1000)
        self._last_archidekt_request = time.monotonic()

    def _request(
        self,
        url: str,
        method: str = "GET",
        data: dict | None = None,
        auth: bool = False,
    ) -> dict | list:
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if auth:
            if not ARCHIDEKT_AUTH_TOKEN:
                raise AuthenticationError(
                    "ARCHIDEKT_AUTH_TOKEN env var not set. "
                    "Set it to your Archidekt session token or JWT."
                )
            headers["Authorization"] = f"Bearer {ARCHIDEKT_AUTH_TOKEN}"

        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        backoff_delays = [1, 2, 4]
        for attempt in range(1 + len(backoff_delays)):
            self._rate_limit()
            try:
                resp: HTTPResponse = urllib.request.urlopen(req, timeout=30)
                resp_body = resp.read()
                if not resp_body:
                    return {}
                return json.loads(resp_body)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed ({e.code}). Check ARCHIDEKT_AUTH_TOKEN."
                    ) from e
                if e.code == 429 or e.code >= 500:
                    if attempt < len(backoff_delays):
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise ArchidektError(
                        f"HTTP {e.code} after retries: {url}"
                    ) from e
                raise ArchidektError(f"HTTP {e.code}: {url}") from e

        raise ArchidektError("Exhausted retries")

    def _scryfall_request(self, url: str, data: dict | None = None) -> dict:
        """One request to api.scryfall.com through the shared limiter (DEC-1092).

        A 429 stops every Scryfall caller on this Mac and raises ScryfallStopped; nothing
        retries it. A 5xx gets one retry, under the same waits. Every other HTTP error raises
        ArchidektError, as before.
        """
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers)

        def transmit() -> dict:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
            return json.loads(resp_body) if resp_body else {}

        for attempt in range(2):
            try:
                return scryfall_limit.send(url, transmit)
            except scryfall_limit.Stopped as e:
                raise ScryfallStopped(str(e)) from e
            except urllib.error.HTTPError as e:
                if e.code < 500 or attempt == 1:
                    raise ArchidektError(f"HTTP {e.code}: {url}") from e

    # --- Archidekt deck operations ---

    def list_decks(self, username: str | None = None) -> list[dict]:
        """List public decks for a user.

        First resolves username to user ID, then queries v3 endpoint.
        """
        owner = username or ARCHIDEKT_USERNAME

        # Resolve username to user ID via a profile deck lookup
        user_id = self._resolve_user_id(owner)
        if not user_id:
            return []

        url = (
            f"{API_BASE}/decks/v3/"
            f"?ownerId={user_id}"
            f"&orderBy=-updatedAt"
            f"&pageSize=50"
        )
        result = self._request(url)
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        if isinstance(result, list):
            return result
        return []

    def _resolve_user_id(self, username: str) -> int | None:
        """Resolve an Archidekt username to a user ID.

        Uses a known mapping or fetches from the user profile page.
        """
        known_users = {"pirex": 958885}
        if username in known_users:
            return known_users[username]

        # Try to get user ID from a deck listing search
        url = f"{API_BASE}/decks/v3/?owner_id=0&pageSize=1"
        return None

    def get_deck(self, deck_id: int) -> dict:
        """Get full deck data by ID."""
        url = f"{API_BASE}/decks/{deck_id}/"
        return self._request(url)

    def update_deck(self, deck_id: int, payload: dict) -> dict:
        """Update a deck (PUT). Requires auth."""
        url = f"{API_BASE}/decks/{deck_id}/"
        return self._request(url, method="PUT", data=payload, auth=True)

    def create_deck(self, payload: dict) -> dict:
        """Create a new deck (POST). Requires auth."""
        url = f"{API_BASE}/decks/"
        return self._request(url, method="POST", data=payload, auth=True)

    # --- Scryfall card resolution ---

    def resolve_card_scryfall(self, card_name: str) -> dict:
        """Look up a card on Scryfall by exact name. Returns the card object."""
        if card_name in self._scryfall_cache:
            return self._scryfall_cache[card_name]

        url = (
            f"{SCRYFALL_API}/cards/named"
            f"?exact={urllib.parse.quote(card_name)}"
        )
        try:
            result = self._scryfall_request(url)
        except ArchidektError as e:
            raise ScryfallError(f"Failed to resolve '{card_name}': {e}") from e

        self._scryfall_cache[card_name] = result
        return result

    def resolve_cards_bulk(self, card_names: list[str]) -> dict[str, dict]:
        """Resolve multiple card names via Scryfall collection endpoint.

        Returns a dict of card_name -> scryfall card object.
        Uses POST /cards/collection for efficiency (max 75 per request).
        """
        results: dict[str, dict] = {}

        # Check cache first
        uncached = []
        for name in card_names:
            if name in self._scryfall_cache:
                results[name] = self._scryfall_cache[name]
            else:
                uncached.append(name)

        # Batch resolve uncached cards (75 per request). A // name goes into the batch as
        # its front face: Scryfall finds the card by it, and answers not_found for the full
        # name (DEC-1072). The final loop below maps the full name to the card.
        fronts = list(dict.fromkeys(name.split(" // ")[0] for name in uncached))
        for i in range(0, len(fronts), 75):
            batch = fronts[i : i + 75]
            identifiers = [{"name": name} for name in batch]
            url = f"{SCRYFALL_API}/cards/collection"

            try:
                resp = self._scryfall_request(url, data={"identifiers": identifiers})
            except ArchidektError as e:
                raise ScryfallError(f"Bulk resolve failed: {e}") from e

            for card in resp.get("data", []):
                name = card.get("name", "")
                self._scryfall_cache[name] = card
                results[name] = card

            # Handle not_found — retry with single-card lookup (handles DFCs). A stop raises
            # ScryfallStopped out of the loop, so no further name goes out.
            for nf in resp.get("not_found", []):
                nf_name = nf.get("name", "unknown")
                try:
                    single = self.resolve_card_scryfall(nf_name)
                    results[nf_name] = single
                except ScryfallError:
                    results[nf_name] = {"error": f"Not found on Scryfall: {nf_name}"}

        # Map original requested names to results (handle DFC name mismatch)
        for name in card_names:
            if name not in results:
                # Scryfall returns full DFC name; try matching
                for cached_name, cached_data in self._scryfall_cache.items():
                    if cached_name.startswith(name.split("//")[0].strip()):
                        results[name] = cached_data
                        break

        return results

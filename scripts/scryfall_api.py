#!/usr/bin/env python3
"""The one door to api.scryfall.com for the fetch scripts (DEC-1075).

Scryfall allows 2 requests a second on /cards/collection, /cards/named,
/cards/search and /cards/random. An HTTP 429 limits the caller for 30 seconds,
and a caller that keeps overloading the API can be banned. So:

- a request starts 600 ms (scryfall_limit.SLOW_INTERVAL) or more after the
  last answer arrived;
- a 429 raises ScryfallRateLimited, and from then on this process sends no
  further request: every later call raises again without sending;
- a 3xx raises urllib.error.HTTPError: the helper follows no redirect, so
  every request goes to API_HOST and waits the 600 ms (DEC-1076).

Every request goes through scryfall_limit.send(), the limiter that the card
tools and the Archidekt server share (DEC-1092). So the waits hold across every
process on this Mac, and a 429 that any of them gets stops all of them: during
that stop the helper raises ScryfallRateLimited and sends nothing.

A caller ends its run on ScryfallRateLimited. Nothing retries a 429.
"""

import json
import urllib.parse
import urllib.request

import scryfall_limit

API_HOST = "api.scryfall.com"
COLLECTION_URL = f"https://{API_HOST}/cards/collection"
TIMEOUT = 30  # seconds
USER_AGENT = "MTGPreconUpgrader/1.0"

_rate_limited = False


def _build_opener() -> urllib.request.OpenerDirector:
    """build_opener()'s handlers for https, without HTTPRedirectHandler.

    ProxyHandler registers only when the environment names a proxy.
    """
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler, urllib.request.HTTPSHandler,
                    urllib.request.HTTPDefaultErrorHandler, urllib.request.HTTPErrorProcessor):
        opener.add_handler(handler())
    return opener


_OPENER = _build_opener()


class ScryfallRateLimited(Exception):
    """Scryfall answered HTTP 429. The run must end."""

    def __init__(self) -> None:
        super().__init__(
            "Scryfall answered HTTP 429 (too many requests): "
            "wait 30 seconds or more before the next run."
        )


def request(url: str, body: dict | None = None) -> bytes:
    """Send one request to api.scryfall.com and return the answer's body.

    A GET when ``body`` is None, else a JSON POST. A 429, or a stop that another
    process's 429 started, raises ScryfallRateLimited. Every other failure
    (urllib.error.URLError and its subclasses, a 3xx among them, a timeout)
    passes through to the caller.
    """
    global _rate_limited

    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname != API_HOST:
        raise ValueError(f"Not an https://{API_HOST} address: {url}")
    if _rate_limited:
        raise ScryfallRateLimited()

    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)

    def transmit() -> bytes:
        with _OPENER.open(req, timeout=TIMEOUT) as resp:
            return resp.read()

    try:
        # slow=True: every request of the helper waits 600 ms, as the
        # 2-a-second class does, also /sets and /cards/:id (DEC-1075).
        return scryfall_limit.send(url, transmit, slow=True)
    except scryfall_limit.Stopped as e:
        _rate_limited = True
        raise ScryfallRateLimited() from e

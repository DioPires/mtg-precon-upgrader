#!/usr/bin/env python3
"""The one door to api.scryfall.com for the fetch scripts (DEC-1075).

Scryfall allows 2 requests a second on /cards/collection, /cards/named,
/cards/search and /cards/random. An HTTP 429 limits the caller for 30 seconds,
and a caller that keeps overloading the API can be banned. So:

- a request starts MIN_INTERVAL or more after the last answer arrived;
- a 429 raises ScryfallRateLimited, and from then on this process sends no
  further request: every later call raises again without sending;
- a 3xx raises urllib.error.HTTPError: the helper follows no redirect, so
  every request goes to API_HOST and waits MIN_INTERVAL (DEC-1076).

A caller ends its run on ScryfallRateLimited. Nothing retries a 429.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.scryfall.com"
COLLECTION_URL = f"https://{API_HOST}/cards/collection"
MIN_INTERVAL = 0.6  # 600ms from one answer to the start of the next request
TIMEOUT = 30  # seconds
USER_AGENT = "MTGPreconUpgrader/1.0"

_last_answer_at: float | None = None  # time.monotonic() of the last answer or failure
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

    A GET when ``body`` is None, else a JSON POST. A 429 raises
    ScryfallRateLimited. Every other failure (urllib.error.URLError and its
    subclasses, a 3xx among them, a timeout) passes through to the caller.
    """
    global _last_answer_at, _rate_limited

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

    if _last_answer_at is not None:
        # The clock decides, not the sleep: loop until the interval has passed.
        while (wait := _last_answer_at + MIN_INTERVAL - time.monotonic()) > 0:
            time.sleep(wait)

    try:
        with _OPENER.open(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            _rate_limited = True
            raise ScryfallRateLimited() from e
        raise
    finally:
        _last_answer_at = time.monotonic()

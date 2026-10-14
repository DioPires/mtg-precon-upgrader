"""One limiter for evary Scryfall caller on this Mac (DEC-1092).

The same file sits in three places, and tests/test_scryfall_limit.py compares their SHA-256:

- scripts/scryfall_limit.py: the fetch scripts, through scripts/scryfall_api.py;
- mcp-servers/scryfall/src/scryfall_mcp/services/scryfall_limit.py: the card tools;
- mcp-servers/archidekt/src/archidekt_mcp/services/scryfall_limit.py: the publish tool.

Scryfall allows 2 requests a second on /cards/named, /cards/search, /cards/random and
/cards/collection, and 10 a second on every other method. A 429 limits the caller for 30
seconds, and a ban can follow. Every request to api.scryfall.com from this Mac goes through
send(), which keeps these rules across processes:

1. send() takes an exclusive flock on <dir>/state.lock, reads <dir>/state.json, waits, sends,
   writes the times and releases the lock. <dir> is SCRYFALL_LIMIT_DIR, default
   /tmp/scryfall-limit. The times are wall-clock times (time.time()). A missing or
   unreadable state.json counts as empty. The new state goes to a temporary file in <dir>
   and moves into place with os.replace, so a process that dies in the middle of a write
   cannot drop a stop.
2. A request of the 2-a-second class starts SLOW_INTERVAL or more after the last answer of
   that class, and every request starts ANY_INTERVAL or more after the last answer of any
   request. A failed request counts as an answer.
3. A 429 starts a stop: blocked_until is the answer's time plus STOP, or plus Retry-After
   when that is longer. Until then send() raises Stopped at once: it sends nothing and does
   not sleep. Nothing here retries.
4. A clock that steps back (an NTP correction) costs nothing (DEC-1093 N6): a wait never
   exceeds its class interval, and the time left in a stop never exceeds the stop's length.
"""

import contextlib
import email.utils
import fcntl
import json
import math
import os
import tempfile
import time
import urllib.error
import urllib.parse

DEFAULT_DIR = "/tmp/scryfall-limit"
SLOW_PATHS = frozenset({"/cards/named", "/cards/search", "/cards/random", "/cards/collection"})
SLOW_INTERVAL = 0.6  # seconds from the last answer of the 2-a-second class
ANY_INTERVAL = 0.1  # seconds from the last answer of any request
STOP = 30.0  # seconds of a stop when Retry-After asks for less
KEYS = ("last_answer", "last_slow_answer", "blocked_at", "blocked_until")


class Stopped(Exception):
    """Scryfall answered HTTP 429: no process on this Mac sends until ``until``."""

    def __init__(self, answered_at: float, until: float, now: float) -> None:
        self.answered_at = answered_at
        self.until = until
        # Whole seconds, rounded up, so a call at the time named never meets the stop.
        # round() first: (t + 30.0) - t can come out a hair above 30.0.
        left = math.ceil(round(until - now, 3))
        super().__init__(
            f"Scryfall answered HTTP 429 at {_clock_text(answered_at)}. "
            f"No request until {_clock_text(math.ceil(until))} (in {left} s). "
            "Call again after that time."
        )


def _clock_text(moment: float) -> str:
    return time.strftime("%H:%M:%SZ", time.gmtime(moment))


def limit_dir() -> str:
    """The folder of the shared lock and state."""
    return os.environ.get("SCRYFALL_LIMIT_DIR") or DEFAULT_DIR


def is_slow(url: str) -> bool:
    """True for a method of the 2-a-second class."""
    return urllib.parse.urlsplit(url).path in SLOW_PATHS


def send(url: str, transmit, slow: bool | None = None):
    """Send one request under the shared rules and return what ``transmit()`` returns.

    ``transmit`` sends the request and reads the whole answer. ``slow`` puts the request in
    the 2-a-second class; None reads the class from ``url``. Raises Stopped during a stop
    and on a 429. Every other failure of ``transmit`` passes through.
    """
    if slow is None:
        slow = is_slow(url)
    directory = limit_dir()
    os.makedirs(directory, exist_ok=True)
    # Closing the file releases the lock, also when the process dies.
    with open(os.path.join(directory, "state.lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _read_state(directory)
        now = time.time()
        until = state.get("blocked_until", -math.inf)
        if now < until:
            at = state.get("blocked_at", now)
            if now < at:
                # The clock stepped back: the stop ends one stop length from now.
                at, until = now, now + (until - at)
                state["blocked_at"], state["blocked_until"] = at, until
                _write_state(directory, state)
            raise Stopped(at, until, now)

        wait = _wait(state, "last_answer", ANY_INTERVAL, now)
        if slow:
            wait = max(wait, _wait(state, "last_slow_answer", SLOW_INTERVAL, now))
        # The clock decides, not the sleep: loop until the wait has passed.
        deadline = time.monotonic() + wait
        while (left := deadline - time.monotonic()) > 0:
            time.sleep(left)

        try:
            answer = transmit()
        except BaseException as error:
            # A failed request counts as an answer too.
            _answered(directory, state, slow, error)
            raise
        _answered(directory, state, slow, None)
        return answer


def _wait(state: dict, key: str, interval: float, now: float) -> float:
    """Seconds until ``interval`` has passed since the answer at ``state[key]``.

    Never more than ``interval``, so a clock that stepped back adds nothing.
    """
    if key not in state:
        return 0.0
    return min(interval, state[key] + interval - now)


def _answered(directory: str, state: dict, slow: bool, error: BaseException | None) -> None:
    """Write the time of an answer; on a 429 also write the stop and raise Stopped."""
    answered = time.time()
    state["last_answer"] = answered
    if slow:
        state["last_slow_answer"] = answered
    if isinstance(error, urllib.error.HTTPError) and error.code == 429:
        state["blocked_at"] = answered
        state["blocked_until"] = answered + max(STOP, _retry_after(error, answered))
        _write_state(directory, state)
        raise Stopped(answered, state["blocked_until"], answered) from error
    _write_state(directory, state)


def _retry_after(error: urllib.error.HTTPError, answered: float) -> float:
    """Seconds that the answer's Retry-After asks for (delay-seconds or an HTTP-date), else 0."""
    value = (error.headers or {}).get("Retry-After")
    if value is None:
        return 0.0
    with contextlib.suppress(ValueError):
        return float(int(value))
    with contextlib.suppress(TypeError, ValueError):
        return email.utils.parsedate_to_datetime(value).timestamp() - answered
    return 0.0


def _read_state(directory: str) -> dict:
    """The times of state.json; {} when the file is missing or unreadable."""
    try:
        with open(os.path.join(directory, "state.json"), encoding="utf-8") as handle:
            state = json.load(handle)
        return {key: float(state[key]) for key in KEYS if key in state}
    except (OSError, ValueError, TypeError):
        return {}


def _write_state(directory: str, state: dict) -> None:
    """Write state.json through a temporary file, so a reader never sees half a file."""
    fd, temporary = tempfile.mkstemp(dir=directory, prefix="state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        os.replace(temporary, os.path.join(directory, "state.json"))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise

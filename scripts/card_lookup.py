#!/usr/bin/env python3
"""Look up cards in an agent run: the oracle mirror first, then Scryfall (DEC-1124).

An agent run has no card tools: Paperclip starts it with --strict-mcp-config and only
the Paperclip servers. This script is its way to read a card. A session that has the
card tools uses them. Nobody sends curl, or any request outside scripts/scryfall_api.py,
to api.scryfall.com.

Usage:
    uv run python scripts/card_lookup.py NAME [NAME ...]
    uv run python scripts/card_lookup.py --api NAME [NAME ...]
    uv run python scripts/card_lookup.py --search QUERY

From eternities-mtg-app, call the script by its absolute path.

1. For each name the script prints one JSON object on one line: name, mana_cost, cmc,
   type_line, oracle_text, power, toughness, loyalty, defense, color_identity,
   legalities.commander, card_faces and source. A field that the card lacks is null.
   source is "mirror <scryfall_updated_at>" or "api".
2. The mirror (priv_data/scryfall-oracle.json, written by
   scripts/refresh_scryfall_mirror.py) comes first, and a lookup there sends no request.
   A name matches without regard to case or accents ("lorien revealed" finds
   "Lórien Revealed"), and a front-face name finds its "A // B" card. The mirror holds
   the commander-legal cards only, so a banned card goes to Scryfall.
3. git ignores priv_data/, so a worktree has no mirror. The script then reads the main
   worktree's copy (the parent of ``git rev-parse --git-common-dir``). With neither, it
   prints one warning on stderr and sends every name to Scryfall.
4. A name that the mirror lacks goes out as one /cards/named?exact= request through
   scripts/scryfall_api.py, so it waits the shared limiter's 600 ms. An "A // B" name
   goes out as its front face, and it is found only when the card has that full name.
   A 404 prints "not found: NAME", and the run goes on with the next name.
5. A 429, or a stop that another process's 429 started, ends the run at once with the
   helper's text. No later request goes out. Any other failed request ends the run too.
6. --api skips the mirror: use it for a card newer than the mirror, or for oracle text
   that changed after the mirror's date. --search QUERY sends one /cards/search request
   and prints the first page only: total_cards, then "name | mana_cost | type_line".

Exit codes: 0 when every name was found, 2 when a name was not found (or a search found
no card, or the arguments are wrong), 1 on a 429 or another failed request.
"""

import argparse
import contextlib
import json
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIRROR = Path("priv_data") / "scryfall-oracle.json"
MIRROR_META_NAME = "scryfall-oracle.meta.json"
NAMED_URL = f"https://{scryfall_api.API_HOST}/cards/named"
SEARCH_URL = f"https://{scryfall_api.API_HOST}/cards/search"
FIELDS = ("name", "mana_cost", "cmc", "type_line", "oracle_text",
          "power", "toughness", "loyalty", "defense", "color_identity")
# The face fields that the mirror keeps (refresh_scryfall_mirror.KEEP_FACE_FIELDS), so a
# card from the API prints the same faces as a card from the mirror.
FACE_FIELDS = ("name", "mana_cost", "type_line", "oracle_text",
               "colors", "power", "toughness", "loyalty", "defense")


def fold(name: str) -> str:
    """The name without case or accents: "Lórien Revealed" and "lorien revealed" fold alike."""
    decomposed = unicodedata.normalize("NFKD", name.strip().casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def front_face(name: str) -> str:
    """The text before `` // ``."""
    return name.split(" // ")[0]


def main_worktree() -> Path | None:
    """The main worktree of PROJECT_ROOT's repository, or None outside a repository.

    ``git -C`` runs in the script's repository, so a call from another repository
    (eternities-mtg-app) still finds this one.
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    # git prints the path relative to the -C folder, or absolute in a linked worktree.
    return (PROJECT_ROOT / common).resolve().parent


def find_mirror() -> Path | None:
    """The repository's mirror, else the main worktree's copy, else None."""
    own = PROJECT_ROOT / MIRROR
    if own.is_file():
        return own
    main = main_worktree()
    if main is not None and (main / MIRROR).is_file():
        return main / MIRROR
    return None


def load_mirror(path: Path) -> dict[str, dict]:
    """Folded name -> card, for every full name and every front face of an "A // B" card."""
    cards = json.loads(path.read_text(encoding="utf-8"))
    index = {fold(card["name"]): card for card in cards}
    for card in cards:
        if " // " in card["name"]:
            # A full name answers before a front face of the same spelling.
            index.setdefault(fold(front_face(card["name"])), card)
    return index


def mirror_source(path: Path) -> str:
    """The source text "mirror <scryfall_updated_at>", from the meta file beside the mirror."""
    try:
        meta = json.loads(path.with_name(MIRROR_META_NAME).read_text(encoding="utf-8"))
        return f"mirror {meta['scryfall_updated_at']}"
    except (OSError, ValueError, KeyError, TypeError):
        return "mirror unknown"


def summary(card: dict, source: str) -> dict:
    """The fields that the script prints for one card."""
    out = {field: card.get(field) for field in FIELDS}
    out["legalities"] = {"commander": (card.get("legalities") or {}).get("commander")}
    faces = card.get("card_faces")
    out["card_faces"] = (
        [{key: face[key] for key in FACE_FIELDS if key in face} for face in faces]
        if faces else None
    )
    out["source"] = source
    return out


def lookup_api(name: str) -> dict | None:
    """One /cards/named?exact= request through the helper; None on a 404."""
    url = f"{NAMED_URL}?exact={urllib.parse.quote(front_face(name))}"
    try:
        card = json.loads(scryfall_api.request(url))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    # An "A // B" name is found only when the card has that full name.
    if " // " in name and fold(name) != fold(card["name"]):
        return None
    return card


def lookup(names: list[str], index: dict[str, dict], source: str | None) -> int:
    """Print each name's card: from ``index`` (the mirror) when it holds the name, else
    from one request. ScryfallRateLimited and every other failed request pass through."""
    missing = False
    for name in names:
        card = index.get(fold(name))
        if card is not None:
            print(json.dumps(summary(card, source), ensure_ascii=False))
            continue
        card = lookup_api(name.strip())
        if card is None:
            print(f"not found: {name}")
            missing = True
        else:
            print(json.dumps(summary(card, "api"), ensure_ascii=False))
    return 2 if missing else 0


def mana_cost(card: dict) -> str:
    """The card's mana cost; a card without a top-level cost (a transform card) joins its
    faces' costs as Scryfall writes a split card's cost."""
    if "mana_cost" in card:
        return card["mana_cost"]
    return " // ".join(face.get("mana_cost", "") for face in card.get("card_faces", []))


def search(query: str) -> int:
    """One /cards/search request through the helper; print its first page."""
    url = f"{SEARCH_URL}?q={urllib.parse.quote(query)}"
    try:
        page = json.loads(scryfall_api.request(url))
    except urllib.error.HTTPError as e:
        # Scryfall answers 404 when no card matches the query.
        if e.code == 404:
            print("total_cards: 0")
            return 2
        raise
    print(f"total_cards: {page.get('total_cards')}")
    for card in page.get("data", []):
        print(f"{card['name']} | {mana_cost(card)} | {card.get('type_line', '')}")
    return 0


def error_text(error: OSError) -> str:
    """The error, with Scryfall's ``details`` when the answer carries them (a bad query)."""
    text = str(error)
    if isinstance(error, urllib.error.HTTPError):
        with contextlib.suppress(Exception):
            details = json.loads(error.read()).get("details")
            if details:
                text = f"{text}: {details}"
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Look up cards: the oracle mirror first, then Scryfall through "
                    "scripts/scryfall_api.py.")
    parser.add_argument("names", nargs="*", metavar="NAME", help="exact card names")
    parser.add_argument("--api", action="store_true",
                        help="skip the mirror and send one request for each name")
    parser.add_argument("--search", metavar="QUERY",
                        help="send one /cards/search request and print its first page")
    args = parser.parse_args(argv)
    if bool(args.names) == (args.search is not None):
        parser.error("give one or more names, or --search QUERY")

    index, source = {}, None
    if args.search is None and not args.api:
        path = find_mirror()
        if path is None:
            print(f"warning: no {MIRROR} in {PROJECT_ROOT} or in its main worktree; "
                  "every name goes to Scryfall.", file=sys.stderr)
        else:
            index, source = load_mirror(path), mirror_source(path)

    try:
        if args.search is not None:
            return search(args.search)
        return lookup(args.names, index, source)
    except scryfall_api.ScryfallRateLimited as e:
        print(e)
        return 1
    except OSError as e:
        # urllib.error.URLError (an HTTP error other than 404 among them) or a timeout.
        print(f"Scryfall request failed: {error_text(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

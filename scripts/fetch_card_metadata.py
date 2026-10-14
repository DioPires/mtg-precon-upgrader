#!/usr/bin/env python3
"""Fetch card metadata from Scryfall and cache locally.

Reads all deck.json files, collects unique card names, fetches metadata
via Scryfall Collection API, and saves to data/card-metadata.json.

Every run asks for the names of the selected decks and for every name already
in the output file, so no name leaves the file and one date
(data/card-metadata.meta.json, ``prices_as_of``) is true for every price.

After the batches, the run asks once more for each card whose printing has no
``usd`` or no ``eur``: a search of its other printings gives the price
(DEC-1079, see _prices_from_other_printings).

Every request goes through scryfall_api, which keeps Scryfall's rate limit. A
429, a failed batch or search, a deck card that Scryfall does not find or a
card that breaks the image rule ends the run: the script writes no file and
exits with 1.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "card-metadata.json"
COMMANDERS_DIR = DATA_DIR / "commanders"
BATCH_SIZE = 75
IMAGE_HOST = "https://cards.scryfall.io"
SEARCH_URL = f"https://{scryfall_api.API_HOST}/cards/search"
CURRENCIES = ("usd", "eur")
# Scryfall's set type of gold-bordered, oversized, trophy, 30th Anniversary
# Edition and Collectors' Edition printings. A sanctioned game allows none of
# them, so their prices do not count in the other-printing pass (DEC-1079 Q2).
MEMORABILIA = "memorabilia"
SOURCE = "scryfall-cards-collection"


class FetchFailed(Exception):
    """The run must end: no further request, no file written."""


def available_deck_ids() -> list[str]:
    """Sorted deck ids discovered from commander deck data."""
    return sorted(path.parent.name for path in COMMANDERS_DIR.glob("*/deck.json"))


def collect_card_names(deck_ids: list[str] | None = None) -> set[str]:
    """Collect unique card names from selected deck.json files."""
    names = set()
    if deck_ids:
        deck_paths = [COMMANDERS_DIR / deck_id / "deck.json" for deck_id in deck_ids]
    else:
        deck_paths = list(COMMANDERS_DIR.glob("*/deck.json"))

    for path in deck_paths:
        with open(path) as f:
            deck = json.load(f)

        # Commander(s)
        if deck.get("commander"):
            names.add(deck["commander"])
        if deck.get("partner"):
            names.add(deck["partner"])

        # Adds (notable/highlighted cards)
        for card in deck.get("adds", []):
            names.add(card["name"])

        # Full decklist
        for card in deck.get("decklist", []):
            names.add(card["name"])

    return names


def front_face(name: str) -> str:
    """The text before `` // ``. Scryfall's collection endpoint finds a
    two-part card by this name and does not find it by its full name."""
    return name.split(" // ")[0]


def _image_path(card: dict) -> str:
    """The ``normal`` image address without ``https://cards.scryfall.io/normal/``.

    Transform and modal DFC layouts carry ``image_uris`` on card_faces only, so
    the front face supplies it. The app builds the ``small``, ``large`` and
    ``art_crop`` addresses from this one value, so a card where that does not
    give Scryfall's own address raises FetchFailed.
    """
    faces = card.get("card_faces") or [{}]
    uris = card.get("image_uris") or faces[0].get("image_uris") or {}
    prefix = f"{IMAGE_HOST}/normal/"
    normal = uris.get("normal") or ""
    image = normal.removeprefix(prefix)
    if not image or image == normal:
        raise FetchFailed(
            f"{card['name']}: no normal image address under {prefix} (got {normal!r})")
    for size in ("small", "large", "art_crop"):
        expected = f"{IMAGE_HOST}/{size}/{image}"
        if uris.get(size) != expected:
            raise FetchFailed(
                f"{card['name']}: the {size} image address is {uris.get(size)!r}, "
                f"not {expected!r}")
    return image


def _price(card: dict, currency: str) -> float | None:
    """``prices[currency]`` as a number, or None when Scryfall gives none.

    No fallback to a foil price: the app reads ``prices.usd`` only.
    """
    value = (card.get("prices") or {}).get(currency)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise FetchFailed(
            f"{card['name']}: the {currency} price is {value!r}, not a number") from None


def _sort_key(card: dict, currency: str) -> float | None:
    """The price by which Scryfall orders a search with ``order=<currency>``.

    The non-foil price, else the foil one, else the etched one; None when the
    card has none. For a card with a non-foil price, the key is that price.
    Scryfall sorts a printing without a key as the lowest: last in its default
    order (the most expensive first), first with ``dir=asc``. The 114 search
    pages of the two DEC-1079 live runs fit this order with 0 inversions: the
    57 of run 1 (sent without ``dir``) and the 57 of run 2 (``dir=asc``).
    """
    for key in (currency, f"{currency}_foil", f"{currency}_etched"):
        price = _price(card, key)
        if price is not None:
            return price
    return None


def _first_page_proves(cards: list[dict], currency: str, price: float | None) -> bool:
    """Whether the first page of a search sent with ``dir=asc`` proves that
    ``price`` is the lowest non-foil price of all its printings that count.

    ``price`` is the lowest non-foil price on the page among the printings
    that count (_counts). The order check reads every card of the page, as
    Scryfall sorts the printings that do not count with the others. The page
    must be in Scryfall's order with ``dir=asc`` (_sort_key): the printings
    without a key first, then the keys from the cheapest up. Then each
    printing after the page has a key at or above the page's last key, and a
    printing's non-foil price is its key, so no printing after the page has a
    non-foil price below ``price``. A page with no ``price`` proves nothing,
    neither a price nor "no price": printings without a key, memorabilia,
    foil-only keys or later releases can fill it, and a printing that counts
    can follow it with a price. A page out of order proves nothing either.
    """
    keys = [_sort_key(card, currency) for card in cards]
    in_order = all(a is None or (b is not None and a <= b) for a, b in zip(keys, keys[1:]))
    return price is not None and in_order


def _counts(card: dict, today: str) -> bool:
    """Whether a printing's price counts: released on or before ``today`` and
    not memorabilia. The search already keeps paper printings only."""
    return card["released_at"] <= today and card["set_type"] != MEMORABILIA


def _search_prints(name: str, oracle_id: str, currency: str) -> dict:
    """The first page of the card's paper printings, in ``currency`` order from the cheapest up.

    One request, and never a second page: a basic land has thousands of
    printings. With ``dir=asc`` Scryfall puts the printings without a price
    first, then the cheapest (_sort_key); without it, the most expensive first.
    A 404 is Scryfall's answer for "no card matches", so it gives an empty
    page. Any other failure raises FetchFailed.
    """
    query = urllib.parse.urlencode({"q": f"oracleid:{oracle_id} game:paper",
                                    "unique": "prints", "order": currency, "dir": "asc"})
    try:
        page = json.loads(scryfall_api.request(f"{SEARCH_URL}?{query}"))
        return {"data": page["data"], "has_more": page["has_more"]}
    except scryfall_api.ScryfallRateLimited:
        raise
    except Exception as e:
        if isinstance(e, urllib.error.HTTPError) and e.code == 404:
            return {"data": [], "has_more": False}
        raise FetchFailed(f"The search for {name} failed: {type(e).__name__}: {e}") from e


def _prices_from_other_printings(lacking: dict, today: str) -> dict[str, list[dict]]:
    """Give each null price of ``lacking`` the price of another printing (DEC-1079).

    ``lacking`` maps an oracle id to the card's name and its entries, in the
    order of the batches. For each currency by itself, the price is the lowest
    non-foil price among the card's paper printings that are released on or
    before ``today`` (``YYYY-MM-DD``) and are not memorabilia (_counts). A
    foil price never counts. A price that the batch printing has stays, and
    ``image`` stays the batch printing's, even when that printing is
    memorabilia.

    The first search is ordered by the first currency that lacks a price. When
    its page holds every printing (``has_more`` false), it gives the other
    currency too; else a second search, ordered by that currency, does. A page
    with ``has_more`` holds the printings without a price and then the
    cheapest ones. When such a page cannot prove that its lowest price is the
    lowest of all (_first_page_proves), the run prints a line and takes no
    price; such a page never proves that a card has no price.

    Returns, for each currency, the entries that gained a price in it.
    """
    gained = {currency: [] for currency in CURRENCIES}
    for oracle_id, (name, entries) in lacking.items():
        page = None
        lines = []
        for currency in CURRENCIES:
            if entries[0][currency] is not None:
                continue
            if page is None or page["has_more"]:
                page = _search_prints(name, oracle_id, currency)
            prices = [_price(card, currency) for card in page["data"] if _counts(card, today)]
            price = min((p for p in prices if p is not None), default=None)
            if page["has_more"] and not _first_page_proves(page["data"], currency, price):
                lines.append(f"the first page does not prove the lowest {currency} price: "
                             f"no price taken")
                continue
            if price is None:
                lines.append(f"no released paper printing outside memorabilia has a "
                             f"non-foil {currency} price")
                continue
            for entry in entries:
                entry[currency] = price
            gained[currency] += entries
            lines.append(f"{currency} {price} from another printing")
        print(f"    {name}: " + "; ".join(lines))
    return gained


def _entry_from_card(card: dict) -> dict:
    """Build a metadata entry from a Scryfall card object.

    Transform/modal DFC layouts carry mana_cost, oracle_text, colors, power and
    toughness on card_faces, not top-level — fill empty fields from the FRONT
    face (the cast face; matches the project's MDFC handling policy). type_line
    and cmc stay top-level ("A // B", front-face cmc) so land/type checks still
    see both faces.

    ``power``/``toughness`` are the printed front-face values as Scryfall gives
    them (strings, so "*" and "1+*" survive) and ``None`` for anything with no
    printed power — non-creatures and the back-face-only creatures of a DFC.
    Added by DEC-940 for the goldfish combat modifiers' printed-power gates.

    ``image``, ``usd`` and ``eur`` (DEC-1075) are the front-face image path
    (see _image_path) and the non-foil prices as numbers (see _price).
    """
    layout = card.get("layout", "normal")
    entry = {
        "type_line": card.get("type_line", "Unknown"),
        "cmc": card.get("cmc", 0),
        "mana_cost": card.get("mana_cost", ""),
        "colors": card.get("colors", []),
        "oracle_text": card.get("oracle_text", ""),
        "power": card.get("power"),
        "toughness": card.get("toughness"),
    }
    faces = card.get("card_faces") or []
    if faces:
        front = faces[0]
        if not entry["mana_cost"]:
            entry["mana_cost"] = front.get("mana_cost", "")
        if not entry["oracle_text"]:
            entry["oracle_text"] = front.get("oracle_text", "")
        if not entry["colors"]:
            entry["colors"] = front.get("colors", [])
        if entry["power"] is None:
            entry["power"] = front.get("power")
        if entry["toughness"] is None:
            entry["toughness"] = front.get("toughness")
    if layout in ("modal_dfc", "transform"):
        entry["layout"] = layout
    entry["image"] = _image_path(card)
    entry["usd"] = _price(card, "usd")
    entry["eur"] = _price(card, "eur")
    return entry


def fetch_metadata(names: set[str], existing: dict | None = None,
                   deck_names: set[str] | None = None, *,
                   today: str) -> tuple[dict, dict[str, int]]:
    """Fetch metadata from Scryfall Collection API in batches of 75.

    A ``//`` name goes into the batch as its front face. Its entry is stored
    under the name asked, under the full name that Scryfall returned and under
    the front face.

    A name that Scryfall does not find keeps its entry of ``existing`` with
    ``image``, ``usd`` and ``eur`` set to None, unless ``deck_names`` holds it.

    After the batches, a card whose printing lacks ``usd`` or ``eur`` takes
    that price from another printing (_prices_from_other_printings, with
    ``today``). Returns the metadata and, for each currency, the number of
    names whose price came from another printing.

    Raises FetchFailed, and sends no further request, when a batch or a search
    fails, when Scryfall does not find a name of ``deck_names`` or when a card
    breaks the image or price rule. scryfall_api.ScryfallRateLimited passes
    through.
    """
    existing = existing or {}
    deck_names = deck_names or set()

    asked_by_request: dict[str, list[str]] = {}
    for name in sorted(names):
        asked_by_request.setdefault(front_face(name), []).append(name)
    request_names = sorted(asked_by_request)

    metadata = {}
    lacking: dict[str, tuple[str, list[dict]]] = {}  # oracle id -> name, entries
    batches = [request_names[i : i + BATCH_SIZE] for i in range(0, len(request_names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Fetching batch {i + 1}/{len(batches)} ({len(batch)} cards)...")

        try:
            raw = scryfall_api.request(
                scryfall_api.COLLECTION_URL,
                {"identifiers": [{"name": name} for name in batch]},
            )
            answer = json.loads(raw)
            cards = answer["data"]
            not_found = {nf["name"] for nf in answer.get("not_found", [])}
        except scryfall_api.ScryfallRateLimited:
            raise
        except Exception as e:
            raise FetchFailed(
                f"Batch {i + 1}/{len(batches)} failed: {type(e).__name__}: {e}") from e

        # A card answers a request by its full name first, then by its front
        # face: "Brainstorm" is a card and also the second part of
        # "Harmonized Trio // Brainstorm".
        by_full = {card["name"].casefold(): card for card in cards}
        by_front = {
            front_face(card["name"]).casefold(): card
            for card in cards if " // " in card["name"]
        }

        problems = []
        matched = set()  # the casefolded names of the cards that answered a name
        for request_name in batch:
            card = entry = None
            if request_name not in not_found:
                key = request_name.casefold()
                card = by_full.get(key) or by_front.get(key)
                if card is None:
                    problems.append(
                        f"{request_name}: Scryfall gave no card of that name and no "
                        f"not_found line for it")
                    continue
                matched.add(card["name"].casefold())
                try:
                    entry = _entry_from_card(card)
                except FetchFailed as e:
                    problems.append(str(e))
                    continue
                if entry["usd"] is None or entry["eur"] is None:
                    # A reversible_card carries its oracle id on each face
                    # only (DEC-1112 B1). The front face answered the name.
                    oracle_id = card.get("oracle_id") or card["card_faces"][0]["oracle_id"]
                    lacking.setdefault(oracle_id, (card["name"], []))[1].append(entry)

            for name in asked_by_request[request_name]:
                # A ``//`` name is found only when the card has that full name.
                if card is not None and (
                        " // " not in name or name.casefold() == card["name"].casefold()):
                    metadata[name] = entry
                    metadata[card["name"]] = entry
                    metadata[front_face(card["name"])] = entry
                    continue
                reason = ("Scryfall did not find it" if card is None
                          else f"Scryfall found {card['name']} under its front face")
                if name in deck_names:
                    problems.append(f"{name}: {reason}, and a deck file names it")
                elif name in existing:
                    metadata[name] = {**existing[name], "image": None, "usd": None, "eur": None}
                    print(f"    {name}: {reason}. Old entry kept without image and prices.")
                else:
                    problems.append(f"{name}: {reason}, and it has no old entry")

        if problems:
            # N5 of the DEC-1080 review: a card that answered no name asked
            # shows the spelling to use for a name that found no card.
            unmatched = [card["name"] for card in cards if card["name"].casefold() not in matched]
            if unmatched:
                problems.append(
                    "Scryfall also returned names that match no name asked: " + "; ".join(unmatched))
            raise FetchFailed(
                f"Batch {i + 1}/{len(batches)} ended the run:\n  " + "\n  ".join(problems))

    print(f"  Asking once more for the {len(lacking)} cards whose printing lacks a price...")
    gained = _prices_from_other_printings(lacking, today)
    other_printing = {}
    for currency in CURRENCIES:
        filled = {id(entry) for entry in gained[currency]}
        other_printing[currency] = sum(id(entry) in filled for entry in metadata.values())
    return metadata, other_printing


def load_existing_metadata(output_file: Path) -> dict:
    """Load existing metadata cache if present."""
    if not output_file.exists():
        return {}
    with open(output_file) as f:
        return json.load(f)


def write_outputs(output_file: Path, metadata: dict, prices_as_of: str,
                  other_printing: dict[str, int]) -> Path:
    """Write the metadata file and its ``.meta.json`` neighbour. Returns the latter.

    ``prices_from_other_printing`` in the meta file is ``other_printing``: for
    each currency, the number of names whose price came from another printing.

    N1 of the DEC-1080 review: each file goes to ``<name>.tmp`` in its folder
    first, then os.replace moves both into place, the meta file last. A run
    that fails before the moves leaves both old files as they were.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    meta_file = output_file.with_suffix(".meta.json")
    meta = {"count": len(metadata), "prices_as_of": prices_as_of,
            "prices_from_other_printing": other_printing, "source": SOURCE}
    texts = {
        output_file: json.dumps(metadata, indent=2, sort_keys=True),
        meta_file: json.dumps(meta, indent=2, sort_keys=True) + "\n",
    }
    temps = {path: path.with_name(path.name + ".tmp") for path in texts}
    try:
        for path, text in texts.items():
            temps[path].write_text(text)
        for path in texts:
            os.replace(temps[path], path)
    finally:
        for temp in temps.values():
            temp.unlink(missing_ok=True)
    return meta_file


def main(argv: list[str] | None = None) -> int:
    deck_ids = available_deck_ids()

    parser = argparse.ArgumentParser(
        description="Fetch Scryfall card metadata for commander decks")
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        choices=deck_ids,
        help="Take the deck names from only the specified deck id. Repeat to select "
             "multiple decks. Every name already in the output file is refreshed too.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=OUTPUT_FILE,
        help=f"Metadata output path (default: {OUTPUT_FILE})",
    )
    args = parser.parse_args(argv)
    output_file = args.output_file

    print("Collecting card names from deck files...")
    deck_names = collect_card_names()
    selected = collect_card_names(args.deck_ids) if args.deck_ids else deck_names
    if args.deck_ids:
        print(f"Found {len(selected)} unique card names across {len(args.deck_ids)} selected deck(s).")
    else:
        print(f"Found {len(selected)} unique card names across all decks.")

    existing = load_existing_metadata(output_file)
    names = selected | set(existing)
    print(f"{output_file.name} holds {len(existing)} names. Asking for {len(names)} names.\n")

    print("Fetching metadata from Scryfall...")
    # Taken just before the first request: the time at which the run read the prices.
    prices_as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        metadata, other_printing = fetch_metadata(
            names, existing, deck_names, today=prices_as_of[:10])
    except (FetchFailed, scryfall_api.ScryfallRateLimited) as e:
        print(f"\n{e}\nNo file written.")
        return 1
    print(f"\nCached {len(metadata)} cards. Prices from another printing: "
          f"{other_printing['usd']} usd, {other_printing['eur']} eur.")

    # No name leaves the file, and no file lacks a batch.
    missing = sorted(names - set(metadata))
    if missing:
        print(f"Missing {len(missing)}: {missing}\nNo file written.")
        return 1

    meta_file = write_outputs(output_file, metadata, prices_as_of, other_printing)

    print(f"\nSaved to {output_file} and {meta_file.name}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

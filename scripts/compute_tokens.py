#!/usr/bin/env python3
"""Compute token data for each deck from Scryfall.

Reads deck.json files (all decks by default, or a subset via --deck),
identifies cards that produce tokens, emblems,
and game-state markers (Experience, Poison Counter, The Monarch, Energy
Reserve, City's Blessing, The Initiative, etc.), fetches token/marker
card details, and writes a tokens array back into each deck.json.

Sources:
  - Scryfall `all_parts` with component="token" or component="emblem"
  - Scryfall `all_parts` with component="combo_piece" pointing at a marker
    card (filtered: not the card itself, not set checklists, type_line
    "Card" / "Emblem" / contains "Token")
  - amass {Type} oracle parsing → {Type} Army token
  - Oracle-text fallback for markers Scryfall doesn't always link
    (e.g. ascend → City's Blessing); resolved by Scryfall name lookup.

Every request goes through scryfall_api, which keeps Scryfall's rate limit. A
429 ends the run: the script writes no deck file and exits with 1 (DEC-1076).
Every other failed request ends the run in the same way (DEC-1098). An answer
that says Scryfall found no card does not: a ``not_found`` entry of a batch, and
a 404 from /cards/named or /cards/search.

A batch holds the front face of a ``//`` name: Scryfall does not find the full
name (DEC-1098).
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMANDERS_DIR = DATA_DIR / "commanders"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SCRYFALL_NAMED_URL = "https://api.scryfall.com/cards/named"
BATCH_SIZE = 75

# Oracle-text fallback table: regex → exact Scryfall card name to fetch.
# Used only for markers not linked via all_parts. Day/Night, monarch, etc.
# resolve via combo_piece in 99% of cases; this catches the stragglers.
ORACLE_MARKER_FALLBACKS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"city['’]s blessing|\bascend\b", re.I), "City's Blessing"),
    (re.compile(r"\b(become|becomes)\s+the\s+monarch\b", re.I), "The Monarch"),
    (re.compile(r"experience counter", re.I), "Experience"),
    (re.compile(r"\bthe ring tempts you\b", re.I), "The Ring // The Ring Tempts You"),
    (re.compile(r"\btake the initiative\b", re.I), "Undercity // The Initiative"),
]
# Avoid false positives: a card that says "you can't become the monarch" is hate, not a producer.
NEGATION_PATTERN = re.compile(r"can[’']t\s+become\s+the\s+monarch", re.I)


class RequestFailed(Exception):
    """A request failed: a 3xx, a 4xx, a 5xx, a network error, a timeout or an
    answer that is not JSON. The run must end, as on a 429 (DEC-1098)."""

    def __init__(self, url: str, body: dict | None, cause: Exception) -> None:
        method = "GET" if body is None else "POST"
        super().__init__(
            f"Scryfall request failed: {method} {url}: {type(cause).__name__}: {cause}")


def _request(url: str, body: dict | None = None, *, pass_404: bool = False) -> dict:
    """Send one request through scryfall_api and return its answer as JSON.

    A 429 raises ScryfallRateLimited. With ``pass_404``, a 404 raises its
    urllib.error.HTTPError: /cards/named and /cards/search answer 404 when no
    card matches. Every other failure raises RequestFailed.
    """
    try:
        return json.loads(scryfall_api.request(url, body))
    except scryfall_api.ScryfallRateLimited:
        raise
    except urllib.error.HTTPError as e:
        if pass_404 and e.code == 404:
            raise
        raise RequestFailed(url, body, e) from e
    except Exception as e:
        raise RequestFailed(url, body, e) from e


def fetch_collection(names: list[str]) -> list[dict]:
    """Batch-fetch full card objects via Scryfall Collection API.

    A ``//`` name (e.g. "Hagra Mauling // Hagra Broodpit") goes into the batch
    as its front face, once. A name that the batch does not find is retried
    via fuzzy named lookup.
    """
    cards = []
    not_found_names: list[str] = []
    names = sorted({name.split(" // ")[0] for name in names})
    batches = [names[i:i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Batch {i + 1}/{len(batches)} ({len(batch)} cards)...")
        body = {"identifiers": [{"name": n} for n in batch]}

        data = _request(SCRYFALL_COLLECTION_URL, body)
        cards.extend(data.get("data", []))
        not_found_names.extend(
            nf.get("name", "") for nf in data.get("not_found", []) if nf.get("name")
        )

    if not_found_names:
        print(f"    Retrying {len(not_found_names)} via fuzzy named lookup...")
        for name in not_found_names:
            front = name.split("//")[0].strip()
            url = f"{SCRYFALL_NAMED_URL}?fuzzy={urllib.parse.quote(front)}"
            try:
                c = _request(url, pass_404=True)
                if c.get("object") == "error":
                    print(f"      Still not found: {name}")
                    continue
                cards.append(c)
            except urllib.error.HTTPError as e:  # a 404: Scryfall found no card
                print(f"      Lookup failed for {name}: {e}")

    return cards


def fetch_token(uri: str) -> dict:
    """Fetch a single token/marker card by URI."""
    return _request(uri)


def fetch_named_exact(name: str, _cache: dict[str, dict | None] = {}) -> dict | None:
    """Fetch a card by exact name; cached across the run."""
    if name in _cache:
        return _cache[name]
    url = f"{SCRYFALL_NAMED_URL}?exact={urllib.parse.quote(name)}"
    try:
        c = _request(url, pass_404=True)
        if c.get("object") == "error":
            print(f"    Marker lookup failed for '{name}': {c.get('details', '')[:80]}")
            _cache[name] = None
            return None
        _cache[name] = c
        return c
    except urllib.error.HTTPError as e:  # a 404: Scryfall found no card
        print(f"    Marker lookup failed for '{name}': {e}")
        _cache[name] = None
        return None


def search_token(query: str) -> dict | None:
    """Search Scryfall for a token card."""
    url = f"https://api.scryfall.com/cards/search?q={urllib.parse.quote(query)}"
    try:
        data = _request(url, pass_404=True)
        results = data.get("data", [])
        return results[0] if results else None
    except urllib.error.HTTPError as e:  # a 404: no card matches the query
        print(f"    Token search failed for '{query}': {e}")
        return None


def extract_amass_types(oracle_text: str) -> set[str]:
    """Extract creature types from amass keywords in oracle text."""
    return set(re.findall(r'[Aa]mass\s+([A-Z][a-z]+)', oracle_text))


def is_marker_part(part: dict, card_name: str) -> bool:
    """Decide whether a combo_piece all_parts entry is a game-state marker.

    Markers (Experience, Poison Counter, The Monarch, Energy Reserve, The
    Ring // The Ring Tempts You, etc.) appear in Scryfall as combo_piece
    related cards with type_line "Card", "Emblem", or composite forms
    thereof. We exclude the card itself and printed artifacts like set
    checklists.
    """
    if part.get("component") != "combo_piece":
        return False
    name = part.get("name", "")
    if not name or name == card_name:
        return False
    # Checklist cards (DFC helper printings) link via all_parts with type_line
    # "Card" and masquerade as markers. Names may carry a numeric suffix
    # ("Shadows Over Innistrad Checklist 2"), so match the word, not just a
    # trailing token. No real token/marker is ever named "...Checklist...".
    if "checklist" in name.lower():
        return False
    type_line = part.get("type_line", "")
    if not type_line:
        return False
    parts = [p.strip() for p in type_line.split("//")]
    return any(
        tp == "Card" or tp.startswith("Emblem") or "Token" in tp
        for tp in parts
    )


def token_identity_key(token_card: dict) -> tuple[str, str | None, str | None, str]:
    """Return (name, power, toughness, oracle_text) for deduplication.

    Oracle text is part of the key because some cards (Wurmcoil Engine,
    Mirrorworks, etc.) produce multiple distinct tokens that share name
    and P/T but differ in keyword abilities — the lifelink Wurm vs the
    deathtouch Wurm collapse without it.
    """
    face = token_card
    if "card_faces" in token_card and token_card["card_faces"]:
        face = token_card["card_faces"][0]
    return (
        face.get("name", token_card.get("name", "Unknown")),
        face.get("power", token_card.get("power")),
        face.get("toughness", token_card.get("toughness")),
        face.get("oracle_text", token_card.get("oracle_text", "")) or "",
    )


def build_token_entry(token_card: dict, produced_by: list[str]) -> dict:
    """Build a token entry from a Scryfall token/marker card object."""
    face = token_card
    image_uri = ""
    if "card_faces" in token_card and token_card["card_faces"]:
        face = token_card["card_faces"][0]
        image_uri = face.get("image_uris", {}).get("normal", "")
    elif "image_uris" in token_card:
        image_uri = token_card["image_uris"].get("normal", "")

    return {
        "name": face.get("name", token_card.get("name", "Unknown")),
        "type_line": face.get("type_line", token_card.get("type_line", "")),
        "oracle_text": face.get("oracle_text", token_card.get("oracle_text", "")),
        "power": face.get("power", token_card.get("power")),
        "toughness": face.get("toughness", token_card.get("toughness")),
        "colors": face.get("colors", token_card.get("colors", [])),
        "scryfall_id": token_card.get("id", ""),
        "image_uri": image_uri,
        "produced_by": sorted(produced_by),
    }


def detect_oracle_marker_names(oracle_text: str) -> set[str]:
    """Identify marker names produced via oracle text (fallback when all_parts is silent)."""
    matches: set[str] = set()
    for pattern, marker_name in ORACLE_MARKER_FALLBACKS:
        if pattern.search(oracle_text):
            if marker_name == "The Monarch" and NEGATION_PATTERN.search(oracle_text):
                continue
            matches.add(marker_name)
    return matches


def compute_tokens_for_deck(deck: dict) -> list[dict]:
    """Compute all tokens and markers needed for a single deck."""
    card_names = [c["name"] for c in deck.get("decklist", [])]
    if deck.get("commander"):
        card_names.append(deck["commander"])
    card_names = sorted(set(card_names))

    print(f"  Fetching {len(card_names)} cards from Scryfall...")
    cards = fetch_collection(card_names)

    # token_uri -> set of producing card names
    token_refs: dict[str, set[str]] = {}
    # amass_type -> set of producing card names
    amass_refs: dict[str, set[str]] = {}
    # marker_name -> set of producing card names (oracle fallback only)
    marker_refs: dict[str, set[str]] = {}

    for card in cards:
        name = card.get("name", "")

        # Track which markers are linked via all_parts to skip oracle fallback
        linked_marker_names: set[str] = set()
        for part in card.get("all_parts", []):
            component = part.get("component", "")
            if component in ("token", "emblem"):
                uri = part.get("uri", "")
                if uri:
                    token_refs.setdefault(uri, set()).add(name)
            elif is_marker_part(part, name):
                uri = part.get("uri", "")
                if uri:
                    token_refs.setdefault(uri, set()).add(name)
                linked_marker_names.add(part.get("name", ""))

        # Concatenate face oracle text for DFCs/MDFCs
        oracle = card.get("oracle_text", "") or ""
        for face in card.get("card_faces", []) or []:
            oracle += "\n" + (face.get("oracle_text", "") or "")

        for amass_type in extract_amass_types(oracle):
            amass_refs.setdefault(amass_type, set()).add(name)

        for marker_name in detect_oracle_marker_names(oracle):
            if marker_name not in linked_marker_names:
                marker_refs.setdefault(marker_name, set()).add(name)

    # Meld results: a deck card's all_parts links its meld_result, but the
    # tokens that melded creature makes (e.g. Hanweir, the Writhing Township's
    # 3/2 Eldrazi Horrors) live on the *result* card, one hop away. Harvest
    # them only when every meld piece is actually in the deck, and attribute
    # them to the in-deck meld pieces that enable the meld.
    deck_names = set(card_names)
    meld_result_uris = {
        part["uri"]
        for card in cards
        for part in card.get("all_parts", [])
        if part.get("component") == "meld_result" and part.get("uri")
    }
    for uri in meld_result_uris:
        meld_card = fetch_token(uri)
        if not meld_card:
            continue
        result_name = meld_card.get("name", "")
        meld_pieces = [
            p.get("name", "")
            for p in meld_card.get("all_parts", [])
            if p.get("component") == "meld_part"
        ]
        if not meld_pieces or not all(mp in deck_names for mp in meld_pieces):
            continue  # deck can't form this meld; skip its tokens
        producers = sorted(mp for mp in meld_pieces if mp in deck_names)
        for part in meld_card.get("all_parts", []):
            component = part.get("component", "")
            part_uri = part.get("uri", "")
            if not part_uri:
                continue
            if component in ("token", "emblem") or is_marker_part(part, result_name):
                token_refs.setdefault(part_uri, set()).update(producers)

    # Fetch each unique token/marker card, deduped by (name, power, toughness)
    tokens_by_key: dict[tuple, dict] = {}
    producers_by_key: dict[tuple, set[str]] = {}

    print(f"  Fetching {len(token_refs)} unique token/marker cards...")
    for uri, producers in token_refs.items():
        token_card = fetch_token(uri)
        if not token_card:
            continue
        if token_card.get("name") == "Copy" or token_card.get("type_line") == "Token":
            continue
        key = token_identity_key(token_card)
        if key in tokens_by_key:
            producers_by_key[key].update(producers)
        else:
            tokens_by_key[key] = token_card
            producers_by_key[key] = set(producers)

    # Amass tokens
    for amass_type, producers in amass_refs.items():
        army_name = f"{amass_type[:-1]} Army" if amass_type.endswith("s") else f"{amass_type} Army"
        existing_key = next((k for k in tokens_by_key if k[0] == army_name), None)
        if existing_key:
            producers_by_key[existing_key].update(producers)
        else:
            print(f"  Searching for {army_name} token...")
            token_card = search_token(f't:token t:army "{amass_type}"')
            if not token_card:
                token_card = search_token(f't:token "{army_name}"')
            if token_card:
                key = token_identity_key(token_card)
                tokens_by_key[key] = token_card
                producers_by_key[key] = set(producers)
            else:
                print(f"    Could not find {army_name} token on Scryfall")

    # Oracle-text-only marker fallback
    for marker_name, producers in marker_refs.items():
        print(f"  Looking up marker '{marker_name}' (oracle fallback)...")
        marker_card = fetch_named_exact(marker_name)
        if not marker_card:
            continue
        key = token_identity_key(marker_card)
        if key in tokens_by_key:
            producers_by_key[key].update(producers)
        else:
            tokens_by_key[key] = marker_card
            producers_by_key[key] = set(producers)

    # Build final list, filtering producers to cards actually in the deck
    deck_card_names = set(c["name"] for c in deck.get("decklist", []))
    if deck.get("commander"):
        deck_card_names.add(deck["commander"])

    tokens = []
    for key, token_card in tokens_by_key.items():
        producers = producers_by_key.get(key, set())
        relevant_producers = sorted(producers & deck_card_names)
        if relevant_producers:
            tokens.append(build_token_entry(token_card, relevant_producers))

    return sorted(tokens, key=lambda t: t["name"])


def deck_paths_for_ids(deck_ids: list[str] | None) -> list[Path]:
    """Resolve requested deck ids to deck.json paths, or all decks when omitted."""
    if not deck_ids:
        return sorted(COMMANDERS_DIR.glob("*/deck.json"))
    return [COMMANDERS_DIR / deck_id / "deck.json" for deck_id in deck_ids]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute token/emblem/marker data and write it into deck.json files."
    )
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        help="Process one deck id. Repeat to process multiple decks. Defaults to all decks.",
    )
    args = parser.parse_args()

    deck_paths = deck_paths_for_ids(args.deck_ids)
    missing = [path for path in deck_paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"Unknown deck: {path.parent.name} ({path})", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(deck_paths)} decks.\n")

    # Every deck first, then every write: a 429 or another failed request leaves
    # every deck file as it was.
    decks = []
    for path in deck_paths:
        with open(path) as f:
            deck = json.load(f)

        deck_name = deck.get("name", path.parent.name)
        print(f"Processing: {deck_name}")

        try:
            deck["tokens"] = compute_tokens_for_deck(deck)
        except (scryfall_api.ScryfallRateLimited, RequestFailed) as e:
            print(f"\n{e}\nNo file written.")
            return 1
        decks.append((path, deck))
        print(f"  -> {len(deck['tokens'])} tokens\n")

    for path, deck in decks:
        with open(path, "w") as f:
            json.dump(deck, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Wrote {path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

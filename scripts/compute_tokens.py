#!/usr/bin/env python3
"""Compute token data for each deck from Scryfall.

Reads all deck.json files, identifies cards that produce tokens, emblems,
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
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SCRYFALL_NAMED_URL = "https://api.scryfall.com/cards/named"
BATCH_SIZE = 75
RATE_LIMIT_DELAY = 0.1  # 100ms between requests
USER_AGENT = "MTGPreconUpgrader/1.0"

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


def _request(url: str, data: bytes | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_collection(names: list[str]) -> list[dict]:
    """Batch-fetch full card objects via Scryfall Collection API.

    DFC composite names (e.g. "Hagra Mauling // Hagra Broodpit") often miss
    the collection API; retry those individually via fuzzy named lookup.
    """
    cards = []
    not_found_names: list[str] = []
    batches = [names[i:i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Batch {i + 1}/{len(batches)} ({len(batch)} cards)...")
        body = json.dumps({"identifiers": [{"name": n} for n in batch]}).encode()

        try:
            data = _request(SCRYFALL_COLLECTION_URL, data=body)
            cards.extend(data.get("data", []))
            not_found_names.extend(
                nf.get("name", "") for nf in data.get("not_found", []) if nf.get("name")
            )
        except Exception as e:
            print(f"    Batch {i + 1} failed: {e}")

        if i < len(batches) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    if not_found_names:
        print(f"    Retrying {len(not_found_names)} via fuzzy named lookup...")
        for name in not_found_names:
            front = name.split("//")[0].strip()
            url = f"{SCRYFALL_NAMED_URL}?fuzzy={urllib.parse.quote(front)}"
            try:
                time.sleep(RATE_LIMIT_DELAY)
                c = _request(url)
                if c.get("object") == "error":
                    print(f"      Still not found: {name}")
                    continue
                cards.append(c)
            except Exception as e:
                print(f"      Lookup failed for {name}: {e}")

    return cards


def fetch_token(uri: str) -> dict | None:
    """Fetch a single token/marker card by URI."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        return _request(uri)
    except Exception as e:
        print(f"    Failed to fetch token {uri}: {e}")
        return None


def fetch_named_exact(name: str, _cache: dict[str, dict | None] = {}) -> dict | None:
    """Fetch a card by exact name; cached across the run."""
    if name in _cache:
        return _cache[name]
    url = f"{SCRYFALL_NAMED_URL}?exact={urllib.parse.quote(name)}"
    try:
        time.sleep(RATE_LIMIT_DELAY)
        c = _request(url)
        if c.get("object") == "error":
            print(f"    Marker lookup failed for '{name}': {c.get('details', '')[:80]}")
            _cache[name] = None
            return None
        _cache[name] = c
        return c
    except Exception as e:
        print(f"    Marker lookup failed for '{name}': {e}")
        _cache[name] = None
        return None


def search_token(query: str) -> dict | None:
    """Search Scryfall for a token card."""
    url = f"https://api.scryfall.com/cards/search?q={urllib.parse.quote(query)}"
    try:
        time.sleep(RATE_LIMIT_DELAY)
        data = _request(url)
        results = data.get("data", [])
        return results[0] if results else None
    except Exception as e:
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
    if name.endswith("Checklist"):
        return False
    type_line = part.get("type_line", "")
    if not type_line:
        return False
    parts = [p.strip() for p in type_line.split("//")]
    return any(
        tp == "Card" or tp.startswith("Emblem") or "Token" in tp
        for tp in parts
    )


def token_identity_key(token_card: dict) -> tuple[str, str | None, str | None]:
    """Return (name, power, toughness) for deduplication across printings."""
    face = token_card
    if "card_faces" in token_card and token_card["card_faces"]:
        face = token_card["card_faces"][0]
    return (
        face.get("name", token_card.get("name", "Unknown")),
        face.get("power", token_card.get("power")),
        face.get("toughness", token_card.get("toughness")),
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


def main():
    deck_paths = sorted(DATA_DIR.glob("commanders/*/deck.json"))
    print(f"Found {len(deck_paths)} decks.\n")

    for path in deck_paths:
        with open(path) as f:
            deck = json.load(f)

        deck_name = deck.get("name", path.parent.name)
        print(f"Processing: {deck_name}")

        tokens = compute_tokens_for_deck(deck)
        deck["tokens"] = tokens

        with open(path, "w") as f:
            json.dump(deck, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"  -> {len(tokens)} tokens written\n")

    print("Done.")


if __name__ == "__main__":
    main()

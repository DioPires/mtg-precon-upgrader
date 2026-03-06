#!/usr/bin/env python3
"""Compute token data for each deck from Scryfall.

Reads all deck.json files, identifies cards that produce tokens via
Scryfall's all_parts field, fetches token card details, and writes
a tokens array back into each deck.json.
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
BATCH_SIZE = 75
RATE_LIMIT_DELAY = 0.1  # 100ms between requests
USER_AGENT = "MTGPreconUpgrader/1.0"


def _request(url: str, data: bytes | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_collection(names: list[str]) -> list[dict]:
    """Batch-fetch full card objects via Scryfall Collection API."""
    cards = []
    batches = [names[i:i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Batch {i + 1}/{len(batches)} ({len(batch)} cards)...")
        body = json.dumps({"identifiers": [{"name": n} for n in batch]}).encode()

        try:
            data = _request(SCRYFALL_COLLECTION_URL, data=body)
            cards.extend(data.get("data", []))
            not_found = data.get("not_found", [])
            if not_found:
                nf = [nf.get("name", str(nf)) for nf in not_found]
                print(f"    Not found: {nf}")
        except Exception as e:
            print(f"    Batch {i + 1} failed: {e}")

        if i < len(batches) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    return cards


def fetch_token(uri: str) -> dict | None:
    """Fetch a single token card by URI."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        return _request(uri)
    except Exception as e:
        print(f"    Failed to fetch token {uri}: {e}")
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
    # Matches "amass Orcs", "amass Zombies", etc.
    return set(re.findall(r'[Aa]mass\s+([A-Z][a-z]+)', oracle_text))


def build_token_entry(token_card: dict, produced_by: list[str]) -> dict:
    """Build a token entry from a Scryfall token card object."""
    image_uri = ""
    if "image_uris" in token_card:
        image_uri = token_card["image_uris"].get("normal", "")
    elif "card_faces" in token_card and token_card["card_faces"]:
        image_uri = token_card["card_faces"][0].get("image_uris", {}).get("normal", "")

    return {
        "name": token_card.get("name", "Unknown"),
        "type_line": token_card.get("type_line", ""),
        "oracle_text": token_card.get("oracle_text", ""),
        "power": token_card.get("power"),
        "toughness": token_card.get("toughness"),
        "colors": token_card.get("colors", []),
        "scryfall_id": token_card.get("id", ""),
        "image_uri": image_uri,
        "produced_by": sorted(produced_by),
    }


def compute_tokens_for_deck(deck: dict) -> list[dict]:
    """Compute all tokens needed for a single deck."""
    # Collect card names from decklist + commander
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

    for card in cards:
        name = card.get("name", "")

        # Check all_parts for token components
        for part in card.get("all_parts", []):
            if part.get("component") == "token":
                uri = part.get("uri", "")
                if uri:
                    token_refs.setdefault(uri, set()).add(name)

        # Check for amass in oracle_text
        oracle = card.get("oracle_text", "")
        for amass_type in extract_amass_types(oracle):
            amass_refs.setdefault(amass_type, set()).add(name)

    # Fetch each unique token card
    tokens_by_id: dict[str, dict] = {}  # scryfall_id -> token entry
    producers_by_id: dict[str, set[str]] = {}

    print(f"  Fetching {len(token_refs)} unique token cards...")
    for uri, producers in token_refs.items():
        token_card = fetch_token(uri)
        if not token_card:
            continue
        # Skip generic copy tokens (no specific physical card needed)
        if token_card.get("name") == "Copy" or token_card.get("type_line") == "Token":
            continue
        tid = token_card.get("id", "")
        if tid in tokens_by_id:
            producers_by_id[tid].update(producers)
        else:
            tokens_by_id[tid] = token_card
            producers_by_id[tid] = set(producers)

    # Handle amass tokens
    for amass_type, producers in amass_refs.items():
        # Check if we already have this army token from all_parts
        army_name = f"{amass_type[:-1]} Army" if amass_type.endswith("s") else f"{amass_type} Army"
        already_found = any(
            t.get("name", "") == army_name
            for t in tokens_by_id.values()
        )
        if already_found:
            # Merge producers into existing
            for tid, tc in tokens_by_id.items():
                if tc.get("name", "") == army_name:
                    producers_by_id[tid].update(producers)
                    break
        else:
            print(f"  Searching for {army_name} token...")
            token_card = search_token(f't:token t:army "{amass_type}"')
            if not token_card:
                # Fallback: broader search
                token_card = search_token(f't:token "{army_name}"')
            if token_card:
                tid = token_card.get("id", "")
                tokens_by_id[tid] = token_card
                producers_by_id[tid] = set(producers)
            else:
                print(f"    Could not find {army_name} token on Scryfall")

    # Build final token list
    tokens = []
    for tid, token_card in tokens_by_id.items():
        producers = producers_by_id.get(tid, set())
        # Filter producers to only cards actually in this deck
        deck_card_names = set(c["name"] for c in deck.get("decklist", []))
        if deck.get("commander"):
            deck_card_names.add(deck["commander"])
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

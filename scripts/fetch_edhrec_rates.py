#!/usr/bin/env python3
"""Fetch per-commander EDHREC inclusion rates into priv_data/edhrec/{deck-id}.json.

Authorization: EDHREC's ToS bars automated queries (DEC-312). The board issued
an explicit, informed risk-acceptance override on DEC-410 (interaction
7a8bc464, 2026-07-06) sanctioning a low-volume cached fetch. Keep the
footprint minimal: one request per commander, 7-day cache TTL, identifying
User-Agent, 1s spacing between decks. Do not widen this without a fresh
board decision. See docs/discovery-playbook.md.

The output file feeds the candidate-pool EDHREC boost (DEC-410):
    {"rates": {front-face card name: inclusion percent 0-100}, "fetched_at": ...}
Manual transcription during the DEC-402 closing diff remains a valid way to
add/correct entries; an explicit "slug" key in an existing file overrides the
derived commander slug and is preserved across refreshes.

Usage:
    python scripts/fetch_edhrec_rates.py --deck DECK_ID [--deck ...] | --all
                                         [--max-age-days N] [--force] [--slug SLUG]
"""

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
EDHREC_RATES_DIR = PROJECT_ROOT / "priv_data" / "edhrec"

EDHREC_JSON_URL = "https://json.edhrec.com/pages/commanders/{slug}.json"
USER_AGENT = "mtg-precon-upgrader/1.0 (personal deckbuilding tool; low-volume cached fetch)"
DEFAULT_MAX_AGE_DAYS = 7
REQUEST_TIMEOUT = 30
INTER_DECK_SLEEP = 1.0


def front_face(name: str) -> str:
    return name.split(" // ", 1)[0]


def edhrec_slug(name: str) -> str:
    """EDHREC commander slug: lowercase front face, punctuation stripped, spaces -> hyphens."""
    face = front_face(name)
    face = unicodedata.normalize("NFKD", face).encode("ascii", "ignore").decode("ascii")
    face = face.lower().replace("&", "and")
    face = re.sub(r"[^a-z0-9 -]", "", face)
    return re.sub(r"\s+", "-", face.strip())


def slug_candidates(commander: str) -> list[str]:
    """Front-face slug first; full-name slug as a 404 fallback for DFC pages."""
    cands = [edhrec_slug(commander)]
    if " // " in commander:
        full = edhrec_slug(commander.replace(" // ", " "))
        if full not in cands:
            cands.append(full)
    return cands


def extract_rates(page: dict) -> dict[str, float]:
    """Pull {card name: inclusion percent} out of an EDHREC commander page JSON."""
    cardlists = (
        page.get("container", {}).get("json_dict", {}).get("cardlists")
        or page.get("cardlist")
        or []
    )
    rates: dict[str, float] = {}
    for cl in cardlists:
        for cv in cl.get("cardviews", []) or []:
            name = cv.get("name")
            if not name:
                continue
            num = cv.get("num_decks", cv.get("inclusion"))
            pot = cv.get("potential_decks")
            rate = None
            if isinstance(num, (int, float)) and isinstance(pot, (int, float)) and pot > 0:
                rate = round(100.0 * num / pot, 1)
            else:
                m = re.search(r"(\d+(?:\.\d+)?)%", cv.get("label") or "")
                if m:
                    rate = float(m.group(1))
            if rate is None:
                continue
            rate = max(0.0, min(100.0, rate))
            key = front_face(name)
            rates[key] = max(rate, rates.get(key, 0.0))
    return rates


def fetch_page(slug: str) -> dict | None:
    """One GET against the EDHREC JSON route. Returns None on 404 (bad slug)."""
    req = urllib.request.Request(
        EDHREC_JSON_URL.format(slug=slug), headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def is_fresh(existing: dict, max_age_days: int) -> bool:
    stamp = existing.get("fetched_at")
    if not stamp:
        return False
    try:
        fetched = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - fetched < timedelta(days=max_age_days)


def refresh_deck(deck_id: str, max_age_days: int, force: bool, slug_override: str | None) -> bool:
    deck_path = COMMANDERS_DIR / deck_id / "deck.json"
    if not deck_path.exists():
        print(f"  [{deck_id}] deck.json not found", file=sys.stderr)
        return False
    commander = json.loads(deck_path.read_text()).get("commander", "")
    if not commander:
        print(f"  [{deck_id}] no commander field", file=sys.stderr)
        return False

    out_path = EDHREC_RATES_DIR / f"{deck_id}.json"
    existing = json.loads(out_path.read_text()) if out_path.exists() else {}
    if not force and existing.get("fetched_at") and is_fresh(existing, max_age_days):
        print(f"  [{deck_id}] fresh (fetched {existing['fetched_at']}), skipping", file=sys.stderr)
        return True

    slugs = [slug_override or existing.get("slug") or ""] if (slug_override or existing.get("slug")) \
        else slug_candidates(commander)
    page = slug = None
    for cand in slugs:
        page = fetch_page(cand)
        if page is not None:
            slug = cand
            break
        print(f"  [{deck_id}] 404 for slug {cand!r}", file=sys.stderr)
    if page is None:
        print(f"  [{deck_id}] no working slug for {commander!r} — set \"slug\" in {out_path} or pass --slug", file=sys.stderr)
        return False

    rates = extract_rates(page)
    if not rates:
        print(f"  [{deck_id}] page parsed but no rates extracted — EDHREC JSON shape changed?", file=sys.stderr)
        return False

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {
        "version": 1,
        "deck_id": deck_id,
        "commander": commander,
        "slug": slug,
        "source": "edhrec json route (board informed-override, DEC-410 interaction 7a8bc464)",
        "recorded_at": now[:10],
        "fetched_at": now,
        "rates": {name: rates[name] for name in sorted(rates)},
    }
    EDHREC_RATES_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"  [{deck_id}] wrote {len(rates)} rates (slug {slug!r})", file=sys.stderr)
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fetch EDHREC inclusion rates per commander deck")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--deck", action="append", help="Deck id (repeatable)")
    target.add_argument("--all", action="store_true", help="All decks")
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS,
                        help=f"Cache TTL in days (default {DEFAULT_MAX_AGE_DAYS})")
    parser.add_argument("--force", action="store_true", help="Refetch even if cache is fresh")
    parser.add_argument("--slug", help="Explicit EDHREC slug (single --deck only)")
    args = parser.parse_args(argv)

    if args.slug and (not args.deck or len(args.deck) != 1):
        parser.error("--slug requires exactly one --deck")

    if args.deck:
        deck_ids = args.deck
    else:
        deck_ids = sorted(p.parent.name for p in COMMANDERS_DIR.glob("*/deck.json"))

    ok = True
    for i, deck_id in enumerate(deck_ids):
        if i:
            time.sleep(INTER_DECK_SLEEP)
        ok = refresh_deck(deck_id, args.max_age_days, args.force, args.slug) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

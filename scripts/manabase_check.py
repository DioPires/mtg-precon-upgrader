#!/usr/bin/env python3
"""DEC-426 manabase discovery + audit.

The candidate pipeline (generate_candidate_pool.score_card) disqualifies any
card with no archetype-pattern match, so fixing lands never reach
candidates.json (0/200 for every deck). This standalone audit closes that gap:

1. Audit — Karsten color compliance, pip census, untapped ratio, land count
   fit for the deck's current manabase (reuses compute_deck_metrics math).
2. Discovery — sweep the owned pool for in-color-identity lands not in the
   decklist, score them on fixing quality (colors produced, deficit coverage,
   untapped, typed-ness, fetchability), and flag free vs locked copies
   (locked = a copy runs in a non-brewing deck; owned duplicates free locks).

Owned-first per DEC-369: the sweep covers the owned pool only. Unowned land
cycles still enter via the EDHREC closing diff (DEC-402).

Known limitation — colorless-CI decks (CI = {}): every `produced & deck_ci`
intersection is empty, so colored credit, pip census, and deficit bonuses all
zero out and the ranking degrades to ETB-tier + free-copy only (Command Tower
ties with genuinely useful utility lands). Treat colorless decks as out of
scope for the discovery ranking; audit half still applies. (Founding Engineer
review finding, DEC-426.)

Usage:
    uv run python scripts/manabase_check.py --deck DECK_ID [--top N] [--json]
    uv run python scripts/manabase_check.py --deck DECK_ID --deck-file PATH

--deck-file audits an alternate deck.json snapshot (e.g. a historical
`git show` extract) while still using --deck for lock bookkeeping.

Non-blocking review tool: exits 0 on findings, 1 on bad input/missing data.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_deck_metrics as cdm  # noqa: E402
import generate_candidate_pool as gcp  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIR = PROJECT_ROOT / "data" / "commanders"
OWNED_FILE = PROJECT_ROOT / "priv_data" / "owned_formatted.csv"

BASIC_TYPES = ("Plains", "Island", "Swamp", "Mountain", "Forest")

# Scoring weights — transparent, documented here so review notes can cite them.
SCORE_FIRST_COLOR = 4       # produces at least one in-CI color
SCORE_EXTRA_COLOR = 6       # each in-CI color beyond the first (duals/triomes)
SCORE_DEFICIT_COLOR = 8     # each produced color below its Karsten requirement
SCORE_ALWAYS_UNTAPPED = 8
SCORE_COND_UNTAPPED = 6     # "enters tapped unless ..." lands
SCORE_TAPPED = -8           # unconditional enters-tapped — B4 bar penalizes hard
                            # (a tapped tri-land must not outrank an untapped dual)
SCORE_TYPED = 4             # has a basic land type (typed-fetchable, Farseek-able)
SCORE_FETCH = 6
SCORE_FREE_COPY = 3         # a copy is free right now (owned-first tiebreak)
SCORE_PIP_DEMAND = 8        # scaled by share of the deck's pips the land covers
SCORE_RESTRICTED = -8       # "spend this mana only ..." — produced_mana overstates
                            # these (DEC-424 restricted-mana lesson); flag + demote

# DEC-429: utility lands almost all land on the same base score (untapped +
# free-copy), which made the utility top-10 effectively alphabetical. The
# cached per-deck EDHREC inclusion rate (priv_data/edhrec/{deck-id}.json,
# written by fetch_edhrec_rates.py) breaks the tie: utility scores get the
# same 0-20 boost the candidate scorer uses; fixing lands keep their
# Karsten-driven score and use the rate only as a sort tiebreak, so a popular
# tapped land can never outrank an untapped dual. Missing cache file or
# missing card entry degrades to a boost of 0 (current behavior).


def edhrec_boost(rate: float | None) -> int:
    """0-20 boost from an EDHREC inclusion percent (candidate-scorer formula)."""
    if rate is None:
        return 0
    return round(min(gcp.EDHREC_MAX, rate / gcp.EDHREC_RATE_SATURATION * gcp.EDHREC_MAX))


def load_owned_quantities() -> dict[str, int]:
    """Owned card name -> total quantity (rows aggregated across printings)."""
    if not OWNED_FILE.exists():
        print(f"missing owned pool: {OWNED_FILE}", file=sys.stderr)
        sys.exit(1)
    owned: dict[str, int] = {}
    with open(OWNED_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            try:
                qty = max(1, int(row.get("quantity") or 1))
            except (TypeError, ValueError):
                qty = 1
            owned[name] = owned.get(name, 0) + qty
    return owned


def load_locks(exclude_deck: str) -> dict[str, list[str]]:
    """Card name -> deck ids of non-brewing decks running it (each locks a copy).

    Brewing decks don't lock (DEC-351 owned-pool policy). Names are indexed
    both by full name and front face so mirror/deck naming variants match.
    """
    locks: dict[str, list[str]] = {}
    for deck_dir in sorted(DECKS_DIR.iterdir()):
        deck_file = deck_dir / "deck.json"
        if deck_dir.name == exclude_deck or not deck_file.exists():
            continue
        deck = json.loads(deck_file.read_text())
        if deck.get("status") == "brewing":
            continue
        for entry in deck.get("decklist", []):
            name = entry.get("name", "")
            if name:
                locks.setdefault(name, []).append(deck_dir.name)
                front = name.split(" // ", 1)[0]
                if front != name:
                    locks.setdefault(front, []).append(deck_dir.name)
    return locks


def is_basic(scry: dict) -> bool:
    return (scry.get("type_line") or "").startswith("Basic")


def front_is_land(scry: dict) -> bool:
    faces = scry.get("card_faces") or []
    type_line = (faces[0].get("type_line") if faces else scry.get("type_line")) or ""
    return "Land" in type_line


def commander_legal(scry: dict) -> bool:
    return (scry.get("legalities") or {}).get("commander") == "legal"


def typed_subtypes(scry: dict) -> list[str]:
    type_line = scry.get("type_line") or ""
    return [t for t in BASIC_TYPES if t in type_line]


def always_untapped(scry: dict) -> bool:
    oracle = cdm.land_oracle(scry)
    return "enters tapped" not in oracle and "enters the battlefield tapped" not in oracle


def pip_census(deck: dict, mirror: dict[str, dict], deck_ci: set[str]) -> dict[str, int]:
    """Mono-colored pips per color across nonland spells (hybrids excluded,
    same convention as the Karsten thresholds in compute_deck_metrics)."""
    census = {c: 0 for c in sorted(deck_ci)}
    for entry in deck.get("decklist", []):
        scry = cdm.get_scry(entry, mirror)
        if not scry or cdm.spell_weight(entry, scry) <= 0:
            continue
        mana_cost = cdm.spell_face_mana_cost(entry, scry)
        qty = cdm.card_quantity(entry)
        for color in census:
            census[color] += cdm.color_pip_count(mana_cost, color) * qty
    return census


def score_land(
    scry: dict,
    deck_ci: set[str],
    deficit_colors: set[str],
    free_copies: int,
    census: dict[str, int] | None = None,
) -> tuple[int, dict]:
    # produced_mana only — no fetch→all-colors fallback here. That fallback is
    # correct for Karsten source accounting but inflates basic-gate fetches
    # (Evolving Wilds) above real duals in discovery; fetch value is scored as
    # its own feature instead.
    produced = sorted(set(scry.get("produced_mana") or []) & deck_ci)
    untapped = cdm.land_is_untapped(scry)
    always = always_untapped(scry)
    typed = typed_subtypes(scry)
    fetch = cdm.land_is_fetch(scry)
    restricted = "spend this mana only" in cdm.land_oracle(scry)

    score = 0
    if produced:
        if restricted:
            score += SCORE_RESTRICTED
        score += SCORE_FIRST_COLOR + SCORE_EXTRA_COLOR * (len(produced) - 1)
        score += SCORE_DEFICIT_COLOR * len(deficit_colors.intersection(produced))
        total_pips = sum(census.values()) if census else 0
        if total_pips:
            covered = sum(census.get(c, 0) for c in produced)
            score += round(SCORE_PIP_DEMAND * covered / total_pips)
    if always:
        score += SCORE_ALWAYS_UNTAPPED
    elif untapped:
        score += SCORE_COND_UNTAPPED
    else:
        score += SCORE_TAPPED
    if typed:
        score += SCORE_TYPED
    if fetch:
        score += SCORE_FETCH
    if free_copies > 0:
        score += SCORE_FREE_COPY

    features = {
        "produces": produced,
        "etb": "untapped" if always else ("conditional" if untapped else "tapped"),
        "typed": typed,
        "fetch": fetch,
        "restricted": restricted,
    }
    return score, features


def discover_lands(
    deck: dict,
    mirror: dict[str, dict],
    deck_ci: set[str],
    deficit_colors: set[str],
    owned: dict[str, int],
    locks: dict[str, list[str]],
    census: dict[str, int] | None = None,
    edhrec_rates: dict[str, float] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Returns (fixing_candidates, utility_candidates), each sorted by score desc.

    Fixing = produces at least one in-CI color or fetches. Utility = in-CI land
    with no in-CI colored production (Reliquary Tower et al.) — listed
    separately so pure fixing review isn't diluted.

    EDHREC inclusion rate (DEC-429): added into the utility score as a 0-20
    boost; used only as a sort tiebreak for fixing lands (score unchanged).
    """
    decklist_names = set()
    for entry in deck.get("decklist", []):
        name = entry.get("name", "")
        decklist_names.add(name)
        decklist_names.add(name.split(" // ", 1)[0])

    fixing: list[dict] = []
    utility: list[dict] = []
    for name, qty in owned.items():
        scry = mirror.get(name) or mirror.get(name.split(" // ", 1)[0])
        if not scry:
            continue
        full_name = scry["name"]
        if full_name in decklist_names or full_name.split(" // ", 1)[0] in decklist_names:
            continue
        if not front_is_land(scry) or is_basic(scry) or not commander_legal(scry):
            continue
        if not set(scry.get("color_identity") or []).issubset(deck_ci):
            continue

        locked_by = locks.get(full_name, [])
        free_copies = max(0, qty - len(locked_by))
        score, features = score_land(scry, deck_ci, deficit_colors, free_copies, census)
        rate = gcp.edhrec_rate_for(full_name, edhrec_rates)
        row = {
            "name": full_name,
            "score": score,
            **features,
            "edhrec_rate": rate,
            "owned": qty,
            "free_copies": free_copies,
            "locked_by": sorted(set(locked_by)),
        }
        if features["produces"] or features["fetch"]:
            fixing.append(row)
        else:
            row["score"] += edhrec_boost(rate)
            utility.append(row)

    key = lambda r: (-r["score"], -(r["edhrec_rate"] or 0), r["name"])  # noqa: E731
    return sorted(fixing, key=key), sorted(utility, key=key)


def weak_current_lands(deck: dict, mirror: dict[str, dict], deck_ci: set[str]) -> list[dict]:
    """Current nonbasic lands that enter tapped unconditionally — swap fodder."""
    weak = []
    for entry in deck.get("decklist", []):
        scry = cdm.get_scry(entry, mirror)
        if not scry or cdm.land_weight(entry, scry) <= 0 or is_basic(scry):
            continue
        if not cdm.land_is_untapped(scry):
            weak.append({
                "name": scry["name"],
                "produces": sorted(cdm.land_color_sources(scry, deck_ci)),
            })
    return weak


def render_text(report: dict, top: int) -> str:
    lines: list[str] = []
    a = report["audit"]
    lines.append(f"Manabase audit — {report['deck_id']} (CI: {''.join(report['color_identity'])})")
    lines.append(
        f"  lands {a['inputs']['total_lands']} (target {a['inputs']['target_lands']})"
        f" | untapped {a['inputs']['untapped_lands']}"
        f" | fetch {a['inputs']['fetch_lands']}"
        f" | manabase_health {a['score']}"
    )
    lines.append(f"  pip census: " + "  ".join(
        f"{c}:{n}" for c, n in report["pip_census"].items()))
    reqs = a["inputs"]["color_requirements"]
    if reqs:
        lines.append("  Karsten: " + "  ".join(
            f"{c} {v['actual']}/{v['required']}" + (" DEFICIT" if v["ratio"] < 1 else "")
            for c, v in sorted(reqs.items())))

    if report["weak_current_lands"]:
        lines.append("\nCurrent lands entering tapped unconditionally (swap fodder):")
        for w in report["weak_current_lands"]:
            lines.append(f"  - {w['name']} ({''.join(w['produces']) or 'none'})")

    lines.append(f"\nOwned fixing lands not in deck (top {top} of {len(report['fixing'])}):")
    for r in report["fixing"][:top]:
        lock = "free" if r["free_copies"] > 0 else f"LOCKED: {', '.join(r['locked_by'])}"
        typed = f" typed[{'/'.join(r['typed'])}]" if r["typed"] else ""
        fetch = " fetch" if r["fetch"] else ""
        restricted = " RESTRICTED" if r.get("restricted") else ""
        rate = f"  edhrec {r['edhrec_rate']:.0f}%" if r.get("edhrec_rate") is not None else ""
        lines.append(
            f"  {r['score']:>3}  {r['name']}  ({''.join(r['produces']) or '-'},"
            f" {r['etb']}{typed}{fetch}{restricted})  x{r['owned']} {lock}{rate}"
        )
    if report["utility"]:
        lines.append(f"\nOwned utility lands (no in-CI colored production, top 10 of {len(report['utility'])}):")
        for r in report["utility"][:10]:
            lock = "free" if r["free_copies"] > 0 else f"LOCKED: {', '.join(r['locked_by'])}"
            rate = f"  edhrec {r['edhrec_rate']:.0f}%" if r.get("edhrec_rate") is not None else ""
            lines.append(f"  {r['score']:>3}  {r['name']}  ({r['etb']})  x{r['owned']} {lock}{rate}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck", required=True, help="deck id (data/commanders/{id})")
    ap.add_argument("--deck-file", help="alternate deck.json path (historical snapshot)")
    ap.add_argument("--top", type=int, default=40, help="fixing candidates to display")
    ap.add_argument("--json", action="store_true", help="emit full JSON report")
    args = ap.parse_args(argv)

    deck_path = Path(args.deck_file) if args.deck_file else DECKS_DIR / args.deck / "deck.json"
    if not deck_path.exists():
        print(f"unknown deck / missing file: {deck_path}", file=sys.stderr)
        return 1
    deck = json.loads(deck_path.read_text())

    mirror, _ = cdm.load_mirror()
    deck_ci = cdm.commander_color_identity(deck, mirror)
    audit = cdm.manabase_health(deck, mirror, deck_ci)

    reqs = audit["inputs"]["color_requirements"]
    deficit_colors = {c for c, v in reqs.items() if v["ratio"] < 1}

    census = pip_census(deck, mirror, deck_ci)
    owned = load_owned_quantities()
    locks = load_locks(exclude_deck=args.deck)
    edhrec_rates, _ = gcp.load_edhrec_rates(args.deck)
    fixing, utility = discover_lands(
        deck, mirror, deck_ci, deficit_colors, owned, locks, census, edhrec_rates
    )

    report = {
        "deck_id": args.deck,
        "color_identity": sorted(deck_ci),
        "audit": audit,
        "pip_census": census,
        "deficit_colors": sorted(deficit_colors),
        "weak_current_lands": weak_current_lands(deck, mirror, deck_ci),
        "fixing": fixing,
        "utility": utility,
    }
    print(json.dumps(report, indent=2) if args.json else render_text(report, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

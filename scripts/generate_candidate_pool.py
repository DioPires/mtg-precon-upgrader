#!/usr/bin/env python3
"""Generate candidate pool for each commander deck.

Reads the local Scryfall mirror, applies archetype filters from the discovery
playbook, scores cards against deck criteria, and writes top-N candidates to
data/commanders/{id}/candidates.json.

DEC-90 phase 3.

Usage:
    python scripts/generate_candidate_pool.py [--deck DECK_ID | --all] [--limit N]
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auto_tag_roles import classify as classify_role

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMANDERS_DIR = DATA_DIR / "commanders"
PLAYBOOK_FILE = DATA_DIR / "discovery-playbook.json"
GAME_CHANGERS_FILE = DATA_DIR / "game-changers.json"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
MIRROR_META = PROJECT_ROOT / "priv_data" / "scryfall-oracle.meta.json"
OWNED_FILE = PROJECT_ROOT / "priv_data" / "owned_formatted.csv"

METHODOLOGY_VERSION = "candidate-pool-v2"
DEFAULT_LIMIT = 200

KEEP_FIELDS = (
    "name", "cmc", "mana_cost", "type_line", "oracle_text",
)


def load_owned() -> set[str]:
    if not OWNED_FILE.exists():
        return set()
    owned = set()
    with open(OWNED_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if name:
                owned.add(name)
    return owned


def load_game_changers() -> set[str]:
    if not GAME_CHANGERS_FILE.exists():
        return set()
    data = json.loads(GAME_CHANGERS_FILE.read_text())
    if isinstance(data, list):
        return set(data)
    if isinstance(data, dict):
        # accept {"cards": [...]} or list under another key
        for v in data.values():
            if isinstance(v, list):
                return set(v)
    return set()


def compile_archetype(arch: dict) -> dict:
    return {
        **arch,
        "_compiled": [re.compile(p, re.IGNORECASE) for p in arch.get("oracle_patterns", [])],
        "_anti_compiled": [re.compile(p, re.IGNORECASE) for p in arch.get("anti_patterns", [])],
        "_staples": set(arch.get("staples", [])),
        "_type_constraints": [t.lower() for t in arch.get("type_constraints", [])],
    }


def card_oracle_blob(card: dict) -> str:
    """Concatenate oracle text from main face + faces (DFCs)."""
    parts = []
    if card.get("oracle_text"):
        parts.append(card["oracle_text"])
    for face in card.get("card_faces", []) or []:
        if face.get("oracle_text"):
            parts.append(face["oracle_text"])
    return "\n".join(parts)


def card_type_blob(card: dict) -> str:
    parts = []
    if card.get("type_line"):
        parts.append(card["type_line"])
    for face in card.get("card_faces", []) or []:
        if face.get("type_line"):
            parts.append(face["type_line"])
    return " | ".join(parts).lower()


def color_identity_subset(card_ci: list[str], deck_ci: set[str]) -> bool:
    return set(card_ci or []).issubset(deck_ci)


def archetype_match_score(card_oracle: str, card_type: str, archetype: dict) -> tuple[int, list[str]]:
    """Return (matches_count, matched_pattern_names). Anti-patterns short-circuit to (-1, ...)."""
    for anti in archetype["_anti_compiled"]:
        if anti.search(card_oracle):
            return -1, []
    matches = []
    for compiled, raw in zip(archetype["_compiled"], archetype.get("oracle_patterns", [])):
        if compiled.search(card_oracle):
            matches.append(raw)
    if archetype["_type_constraints"]:
        if not any(tc in card_type for tc in archetype["_type_constraints"]):
            matches.append("__type_match_missing__")
            matches.pop()
    return len(matches), matches


def score_card(
    card: dict,
    archetypes: list[dict],
    deck_avg_cmc: float,
    decklist_names: set[str],
    owned: set[str],
    game_changers: set[str],
    bracket: int,
) -> tuple[float, dict, list[str]]:
    """Return (score, breakdown, matched_archetypes)."""
    oracle = card_oracle_blob(card).lower()
    type_blob = card_type_blob(card)
    name = card.get("name", "")

    # Anti-pattern disqualification across any archetype
    archetype_hits: list[tuple[str, float]] = []  # (archetype_name, per-archetype score)
    pattern_score = 0.0
    total_patterns = 0
    type_constraint_satisfied = False
    type_constraint_required = False

    for arch in archetypes:
        for anti in arch["_anti_compiled"]:
            if anti.search(oracle):
                return 0.0, {"disqualified": "anti-pattern", "archetype": arch["name"]}, []

        if arch["_type_constraints"]:
            type_constraint_required = True
            if any(tc in type_blob for tc in arch["_type_constraints"]):
                type_constraint_satisfied = True

        local_matches = 0
        for compiled in arch["_compiled"]:
            if compiled.search(oracle):
                local_matches += 1
        is_staple = name in arch["_staples"]
        if local_matches > 0 or is_staple:
            n_patterns = len(arch["_compiled"])
            arch_strength = float(local_matches)
            if is_staple:
                arch_strength = max(arch_strength, n_patterns * 0.5)
            archetype_hits.append((arch["name"], arch_strength))
            pattern_score += local_matches
            total_patterns += n_patterns
            if is_staple:
                # staples always count for at least 50% of pattern score
                pattern_score = max(pattern_score, total_patterns * 0.5)

    if not archetype_hits:
        return 0.0, {"disqualified": "no archetype match"}, []
    # Sort matched archetypes by per-archetype strength desc, preserving order for ties
    archetype_hits.sort(key=lambda t: -t[1])
    matched_archetypes = [n for n, _ in archetype_hits]
    if type_constraint_required and not type_constraint_satisfied:
        # Voltron archetype with type_constraints requires Equipment/Aura
        return 0.0, {"disqualified": "type constraint not satisfied"}, []

    # 1. Keyword density (0–40)
    density = (pattern_score / total_patterns) if total_patterns else 0.0
    density_score = min(40.0, density * 40.0)

    # 2. CMC fit (0–20)
    cmc = card.get("cmc") or 0
    if isinstance(cmc, str):
        try:
            cmc = float(cmc)
        except ValueError:
            cmc = 0
    cmc_distance = abs(cmc - deck_avg_cmc)
    cmc_score = max(0.0, 20.0 * (1.0 - cmc_distance / 8.0))

    # 3. Owned (0–15)
    owned_score = 15.0 if name in owned else 0.0

    # 4. Game Changer × bracket (0–15)
    is_gc = name in game_changers
    if not is_gc:
        gc_score = 15.0
    elif bracket >= 5:
        gc_score = 10.0
    else:
        gc_score = 0.0

    # 5. Already-in-decklist demotion: cap total at 5
    base_total = density_score + cmc_score + owned_score + gc_score
    if name in decklist_names:
        return min(5.0, base_total), {
            "density": round(density_score, 1),
            "cmc_fit": round(cmc_score, 1),
            "owned": owned_score,
            "bracket_fit": gc_score,
            "decklist_demoted": True,
        }, matched_archetypes

    return round(base_total, 1), {
        "density": round(density_score, 1),
        "cmc_fit": round(cmc_score, 1),
        "owned": owned_score,
        "bracket_fit": gc_score,
        "decklist_demoted": False,
    }, matched_archetypes


def deck_avg_cmc(deck: dict, mirror_index: dict[str, dict]) -> float:
    cmcs = []
    for entry in deck.get("decklist", []):
        c = mirror_index.get(entry["name"])
        if c is None:
            continue
        type_line = (c.get("type_line") or "").lower()
        if "land" in type_line:
            continue
        cmc = c.get("cmc") or 0
        cmcs.append(cmc)
    return (sum(cmcs) / len(cmcs)) if cmcs else 3.0


def commander_color_identity(deck: dict, mirror_index: dict[str, dict]) -> set[str]:
    name = deck.get("commander", "")
    card = mirror_index.get(name)
    if card:
        return set(card.get("color_identity", []))
    # fallback: scan decklist for commander entry, infer from any mirrored card
    return set("WUBRG")


def load_gap_roles(deck_id: str) -> list[str]:
    """Read metrics.json for the deck and return ordered gap[].role list (worst first)."""
    metrics_path = COMMANDERS_DIR / deck_id / "metrics.json"
    if not metrics_path.exists():
        return []
    metrics = json.loads(metrics_path.read_text())
    return [g.get("role") for g in metrics.get("gaps", []) if g.get("role")]


def trim_card(
    card: dict,
    score: float,
    breakdown: dict,
    archetypes: list[str],
    owned: bool,
    gc: bool,
    deck_role: str | None,
    strategy_line: str | None,
    mitigates_gap: str | None,
) -> dict:
    out = {k: card.get(k) for k in KEEP_FIELDS if k in card}
    if "card_faces" in card:
        out["card_faces"] = [
            {k: f.get(k) for k in ("name", "mana_cost", "type_line", "oracle_text") if f.get(k)}
            for f in card["card_faces"]
        ]
    out["score"] = score
    out["score_breakdown"] = breakdown
    out["matched_archetypes"] = archetypes
    out["owned"] = owned
    out["game_changer"] = gc
    out["deck_role"] = deck_role
    out["strategy_line"] = strategy_line
    out["mitigates_gap"] = mitigates_gap
    return out


def generate_for_deck(
    deck_id: str,
    deck: dict,
    cards: list[dict],
    mirror_index: dict[str, dict],
    playbook: dict,
    owned: set[str],
    game_changers: set[str],
    mirror_updated_at: str,
    limit: int,
) -> dict:
    archetype_ids = deck.get("archetypes", [])
    if not archetype_ids:
        print(f"  [{deck_id}] no archetypes — skipping", file=sys.stderr)
        return None

    archetypes = [compile_archetype(playbook["archetypes"][a]) for a in archetype_ids]
    deck_ci = commander_color_identity(deck, mirror_index)
    avg_cmc = deck_avg_cmc(deck, mirror_index)
    decklist_names = {e["name"] for e in deck.get("decklist", [])}
    bracket_raw = deck.get("bracket", 4)
    try:
        bracket = int(str(bracket_raw).strip())
    except (TypeError, ValueError):
        bracket = 4

    candidates = []
    commander_name = deck.get("commander", "")

    for card in cards:
        if card.get("name") == commander_name:
            continue
        type_line = (card.get("type_line") or "").lower()
        if "basic" in type_line and "land" in type_line:
            continue
        if not color_identity_subset(card.get("color_identity", []), deck_ci):
            continue

        score, breakdown, matched = score_card(
            card, archetypes, avg_cmc, decklist_names, owned, game_changers, bracket
        )
        if score <= 0:
            continue

        candidates.append((score, card, breakdown, matched))

    candidates.sort(key=lambda t: (-t[0], t[1].get("name", "")))
    top = candidates[:limit]

    gap_roles = load_gap_roles(deck_id)
    gap_role_set = set(gap_roles)

    enriched = []
    for s, c, b, m in top:
        role, _conf = classify_role(c)
        strategy_line = m[0] if m else None
        mitigates = role if role and role in gap_role_set else None
        enriched.append(
            trim_card(
                c, s, b, m,
                c.get("name") in owned,
                c.get("name") in game_changers,
                role,
                strategy_line,
                mitigates,
            )
        )

    output = {
        "version": 1,
        "methodology": METHODOLOGY_VERSION,
        "deck_id": deck_id,
        "commander": commander_name,
        "archetypes": archetype_ids,
        "deck_avg_cmc": round(avg_cmc, 2),
        "deck_color_identity": sorted(deck_ci),
        "bracket": bracket,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scryfall_mirror_updated_at": mirror_updated_at,
        "deck_gaps": gap_roles,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }
    return output


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate per-deck candidate pools")
    parser.add_argument("--deck", help="Single deck id; default is --all")
    parser.add_argument("--all", action="store_true", help="Process every deck")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Top-N candidates per deck (default {DEFAULT_LIMIT})")
    args = parser.parse_args(argv)

    if not MIRROR_FILE.exists():
        print(f"Mirror missing: {MIRROR_FILE}. Run scripts/refresh_scryfall_mirror.py first.", file=sys.stderr)
        return 1
    if not PLAYBOOK_FILE.exists():
        print(f"Playbook missing: {PLAYBOOK_FILE}.", file=sys.stderr)
        return 1

    print("Loading mirror...", file=sys.stderr)
    cards = json.loads(MIRROR_FILE.read_text())
    mirror_index = {c["name"]: c for c in cards}
    mirror_meta = json.loads(MIRROR_META.read_text()) if MIRROR_META.exists() else {}
    mirror_updated_at = mirror_meta.get("scryfall_updated_at", "unknown")

    playbook = json.loads(PLAYBOOK_FILE.read_text())
    owned = load_owned()
    game_changers = load_game_changers()

    print(f"Mirror: {len(cards):,} cards | Owned: {len(owned):,} | GC: {len(game_changers):,}", file=sys.stderr)

    if args.deck:
        deck_ids = [args.deck]
    elif args.all:
        deck_ids = sorted(p.parent.name for p in COMMANDERS_DIR.glob("*/deck.json"))
    else:
        parser.print_help()
        return 2

    for deck_id in deck_ids:
        deck_path = COMMANDERS_DIR / deck_id / "deck.json"
        if not deck_path.exists():
            print(f"  [{deck_id}] not found", file=sys.stderr)
            continue
        deck = json.loads(deck_path.read_text())
        out = generate_for_deck(
            deck_id, deck, cards, mirror_index, playbook,
            owned, game_changers, mirror_updated_at, args.limit,
        )
        if out is None:
            continue

        out_path = COMMANDERS_DIR / deck_id / "candidates.json"
        existing = json.loads(out_path.read_text()) if out_path.exists() else None
        # idempotency: skip write if mirror, methodology, archetypes, decklist unchanged AND existing candidates identical
        if (
            existing
            and existing.get("scryfall_mirror_updated_at") == out["scryfall_mirror_updated_at"]
            and existing.get("methodology") == out["methodology"]
            and existing.get("deck_gaps") == out.get("deck_gaps")
        ):
            existing_names = [c.get("name") for c in existing.get("candidates", [])]
            new_names = [c.get("name") for c in out["candidates"]]
            if existing_names == new_names:
                print(f"  [{deck_id}] no change ({len(new_names)} candidates).", file=sys.stderr)
                continue

        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        top = out["candidates"][:1]
        top_summary = f", top score {top[0]['score']:.1f}" if top else ""
        print(f"  [{deck_id}] wrote {len(out['candidates'])} candidates{top_summary}.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

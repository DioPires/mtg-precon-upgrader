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
import statistics
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

METHODOLOGY_VERSION = "candidate-pool-v4"
DEFAULT_LIMIT = 200
SATURATION_THRESHOLD = 8
SATURATION_FLOOR = 0.35
ASYMMETRIC_ONLY_MULTIPLIER = 0.55
ARCHETYPE_POSITION_WEIGHTS = (1.0, 0.5, 0.25)
ROLE_SATURATION_THRESHOLD = 8
ROLE_REDUNDANCY_FLOOR = 0.65

TOKEN_ENTRY_MISMATCH = re.compile(
    r"tokens? you control (?:that )?entered this turn|whenever [^.]*tokens? enters?",
    re.IGNORECASE,
)
OFF_TRIBE_AMASS = re.compile(r"\bamass zombies?\b", re.IGNORECASE)
SACRIFICE_CREATURE = re.compile(r"sacrifice (?:a |another |target |this )?creature", re.IGNORECASE)
SELF_DEATH_TRIGGER = re.compile(r"when(?:ever)? (?:this creature|[^.]{0,40}) dies", re.IGNORECASE)
SYMMETRIC_REANIMATION = re.compile(
    r"each player exiles all creature cards.*sacrifices all creatures.*puts all cards",
    re.IGNORECASE | re.DOTALL,
)
EACH_PLAYER_EFFECT = re.compile(
    r"\beach player(?:'s)?\b|\beach opponent and you\b|\bwhenever a player\b",
    re.IGNORECASE,
)
SYMMETRIC_LIFEGAIN_LOCK = re.compile(
    r"\bplayers? (?:can't|cannot) gain life\b|\bif a player would gain life\b",
    re.IGNORECASE,
)
SYMMETRIC_LAND_ENTRY = re.compile(
    r"\bwhenever (?:a|one or more) lands? enters? the battlefield\b",
    re.IGNORECASE,
)
OPPONENT_LAND_ENTRY = re.compile(
    r"\bwhenever (?:a|one or more) lands? enters? the battlefield under an opponent's control\b",
    re.IGNORECASE,
)

KEEP_FIELDS = (
    "name", "cmc", "mana_cost", "type_line", "oracle_text",
)


def front_face(name: str) -> str:
    """Mirror indexes DFCs as 'Front // Back'; deck.json decklists use front-face names."""
    return name.split(" // ", 1)[0]


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


def archetype_raw_strength(
    card_oracle: str,
    card_type: str,
    card_name: str,
    archetype: dict,
) -> tuple[float, int]:
    """Return (raw pattern strength, pattern denominator) for one archetype."""
    for anti in archetype["_anti_compiled"]:
        if anti.search(card_oracle):
            return -1.0, len(archetype["_compiled"])
    if archetype["_type_constraints"] and not any(tc in card_type for tc in archetype["_type_constraints"]):
        return 0.0, len(archetype["_compiled"])

    local_matches = sum(1 for compiled in archetype["_compiled"] if compiled.search(card_oracle))
    is_staple = card_name in archetype["_staples"]
    if local_matches <= 0 and not is_staple:
        return 0.0, len(archetype["_compiled"])

    strength = float(local_matches)
    if is_staple:
        strength = max(strength, len(archetype["_compiled"]) * 0.5)
    return strength, len(archetype["_compiled"])


def saturation_multiplier(match_count: int) -> float:
    """Diminish same-archetype density once a deck is already deep on that tag."""
    if match_count <= SATURATION_THRESHOLD:
        return 1.0
    return max(SATURATION_FLOOR, SATURATION_THRESHOLD / float(match_count))


def archetype_position_weight(index: int) -> float:
    """Position-1 archetype gets full weight; later positions decay."""
    if index < len(ARCHETYPE_POSITION_WEIGHTS):
        return ARCHETYPE_POSITION_WEIGHTS[index]
    return ARCHETYPE_POSITION_WEIGHTS[-1]


def build_position_weights(archetypes: list[dict]) -> dict[str, float]:
    """Map compiled-archetype name → position weight (1.0×, 0.5×, 0.25×, ...)."""
    return {arch["name"]: archetype_position_weight(i) for i, arch in enumerate(archetypes)}


def deck_archetype_match_counts(
    deck: dict,
    mirror_index: dict[str, dict],
    archetypes: list[dict],
) -> dict[str, int]:
    counts = {arch["name"]: 0 for arch in archetypes}
    for entry in deck.get("decklist", []):
        card = mirror_index.get(entry.get("name", ""))
        if not card and " // " in entry.get("name", ""):
            card = mirror_index.get(entry["name"].split(" // ", 1)[0])
        if not card:
            continue
        oracle = card_oracle_blob(card).lower()
        type_blob = card_type_blob(card)
        quantity = max(1, int(entry.get("quantity") or 1))
        for arch in archetypes:
            strength, _denom = archetype_raw_strength(oracle, type_blob, card.get("name", ""), arch)
            if strength > 0:
                counts[arch["name"]] += quantity
    return counts


def deck_context(
    deck: dict,
    mirror_index: dict[str, dict],
    archetype_ids: list[str],
    archetype_counts: dict[str, int],
) -> dict:
    creature_count = 0
    sac_outlet_count = 0
    for entry in deck.get("decklist", []):
        card = mirror_index.get(entry.get("name", ""))
        if not card and " // " in entry.get("name", ""):
            card = mirror_index.get(entry["name"].split(" // ", 1)[0])
        if not card:
            continue
        quantity = max(1, int(entry.get("quantity") or 1))
        type_blob = card_type_blob(card)
        oracle = card_oracle_blob(card)
        if "creature" in type_blob:
            creature_count += quantity
        if SACRIFICE_CREATURE.search(oracle):
            sac_outlet_count += quantity

    return {
        "archetype_ids": set(archetype_ids),
        "archetype_counts": archetype_counts,
        "asymmetric_only": bool(deck.get("asymmetric_only")),
        "creature_count": creature_count,
        "sac_outlet_count": sac_outlet_count,
    }


def has_symmetric_effect(card_oracle: str) -> bool:
    """Return true for broad symmetric templates an asymmetric-only deck avoids."""
    if EACH_PLAYER_EFFECT.search(card_oracle):
        return True
    if SYMMETRIC_LIFEGAIN_LOCK.search(card_oracle):
        return True
    if SYMMETRIC_LAND_ENTRY.search(card_oracle) and not OPPONENT_LAND_ENTRY.search(card_oracle):
        return True
    return False


def detect_anti_synergy(card: dict, context: dict) -> list[dict]:
    """Return deterministic deck-context anti-synergy signals with point penalties."""
    oracle = card_oracle_blob(card)
    archetype_ids = context["archetype_ids"]
    flags: list[dict] = []

    if (
        ("amass-orcs" in archetype_ids or "amass-armies" in archetype_ids)
        and TOKEN_ENTRY_MISMATCH.search(oracle)
    ):
        flags.append({
            "name": "amass-token-entry-mismatch",
            "penalty": 12.0,
        })
    if "amass-orcs" in archetype_ids and OFF_TRIBE_AMASS.search(oracle):
        flags.append({
            "name": "off-tribe-amass",
            "penalty": 8.0,
        })
    if context["sac_outlet_count"] < 3 and SACRIFICE_CREATURE.search(oracle):
        flags.append({
            "name": "low-sacrifice-support",
            "penalty": 12.0,
        })
    if context["sac_outlet_count"] < 3 and SELF_DEATH_TRIGGER.search(oracle):
        flags.append({
            "name": "death-trigger-low-sacrifice-support",
            "penalty": 8.0,
        })
    if context["creature_count"] < 25 and SYMMETRIC_REANIMATION.search(oracle):
        flags.append({
            "name": "creature-light-symmetric-reanimation",
            "penalty": 15.0,
        })
    if context.get("asymmetric_only") and has_symmetric_effect(oracle):
        flags.append({
            "name": "symmetric-effect-in-asymmetric-only",
            "multiplier": ASYMMETRIC_ONLY_MULTIPLIER,
        })

    return flags


def score_card(
    card: dict,
    archetypes: list[dict],
    deck_avg_cmc: float,
    decklist_names: set[str],
    owned: set[str],
    game_changers: set[str],
    bracket: int,
    context: dict | None = None,
    position_weights: dict[str, float] | None = None,
    role_pool: dict[str, dict] | None = None,
) -> tuple[float, dict, list[str]]:
    """Return (score, breakdown, matched_archetypes)."""
    oracle = card_oracle_blob(card).lower()
    type_blob = card_type_blob(card)
    name = card.get("name", "")

    # Anti-pattern disqualification across any archetype
    archetype_hits: list[tuple[str, float]] = []  # (archetype_name, per-archetype score)
    raw_pattern_score = 0.0
    adjusted_pattern_score = 0.0
    total_patterns = 0
    type_constraint_satisfied = False
    type_constraint_required = False
    saturated_archetypes = []
    position_weights_applied: dict[str, float] = {}

    for arch in archetypes:
        for anti in arch["_anti_compiled"]:
            if anti.search(oracle):
                return 0.0, {"disqualified": "anti-pattern", "archetype": arch["name"]}, []

        if arch["_type_constraints"]:
            type_constraint_required = True
            if any(tc in type_blob for tc in arch["_type_constraints"]):
                type_constraint_satisfied = True

        arch_strength, n_patterns = archetype_raw_strength(oracle, type_blob, name, arch)
        if arch_strength > 0:
            archetype_hits.append((arch["name"], arch_strength))
            raw_pattern_score += arch_strength
            total_patterns += n_patterns
            match_count = (context or {}).get("archetype_counts", {}).get(arch["name"], 0)
            sat_mult = saturation_multiplier(match_count)
            pos_mult = (position_weights or {}).get(arch["name"], 1.0)
            adjusted_pattern_score += arch_strength * sat_mult * pos_mult
            if sat_mult < 1.0:
                saturated_archetypes.append({
                    "archetype": arch["name"],
                    "deck_matches": match_count,
                    "multiplier": round(sat_mult, 2),
                })
            if pos_mult < 1.0:
                position_weights_applied[arch["name"]] = round(pos_mult, 2)

    if not archetype_hits:
        return 0.0, {"disqualified": "no archetype match"}, []
    # Sort matched archetypes by per-archetype strength desc, preserving order for ties
    archetype_hits.sort(key=lambda t: -t[1])
    matched_archetypes = [n for n, _ in archetype_hits]
    if type_constraint_required and not type_constraint_satisfied:
        # Voltron archetype with type_constraints requires Equipment/Aura
        return 0.0, {"disqualified": "type constraint not satisfied"}, []

    # 1. Keyword density (0–40)
    raw_density = (raw_pattern_score / total_patterns) if total_patterns else 0.0
    density = (adjusted_pattern_score / total_patterns) if total_patterns else 0.0
    raw_density_score = min(40.0, raw_density * 40.0)
    density_score = min(40.0, density * 40.0)
    saturation_penalty = max(0.0, raw_density_score - density_score)

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
    raw_total = density_score + cmc_score + owned_score + gc_score
    anti_synergy = detect_anti_synergy(card, context) if context else []
    flat_anti_synergy_penalty = sum(flag.get("penalty", 0.0) for flag in anti_synergy)
    anti_synergy_multiplier = 1.0
    for flag in anti_synergy:
        anti_synergy_multiplier *= flag.get("multiplier", 1.0)
    base_total = max(0.0, (raw_total - flat_anti_synergy_penalty) * anti_synergy_multiplier)
    anti_synergy_penalty = max(0.0, raw_total - base_total)
    in_decklist = front_face(name) in decklist_names
    breakdown = {
        "density": round(density_score, 1),
        "cmc_fit": round(cmc_score, 1),
        "owned": owned_score,
        "bracket_fit": gc_score,
        "decklist_demoted": in_decklist,
    }
    if saturation_penalty > 0:
        breakdown["density_raw"] = round(raw_density_score, 1)
        breakdown["saturation_penalty"] = round(saturation_penalty, 1)
        breakdown["saturated_archetypes"] = saturated_archetypes
    if position_weights_applied:
        breakdown["archetype_position_weights"] = position_weights_applied
    if anti_synergy_penalty > 0:
        breakdown["anti_synergy_penalty"] = round(anti_synergy_penalty, 1)
        if anti_synergy_multiplier < 1.0:
            breakdown["anti_synergy_multiplier"] = round(anti_synergy_multiplier, 2)
        breakdown["anti_synergy_flags"] = []
        multiplier_base = max(0.0, raw_total - flat_anti_synergy_penalty)
        for flag in anti_synergy:
            visible = {"name": flag["name"]}
            if "penalty" in flag:
                visible["penalty"] = flag["penalty"]
            if "multiplier" in flag:
                visible["multiplier"] = flag["multiplier"]
                visible["penalty"] = round(multiplier_base * (1.0 - flag["multiplier"]), 1)
                multiplier_base *= flag["multiplier"]
            breakdown["anti_synergy_flags"].append(visible)

    if role_pool is not None and base_total > 0:
        cand_role, _conf = classify_role(card)
        if cand_role:
            bucket = role_pool.get(cand_role)
            if (
                bucket
                and bucket.get("count", 0) >= ROLE_SATURATION_THRESHOLD
                and base_total < bucket.get("median", 0.0)
            ):
                demoted_total = base_total * ROLE_REDUNDANCY_FLOOR
                breakdown["redundancy_below_roster_median"] = {
                    "role": cand_role,
                    "bucket_count": bucket["count"],
                    "bucket_median": bucket["median"],
                    "multiplier": ROLE_REDUNDANCY_FLOOR,
                    "penalty": round(base_total - demoted_total, 1),
                }
                base_total = demoted_total

    if in_decklist:
        return min(5.0, base_total), breakdown, matched_archetypes

    return round(base_total, 1), breakdown, matched_archetypes


def compute_role_pool_scores(
    deck: dict,
    mirror_index: dict[str, dict],
    archetypes: list[dict],
    deck_avg_cmc_value: float,
    owned: set[str],
    game_changers: set[str],
    bracket: int,
    context: dict,
    position_weights: dict[str, float],
) -> dict[str, dict]:
    """For each in-deck primary_role, compute count + median candidate-pool score.

    Each in-deck card is scored as if it were a fresh candidate (no decklist
    demotion, no role-redundancy demote) so the median is a comparable
    quality benchmark for incoming candidates. Median includes zero-scored
    cards because those are still part of the role bucket the candidate
    competes against.
    """
    by_role: dict[str, list[float]] = {}
    for entry in deck.get("decklist", []):
        role = entry.get("primary_role")
        if not role:
            continue
        card_name = entry.get("name", "")
        card = mirror_index.get(card_name)
        if not card and " // " in card_name:
            card = mirror_index.get(card_name.split(" // ", 1)[0])
        if not card:
            continue
        score, _bd, _m = score_card(
            card,
            archetypes,
            deck_avg_cmc_value,
            decklist_names=set(),
            owned=owned,
            game_changers=game_changers,
            bracket=bracket,
            context=context,
            position_weights=position_weights,
            role_pool=None,
        )
        by_role.setdefault(role, []).append(score)

    return {
        role: {"count": len(scores), "median": round(statistics.median(scores), 1)}
        for role, scores in by_role.items()
        if scores
    }


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
    archetype_counts = deck_archetype_match_counts(deck, mirror_index, archetypes)
    context = deck_context(deck, mirror_index, archetype_ids, archetype_counts)
    deck_ci = commander_color_identity(deck, mirror_index)
    avg_cmc = deck_avg_cmc(deck, mirror_index)
    decklist_names = {front_face(e["name"]) for e in deck.get("decklist", [])}
    bracket_raw = deck.get("bracket", 4)
    try:
        bracket = int(str(bracket_raw).strip())
    except (TypeError, ValueError):
        bracket = 4

    position_weights = build_position_weights(archetypes)
    role_pool = compute_role_pool_scores(
        deck, mirror_index, archetypes, avg_cmc,
        owned, game_changers, bracket, context, position_weights,
    )

    candidates = []
    commander_name = deck.get("commander", "")

    for card in cards:
        if front_face(card.get("name", "")) == front_face(commander_name):
            continue
        type_line = (card.get("type_line") or "").lower()
        if "basic" in type_line and "land" in type_line:
            continue
        if not color_identity_subset(card.get("color_identity", []), deck_ci):
            continue

        score, breakdown, matched = score_card(
            card, archetypes, avg_cmc, decklist_names, owned, game_changers, bracket,
            context, position_weights=position_weights, role_pool=role_pool,
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
        "asymmetric_only": bool(deck.get("asymmetric_only")),
        "deck_avg_cmc": round(avg_cmc, 2),
        "deck_color_identity": sorted(deck_ci),
        "bracket": bracket,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scryfall_mirror_updated_at": mirror_updated_at,
        "deck_gaps": gap_roles,
        "deck_archetype_match_counts": archetype_counts,
        "archetype_position_weights": {
            arch["name"]: position_weights[arch["name"]] for arch in archetypes
        },
        "role_pool": role_pool,
        "saturation": {
            "threshold": SATURATION_THRESHOLD,
            "floor": SATURATION_FLOOR,
        },
        "role_redundancy": {
            "threshold": ROLE_SATURATION_THRESHOLD,
            "floor": ROLE_REDUNDANCY_FLOOR,
        },
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
            and existing.get("asymmetric_only") == out.get("asymmetric_only")
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

#!/usr/bin/env python3
"""Generate candidate pool for each commander deck.

Reads the local Scryfall mirror, applies archetype filters from the discovery
playbook, scores cards against deck criteria, and writes top-N candidates to
data/commanders/{id}/candidates.json. Cards named in the deck's optional
`candidate_pins` list are seated too, at their score-order position, with
`"pinned": true` (DEC-992). A gap role of metrics.json with fewer than
GAP_SEAT_FLOOR pool cards gets cards of that role seated after the top N, with
`"seeded_for_gap": "<role>"` (DEC-1078).

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
EDHREC_RATES_DIR = PROJECT_ROOT / "priv_data" / "edhrec"

METHODOLOGY_VERSION = "candidate-pool-v7"
DEFAULT_LIMIT = 200
SATURATION_THRESHOLD = 8
SATURATION_FLOOR = 0.35
ASYMMETRIC_ONLY_MULTIPLIER = 0.55
ARCHETYPE_POSITION_WEIGHTS = (1.0, 0.5, 0.25)
ROLE_SATURATION_THRESHOLD = 8
ROLE_REDUNDANCY_FLOOR = 0.65
# DEC-410: manually recorded EDHREC inclusion rates (see docs/discovery-playbook.md).
# min(EDHREC_MAX, rate / EDHREC_RATE_SATURATION * EDHREC_MAX): 40% -> 16 (> owned 15),
# 50%+ -> 20. Half the density ceiling so archetype fit stays dominant.
EDHREC_MAX = 20.0
EDHREC_RATE_SATURATION = 50.0
# DEC-477 (DEC-474 L1): tiebreaker for opponent-scaled triggers — must stay below
# owned (15) and EDHREC (20), and at 1/8 of the density ceiling (40).
MULTIPLAYER_SCALED_BOOST = 5.0
# DEC-1078: each role gap of metrics.json gets pool cards of that role up to this
# count, seated after the top N. A seat changes no score.
GAP_SEAT_FLOOR = 5

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
# DEC-477: opponent-scaled trigger templates. Per-opponent effects and opponent-turn
# triggers ("each opponent", incl. "each opponent's upkeep/turn"), opponent-action
# triggers ("whenever an opponent"), and opponent-permanent event triggers whose
# trigger subject is opponent-owned (Authority of the Consuls class). The comma-free
# {0,60} window keeps the opponent scope inside the trigger condition, so
# "whenever this creature attacks, ... an opponent controls" does not match.
MULTIPLAYER_SCALED_TRIGGER = re.compile(
    r"\beach opponent\b(?! and you\b)"
    r"|\beach of your opponents\b"
    r"|\bwhenever an opponent\b"
    r"|\bwhenever [^.,\n;]{0,60}?(?:an opponent controls|your opponents control"
    r"|under an opponent's control|you don't control)\b"
    r"|\bduring an opponent's turn\b",
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


def load_edhrec_rates(deck_id: str) -> tuple[dict[str, float], dict | None]:
    """Load manually recorded EDHREC inclusion rates for a deck.

    Returns (rates, meta). Rates map card name (front-face) -> inclusion percent
    (0-100). Missing file is normal — automated EDHREC fetching is barred by ToS
    (DEC-312); rates are recorded by hand during the mandatory closing diff
    (DEC-402) into priv_data/edhrec/{deck_id}.json.
    """
    path = EDHREC_RATES_DIR / f"{deck_id}.json"
    if not path.exists():
        return {}, None
    data = json.loads(path.read_text())
    rates = {}
    for name, rate in (data.get("rates") or {}).items():
        try:
            rates[name] = max(0.0, min(100.0, float(rate)))
        except (TypeError, ValueError):
            print(f"  [{deck_id}] edhrec-rates: non-numeric rate for {name!r} ignored", file=sys.stderr)
    meta = {
        "recorded_at": data.get("recorded_at"),
        "source": data.get("source"),
        "count": len(rates),
    }
    return rates, meta


def edhrec_rate_for(name: str, edhrec_rates: dict[str, float] | None) -> float | None:
    if not edhrec_rates:
        return None
    rate = edhrec_rates.get(name)
    if rate is None:
        rate = edhrec_rates.get(front_face(name))
    return rate


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
    edhrec_rates: dict[str, float] | None = None,
    archetype_gate: bool = True,
) -> tuple[float, dict, list[str]]:
    """Return (score, breakdown, matched_archetypes).

    With `archetype_gate=False` a card that matches no archetype scores without
    the density term instead of scoring 0 (DEC-1078 step 2 only).
    """
    oracle = card_oracle_blob(card).lower()
    type_blob = card_type_blob(card)
    name = card.get("name", "")

    # Anti-pattern disqualification across any archetype
    archetype_hits: list[tuple[str, float]] = []  # (archetype_name, per-archetype score)
    raw_pattern_score = 0.0
    adjusted_pattern_score = 0.0
    total_patterns = 0
    saturated_archetypes = []
    position_weights_applied: dict[str, float] = {}

    for arch in archetypes:
        for anti in arch["_anti_compiled"]:
            if anti.search(oracle):
                return 0.0, {"disqualified": "anti-pattern", "archetype": arch["name"]}, []

        # type_constraints gate their own archetype only (DEC-990): a card off the
        # constrained type gets no hit here but can still hit the deck's other archetypes.
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

    if not archetype_hits and archetype_gate:
        return 0.0, {"disqualified": "no archetype match"}, []
    # Sort matched archetypes by per-archetype strength desc, preserving order for ties
    archetype_hits.sort(key=lambda t: -t[1])
    matched_archetypes = [n for n, _ in archetype_hits]

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

    # 5. EDHREC inclusion (0–20): manually recorded rates only (DEC-410)
    edhrec_rate = edhrec_rate_for(name, edhrec_rates)
    edhrec_score = (
        min(EDHREC_MAX, edhrec_rate / EDHREC_RATE_SATURATION * EDHREC_MAX)
        if edhrec_rate is not None
        else 0.0
    )

    # 6. Multiplayer-scaling boost (DEC-477): deck-independent tiebreaker for
    # triggers that scale with opponent count in 4-player (fire up to 3x per
    # turn cycle vs the 1v1 read). Additive like EDHREC, so anti-synergy
    # penalties/multipliers and role-redundancy demotion compose over it.
    multiplayer_score = (
        MULTIPLAYER_SCALED_BOOST if MULTIPLAYER_SCALED_TRIGGER.search(oracle) else 0.0
    )

    # 7. Already-in-decklist demotion: cap total at 5
    raw_total = density_score + cmc_score + owned_score + gc_score + edhrec_score + multiplayer_score
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
    if edhrec_rate is not None:
        breakdown["edhrec"] = round(edhrec_score, 1)
        breakdown["edhrec_rate"] = edhrec_rate
    if multiplayer_score > 0:
        breakdown["multiplayer_scaled"] = multiplayer_score
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
    edhrec_rates: dict[str, float] | None = None,
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
            edhrec_rates=edhrec_rates,
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


def candidate_pin_names(deck_id: str, deck: dict) -> list[str]:
    """Return the card names in deck.json `candidate_pins` (DEC-992), in file order."""
    names: list[str] = []
    for item in deck.get("candidate_pins") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name.strip():
            print(f"  [{deck_id}] candidate-pin: entry without a name skipped: {item!r}", file=sys.stderr)
            continue
        if name.strip() not in names:
            names.append(name.strip())
    return names


def resolve_candidate_pins(
    deck_id: str,
    pin_names: list[str],
    candidates: list[tuple[float, dict, dict, list[str]]],
    mirror_index: dict[str, dict],
    deck_ci: set[str],
    decklist_names: set[str],
    commander_name: str,
) -> set[str]:
    """Return the mirror names of pinned cards to seat; warn and skip the rest.

    Pins add an entry; they change no score (DEC-992). A pin is skipped when the
    name is not in the mirror, the card is outside the colour identity, the card is
    the commander, the card is already in the decklist, or the card scores 0 for
    this deck. Each skip prints its own reason.
    """
    rank_by_name = {c.get("name"): i for i, (_s, c, _b, _m) in enumerate(candidates)}
    seated: set[str] = set()
    for pin in pin_names:
        card = mirror_index.get(pin) or next(
            (c for n, c in mirror_index.items() if front_face(n) == pin), None
        )
        if card is None:
            reason = "not in the Scryfall mirror"
        elif not color_identity_subset(card.get("color_identity", []), deck_ci):
            reason = f"outside the colour identity {''.join(sorted(deck_ci))}"
        elif front_face(card["name"]) == front_face(commander_name):
            reason = "is the commander"
        elif front_face(card["name"]) in decklist_names:
            reason = "already in the decklist"
        elif card["name"] not in rank_by_name:
            reason = "scores 0 for this deck"
        else:
            rank = rank_by_name[card["name"]]
            print(
                f"  [{deck_id}] candidate-pin: {pin!r} seated at rank {rank + 1} "
                f"(score {candidates[rank][0]:.1f}).",
                file=sys.stderr,
            )
            seated.add(card["name"])
            continue
        print(f"  [{deck_id}] candidate-pin: {pin!r} skipped: {reason}.", file=sys.stderr)
    return seated


def seat_gap_cards(
    deck_id: str,
    gap_roles: list[str],
    candidates: list[tuple[float, dict, dict, list[str]]],
    limit: int,
    pinned: set[str],
    decklist_names: set[str],
    gated: list[dict],
    score_without_gate,
    edhrec_rates: dict[str, float],
) -> tuple[dict[str, str], list[tuple[float, dict, dict, list[str]]]]:
    """Seat cards of each gap role until the pool holds GAP_SEAT_FLOOR of that role.

    Step 1 takes cards of the role below the cut, best score first. Step 2 runs
    only for a role that step 1 leaves under the floor: a card of the role in
    `gated` (no archetype match, listed on the deck's EDHREC page) scores without
    the density term, and the highest EDHREC rate goes first, then the name. A
    card in the decklist is not seated, as for a pin. Returns the seated names
    with their role, and the step-2 entries, which `candidates` does not hold.
    """
    role_of: dict[str, str | None] = {}

    def role(card: dict) -> str | None:
        name = card.get("name", "")
        if name not in role_of:
            role_of[name] = classify_role(card)[0]
        return role_of[name]

    below = candidates[limit:]
    pool = [c for _s, c, _b, _m in candidates[:limit]]
    pool += [c for _s, c, _b, _m in below if c.get("name") in pinned]
    seated: dict[str, str] = {}
    step2: list[tuple[float, dict, dict, list[str]]] = []
    for gap in gap_roles:
        before = sum(1 for c in pool if role(c) == gap)
        if before >= GAP_SEAT_FLOOR:
            continue
        count = before
        for _s, c, _b, _m in below:
            if count >= GAP_SEAT_FLOOR:
                break
            name = c.get("name", "")
            if name in pinned or front_face(name) in decklist_names or role(c) != gap:
                continue
            seated[name] = gap
            count += 1
        from_step1 = count - before
        if count < GAP_SEAT_FLOOR:
            listed = []
            for c in gated:
                if role(c) != gap or front_face(c.get("name", "")) in decklist_names:
                    continue
                score, breakdown, matched = score_without_gate(c)
                if score > 0:
                    listed.append((score, c, breakdown, matched))
            listed.sort(key=lambda t: (-edhrec_rate_for(t[1].get("name", ""), edhrec_rates), t[1].get("name", "")))
            for entry in listed[:GAP_SEAT_FLOOR - count]:
                seated[entry[1]["name"]] = gap
                step2.append(entry)
                count += 1
        print(
            f"  [{deck_id}] gap-seat: {gap} {before} -> {count} "
            f"({from_step1} below the cut, {count - before - from_step1} from the EDHREC page).",
            file=sys.stderr,
        )
    return seated, step2


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
    edhrec_rate: float | None,
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
    out["edhrec_rate"] = edhrec_rate
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

    edhrec_rates, edhrec_meta = load_edhrec_rates(deck_id)
    position_weights = build_position_weights(archetypes)
    role_pool = compute_role_pool_scores(
        deck, mirror_index, archetypes, avg_cmc,
        owned, game_changers, bracket, context, position_weights,
        edhrec_rates=edhrec_rates,
    )

    candidates = []
    # DEC-1078 step 2: cards that only the archetype gate keeps out, on the EDHREC page.
    gated = []
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
            edhrec_rates=edhrec_rates,
        )
        if score <= 0:
            if (
                breakdown.get("disqualified") == "no archetype match"
                and edhrec_rate_for(card.get("name", ""), edhrec_rates) is not None
            ):
                gated.append(card)
            continue

        candidates.append((score, card, breakdown, matched))

    candidates.sort(key=lambda t: (-t[0], t[1].get("name", "")))
    # DEC-992: pinned cards below the cut keep their score-order position.
    pinned = resolve_candidate_pins(
        deck_id, candidate_pin_names(deck_id, deck), candidates,
        mirror_index, deck_ci, decklist_names, commander_name,
    )

    gap_roles = load_gap_roles(deck_id)
    gap_role_set = set(gap_roles)
    seated, step2 = seat_gap_cards(
        deck_id, gap_roles, candidates, limit, pinned, decklist_names, gated,
        lambda card: score_card(
            card, archetypes, avg_cmc, decklist_names, owned, game_changers, bracket,
            context, position_weights=position_weights, role_pool=role_pool,
            edhrec_rates=edhrec_rates, archetype_gate=False,
        ),
        edhrec_rates,
    )
    # The top N never move: pins and gap seats follow them in score order.
    tail = [t for t in candidates[limit:] if t[1].get("name") in pinned or t[1].get("name") in seated]
    tail = sorted(tail + step2, key=lambda t: (-t[0], t[1].get("name", "")))
    top = candidates[:limit] + tail

    enriched = []
    for s, c, b, m in top:
        role, _conf = classify_role(c)
        strategy_line = m[0] if m else None
        mitigates = role if role and role in gap_role_set else None
        entry = trim_card(
            c, s, b, m,
            c.get("name") in owned,
            c.get("name") in game_changers,
            role,
            strategy_line,
            mitigates,
            edhrec_rate_for(c.get("name", ""), edhrec_rates),
        )
        if c.get("name") in pinned:
            entry["pinned"] = True
        if c.get("name") in seated:
            entry["seeded_for_gap"] = seated[c.get("name")]
        enriched.append(entry)

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
        "multiplayer_scaling": {
            "boost": MULTIPLAYER_SCALED_BOOST,
        },
        "edhrec_rates": (
            {**edhrec_meta, "max_boost": EDHREC_MAX, "rate_saturation": EDHREC_RATE_SATURATION}
            if edhrec_meta
            else None
        ),
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
            # the pinned and seeded_for_gap flags are compared too, so a change of a seat writes
            existing_names = [
                (c.get("name"), bool(c.get("pinned")), c.get("seeded_for_gap"))
                for c in existing.get("candidates", [])
            ]
            new_names = [
                (c.get("name"), bool(c.get("pinned")), c.get("seeded_for_gap"))
                for c in out["candidates"]
            ]
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

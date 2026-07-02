#!/usr/bin/env python3
"""DEC-90 P7.5 metrics computer.

Reads deck.json + Scryfall mirror + role tags and writes
data/commanders/{id}/metrics.json with the five deterministic metrics
defined in docs/deck-metrics.md, plus a derived gaps[] feed for P7.6/P7.7.

Usage:
    python scripts/compute_deck_metrics.py --deck DECK_ID
    python scripts/compute_deck_metrics.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIR = PROJECT_ROOT / "data" / "commanders"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
MIRROR_META = PROJECT_ROOT / "priv_data" / "scryfall-oracle.meta.json"

METHODOLOGY_VERSION = "deck-metrics-v2"

# DEC-308 — global_health weight options. Each tuple weights are
# (manabase, role, curve, interaction, cohesion, resilience). Sum = 1.0.
# The chosen option is committed below in DEFAULT_WEIGHT_OPTION after
# calibration; the rest stay available for `--calibrate` runs.
GLOBAL_WEIGHT_OPTIONS: dict[str, tuple[float, float, float, float, float, float]] = {
    "A": (0.25, 0.25, 0.15, 0.15, 0.10, 0.10),
    "B": (0.28, 0.28, 0.14, 0.14, 0.08, 0.08),
    "C": (0.30, 0.25, 0.15, 0.12, 0.08, 0.10),
}
DEFAULT_WEIGHT_OPTION = "A"

# DEC-389 — global_health_normalized scores every deck against this one fixed
# reference bracket's target tables, so cross-deck comparison doesn't mix bars
# (a bracket redeclaration alone must not move the normalized score).
NORMALIZED_REFERENCE_BRACKET = 3

VALID_ROLES = {
    "land", "ramp", "mana-fixing", "card-draw", "tutor",
    "removal-spot", "removal-board", "counterspell", "protection",
    "recursion", "payoff", "wincon", "engine", "threat", "utility",
}

# docs/deck-metrics.md — per-role targets per bracket
ROLE_TARGETS = {
    "ramp":          {3: 10, 4: 10, 5: 12},
    "card-draw":     {3:  8, 4: 10, 5: 12},
    "removal-spot":  {3:  6, 4:  8, 5:  8},
    "removal-board": {3:  2, 4:  3, 5:  3},
    "protection":    {3:  2, 4:  4, 5:  5},
    "tutor":         {3:  2, 4:  4, 5:  6},
    "wincon":        {3:  2, 4:  3, 5:  3},
    "counterspell":  {3:  4, 4:  6, 5:  8},
}

INTERACTION_TARGETS = {3: 10, 4: 14, 5: 18}

# Deck-level `wincon_style` adjusts the wincon row in role_coverage. See
# docs/deck-metrics.md §role_coverage_health/wincon_style for rationale.
#   - combo:            single assembly closes the game, target = 1
#   - value-incremental:engine *is* the closer; target = 1 with engines
#                       substituting for missing wincon-tagged cards
#   - discrete-threats: must threaten on multiple axes; target = 2
WINCON_STYLE_TARGET = {
    "combo": 1,
    "value-incremental": 1,
    "discrete-threats": 2,
}
WINCON_STYLE_ENGINE_SUB = {"value-incremental"}

# Curve targets keyed by archetype id. Multiple deck archetypes are averaged.
CURVE_TARGETS = {
    "ramp-big-mana": 4.2,
    "eldrazi-colorless": 4.2,
    "tokens-go-wide": 2.8,
    "aristocrats": 2.8,
    "voltron": 2.5,
    "infect-poison": 2.5,
    "graveyard-reanimator": 3.0,
    "spellslinger": 3.0,
}
DEFAULT_CURVE_TARGET = 3.2

COHESION_BASE_ROLES = {"payoff", "engine", "wincon", "threat"}

# DEC-308 — resilience_health targets keyed by deck-level `wincon_style`.
# Rationale lives in docs/deck-metrics.md §resilience_health.
RESILIENCE_RECURSION_TARGETS: dict[str | None, dict[int, int]] = {
    "combo":             {3: 1, 4: 2, 5: 2},
    "value-incremental": {3: 3, 4: 4, 5: 5},
    "discrete-threats":  {3: 2, 4: 3, 5: 3},
    "combat":            {3: 2, 4: 3, 5: 4},
    "drain":             {3: 2, 4: 3, 5: 4},
    "drain-x":           {3: 2, 4: 3, 5: 4},
    "mixed":             {3: 2, 4: 3, 5: 4},
    None:                {3: 2, 4: 3, 5: 4},
}
RESILIENCE_WINCON_LINE_FLOOR: dict[str | None, int] = {
    "combo": 1,
    "value-incremental": 1,
    "discrete-threats": 2,
    "combat": 1,
    "drain": 1,
    "drain-x": 1,
    "mixed": 1,
    None: 1,
}
RESILIENCE_PROTECTION_TARGETS = {3: 2, 4: 4, 5: 5}
RESILIENCE_GY_TARGET = 6
RESILIENCE_GY_ROLES = {"recursion", "engine"}

# DEC-311 — win_turn triple thresholds. Best floor MUST match DEC-309's
# PAYOFF_FLOOR (see scripts/validate_strategy_ceiling.py); both values are
# documented in docs/deck-metrics.md and data/bracket-philosophy.md.
WIN_TURN_BEST_THRESHOLD = 15.0
WIN_TURN_TYPICAL_THRESHOLD = 50.0
WIN_TURN_DRAG = {3: 0, 4: 1, 5: 2}

ARCHETYPE_COHESION_EXT = {
    "graveyard-reanimator": {"recursion"},
    "aristocrats": {"recursion"},
    "tokens-go-wide": {"utility"},
    "plus-one-counters": {"utility"},  # playbook id
    "+1+1-counters": {"utility"},       # docs id alias
    "lands-matter": {"ramp"},
    "landfall": {"ramp"},
}


# ---- Helpers ----------------------------------------------------------------

def load_mirror() -> tuple[dict[str, dict], str]:
    if not MIRROR_FILE.exists():
        print(f"missing scryfall mirror: {MIRROR_FILE}", file=sys.stderr)
        print("run: python scripts/refresh_scryfall_mirror.py", file=sys.stderr)
        sys.exit(2)
    cards = json.loads(MIRROR_FILE.read_text())
    by_name: dict[str, dict] = {}
    for c in cards:
        by_name[c["name"]] = c
        for face in c.get("card_faces") or []:
            fname = face.get("name")
            if fname and fname not in by_name:
                by_name[fname] = c
    meta = json.loads(MIRROR_META.read_text()) if MIRROR_META.exists() else {}
    return by_name, meta.get("scryfall_updated_at", "unknown")


def card_quantity(entry: dict) -> int:
    try:
        return max(1, int(entry.get("quantity") or 1))
    except (TypeError, ValueError):
        return 1


def _front_face_typeline(entry: dict, scry: dict | None) -> str:
    """Type line of the FRONT (primary) face. For an MDFC/DFC the front face is
    the one you reference and play first; Scryfall lists it first in card_faces.
    Falls back to the deck.json `type` field when no Scryfall data is present."""
    if scry:
        faces = scry.get("card_faces") or []
        if faces:
            return (faces[0].get("type_line") or "").lower()
        return (scry.get("type_line") or "").lower()
    return (entry.get("type") or "").lower()


def _front_is_land(entry: dict, scry: dict | None) -> bool:
    return "land" in _front_face_typeline(entry, scry)


def is_land_entry(entry: dict, scry: dict | None) -> bool:
    # A card contributes a *playable* land if its front face is a land (real
    # lands, Pathways, Westvale Abbey) OR it's a modal DFC with a land back
    # (is_mdfc_land — Hagra Mauling, Valakut Awakening). A transform DFC whose
    # front is a nonland (Ojer Taq — a creature that only becomes a land on
    # death) is NOT a playable land. (DEC-347 board policy.)
    return _front_is_land(entry, scry) or bool(entry.get("is_mdfc_land"))


def land_weight(entry: dict, scry: dict | None) -> float:
    """Lands this entry contributes (basics multiply by quantity)."""
    qty = card_quantity(entry)
    if _front_is_land(entry, scry):
        return 1.0 * qty           # real land / Pathway / Westvale (front is land)
    if entry.get("is_mdfc_land"):
        return 0.5 * qty           # modal spell//land — counts as half a land
    return 0.0                      # transform creature (Ojer Taq) / nonland


def spell_weight(entry: dict, scry: dict | None) -> float:
    """Spells this entry contributes (modal land MDFCs count 0.5 on each side)."""
    qty = card_quantity(entry)
    if entry.get("is_mdfc_land") and not _front_is_land(entry, scry):
        return 0.5 * qty           # modal spell//land — half spell, half land
    if _front_is_land(entry, scry):
        return 0.0                  # pure land contributes no spell
    return 1.0 * qty                # everything else incl. Ojer Taq (creature)


def get_scry(entry: dict, mirror: dict[str, dict]) -> dict | None:
    name = entry.get("name", "")
    c = mirror.get(name)
    if c is None and " // " in name:
        c = mirror.get(name.split(" // ", 1)[0])
    return c


def spell_face_cmc(entry: dict, scry: dict) -> float:
    """CMC of the spell-relevant face (front face for MDFC-with-land-back)."""
    if entry.get("is_mdfc_land"):
        faces = scry.get("card_faces") or []
        if faces:
            front = faces[0]
            cmc = front.get("cmc")
            if cmc is not None:
                return float(cmc)
    cmc = scry.get("cmc")
    return float(cmc) if cmc is not None else 0.0


def spell_face_mana_cost(entry: dict, scry: dict) -> str:
    if entry.get("is_mdfc_land"):
        faces = scry.get("card_faces") or []
        if faces:
            return faces[0].get("mana_cost") or ""
    if scry.get("mana_cost"):
        return scry["mana_cost"]
    faces = scry.get("card_faces") or []
    if faces:
        return faces[0].get("mana_cost") or ""
    return ""


# ---- Manabase health --------------------------------------------------------

CONDITIONAL_TAP_TOKENS = (
    "unless",
    "you may pay",
    "if you've",
    "if you control",
    "if you reveal",
    "you may reveal",
    "as long as",
    "rather than pay",
)


def land_oracle(scry: dict) -> str:
    parts = []
    if scry.get("oracle_text"):
        parts.append(scry["oracle_text"])
    for face in scry.get("card_faces") or []:
        if face.get("oracle_text"):
            parts.append(face["oracle_text"])
    return "\n".join(parts).lower()


def land_is_untapped(scry: dict) -> bool:
    """Lands that always or conditionally enter untapped count as untapped."""
    oracle = land_oracle(scry)
    if "enters tapped" not in oracle and "enters the battlefield tapped" not in oracle:
        return True
    return any(tok in oracle for tok in CONDITIONAL_TAP_TOKENS)


_FETCH_BASIC = re.compile(
    r"search your library for (?:a |an |up to (?:one|two) )?basic land", re.IGNORECASE
)
_FETCH_TYPED = re.compile(
    r"search your library for an? .{0,30}?(?:plains|island|swamp|mountain|forest)\b",
    re.IGNORECASE,
)


def land_is_fetch(scry: dict) -> bool:
    oracle = land_oracle(scry)
    if not oracle:
        return False
    if _FETCH_BASIC.search(oracle):
        return True
    if _FETCH_TYPED.search(oracle) and "sacrifice" in oracle:
        return True
    return False


def land_color_sources(scry: dict, deck_ci: set[str]) -> set[str]:
    """Return the set of colors this land produces (within the deck CI)."""
    produced = scry.get("produced_mana") or []
    colors = {c for c in produced if c in deck_ci}
    if colors:
        return colors
    # Fetches don't have produced_mana; treat as full sources for any in-CI color
    if land_is_fetch(scry):
        return set(deck_ci)
    return set()


_PIP_RE = re.compile(r"\{([^}]+)\}")


def color_pip_count(mana_cost: str, color: str) -> int:
    if not mana_cost:
        return 0
    # Count pure mono-colored pips ({B}). Hybrid pips ({W/B}) and phyrexian
    # ({B/P}) are intentionally excluded — Karsten's table assumes a hard
    # color requirement.
    return sum(1 for sym in _PIP_RE.findall(mana_cost) if sym == color)


def karsten_threshold(cmc: float, pips: int) -> int:
    """Sources required for `pips` of color C at total CMC `cmc`."""
    icmc = int(cmc) if cmc < 4 else 4  # 4+ all share the C row
    if pips <= 0:
        return 0
    if icmc <= 1:
        return 20 if pips >= 2 else 14
    if icmc == 2:
        return 18 if pips >= 2 else 13
    if icmc == 3:
        if pips >= 3:
            return 20
        if pips == 2:
            return 16
        return 12
    return 10  # 4+


def manabase_health(deck: dict, mirror: dict[str, dict], deck_ci: set[str]) -> dict:
    decklist = deck.get("decklist", [])

    # Land inventory
    total_lands = 0.0
    untapped_lands = 0.0
    fetch_lands = 0.0
    sources_by_color: dict[str, float] = {c: 0.0 for c in deck_ci}

    # Spell inventory (for land count fit avg cmc, and Karsten thresholds)
    nonland_cmcs: list[float] = []
    requirements: dict[str, int] = {c: 0 for c in deck_ci}

    for entry in decklist:
        scry = get_scry(entry, mirror)
        qty = card_quantity(entry)

        lw = land_weight(entry, scry)
        sw = spell_weight(entry, scry)
        total_lands += lw

        if lw > 0 and scry:
            untapped = land_is_untapped(scry)
            if untapped:
                untapped_lands += lw
            if land_is_fetch(scry):
                fetch_lands += lw
            for color in land_color_sources(scry, deck_ci):
                sources_by_color[color] += lw

        if sw > 0 and scry:
            cmc = spell_face_cmc(entry, scry)
            for _ in range(qty):
                nonland_cmcs.append(cmc)
            mana_cost = spell_face_mana_cost(entry, scry)
            for color in deck_ci:
                pips = color_pip_count(mana_cost, color)
                if pips:
                    req = karsten_threshold(cmc, pips)
                    if req > requirements[color]:
                        requirements[color] = req

    avg_cmc = (sum(nonland_cmcs) / len(nonland_cmcs)) if nonland_cmcs else 0.0

    # 1. Karsten color compliance (40)
    if deck_ci and any(requirements[c] > 0 for c in deck_ci):
        ratios = []
        per_color: dict[str, dict] = {}
        for c in deck_ci:
            req = requirements[c]
            if req <= 0:
                continue
            actual = sources_by_color.get(c, 0.0)
            ratio = min(actual / req, 1.0) if req else 1.0
            ratios.append(ratio)
            per_color[c] = {"required": req, "actual": round(actual, 1), "ratio": round(ratio, 2)}
        karsten_score = (sum(ratios) / len(ratios)) * 40 if ratios else 40.0
    else:
        per_color = {}
        karsten_score = 40.0  # colorless deck — no constraint

    # 2. Untapped ratio (30)
    if total_lands > 0:
        untapped_ratio = untapped_lands / total_lands
        untapped_score = untapped_ratio * 30
    else:
        untapped_ratio = 0.0
        untapped_score = 0.0

    # 3. Fetch density (15)
    fetch_score = min(fetch_lands / 6.0, 1.0) * 15

    # 4. Land count fit (15)
    target_lands = 35 + (avg_cmc * 1.5)
    delta = abs(total_lands - target_lands)
    if delta <= 1:
        land_count_score = 15.0
    elif delta <= 2:
        land_count_score = 7.5
    else:
        land_count_score = 0.0

    score = round(karsten_score + untapped_score + fetch_score + land_count_score)
    return {
        "score": score,
        "components": {
            "karsten": round(karsten_score, 1),
            "untapped": round(untapped_score, 1),
            "fetch": round(fetch_score, 1),
            "land_count": round(land_count_score, 1),
        },
        "inputs": {
            "total_lands": round(total_lands, 1),
            "untapped_lands": round(untapped_lands, 1),
            "fetch_lands": round(fetch_lands, 1),
            "avg_nonland_cmc": round(avg_cmc, 2),
            "target_lands": round(target_lands, 1),
            "color_sources": {c: round(sources_by_color.get(c, 0.0), 1) for c in deck_ci},
            "color_requirements": per_color,
        },
    }


# ---- Role coverage ----------------------------------------------------------

def role_count(deck: dict) -> dict[str, float]:
    """Weighted count per role: primary 1.0, secondary 0.5; respects quantity."""
    counts: dict[str, float] = {r: 0.0 for r in VALID_ROLES}
    for entry in deck.get("decklist", []):
        qty = card_quantity(entry)
        primary = entry.get("primary_role")
        secondary = entry.get("secondary_role")
        if primary in counts:
            counts[primary] += 1.0 * qty
        if secondary in counts:
            counts[secondary] += 0.5 * qty
    cr = deck.get("commanderRoles") or {}
    cprim, csec = cr.get("primary"), cr.get("secondary")
    if cprim in counts:
        counts[cprim] += 1.0
    if csec in counts:
        counts[csec] += 0.5
    return counts


def role_coverage_health(deck: dict, deck_ci: set[str], bracket: int) -> tuple[dict, list[dict]]:
    counts = role_count(deck)
    by_role: dict[str, dict] = {}
    per_scores = []
    gaps: list[dict] = []

    wincon_style = deck.get("wincon_style")
    wincon_target_override = WINCON_STYLE_TARGET.get(wincon_style)
    engine_substitutes = wincon_style in WINCON_STYLE_ENGINE_SUB

    for role, by_bracket in ROLE_TARGETS.items():
        if role == "counterspell" and "U" not in deck_ci:
            continue
        target = by_bracket.get(bracket, by_bracket[4])
        actual = counts.get(role, 0.0)

        if role == "wincon":
            if wincon_target_override is not None:
                target = wincon_target_override
            if engine_substitutes:
                # value-incremental decks treat engine cards as their closer.
                # Engines substitute *only* for the shortfall — never inflate
                # past target.
                shortfall = max(0.0, target - actual)
                actual = actual + min(counts.get("engine", 0.0), shortfall)

        ratio = (actual / target) if target else 1.0
        per = round(min(ratio, 1.2) * 100)
        per_scores.append(per)
        by_role[role] = {"actual": round(actual, 1), "target": target, "score": per}
        if per < 70:
            gap_entry = {"role": role, "actual": round(actual, 1), "target": target, "score": per}
            if role == "wincon" and wincon_style:
                gap_entry["wincon_style"] = wincon_style
            gaps.append(gap_entry)

    score = round(sum(per_scores) / len(per_scores)) if per_scores else 0
    return (
        {"score": score, "by_role": {r: by_role[r]["score"] for r in by_role}, "details": by_role},
        gaps,
    )


# ---- Curve ------------------------------------------------------------------

def archetype_curve_target(archetypes: list[str]) -> tuple[float, list[str]]:
    matched = [a for a in archetypes if a in CURVE_TARGETS]
    if not matched:
        return DEFAULT_CURVE_TARGET, []
    targets = [CURVE_TARGETS[a] for a in matched]
    return round(sum(targets) / len(targets), 2), matched


def curve_health(deck: dict, mirror: dict[str, dict]) -> dict:
    weights: list[tuple[float, float]] = []  # (cmc, weight)
    high_curve_weight = 0.0
    distribution: dict[int, float] = {}

    for entry in deck.get("decklist", []):
        scry = get_scry(entry, mirror)
        if not scry:
            continue
        sw = spell_weight(entry, scry)
        if sw <= 0:
            continue
        cmc = spell_face_cmc(entry, scry)
        weights.append((cmc, sw))
        bucket = min(7, int(cmc))  # 7+ collapsed into one bucket
        distribution[bucket] = distribution.get(bucket, 0.0) + sw
        if cmc >= 6:
            high_curve_weight += sw

    if weights:
        total_w = sum(w for _, w in weights)
        actual = sum(c * w for c, w in weights) / total_w if total_w else 0.0
    else:
        actual = 0.0

    target, matched = archetype_curve_target(deck.get("archetypes", []))
    delta = abs(actual - target)
    raw = max(0.0, 100 - delta * 25)

    high_count = high_curve_weight  # already weighted
    topcurve_penalty = 0.0
    if high_count > 8:
        topcurve_penalty = (high_count - 8) * 5

    score = round(max(0.0, raw - topcurve_penalty))
    cmc_distribution = {str(b): round(distribution.get(b, 0.0), 1) for b in range(0, 8)}
    return {
        "score": score,
        "actual_avg_cmc": round(actual, 2),
        "target_avg_cmc": target,
        "matched_archetype_targets": matched,
        "high_curve_count": round(high_count, 1),
        "topcurve_penalty": round(topcurve_penalty, 1),
        "cmc_distribution": cmc_distribution,
    }


# ---- Interaction density ----------------------------------------------------

def interaction_density(deck: dict, bracket: int) -> dict:
    counts = role_count(deck)  # primary 1.0, secondary 0.5
    rs = counts.get("removal-spot", 0.0)
    rb = counts.get("removal-board", 0.0)
    cs = counts.get("counterspell", 0.0)
    pr = counts.get("protection", 0.0)

    weighted = rs * 1.0 + rb * 2.0 + cs * 1.5 + pr * 1.0

    cr = deck.get("commanderRoles") or {}
    cmd_roles = {cr.get("primary"), cr.get("secondary")}
    bonus = 1.0 if cmd_roles & {"removal-spot", "removal-board", "counterspell", "protection"} else 0.0
    weighted += bonus

    target = INTERACTION_TARGETS.get(bracket, INTERACTION_TARGETS[4])
    score = round(min(weighted / target, 1.2) * 100)
    return {
        "score": score,
        "weighted": round(weighted, 1),
        "target": target,
        "components": {
            "removal_spot": round(rs, 1),
            "removal_board": round(rb, 1),
            "counterspell": round(cs, 1),
            "protection": round(pr, 1),
            "commander_bonus": round(bonus, 1),
        },
    }


# ---- Gameplan cohesion ------------------------------------------------------

def gameplan_cohesion(
    deck: dict, mirror: dict[str, dict], bracket: int, apply_bracket_penalty: bool = True
) -> dict:
    archetypes = deck.get("archetypes") or []
    cohesion_set = set(COHESION_BASE_ROLES)
    extensions: list[str] = []
    for a in archetypes:
        ext = ARCHETYPE_COHESION_EXT.get(a)
        if ext:
            for r in ext:
                if r not in cohesion_set:
                    cohesion_set.add(r)
                    extensions.append(r)

    nonland_total = 0.0
    in_set = 0.0
    combo_wincons = 0
    has_wincon = False
    tutor_count = 0.0

    for entry in deck.get("decklist", []):
        scry = get_scry(entry, mirror)
        sw = spell_weight(entry, scry)
        if sw <= 0:
            continue
        nonland_total += sw
        primary = entry.get("primary_role")
        secondary = entry.get("secondary_role")
        if primary in cohesion_set:
            in_set += sw
        if primary == "wincon" or secondary == "wincon":
            has_wincon = True
            if entry.get("wincon_style") == "combo":
                combo_wincons += 1
        if primary == "tutor" or secondary == "tutor":
            tutor_count += sw

    cr = deck.get("commanderRoles") or {}
    cmd_roles = {cr.get("primary"), cr.get("secondary")}
    if "wincon" in cmd_roles:
        has_wincon = True
        if deck.get("wincon_style") == "combo":
            combo_wincons += 1

    # tutor-heavy / combo-wincon archetype extension
    if tutor_count >= 6 or combo_wincons >= 1:
        if "tutor" not in cohesion_set:
            cohesion_set.add("tutor")
            extensions.append("tutor")
            # Recompute in_set with tutor counted
            for entry in deck.get("decklist", []):
                scry = get_scry(entry, mirror)
                sw = spell_weight(entry, scry)
                if sw <= 0:
                    continue
                primary = entry.get("primary_role")
                if primary == "tutor":
                    in_set += sw

    in_set_pct = (in_set / nonland_total) if nonland_total else 0.0
    raw = in_set_pct * 100

    # The combo penalty judges fit against the deck's *declared* bracket, not
    # construction quality — the normalized companion score (DEC-389) skips it.
    penalty = 0.0
    if apply_bracket_penalty:
        if combo_wincons >= 1 and bracket == 3:
            penalty += 15
        if combo_wincons >= 2 and bracket == 4:
            penalty += 10

    score = max(0.0, raw - penalty)
    if not has_wincon:
        score = min(score, 50.0)

    return {
        "score": round(score),
        "in_set_pct": round(in_set_pct, 2),
        "archetype_extensions": extensions,
        "combo_wincons": combo_wincons,
        "has_wincon": has_wincon,
        "tutor_count": round(tutor_count, 1),
        "penalty": round(penalty, 1),
    }


# ---- Resilience health (DEC-308) -------------------------------------------

def _role_count_weighted(deck: dict, role: str) -> float:
    """Sum of role weight (primary 1.0, secondary 0.5) including commander."""
    total = 0.0
    for entry in deck.get("decklist", []):
        qty = card_quantity(entry)
        if entry.get("primary_role") == role:
            total += 1.0 * qty
        if entry.get("secondary_role") == role:
            total += 0.5 * qty
    cr = deck.get("commanderRoles") or {}
    if cr.get("primary") == role:
        total += 1.0
    if cr.get("secondary") == role:
        total += 0.5
    return total


def _gy_second_hand_count(deck: dict) -> float:
    """Count of cards whose primary or secondary role is in {recursion, engine}.

    Per DEC-308: we deliberately do NOT re-derive from oracle text — that
    produces false positives (every reanimate spell also flags), and the
    recursion role tag already captures the intent. Counting the union of
    recursion+engine surfaces grindy yard-rebuild engines (Deep Analysis,
    Snapcaster, Bone Shards on engine creatures, …) without re-counting any
    single card more than once across this component.
    """
    total = 0.0
    for entry in deck.get("decklist", []):
        primary = entry.get("primary_role")
        secondary = entry.get("secondary_role")
        if primary in RESILIENCE_GY_ROLES or secondary in RESILIENCE_GY_ROLES:
            total += card_quantity(entry)
    cr = deck.get("commanderRoles") or {}
    if cr.get("primary") in RESILIENCE_GY_ROLES or cr.get("secondary") in RESILIENCE_GY_ROLES:
        total += 1.0
    return total


def resilience_health(deck: dict, bracket: int) -> tuple[dict, list[dict]]:
    wincon_style = deck.get("wincon_style")
    recursion_target = (
        RESILIENCE_RECURSION_TARGETS.get(wincon_style)
        or RESILIENCE_RECURSION_TARGETS[None]
    ).get(bracket, RESILIENCE_RECURSION_TARGETS[None][4])
    wincon_floor = RESILIENCE_WINCON_LINE_FLOOR.get(
        wincon_style, RESILIENCE_WINCON_LINE_FLOOR[None]
    )
    protection_target = RESILIENCE_PROTECTION_TARGETS.get(
        bracket, RESILIENCE_PROTECTION_TARGETS[4]
    )

    recursion_count = _role_count_weighted(deck, "recursion")
    protection_count = _role_count_weighted(deck, "protection")
    wincon_lines = len(deck.get("winConditions") or [])
    gy_count = _gy_second_hand_count(deck)

    recursion_ratio = (recursion_count / recursion_target) if recursion_target else 1.0
    recursion_score = round(min(recursion_ratio, 1.2) * 30, 1)

    redundancy_extra = max(0.0, wincon_lines - wincon_floor)
    redundancy_ratio = min(redundancy_extra / 2.0, 1.0)
    redundancy_score = round(redundancy_ratio * 25, 1)

    protection_ratio = min(protection_count / protection_target, 1.0) if protection_target else 1.0
    protection_score = round(protection_ratio * 25, 1)

    gy_ratio = min(gy_count / RESILIENCE_GY_TARGET, 1.0)
    gy_score = round(gy_ratio * 20, 1)

    total = recursion_score + redundancy_score + protection_score + gy_score
    score = round(total)

    components = {
        "recursion":      {"score": recursion_score, "actual": round(recursion_count, 1), "target": recursion_target, "max": 30},
        "redundancy":     {"score": redundancy_score, "lines": wincon_lines, "floor": wincon_floor, "max": 25},
        "protection":     {"score": protection_score, "actual": round(protection_count, 1), "target": protection_target, "max": 25},
        "gy_second_hand": {"score": gy_score, "actual": round(gy_count, 1), "target": RESILIENCE_GY_TARGET, "max": 20},
    }

    # Per-component gap: surface to gaps[] when the component's % of its max is < 70.
    gaps: list[dict] = []
    for name, comp in components.items():
        pct = round((comp["score"] / comp["max"]) * 100)
        if pct < 70:
            gap_entry = {"resilience_component": name, "score_pct": pct, "max": comp["max"]}
            if name == "recursion":
                gap_entry.update({"actual": comp["actual"], "target": comp["target"], "wincon_style": wincon_style})
            elif name == "redundancy":
                gap_entry.update({"lines": comp["lines"], "floor": comp["floor"], "wincon_style": wincon_style})
            elif name == "protection":
                gap_entry.update({"actual": comp["actual"], "target": comp["target"]})
            elif name == "gy_second_hand":
                gap_entry.update({"actual": comp["actual"], "target": comp["target"]})
            gaps.append(gap_entry)

    return (
        {
            "score": score,
            "components": components,
            "inputs": {
                "wincon_style": wincon_style,
                "bracket_effective": bracket,
            },
        },
        gaps,
    )


# ---- Win-turn triple (DEC-311) ---------------------------------------------

# Which simulated lethality curve drives the triple, branched on the deck-level
# `wincon_style`. Multi-kind detection (combo cards + non-combo cards both
# present) and unset/value-incremental decks fall back to `max(CL, LP)` so the
# triple stays honest when the deck closes on more than one axis.
_WIN_TURN_LP_STYLES = {"combat", "drain", "drain-x", "discrete-threats"}
_WIN_TURN_COMBO_STYLES = {"combo"}


def _is_multi_kind_wincon(deck: dict) -> bool:
    """True if the decklist carries both combo and non-combo wincon styles.

    Matches DEC-309's heuristic in scripts/validate_strategy_ceiling.py so the
    two metrics agree on what counts as "mixed".
    """
    card_styles = {
        c.get("wincon_style") for c in deck.get("decklist", []) if c.get("wincon_style")
    }
    non_combo = {"combat", "drain", "drain-x", "discrete-threats", "tokens", "mill", "alt"}
    return "combo" in card_styles and bool(card_styles & non_combo)


def _win_turn_source(deck: dict) -> str:
    """Return 'comboLethal' | 'lethalProxy' | 'max' per DEC-311 branching."""
    style = deck.get("wincon_style")
    if _is_multi_kind_wincon(deck):
        return "max"
    if style in _WIN_TURN_COMBO_STYLES:
        return "comboLethal"
    if style in _WIN_TURN_LP_STYLES:
        return "lethalProxy"
    # value-incremental, "mixed", unset, or any unknown style — fall through to max.
    return "max"


def _read_simulation(deck_id: str) -> dict | None:
    sim_path = DECKS_DIR / deck_id / "simulation.json"
    if not sim_path.exists():
        return None
    try:
        return json.loads(sim_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def win_turn_triple(deck: dict, deck_id: str, bracket: int) -> dict | None:
    """Derive a Best/Typical/Contested win-turn triple from simulation.json.

    Returns None when the triple should be entirely suppressed (no sim, or the
    selected payoff curve is flat at zero). Otherwise returns a dict with
    `best`, `typical`, `contested` (any may be None when the threshold is not
    reached inside the simulated window), plus the curve `source` and the
    `bracket_drag` actually applied so the math is reproducible.
    """
    sim = _read_simulation(deck_id)
    if sim is None:
        return None
    by_turn = (sim.get("goldfish") or {}).get("byTurn") or {}
    if not by_turn:
        return None

    try:
        turns = sorted((int(k) for k in by_turn.keys()))
    except (TypeError, ValueError):
        return None
    if not turns:
        return None

    source = _win_turn_source(deck)

    def payoff_at(t: int) -> float:
        row = by_turn.get(str(t)) or {}
        cl = float(row.get("comboLethal") or 0.0)
        lp = float(row.get("lethalProxy") or 0.0)
        if source == "comboLethal":
            return cl
        if source == "lethalProxy":
            return lp
        return max(cl, lp)

    curve = [(t, payoff_at(t)) for t in turns]
    if max(v for _, v in curve) <= 0.0:
        # Flat-zero curve — the selected source carries no signal at all.
        # Suppress everything; surfacing "—" three times is just noise.
        return None

    best = next((t for t, v in curve if v >= WIN_TURN_BEST_THRESHOLD), None)
    typical = next((t for t, v in curve if v >= WIN_TURN_TYPICAL_THRESHOLD), None)
    drag = WIN_TURN_DRAG.get(bracket, WIN_TURN_DRAG[4])
    contested = (typical + drag) if typical is not None else None

    return {
        "best": best,
        "typical": typical,
        "contested": contested,
        "source": source,
        "bracket_drag": drag,
        "thresholds": {
            "best": WIN_TURN_BEST_THRESHOLD,
            "typical": WIN_TURN_TYPICAL_THRESHOLD,
        },
        "window_last_turn": turns[-1],
    }


# ---- Top-level orchestration ------------------------------------------------

def commander_color_identity(deck: dict, mirror: dict[str, dict]) -> set[str]:
    name = deck.get("commander", "")
    card = mirror.get(name)
    if card:
        return set(card.get("color_identity") or [])
    return set()


def parse_bracket(deck: dict) -> int:
    # Canonical mapping: "3+" → 3, "4+" → 4 (DEC-308). The "+" suffix is a
    # display flourish meaning "slightly above" — target tables collapse it to
    # the base bracket. See docs/deck-metrics.md §bracket-mapping.
    raw = str(deck.get("bracket", 4)).strip().rstrip("+")
    try:
        b = int(raw)
    except (TypeError, ValueError):
        return 4
    if b not in (3, 4, 5):
        if b < 3:
            return 3
        return 5
    return b


def validate_roles(deck: dict, deck_id: str) -> list[str]:
    errs = []
    for entry in deck.get("decklist", []):
        for field in ("primary_role", "secondary_role"):
            r = entry.get(field)
            if r is not None and r not in VALID_ROLES:
                errs.append(f"{deck_id}: {entry.get('name')} has invalid {field}={r!r}")
    cr = deck.get("commanderRoles") or {}
    for field in ("primary", "secondary"):
        r = cr.get(field)
        if r is not None and r not in VALID_ROLES:
            errs.append(f"{deck_id}: commanderRoles.{field}={r!r} invalid")
    return errs


CONFIDENCE_DEFAULT = 5
CONFIDENCE_MIN = 2
CONFIDENCE_MAX = 15
CONFIDENCE_ROLE_PENALTY_CAP = 15
CONFIDENCE_CANDIDATES_STALE_DAYS = 90
CONFIDENCE_CANDIDATES_FRESH_DAYS = 30


def _is_nonland_entry(entry: dict, scry: dict | None) -> bool:
    """A non-land card for role-coverage purposes; MDFC-with-land-back still counts."""
    if entry.get("is_mdfc_land"):
        return True
    if scry and "land" in (scry.get("type_line") or "").lower():
        return False
    if "land" in (entry.get("type") or "").lower():
        return False
    return True


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # tolerate both "Z" and "+00:00" suffixes
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def confidence_margin(
    deck: dict,
    deck_id: str,
    mirror: dict[str, dict],
    role_cov_score: int,
    resilience_components: dict,
) -> dict:
    """DEC-310 — ±margin around global_health based on data-completeness signals.

    Returns {"margin": int, "inputs": {...}}: the inputs dict is descriptive
    only (does not feed downstream), but is stored on metrics.json so reviewers
    can see exactly which penalties/bonuses fired.
    """
    deck_dir = DECKS_DIR / deck_id
    sim_path = deck_dir / "simulation.json"
    cand_path = deck_dir / "candidates.json"

    # Penalty: non-land cards without primary_role (+1 each, cap +15)
    role_unset = 0
    for entry in deck.get("decklist", []):
        scry = get_scry(entry, mirror)
        if not _is_nonland_entry(entry, scry):
            continue
        if not entry.get("primary_role"):
            role_unset += card_quantity(entry)
    role_penalty = min(role_unset, CONFIDENCE_ROLE_PENALTY_CAP)

    # Penalty: wincon_style unset on commander deck (+6)
    is_commander = (deck.get("type") or "commander") == "commander"
    wincon_unset = is_commander and not deck.get("wincon_style")
    wincon_penalty = 6 if wincon_unset else 0

    # Penalty: archetypes empty (+6)
    archetypes_unset = not (deck.get("archetypes") or [])
    archetypes_penalty = 6 if archetypes_unset else 0

    # Penalty: simulation.json missing (+10)
    sim_missing = not sim_path.exists()
    sim_penalty = 10 if sim_missing else 0

    # Penalty: candidates.json missing OR stale (+6).
    # Prefer the file's internal `generated_at` over mtime — the ticket asks us
    # to confirm there's no internal stamp before falling back. There is one.
    cand_missing = not cand_path.exists()
    cand_age_days: float | None = None
    if not cand_missing:
        try:
            cand_payload = json.loads(cand_path.read_text())
            gen_at = _parse_iso(cand_payload.get("generated_at"))
        except (json.JSONDecodeError, OSError):
            gen_at = None
        if gen_at is None:
            # Fallback to file mtime
            gen_at = datetime.fromtimestamp(cand_path.stat().st_mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        cand_age_days = (now - gen_at).total_seconds() / 86400.0
    cand_stale = cand_missing or (cand_age_days is not None and cand_age_days > CONFIDENCE_CANDIDATES_STALE_DAYS)
    cand_penalty = 6 if cand_stale else 0

    # Penalty: fewer than 4 resilience components carrying real signal (+3).
    # "Data completeness" framing: a component scoring 0 means we have no
    # signal on that axis at all (no recursion tags, no protection, no
    # winConditions[], no graveyard rebuild).
    res_components = resilience_components or {}
    res_signal_count = sum(1 for c in res_components.values() if (c.get("score") or 0) > 0)
    res_penalty = 3 if res_signal_count < 4 else 0

    penalties = role_penalty + wincon_penalty + archetypes_penalty + sim_penalty + cand_penalty + res_penalty

    # Bonus floor: all of {archetypes set, wincon_style set, 100% role coverage,
    # simulation present, candidates within 30 days} → floor at ±2.
    full_data = (
        not archetypes_unset
        and not wincon_unset
        and role_cov_score >= 100
        and not sim_missing
        and cand_age_days is not None
        and cand_age_days <= CONFIDENCE_CANDIDATES_FRESH_DAYS
    )

    raw = CONFIDENCE_DEFAULT + penalties
    if full_data:
        raw = min(raw, CONFIDENCE_MIN)
    margin = max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, raw))

    return {
        "margin": margin,
        "inputs": {
            "default": CONFIDENCE_DEFAULT,
            "penalties": {
                "role_unset_cards": role_unset,
                "role_unset_applied": role_penalty,
                "wincon_style_unset": wincon_unset,
                "archetypes_unset": archetypes_unset,
                "simulation_missing": sim_missing,
                "candidates_missing": cand_missing,
                "candidates_age_days": (round(cand_age_days, 1) if cand_age_days is not None else None),
                "candidates_stale": cand_stale,
                "resilience_signal_components": res_signal_count,
                "resilience_signal_low": res_signal_count < 4,
                "total": penalties,
            },
            "bonus_floor_eligible": full_data,
            "role_coverage_score": role_cov_score,
        },
    }


def blend_global_health(
    manabase: int, role: int, curve: int, interaction: int, cohesion: int, resilience: int,
    weights: tuple[float, float, float, float, float, float],
) -> int:
    wm, wr, wc, wi, wco, wre = weights
    return round(
        wm * manabase + wr * role + wc * curve + wi * interaction + wco * cohesion + wre * resilience
    )


def compute(
    deck: dict,
    deck_id: str,
    mirror: dict[str, dict],
    mirror_updated_at: str,
    weight_option: str = DEFAULT_WEIGHT_OPTION,
) -> dict:
    errs = validate_roles(deck, deck_id)
    if errs:
        for e in errs:
            print(f"  WARN {e}", file=sys.stderr)

    deck_ci = commander_color_identity(deck, mirror)
    bracket = parse_bracket(deck)

    manabase = manabase_health(deck, mirror, deck_ci)
    role_cov, role_gaps = role_coverage_health(deck, deck_ci, bracket)
    curve = curve_health(deck, mirror)
    interaction = interaction_density(deck, bracket)
    cohesion = gameplan_cohesion(deck, mirror, bracket)
    resilience, resilience_gaps = resilience_health(deck, bracket)

    weights = GLOBAL_WEIGHT_OPTIONS[weight_option]
    global_health = blend_global_health(
        manabase["score"], role_cov["score"], curve["score"],
        interaction["score"], cohesion["score"], resilience["score"],
        weights,
    )

    # DEC-389 — companion score against the fixed reference bracket's targets.
    # Manabase + curve are bracket-independent and reused as-is; the cohesion
    # bracket-fit combo penalty is excluded (declared-bracket concern, not
    # construction quality). Gaps from the normalized pass are discarded —
    # gaps[] stays scored against the deck's own declared bar.
    norm_bracket = NORMALIZED_REFERENCE_BRACKET
    role_cov_norm, _ = role_coverage_health(deck, deck_ci, norm_bracket)
    interaction_norm = interaction_density(deck, norm_bracket)
    cohesion_norm = gameplan_cohesion(deck, mirror, norm_bracket, apply_bracket_penalty=False)
    resilience_norm, _ = resilience_health(deck, norm_bracket)
    global_health_normalized = blend_global_health(
        manabase["score"], role_cov_norm["score"], curve["score"],
        interaction_norm["score"], cohesion_norm["score"], resilience_norm["score"],
        weights,
    )

    confidence = confidence_margin(
        deck, deck_id, mirror,
        role_cov_score=role_cov["score"],
        resilience_components=resilience.get("components", {}),
    )

    win_turn = win_turn_triple(deck, deck_id, bracket)

    return {
        "version": 2,
        "methodology": METHODOLOGY_VERSION,
        "deck_id": deck_id,
        "commander": deck.get("commander", ""),
        "bracket": str(deck.get("bracket", bracket)),
        "bracket_effective": bracket,
        "color_identity": sorted(deck_ci),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scryfall_mirror_updated_at": mirror_updated_at,
        "weight_option": weight_option,
        "weights": {
            "manabase":    weights[0],
            "role":        weights[1],
            "curve":       weights[2],
            "interaction": weights[3],
            "cohesion":    weights[4],
            "resilience":  weights[5],
        },
        "metrics": {
            "manabase_health": manabase,
            "role_coverage_health": role_cov,
            "curve_health": curve,
            "interaction_density": interaction,
            "gameplan_cohesion": cohesion,
            "resilience_health": resilience,
        },
        "global_health": global_health,
        "global_health_normalized": global_health_normalized,
        "normalized": {
            "reference_bracket": norm_bracket,
            "components": {
                "manabase":    manabase["score"],
                "role":        role_cov_norm["score"],
                "curve":       curve["score"],
                "interaction": interaction_norm["score"],
                "cohesion":    cohesion_norm["score"],
                "resilience":  resilience_norm["score"],
            },
        },
        "confidence_margin": confidence["margin"],
        "confidence_inputs": confidence["inputs"],
        "win_turn": win_turn,
        "gaps": role_gaps + resilience_gaps,
    }


def write_metrics(deck_id: str, payload: dict) -> bool:
    out_path = DECKS_DIR / deck_id / "metrics.json"
    new_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if out_path.exists():
        existing = out_path.read_text()
        # Idempotency: ignore generated_at when comparing
        try:
            old = json.loads(existing)
            new = json.loads(new_text)
            old.pop("generated_at", None)
            new.pop("generated_at", None)
            if old == new:
                return False
        except json.JSONDecodeError:
            pass
    out_path.write_text(new_text)
    return True


def _grade(g: int) -> str:
    if g >= 90:
        return "A"
    if g >= 80:
        return "B"
    if g >= 70:
        return "C"
    if g >= 60:
        return "D"
    return "F"


def run_calibration(paths: list[Path], mirror: dict[str, dict], mirror_updated_at: str) -> int:
    """DEC-308 — compute components once, then project global_health under each
    weight option. Prints a markdown-ready table; writes nothing.
    """
    rows = []
    for p in paths:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        deck_id = p.parent.name
        deck = json.loads(p.read_text())
        # Compute once under option A; the component sub-scores are
        # weight-option-independent, so we can reuse them.
        payload = compute(deck, deck_id, mirror, mirror_updated_at, weight_option="A")
        m = payload["metrics"]
        comps = (
            m["manabase_health"]["score"], m["role_coverage_health"]["score"],
            m["curve_health"]["score"], m["interaction_density"]["score"],
            m["gameplan_cohesion"]["score"], m["resilience_health"]["score"],
        )
        per_option = {opt: blend_global_health(*comps, GLOBAL_WEIGHT_OPTIONS[opt])
                      for opt in GLOBAL_WEIGHT_OPTIONS}
        rows.append((deck_id, comps, per_option))

    rows.sort(key=lambda r: r[2]["A"], reverse=True)

    header = (
        "| Deck | mana | role | curve | int | cohesion | resilience "
        "| A (25/25/15/15/10/10) | B (28/28/14/14/8/8) | C (30/25/15/12/8/10) "
        "| A grade | B grade | C grade |"
    )
    sep = "|" + "|".join(["---"] * 13) + "|"
    print(header)
    print(sep)
    for deck_id, comps, per_option in rows:
        ma, ro, cu, intr, co, re = comps
        a, b, c = per_option["A"], per_option["B"], per_option["C"]
        print(
            f"| {deck_id} | {ma} | {ro} | {cu} | {intr} | {co} | {re} "
            f"| {a} | {b} | {c} | {_grade(a)} | {_grade(b)} | {_grade(c)} |"
        )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compute deck metrics (DEC-119, DEC-308)")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--deck", help="Single deck id")
    target.add_argument("--all", action="store_true", help="All decks")
    parser.add_argument(
        "--weights", choices=sorted(GLOBAL_WEIGHT_OPTIONS), default=DEFAULT_WEIGHT_OPTION,
        help="Which global_health weight option to use when writing metrics.json",
    )
    parser.add_argument(
        "--calibrate", action="store_true",
        help="Print A/B/C global_health projection table for all decks; do not write metrics.json",
    )
    args = parser.parse_args(argv)

    if not args.deck and not args.all:
        args.all = True

    if args.deck:
        paths = [DECKS_DIR / args.deck / "deck.json"]
    else:
        paths = sorted(DECKS_DIR.glob("*/deck.json"))

    mirror, mirror_updated_at = load_mirror()

    if args.calibrate:
        return run_calibration(paths, mirror, mirror_updated_at)

    written = 0
    for p in paths:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        deck_id = p.parent.name
        deck = json.loads(p.read_text())
        payload = compute(deck, deck_id, mirror, mirror_updated_at, weight_option=args.weights)
        changed = write_metrics(deck_id, payload)
        m = payload["metrics"]
        print(
            f"  [{deck_id}] global={payload['global_health']}±{payload['confidence_margin']}  "
            f"norm={payload['global_health_normalized']}  "
            f"mana={m['manabase_health']['score']}  "
            f"roles={m['role_coverage_health']['score']}  "
            f"curve={m['curve_health']['score']}  "
            f"interaction={m['interaction_density']['score']}  "
            f"cohesion={m['gameplan_cohesion']['score']}  "
            f"resilience={m['resilience_health']['score']}  "
            f"gaps={len(payload['gaps'])}"
            f"{'' if changed else '  (unchanged)'}",
            file=sys.stderr,
        )
        if changed:
            written += 1

    print(f"\nWrote {written} metrics file(s) (weights={args.weights}).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

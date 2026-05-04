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

METHODOLOGY_VERSION = "deck-metrics-v1"

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


def is_land_entry(entry: dict, scry: dict | None) -> bool:
    if scry and "land" in (scry.get("type_line") or "").lower():
        # An MDFC counts as a land via is_mdfc_land flag, but its non-land face
        # is also a spell. The caller decides weighting; here just say "has land
        # face".
        if entry.get("is_mdfc_land"):
            return True
        return "land" in (scry.get("type_line") or "").lower() and not entry.get("is_mdfc_land", False) or False
    # Fallback: trust the deck.json type field
    type_field = (entry.get("type") or "").lower()
    return "land" in type_field


def land_weight(entry: dict, scry: dict | None) -> float:
    """How many lands this entry contributes (basics multiply by quantity)."""
    qty = card_quantity(entry)
    if entry.get("is_mdfc_land"):
        return 0.5 * qty
    if scry and "land" in (scry.get("type_line") or "").lower():
        return 1.0 * qty
    if "land" in (entry.get("type") or "").lower():
        return 1.0 * qty
    return 0.0


def spell_weight(entry: dict, scry: dict | None) -> float:
    """How many spells this entry contributes (MDFCs at 0.5)."""
    qty = card_quantity(entry)
    if entry.get("is_mdfc_land"):
        return 0.5 * qty
    if scry and "land" in (scry.get("type_line") or "").lower():
        return 0.0
    if "land" in (entry.get("type") or "").lower():
        return 0.0
    return 1.0 * qty


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

    for role, by_bracket in ROLE_TARGETS.items():
        if role == "counterspell" and "U" not in deck_ci:
            continue
        target = by_bracket.get(bracket, by_bracket[4])
        actual = counts.get(role, 0.0)
        ratio = (actual / target) if target else 1.0
        per = round(min(ratio, 1.2) * 100)
        per_scores.append(per)
        by_role[role] = {"actual": round(actual, 1), "target": target, "score": per}
        if per < 70:
            gaps.append({"role": role, "actual": round(actual, 1), "target": target, "score": per})

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

    for entry in deck.get("decklist", []):
        scry = get_scry(entry, mirror)
        if not scry:
            continue
        sw = spell_weight(entry, scry)
        if sw <= 0:
            continue
        cmc = spell_face_cmc(entry, scry)
        weights.append((cmc, sw))
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
    return {
        "score": score,
        "actual_avg_cmc": round(actual, 2),
        "target_avg_cmc": target,
        "matched_archetype_targets": matched,
        "high_curve_count": round(high_count, 1),
        "topcurve_penalty": round(topcurve_penalty, 1),
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

def gameplan_cohesion(deck: dict, mirror: dict[str, dict], bracket: int) -> dict:
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

    penalty = 0.0
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


# ---- Top-level orchestration ------------------------------------------------

def commander_color_identity(deck: dict, mirror: dict[str, dict]) -> set[str]:
    name = deck.get("commander", "")
    card = mirror.get(name)
    if card:
        return set(card.get("color_identity") or [])
    return set()


def parse_bracket(deck: dict) -> int:
    raw = deck.get("bracket", 4)
    try:
        b = int(str(raw).strip())
    except (TypeError, ValueError):
        return 4
    if b not in (3, 4, 5):
        # B1/B2 not modeled; clamp to closest tabled bracket
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


def compute(deck: dict, deck_id: str, mirror: dict[str, dict], mirror_updated_at: str) -> dict:
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

    global_health = round(
        0.30 * manabase["score"]
        + 0.30 * role_cov["score"]
        + 0.15 * curve["score"]
        + 0.15 * interaction["score"]
        + 0.10 * cohesion["score"]
    )

    return {
        "version": 1,
        "methodology": METHODOLOGY_VERSION,
        "deck_id": deck_id,
        "commander": deck.get("commander", ""),
        "bracket": str(deck.get("bracket", bracket)),
        "color_identity": sorted(deck_ci),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scryfall_mirror_updated_at": mirror_updated_at,
        "metrics": {
            "manabase_health": manabase,
            "role_coverage_health": role_cov,
            "curve_health": curve,
            "interaction_density": interaction,
            "gameplan_cohesion": cohesion,
        },
        "global_health": global_health,
        "gaps": role_gaps,
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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compute deck metrics (DEC-119)")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--deck", help="Single deck id")
    target.add_argument("--all", action="store_true", help="All decks")
    args = parser.parse_args(argv)

    if not args.deck and not args.all:
        args.all = True

    if args.deck:
        paths = [DECKS_DIR / args.deck / "deck.json"]
    else:
        paths = sorted(DECKS_DIR.glob("*/deck.json"))

    mirror, mirror_updated_at = load_mirror()

    written = 0
    for p in paths:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        deck_id = p.parent.name
        deck = json.loads(p.read_text())
        payload = compute(deck, deck_id, mirror, mirror_updated_at)
        changed = write_metrics(deck_id, payload)
        m = payload["metrics"]
        print(
            f"  [{deck_id}] global={payload['global_health']}  "
            f"mana={m['manabase_health']['score']}  "
            f"roles={m['role_coverage_health']['score']}  "
            f"curve={m['curve_health']['score']}  "
            f"interaction={m['interaction_density']['score']}  "
            f"cohesion={m['gameplan_cohesion']['score']}  "
            f"gaps={len(payload['gaps'])}"
            f"{'' if changed else '  (unchanged)'}",
            file=sys.stderr,
        )
        if changed:
            written += 1

    print(f"\nWrote {written} metrics file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

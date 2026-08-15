#!/usr/bin/env python3
"""Author the Combo Lab knowledge-base ontology (versioned artifact).

Emits ``data/combo-kb/ontology.json`` — the single source of truth the
deterministic extractor (``build_combo_kb.py``) and the LLM classifier
(``classify_combo_kb.py``) both load. Kept as a generator so the regex
patterns stay readable Python raw strings instead of double-escaped JSON.

Ontology versioning (RSK-3 / QE-3): bump ``VERSION`` and record the change in
the changelog below whenever a feature, resource, event, or guard is added or a
pattern is materially reworked. Each set release triggers a gap review; new
mechanics not expressible here are logged as blind spots until modelled.

DEC-476 Phase 1 (DEC-488). See docs/combo-kb-schema.md.

Usage:
    uv run python scripts/gen_combo_kb_ontology.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT / "data" / "combo-kb" / "ontology.json"

# ---------------------------------------------------------------------------
# Version. Semantic: MAJOR = incompatible entry-schema change; MINOR = features
# added; PATCH = pattern tuning that does not change the feature set.
# ---------------------------------------------------------------------------
VERSION = "1.0.0"

CHANGELOG = [
    {
        "version": "1.0.0",
        "date": "2026-08-15",
        "note": (
            "Ontology v1 (DEC-488). Seeded from the 15-role taxonomy "
            "(docs/role-taxonomy.md) and the KB-3 mandated trigger economies "
            "(ETB, dies, LTB, cast, sacrifice outlet/fodder, blink, untap, "
            "tap-ability, token creation, mill, drain/lifegain, cost reduction, "
            "trigger doubling, recursion) plus core combo resources (mana, "
            "draw, damage, counters, extra turns)."
        ),
    }
]

# ---------------------------------------------------------------------------
# Resource type system (PRD 6.1). What Tier-B closure accounting is expressed
# in. Deterministic extraction records which resources a card touches; the
# closure math itself lands in Phase 3.
# ---------------------------------------------------------------------------
RESOURCES = [
    {"id": "mana", "label": "Mana", "finite_zone": False,
     "note": "Typed by color plus generic; floating within a phase."},
    {"id": "hand", "label": "Cards in hand", "finite_zone": False},
    {"id": "library", "label": "Cards in library", "finite_zone": True,
     "note": "Finite zone — net-consuming loops are bounded (PRD 6.5.4)."},
    {"id": "graveyard", "label": "Cards in graveyard", "finite_zone": True},
    {"id": "exile", "label": "Cards in exile", "finite_zone": True},
    {"id": "life", "label": "Life total", "finite_zone": False},
    {"id": "tokens", "label": "Tokens by type", "finite_zone": False},
    {"id": "counters", "label": "Counters (+1/+1, charge, loyalty, experience)",
     "finite_zone": False},
    {"id": "turn_phase_budget", "label": "Per-turn allowances",
     "finite_zone": False,
     "note": "Untap steps, draw steps, once-per-turn windows, extra turns — "
             "the k in the k=0 / k>0 classification (PRD 6.5)."},
]

# ---------------------------------------------------------------------------
# Event type system (PRD 6.2). Typed occurrences that trigger rules key on.
# ---------------------------------------------------------------------------
EVENTS = [
    "etb", "dies", "ltb", "cast", "draw", "discard", "mill", "sacrifice",
    "exile", "tap", "untap", "damage", "token_create", "attack", "lifegain",
    "lifeloss", "counter_add", "extra_turn",
]

# ---------------------------------------------------------------------------
# Guard type system (PRD 6.3). Non-consumable preconditions that must appear in
# computed prerequisites (Phase 3) — detected here so entries carry them.
# ---------------------------------------------------------------------------
GUARDS = [
    {"id": "zone_graveyard", "label": "Requires a card in a graveyard",
     "patterns": [r"from (?:your |a |target )?graveyard",
                  r"in your graveyard", r"cards? in (?:your |a )?graveyard"]},
    {"id": "zone_exile", "label": "Interacts with exile",
     "patterns": [r"in exile", r"exiled with", r"from exile"]},
    {"id": "timing_sorcery", "label": "Sorcery-speed timing",
     "patterns": [r"any time you could cast a sorcery",
                  r"only (?:as a sorcery|during your (?:main phase|turn))"]},
    {"id": "summoning_sick", "label": "Summoning-sickness / haste-relevant tap cost",
     "patterns": [r"\{T\}", r"tap an untapped", r"tap (?:target|another)"]},
    {"id": "control_requirement", "label": "Control / ownership requirement",
     "patterns": [r"you control", r"under your control",
                  r"you own and control"]},
    {"id": "once_per_turn", "label": "Once-per-turn / per-turn window",
     "patterns": [r"once (?:each|per) turn", r"only once each turn",
                  r"for the first time each turn"]},
]

# ---------------------------------------------------------------------------
# Features: the provides/wants ontology (KB-1, KB-2, KB-3). Each feature:
#   id        stable key
#   kind      provides | wants | ambient
#   economy   the KB-3 economy bucket (for gap review grouping)
#   patterns  case-insensitive regex matched against oracle text (per face)
#   magnitude optional scalar extractor {pattern, group, default}; else default 1
#   pairs_with  complementary feature ids (the provides/wants edge Phase 2 walks)
#   role_hint   related role-taxonomy role, for cross-referencing
#
# Magnitude patterns use \b(\d+)\b style capture; word-number normalisation
# ("a"/"two"/"three") is handled in build_combo_kb.py before magnitude match.
# ---------------------------------------------------------------------------

# Reusable sub-patterns.
_NUM = r"(\d+)"

FEATURES = [
    # --- Mana (combo backbone; not a KB-3 economy but essential) -----------
    {"id": "mana_add", "kind": "provides", "economy": "mana",
     "label": "Adds mana", "role_hint": "ramp",
     "patterns": [r"\badd\b[^.]*\{[wubrgc0-9]", r"\badd (?:one|two|three) mana",
                  r"add \{[wubrgcx]\}"],
     "magnitude": {"pattern": r"add ((?:\{[wubrgcx0-9]\})+)", "group": 1,
                   "default": 1, "kind": "pip_count"},
     "pairs_with": ["mana_sink", "untap_permanent"]},
    {"id": "mana_sink", "kind": "wants", "economy": "mana",
     "label": "Repeatable mana sink", "role_hint": "payoff",
     "patterns": [r"\{\d+\}[^.]*:", r"pay \{?\d", r"\bx\b[^.]*(?:damage|mana|/)"],
     "pairs_with": ["mana_add"]},
    {"id": "cost_reduction", "kind": "ambient", "economy": "cost_reduction",
     "label": "Reduces costs (ambient modifier)", "role_hint": "engine",
     "patterns": [r"cost(?:s)? \{?\d+\}? less", r"cost(?:s)? \{[wubrg]\} less",
                  r"spells you cast cost", r"costs? \{?\d+\}? less to (?:cast|activate)"],
     "magnitude": {"pattern": r"cost(?:s)? \{?(\d+)\}? less", "group": 1,
                   "default": 1},
     "pairs_with": []},

    # --- Enters-the-battlefield --------------------------------------------
    {"id": "etb_trigger", "kind": "provides", "economy": "etb",
     "label": "ETB payoff", "role_hint": "engine",
     "patterns": [r"when(?:ever)? (?:this creature|[^.]{0,40}?) enters",
                  r"when(?:ever)? (?:a|another)[^.]{0,40}? enters(?: the battlefield)? under your control"],
     "pairs_with": ["blink", "token_create", "recursion"]},
    {"id": "blink", "kind": "provides", "economy": "blink",
     "label": "Blink / flicker (re-triggers ETB)", "role_hint": "engine",
     "patterns": [r"exile (?:target|another target|up to one target|any number of target)[^.]*?(?:then )?return (?:it|them|that card)[^.]*?(?:to the battlefield|under (?:your|its owner's) control)",
                  r"flicker", r"exile[^.]*?return[^.]*?to the battlefield[^.]*?(?:tapped|under)"],
     "pairs_with": ["etb_trigger"]},

    # --- Dies / death triggers ---------------------------------------------
    {"id": "dies_trigger", "kind": "provides", "economy": "dies",
     "label": "Death payoff", "role_hint": "engine",
     "patterns": [r"when(?:ever)? (?:this creature|[^.]{0,40}?) dies",
                  r"when(?:ever)? (?:a|another)[^.]{0,40}? dies"],
     "pairs_with": ["sac_outlet", "sac_fodder"]},

    # --- Leaves-the-battlefield --------------------------------------------
    {"id": "ltb_trigger", "kind": "provides", "economy": "ltb",
     "label": "Leaves-the-battlefield payoff", "role_hint": "engine",
     "patterns": [r"when(?:ever)? (?:this creature|[^.]{0,40}?) leaves the battlefield"],
     "pairs_with": ["blink", "sac_outlet"]},

    # --- Cast triggers (magecraft-style) -----------------------------------
    {"id": "cast_trigger", "kind": "provides", "economy": "cast",
     "label": "Cast payoff (magecraft-style)", "role_hint": "payoff",
     "patterns": [r"when(?:ever)? you cast (?:a|your|an)[^.]{0,40}?spell",
                  r"\bmagecraft\b",
                  r"when(?:ever)? you cast (?:an instant or sorcery|a noncreature)"],
     "pairs_with": ["spell_source"]},
    {"id": "spell_source", "kind": "provides", "economy": "cast",
     "label": "Repeatable / recastable spell source", "role_hint": "engine",
     "patterns": [r"\bflashback\b", r"\bretrace\b", r"cast [^.]*?from your graveyard",
                  r"copy that spell", r"you may cast (?:it|that card) from exile"],
     "pairs_with": ["cast_trigger"]},

    # --- Sacrifice: OUTLET and FODDER separately (KB-3) ---------------------
    {"id": "sac_outlet", "kind": "provides", "economy": "sacrifice",
     "label": "Sacrifice outlet", "role_hint": "utility",
     "patterns": [r"sacrifice (?:a|another|target|this|two|three|any number of)[^.:]*?(?:creature|permanent|artifact|token)[^.]*?:",
                  r"sacrifice (?:a|another)[^.:]*?:"],
     "pairs_with": ["sac_fodder", "dies_trigger"]},
    {"id": "sac_fodder", "kind": "provides", "economy": "sacrifice",
     "label": "Recurring sacrifice fodder", "role_hint": "engine",
     "patterns": [r"create[^.]*?token", r"return (?:it|this card)[^.]*?to (?:the battlefield|your hand)",
                  r"when(?:ever)? [^.]*? dies,[^.]*?return"],
     "pairs_with": ["sac_outlet"]},

    # --- Blink handled above; Untap / tap-ability --------------------------
    {"id": "untap_permanent", "kind": "provides", "economy": "untap",
     "label": "Untaps a permanent", "role_hint": "engine",
     "patterns": [r"untap (?:target|another target|up to (?:one|two|three)|all)[^.]*?(?:permanent|creature|land|artifact)",
                  r"untap [^.]*?\bit\b"],
     "pairs_with": ["tap_ability", "mana_add"]},
    {"id": "tap_ability", "kind": "wants", "economy": "untap",
     "label": "Has a tap-ability worth untapping", "role_hint": "engine",
     "patterns": [r"\{T\}[^.]*?:", r"\{T\},"],
     "pairs_with": ["untap_permanent"]},

    # --- Token creation ----------------------------------------------------
    {"id": "token_create", "kind": "provides", "economy": "token",
     "label": "Creates tokens", "role_hint": "engine",
     "patterns": [r"create(?:s)? [^.]*?token", r"put(?:s)? [^.]*?token onto the battlefield"],
     "magnitude": {"pattern": r"create(?:s)? (\d+)[^.]*?token", "group": 1,
                   "default": 1},
     "pairs_with": ["sac_outlet", "anthem", "token_doubler"]},
    {"id": "token_doubler", "kind": "ambient", "economy": "token",
     "label": "Token doubler (ambient)", "role_hint": "payoff",
     "patterns": [r"create twice that many[^.]*?token",
                  r"if [^.]*?would create one or more tokens[^.]*?(?:twice|instead)"],
     "pairs_with": ["token_create"]},

    # --- Mill --------------------------------------------------------------
    {"id": "mill", "kind": "provides", "economy": "mill",
     "label": "Mill (self or opponent)", "role_hint": "payoff",
     "patterns": [r"\bmills?\b", r"put(?:s)? the top (\d+) cards? of [^.]*?library into"],
     "magnitude": {"pattern": r"mills? (\d+)", "group": 1, "default": 1},
     "pairs_with": ["recursion", "graveyard_payoff"]},

    # --- Drain / lifegain --------------------------------------------------
    {"id": "drain", "kind": "provides", "economy": "drain",
     "label": "Life drain to opponents", "role_hint": "wincon",
     "patterns": [r"each opponent loses (\d+) life",
                  r"loses (\d+) life[^.]*?you gain",
                  r"each opponent loses[^.]*?life"],
     "magnitude": {"pattern": r"loses (\d+) life", "group": 1, "default": 1},
     "pairs_with": ["dies_trigger", "etb_trigger"]},
    {"id": "lifegain", "kind": "provides", "economy": "lifegain",
     "label": "Life gain", "role_hint": "payoff",
     "patterns": [r"you gain (\d+) life", r"gain (\d+) life",
                  r"whenever you gain life"],
     "magnitude": {"pattern": r"gain (\d+) life", "group": 1, "default": 1},
     "pairs_with": ["lifegain_payoff"]},
    {"id": "lifegain_payoff", "kind": "wants", "economy": "lifegain",
     "label": "Lifegain payoff", "role_hint": "payoff",
     "patterns": [r"whenever you gain life", r"if you gained life"],
     "pairs_with": ["lifegain"]},

    # --- Recursion ---------------------------------------------------------
    {"id": "recursion", "kind": "provides", "economy": "recursion",
     "label": "Graveyard recursion", "role_hint": "recursion",
     "patterns": [r"return (?:target|[^.]{0,40}?) card[^.]*?from (?:your |a )?graveyard to (?:your hand|the battlefield)",
                  r"return [^.]*?from your graveyard",
                  r"\bunearth\b", r"\bencore\b", r"\bembalm\b", r"\beternalize\b"],
     "pairs_with": ["mill", "sac_fodder", "self_mill"]},
    {"id": "graveyard_payoff", "kind": "wants", "economy": "recursion",
     "label": "Graveyard-as-resource payoff", "role_hint": "payoff",
     "patterns": [r"\bdelve\b", r"\bescape\b", r"cards? in your graveyard",
                  r"for each [^.]*?in your graveyard"],
     "pairs_with": ["mill", "recursion"]},

    # --- Trigger doubling (ambient) ----------------------------------------
    {"id": "trigger_doubler", "kind": "ambient", "economy": "trigger_doubling",
     "label": "Trigger doubler (ambient)", "role_hint": "payoff",
     "patterns": [r"triggers? an additional time", r"triggers? one more time",
                  r"if [^.]*?would (?:trigger|be dealt|create)[^.]*?(?:twice|instead)"],
     "pairs_with": ["etb_trigger", "dies_trigger", "cast_trigger"]},

    # --- Counters / proliferate --------------------------------------------
    {"id": "counter_add", "kind": "provides", "economy": "counters",
     "label": "Adds counters", "role_hint": "engine",
     "patterns": [r"put(?:s)? (\d+|a|one|two|three)[^.]*?counters?",
                  r"\bproliferate\b", r"\bamass\b"],
     "magnitude": {"pattern": r"put (\d+)[^.]*?counter", "group": 1, "default": 1},
     "pairs_with": ["counter_payoff"]},
    {"id": "counter_payoff", "kind": "wants", "economy": "counters",
     "label": "Counter payoff", "role_hint": "payoff",
     "patterns": [r"for each [^.]*?counter", r"remove (?:a|one|\d+)[^.]*?counter"],
     "pairs_with": ["counter_add"]},

    # --- Card draw ---------------------------------------------------------
    {"id": "draw", "kind": "provides", "economy": "draw",
     "label": "Card draw", "role_hint": "card-draw",
     "patterns": [r"draws? (\d+|a|one|two|three) cards?", r"draw a card"],
     "magnitude": {"pattern": r"draws? (\d+) cards?", "group": 1, "default": 1},
     "pairs_with": []},

    # --- Damage ------------------------------------------------------------
    {"id": "damage", "kind": "provides", "economy": "damage",
     "label": "Deals damage", "role_hint": "wincon",
     "patterns": [r"deals? (\d+) damage", r"deals? damage equal to",
                  r"deals? x damage"],
     "magnitude": {"pattern": r"deals? (\d+) damage", "group": 1, "default": 1},
     "pairs_with": ["ping_outlet"]},
    {"id": "ping_outlet", "kind": "provides", "economy": "damage",
     "label": "Repeatable damage outlet", "role_hint": "wincon",
     "patterns": [r"\{T\}[^.]*?deals? \d+ damage", r":[^.]*?deals? \d+ damage to any target"],
     "pairs_with": ["untap_permanent"]},

    # --- Extra turns / anthem ----------------------------------------------
    {"id": "extra_turn", "kind": "provides", "economy": "turn_phase_budget",
     "label": "Extra turn / extra combat", "role_hint": "wincon",
     "patterns": [r"take an extra turn", r"an additional combat phase",
                  r"take (?:a|an) [^.]*?turn after this one"],
     "pairs_with": []},
    {"id": "anthem", "kind": "ambient", "economy": "token",
     "label": "Anthem / static buff (ambient)", "role_hint": "payoff",
     "patterns": [r"creatures you control get \+", r"other creatures you control get \+",
                  r"get \+\d+/\+\d+"],
     "pairs_with": ["token_create"]},

    # --- Self-mill (recursion enabler) -------------------------------------
    {"id": "self_mill", "kind": "provides", "economy": "mill",
     "label": "Self-mill", "role_hint": "engine",
     "patterns": [r"mill(?:s)? (?:yourself|\d+)", r"put the top [^.]*?of your library into your graveyard"],
     "pairs_with": ["recursion", "graveyard_payoff"]},
]


def build() -> dict:
    return {
        "schema": "combo-kb-ontology",
        "version": VERSION,
        "comment": (
            "Combo Lab knowledge-base ontology (DEC-476 Phase 1 / DEC-488). "
            "Source of truth for deterministic feature extraction. Patterns are "
            "case-insensitive Python regex matched against oracle_text (per face "
            "for DFCs), after word-number normalisation. See "
            "docs/combo-kb-schema.md."
        ),
        "resources": RESOURCES,
        "events": EVENTS,
        "guards": GUARDS,
        "features": FEATURES,
        "changelog": CHANGELOG,
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = build()
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_prov = sum(1 for f in FEATURES if f["kind"] == "provides")
    n_want = sum(1 for f in FEATURES if f["kind"] == "wants")
    n_amb = sum(1 for f in FEATURES if f["kind"] == "ambient")
    print(f"Wrote {OUT.relative_to(PROJECT_ROOT)} v{VERSION}")
    print(f"  features: {len(FEATURES)} ({n_prov} provides, {n_want} wants, {n_amb} ambient)")
    print(f"  resources: {len(RESOURCES)}  events: {len(EVENTS)}  guards: {len(GUARDS)}")


if __name__ == "__main__":
    main()

"""DEC-426 — manabase_check scoring and discovery unit tests (synthetic data)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import manabase_check as mc  # noqa: E402


def land(name, type_line="Land", oracle="", produced=None, ci=None, legal="legal"):
    return {
        "name": name,
        "type_line": type_line,
        "oracle_text": oracle,
        "produced_mana": produced or [],
        "color_identity": ci if ci is not None else [c for c in (produced or []) if c != "C"],
        "legalities": {"commander": legal},
    }


CI = {"R", "U", "W"}
NO_DEFICIT = set()
CENSUS = {"R": 14, "U": 10, "W": 31}

UNTAPPED_DUAL = land("Untapped Dual", oracle="{T}: Add {R} or {W}.", produced=["R", "W"])
SLOWLAND = land(
    "Slowland",
    oracle="This land enters tapped unless you control two or more other lands.\n{T}: Add {R} or {W}.",
    produced=["R", "W"],
)
TAPPED_TRI = land(
    "Tapped Tri",
    oracle="This land enters tapped.\n{T}: Add {U}, {R}, or {W}.",
    produced=["R", "U", "W"],
)
RESTRICTED_ANY = land(
    "Tribal Estate",
    oracle="{T}: Add {C}.\n{T}: Add one mana of any color. Spend this mana only to cast a Vampire spell.",
    produced=["C", "R", "U", "W"],
    ci=[],
)
TYPED_DUAL = land(
    "Typed Dual",
    type_line="Land — Mountain Plains",
    oracle="This land enters tapped unless your opponents control eight or more cards.\n({T}: Add {R} or {W}.)",
    produced=["R", "W"],
)


def score(scry, deficit=NO_DEFICIT, free=1, census=CENSUS):
    s, _ = mc.score_land(scry, CI, deficit, free, census)
    return s


def test_etb_ordering_untapped_dual_beats_tapped_tri():
    # B4 bar: an unconditionally tapped tri-land must not outrank an untapped dual.
    assert score(UNTAPPED_DUAL) > score(TAPPED_TRI)


def test_slowland_between_untapped_and_tapped():
    assert score(UNTAPPED_DUAL) > score(SLOWLAND) > score(TAPPED_TRI)


def test_typed_subtypes_add_score():
    assert score(TYPED_DUAL) > score(SLOWLAND)
    _, features = mc.score_land(TYPED_DUAL, CI, NO_DEFICIT, 1, CENSUS)
    assert features["typed"] == ["Plains", "Mountain"]


def test_deficit_color_boost():
    assert score(SLOWLAND, deficit={"W"}) == score(SLOWLAND) + mc.SCORE_DEFICIT_COLOR
    assert score(SLOWLAND, deficit={"U"}) == score(SLOWLAND)  # slowland makes no U


def test_pip_demand_weights_heavy_colors():
    rw = land("RW", oracle="{T}: Add {R} or {W}.", produced=["R", "W"])
    ru = land("RU", oracle="{T}: Add {R} or {U}.", produced=["R", "U"])
    assert score(rw) > score(ru)  # W (31 pips) outweighs U (10 pips)


def test_restricted_producer_flagged_and_demoted():
    s, features = mc.score_land(RESTRICTED_ANY, CI, NO_DEFICIT, 1, CENSUS)
    assert features["restricted"] is True
    unrestricted = land("Any", oracle="{T}: Add one mana of any color.", produced=["R", "U", "W"])
    assert s == score(unrestricted) + mc.SCORE_RESTRICTED


def test_fetch_scores_without_produced_mana():
    fetch = land(
        "Basic Gate",
        oracle="{T}, Sacrifice this land: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.",
    )
    s, features = mc.score_land(fetch, CI, NO_DEFICIT, 1, CENSUS)
    assert features["fetch"] is True
    assert features["produces"] == []
    assert s == mc.SCORE_ALWAYS_UNTAPPED + mc.SCORE_FETCH + mc.SCORE_FREE_COPY


def test_discover_lands_filters_and_locks():
    mirror = {
        "Untapped Dual": UNTAPPED_DUAL,
        "Slowland": SLOWLAND,
        "Plains": land("Plains", type_line="Basic Land — Plains", produced=["W"]),
        "Off Color": land("Off Color", oracle="{T}: Add {B} or {G}.", produced=["B", "G"]),
        "Banned Land": land("Banned Land", produced=["W"], legal="not_legal"),
        "Some Creature": land("Some Creature", type_line="Creature — Elf"),
        "Utility Land": land("Utility Land", oracle="{T}: Add {C}.", produced=["C"], ci=[]),
    }
    deck = {"decklist": [{"name": "Untapped Dual", "type": "Land"}]}
    owned = {name: 1 for name in mirror}
    owned["Slowland"] = 2
    locks = {"Slowland": ["prod-deck-a"]}

    fixing, utility = mc.discover_lands(deck, mirror, CI, NO_DEFICIT, owned, locks, CENSUS)
    fixing_names = [r["name"] for r in fixing]
    assert fixing_names == ["Slowland"]  # in-deck, basic, off-CI, illegal, nonland all excluded
    assert [r["name"] for r in utility] == ["Utility Land"]

    row = fixing[0]
    assert row["owned"] == 2
    assert row["locked_by"] == ["prod-deck-a"]
    assert row["free_copies"] == 1  # owned duplicate frees the locked copy


# --- DEC-429: EDHREC inclusion rate in discovery ranking ---

UTILITY_A = land("Alpha Filler", oracle="{T}: Add {C}.", produced=["C"], ci=[])
UTILITY_Z = land("Zeta Staple", oracle="{T}: Add {C}.", produced=["C"], ci=[])


def discover(mirror, rates=None):
    deck = {"decklist": []}
    owned = {name: 1 for name in mirror}
    return mc.discover_lands(deck, mirror, CI, NO_DEFICIT, owned, {}, CENSUS, rates)


def test_edhrec_boost_formula_mirrors_candidate_scorer():
    assert mc.edhrec_boost(None) == 0
    assert mc.edhrec_boost(25.0) == 10
    assert mc.edhrec_boost(50.0) == 20
    assert mc.edhrec_boost(90.0) == 20  # saturates at 50%


def test_utility_high_inclusion_staple_outranks_alphabetical_filler():
    # Regression (DEC-429): both score base 11 (untapped 8 + free copy 3);
    # without rates the alphabetically-earlier filler wins the display slot.
    mirror = {"Alpha Filler": UTILITY_A, "Zeta Staple": UTILITY_Z}
    _, utility = discover(mirror, rates={"Zeta Staple": 45.0})
    assert [r["name"] for r in utility] == ["Zeta Staple", "Alpha Filler"]
    assert utility[0]["score"] == utility[1]["score"] + mc.edhrec_boost(45.0)
    assert utility[0]["edhrec_rate"] == 45.0


def test_missing_rates_degrade_to_current_behavior():
    mirror = {"Alpha Filler": UTILITY_A, "Zeta Staple": UTILITY_Z}
    for rates in (None, {}):
        _, utility = discover(mirror, rates=rates)
        assert [r["name"] for r in utility] == ["Alpha Filler", "Zeta Staple"]
        assert {r["score"] for r in utility} == {mc.SCORE_ALWAYS_UNTAPPED + mc.SCORE_FREE_COPY}


def test_fixing_rate_is_tiebreak_only():
    dual_a = land("Alpha Dual", oracle="{T}: Add {R} or {W}.", produced=["R", "W"])
    dual_z = land("Zeta Dual", oracle="{T}: Add {R} or {W}.", produced=["R", "W"])
    mirror = {
        "Alpha Dual": dual_a,
        "Zeta Dual": dual_z,
        "Tapped Tri": TAPPED_TRI,
    }
    fixing, _ = discover(mirror, rates={"Zeta Dual": 60.0, "Tapped Tri": 60.0})
    # Equal scores: rate flips the alphabetical tie, but no boost lands on the
    # fixing score — a 60%-inclusion tapped tri still can't outrank an
    # untapped dual (B4 ETB ordering preserved).
    assert [r["name"] for r in fixing] == ["Zeta Dual", "Alpha Dual", "Tapped Tri"]
    assert fixing[0]["score"] == fixing[1]["score"]

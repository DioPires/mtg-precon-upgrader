"""Tests for scripts/sealed_sim.py and the DEC-926 Reality Fracture inputs."""

from __future__ import annotations

import json
import pathlib
import random
import sys
from collections import Counter

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sealed_sim as ss  # noqa: E402

DATA = ROOT / "agents" / "ceo" / "analysis" / "dec925"
CARDS_PATH = DATA / "fra_all_cards.json"
PAIRS_PATH = DATA / "echoed_pairs.json"
CONFIG_PATH = DATA / "collation.json"

pytestmark = pytest.mark.skipif(
    not CARDS_PATH.exists(),
    reason="DEC-925 card dump is untracked; skip when it is absent",
)


@pytest.fixture(scope="module")
def cards():
    return json.loads(CARDS_PATH.read_text())


@pytest.fixture(scope="module")
def pair_table():
    return json.loads(PAIRS_PATH.read_text())


@pytest.fixture(scope="module")
def config():
    return json.loads(CONFIG_PATH.read_text())


@pytest.fixture(scope="module")
def table(cards, pair_table):
    return ss.CardTable(cards, pair_table)


@pytest.fixture(scope="module")
def collation(config, table):
    return ss.Collation(config, table)


# -- echoed-pair table ------------------------------------------------------


def test_pair_table_has_43_pairs(pair_table):
    assert len(pair_table["pairs"]) == 43


def test_pair_table_rarity_split(pair_table):
    counts = Counter(p["rarity"] for p in pair_table["pairs"])
    assert counts == {"uncommon": 33, "rare": 7, "mythic": 3}
    cards = Counter(
        p["rarity"] for p in pair_table["pairs"] for _ in p["halves"]
    )
    assert cards == {"uncommon": 66, "rare": 14, "mythic": 6}


def test_pair_halves_share_rarity_and_exist(pair_table, cards):
    by_name = {c["name"]: c for c in cards}
    for p in pair_table["pairs"]:
        a, b = p["halves"]
        assert a["name"] in by_name, a["name"]
        assert b["name"] in by_name, b["name"]
        assert by_name[a["name"]]["rarity"] == by_name[b["name"]]["rarity"]
        assert by_name[a["name"]]["rarity"] == p["rarity"]


def test_no_card_in_two_pairs(pair_table):
    names = [h["name"] for p in pair_table["pairs"] for h in p["halves"]]
    assert len(names) == 86
    assert len(set(names)) == 86


def test_paired_cards_sit_in_the_cycle_block(pair_table, cards):
    """The cycle is collector numbers 195-280 and nothing else.

    (The set's main numbering runs 1-280 for its 270 cards plus the 10 common
    duals, with five gaps where `unique=cards` returned a showcase print;
    281-289 are basics.)
    """
    by_name = {c["name"]: c for c in cards}
    seen = set()
    for p in pair_table["pairs"]:
        for h in p["halves"]:
            n = ss.collector_num(by_name[h["name"]])
            assert 195 <= n <= 280, (h["name"], n)
            seen.add(n)
    assert seen == set(range(195, 281))


def test_nonpaired_counts(table):
    assert len(table.group("nonpaired_uncommon")) == 43
    assert len(table.group("nonpaired_rare")) == 50
    assert len(table.group("nonpaired_mythic")) == 20
    assert len(table.group("main_common")) == 71
    assert len(table.group("dual_common_land")) == 10


def test_pair_table_watermark_corroboration(pair_table, cards):
    """45 of the 86 cycle cards carry a watermark and none contradicts a pair."""
    marked = {c["name"] for c in cards if c.get("watermark")}
    in_cycle = {h["name"] for p in pair_table["pairs"] for h in p["halves"]}
    assert len(marked & in_cycle) == 45
    # the only watermarked card outside the cycle is called out in the file
    assert sorted(marked - in_cycle) == pair_table["unmatched_watermarked_cards"]


# -- collation --------------------------------------------------------------


def test_slot_weights_sum_to_one(collation):
    for slot in collation.slots:
        # cum ends either at 1.0, or at basic_from with the rest being a basic
        end = slot["cum"][-1]
        assert end == pytest.approx(slot["basic_from"], abs=1e-9) or end == \
            pytest.approx(1.0, abs=1e-9)
        assert slot["cum"] == sorted(slot["cum"])
        assert slot["cum"][0] > 0


def test_slot_count_yields_14_cards_per_pack(collation):
    yielded = sum(2 if s["kind"] == "echoed_pair" else 1 for s in collation.slots)
    assert yielded == 14


def test_pack_expectation_matches_closed_form(collation, table):
    sim = ss.pack_expectations(collation, table, 50_000, seed=7)
    exact = ss.analytic_pack_expectations(collation, table)
    for key in ("common", "uncommon", "rare_plus_mythic", "dual_land"):
        assert sim[key] == pytest.approx(exact[key], abs=0.05), key


def test_pack_expectation_matches_ceo_targets(collation, table, config):
    """Spec sanity target. Uncommons are the documented normalization gap."""
    sim = ss.pack_expectations(collation, table, 50_000, seed=7)
    target = config["sanity_targets"]["per_pack_excluding_basics"]
    for key in ("common", "rare_plus_mythic", "dual_land"):
        assert sim[key] == pytest.approx(target[key], abs=0.05), key
    # The CEO's 4.81 was computed from raw weights summing to 0.97-0.972.
    # Re-derive it that way to show the gap is a normalization choice, not a
    # sampler bug, then pin the normalized value the model actually produces.
    raw = 1 + 0.74 + 3 * 0.889 + 0.405
    assert raw == pytest.approx(target["uncommon"], abs=0.005)
    assert sim["uncommon"] == pytest.approx(4.936, abs=0.05)


def test_echoed_pair_slot_always_delivers_one_full_pair(collation, table):
    pair_lookup = {frozenset(p) for p in table.pairs}
    slot = next(s for s in collation.slots if s["kind"] == "echoed_pair")
    rng = random.Random(11)
    for _ in range(2000):
        out: list[int] = []
        # drive just this slot
        r = rng.random()
        j = 0
        while slot["cum"][j] < r:
            j += 1
        pick = slot["pools"][j][int(rng.random() * len(slot["pools"][j]))]
        out.extend(pick)
        assert len(out) == 2
        assert frozenset(out) in pair_lookup
        assert table.rarity[out[0]] == table.rarity[out[1]]


def test_full_pack_contains_a_complete_pair(collation, table):
    pair_lookup = {frozenset(p) for p in table.pairs}
    rng = random.Random(3)
    for _ in range(500):
        out: list[int] = []
        collation.pack(rng.random, out)
        assert any(
            frozenset((a, b)) in pair_lookup
            for i, a in enumerate(out)
            for b in out[i + 1:]
        )


def test_basics_never_enter_the_pool(collation, table):
    rng = random.Random(5)
    for _ in range(300):
        for i in collation.pool(rng.random):
            assert not table.cards[i]["type_line"].startswith("Basic Land")


# -- determinism ------------------------------------------------------------


def test_seed_determinism(collation, table):
    gt = ss.GradeTable(table, ss.placeholder_grades(table))
    a = ss.run(collation, table, gt, pools=300, seed=20260925)
    b = ss.run(collation, table, gt, pools=300, seed=20260925)
    a.pop("elapsed_seconds", None)
    b.pop("elapsed_seconds", None)
    assert a == b
    c = ss.run(collation, table, gt, pools=300, seed=20260926)
    assert c["per_pair"] != a["per_pair"]


# -- deck evaluation --------------------------------------------------------


def _graded(table, overrides):
    rows = ss.placeholder_grades(table, grade=0.0)
    by_name = {r["name"]: r for r in rows}
    for name, patch in overrides.items():
        by_name[name].update(patch)
    return ss.GradeTable(table, rows)


def _pairs_for(table, name):
    i = table.index[name]
    return {ss.PAIR_NAMES[p] for p in table.pair_slots[i]}


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("W", "W"),
        ("W/B", "WB"),
        ("2/W", None),
        ("W/P", None),
        ("3", None),
        ("X", None),
        ("C", None),
        ("S", None),
    ],
)
def test_pip_mask(symbol, expected):
    want = None if expected is None else sum(ss.COLOR_BIT[c] for c in expected)
    assert ss.pip_mask(symbol) == want


def test_front_face_cost_uses_face_zero(cards):
    by_name = {c["name"]: c for c in cards}
    heckler = by_name["Hallway Heckler // Vicious Verse"]
    assert heckler["mana_cost"] == "{2}{R} // {B/R}"
    assert ss.front_face_cost(heckler) == "{2}{R}"
    assert ss.front_face_cost(by_name["Twisted Fates"]) == "{2}{W}{W}{B}"
    assert ss.front_face_cost(by_name["Plains"]) == ""


def test_eligibility_is_pip_castability(table):
    """DEC-927: every front-face pip must be payable by the pair."""
    for p, name in enumerate(ss.PAIR_NAMES):
        mask = ss.PAIR_MASKS[p]
        for i in range(len(table.cards)):
            reqs = ss.pip_requirements(table.cards[i])
            expected = (not table.is_land[i]) and all(r & mask for r in reqs)
            assert (p in table.pair_slots[i]) is expected, (name, table.name[i])


def test_dec927_castability_cases(table):
    """The four worked examples from the DEC-927 addendum."""
    # hybrid {W/B}: any deck with W or with B
    assert _pairs_for(table, "Blessed Ghoul") == {
        "WU", "WB", "WR", "WG", "UB", "BR", "BG"
    }
    # prepare DFC, front face {2}{R}: any pair with R
    assert _pairs_for(table, "Hallway Heckler // Vicious Verse") == {
        "WR", "UR", "BR", "RG"
    }
    # prepare DFC, front face {1}{W/U}: any pair with W or U
    assert _pairs_for(table, "Fatehold Chronologist // Peer Review") == {
        "WU", "WB", "WR", "WG", "UB", "UR", "UG"
    }
    # plain coloured pips
    assert _pairs_for(table, "Twisted Fates") == {"WB"}
    # all-generic-hybrid: castable everywhere, the 8 mana is priced in the grade
    assert _pairs_for(table, "Karn, Gilded Guardian") == set(ss.PAIR_NAMES)


def test_lands_are_never_eligible_spells(table):
    for i in range(len(table.cards)):
        if table.is_land[i]:
            assert table.pair_slots[i] == (), table.name[i]


def test_hybrids_are_no_longer_locked_to_their_colour_pair(table):
    """The rule this replaced would have put every hybrid in exactly 1 pair."""
    widened = [
        table.name[i]
        for i in range(len(table.cards))
        if not table.is_land[i]
        and bin(table.cmask[i]).count("1") >= 2
        and len(table.pair_slots[i]) > 1
    ]
    assert len(widened) >= 10


def test_deck_takes_the_top_23_by_effective_grade(table):
    mono_w = [
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["W"] and not table.is_land[i]
    ][:30]
    overrides = {
        table.name[i]: {"grade": 10 if n < 5 else 2} for n, i in enumerate(mono_w)
    }
    gt = _graded(table, overrides)
    res = ss.evaluate_pool(mono_w, table, gt)
    wu = next(r for r in res if r["pair"] == "WU")
    # 5 tens + 18 twos, out of 30 available
    assert wu["score"] == pytest.approx((5 * 10 + 18 * 2) / 23)
    assert wu["bombs"] == 5
    assert wu["playables"] == 5


def test_short_pool_is_padded_to_23_at_grade_one(table):
    mono_w = [
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["W"] and not table.is_land[i]
    ][:4]
    gt = _graded(table, {table.name[i]: {"grade": 6} for i in mono_w})
    wu = next(r for r in ss.evaluate_pool(mono_w, table, gt) if r["pair"] == "WU")
    assert wu["score"] == pytest.approx((4 * 6 + 19 * 1) / 23)


def test_synergy_grade_activates_at_threshold(table):
    mono_u = [
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["U"] and not table.is_land[i]
    ][:6]
    payoff, *enablers = mono_u
    over = {
        table.name[payoff]: {
            "grade": 3,
            "grade_synergy": 9,
            "needs": "jace",
            "needs_threshold": 4,
        }
    }
    for i in enablers:
        over[table.name[i]] = {"grade": 1, "provides": ["jace"]}
    gt = _graded(table, over)

    below = ss.evaluate_pool([payoff] + enablers[:3], table, gt)
    assert next(r for r in below if r["pair"] == "WU")["bombs"] == 0
    at = ss.evaluate_pool([payoff] + enablers[:4], table, gt)
    assert next(r for r in at if r["pair"] == "WU")["bombs"] == 1


def test_splash_needs_two_fixers_and_a_grade_seven_card(table):
    idx = table.index
    duals = [i for i in range(len(table.cards)) if table.is_dual[i]]
    green_fixers = [i for i in duals if table.fix[i] & ss.COLOR_BIT["G"]]
    assert len(green_fixers) >= 2

    # no spell may be a fixer under the lands-only gate; assert that rather
    # than relying on it, since this pool must supply exactly the 2 green
    # fixers the test adds by hand
    mono_w = [
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["W"] and not table.is_land[i]
    ][:23]
    assert all(table.fix[i] == 0 for i in mono_w)
    green_bomb = next(
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["G"] and not table.is_land[i]
    )
    over = {table.name[i]: {"grade": 2} for i in mono_w}
    over[table.name[green_bomb]] = {"grade": 9}
    gt = _graded(table, over)

    without = ss.evaluate_pool(mono_w + [green_bomb], table, gt)
    assert next(r for r in without if r["pair"] == "WU")["splash"] == 0

    with_one = ss.evaluate_pool(
        mono_w + [green_bomb, green_fixers[0]], table, gt
    )
    assert next(r for r in with_one if r["pair"] == "WU")["splash"] == 0

    with_two = ss.evaluate_pool(
        mono_w + [green_bomb] + green_fixers[:2], table, gt
    )
    wu = next(r for r in with_two if r["pair"] == "WU")
    assert wu["splash"] == 1
    assert wu["bombs"] == 1
    assert idx  # keep the fixture reference meaningful


def _landcyclers(table):
    return [
        i
        for i in range(len(table.cards))
        if "landcycling" in (table.cards[i].get("oracle_text") or "").lower()
    ]


def test_landcycling_spells_are_not_fixers(table):
    """Board ruling (DEC-926 CEO review): the splash gate is lands only."""
    cyclers = _landcyclers(table)
    assert len(cyclers) == 5
    for i in cyclers:
        assert not table.is_land[i], table.name[i]
        assert table.fix[i] == 0, table.name[i]


def test_common_dual_fixes_exactly_its_two_colours(table, cards):
    duals = [i for i in range(len(table.cards)) if table.is_dual[i]]
    assert len(duals) == 10
    for i in duals:
        pairs = ss.DUAL_MANA_RE.findall(table.cards[i].get("oracle_text") or "")
        assert len(pairs) == 1, table.name[i]
        a, b = pairs[0]
        expected = ss.COLOR_BIT[a] | ss.COLOR_BIT[b]
        assert table.fix[i] == expected, table.name[i]
        assert bin(table.fix[i]).count("1") == 2, table.name[i]
    # the 10 duals cover all 10 colour pairs exactly once
    assert len({table.fix[i] for i in duals}) == 10
    assert cards  # fixture kept meaningful


def test_room_of_refuge_fixes_every_colour(table):
    assert table.fix[table.index["Room of Refuge"]] == 0b11111


def test_spec_splash_mode_restores_landcycling_fixers(cards, pair_table):
    """The superseded spec rule stays reachable for the range table."""
    spec = ss.CardTable(cards, pair_table, count_landcycling_as_fixer=True)
    for i in _landcyclers(spec):
        assert spec.fix[i] == 0b11111, spec.name[i]
    # lands are unaffected by the switch
    assert spec.fix[spec.index["Room of Refuge"]] == 0b11111


def test_viability_thresholds(table):
    mono_w = [
        i
        for i in range(len(table.cards))
        if table.cmask[i] == ss.COLOR_BIT["W"] and not table.is_land[i]
    ][:23]
    over = {table.name[i]: {"grade": 5} for i in mono_w}
    for i in mono_w[:3]:
        over[table.name[i]] = {"grade": 5, "roles": ["removal"]}
    over[table.name[mono_w[3]]] = {"grade": 9}
    gt = _graded(table, over)
    wu = next(r for r in ss.evaluate_pool(mono_w, table, gt) if r["pair"] == "WU")
    assert wu["playables"] == 23 and wu["removal"] == 3 and wu["bombs"] == 1

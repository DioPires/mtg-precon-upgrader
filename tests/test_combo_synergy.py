"""DEC-491 (DEC-476 Phase 2) — Tier-C synergy engine unit tests.

Pins the engine's load-bearing behaviour: the ontology compatibility relation,
DFC face aliasing, the noise-pair exclusion + IDF weighting that keep the ranking
out of "candidate soup", candidate enumeration (pairs/triples/4-cycles with the
deep-focus bound), the coarse RK-5 bands, RK-6 tier invariance, the KB-gap
uncovered distinction, and the shared config both engines consume.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import combo_synergy_lib as L  # noqa: E402


# --------------------------------------------------------------------------- #
# Synthetic ontology + KB — small, deterministic, independent of the full pool #
# --------------------------------------------------------------------------- #
ONT = {
    "version": "test-1",
    "features": [
        {"id": "sac_outlet", "kind": "provides", "economy": "sacrifice",
         "label": "Sacrifice outlet", "pairs_with": ["sac_fodder", "dies_trigger"]},
        {"id": "sac_fodder", "kind": "provides", "economy": "sacrifice",
         "label": "Sac fodder", "pairs_with": ["sac_outlet", "dies_trigger"]},
        {"id": "dies_trigger", "kind": "provides", "economy": "dies",
         "label": "Death payoff", "pairs_with": ["sac_outlet", "sac_fodder"]},
        {"id": "mana_add", "kind": "provides", "economy": "mana",
         "label": "Adds mana", "pairs_with": ["mana_sink"]},
        {"id": "mana_sink", "kind": "wants", "economy": "mana",
         "label": "Mana sink", "pairs_with": ["mana_add"]},
    ],
}


def _entry(oid, name, ci="", provides=(), wants=(), ambient=()):
    def mk(items):
        return [{"feature": f, "magnitude": m} for f, m in items]
    return {"oracle_id": oid, "name": name, "ci": list(ci),
            "provides": mk(provides), "wants": mk(wants), "ambient": mk(ambient)}


def _mini_kb():
    entries = [
        _entry("o1", "Viscera Seer", provides=[("sac_outlet", 1)]),
        _entry("o2", "Blood Artist", provides=[("dies_trigger", 1)]),
        _entry("o3", "Chatterfang Token", provides=[("sac_fodder", 1)]),
        _entry("o4", "Sol Ring", provides=[("mana_add", 2)]),
        _entry("o5", "Hydra X Spell", wants=[("mana_sink", 1)]),
        _entry("o6", "Vanilla Bear", provides=[]),  # covered, featureless
    ]
    by_oid = {e["oracle_id"]: e for e in entries}
    name_to_oid = {}
    for e in entries:
        for k in L.name_keys(e["name"]):
            name_to_oid.setdefault(k, e["oracle_id"])
    return by_oid, name_to_oid


IDF = {"sac_outlet": 3.1, "sac_fodder": 2.1, "dies_trigger": 3.4,
       "mana_add": 2.7, "mana_sink": 1.7}


# --------------------------------------------------------------------------- #
# Compatibility relation                                                       #
# --------------------------------------------------------------------------- #
def test_compat_is_symmetric_closure():
    compat = L.compat_relation(ONT)
    assert "sac_fodder" in compat["sac_outlet"]
    assert "sac_outlet" in compat["sac_fodder"]  # symmetric even if authored one way
    assert "dies_trigger" in compat["sac_outlet"]
    assert "sac_outlet" in compat["dies_trigger"]


def test_name_keys_alias_every_face():
    keys = L.name_keys("Tony Stark // The Invincible Iron Man")
    assert L.normalize_name("Tony Stark") in keys
    assert L.normalize_name("The Invincible Iron Man") in keys  # back face aliased


# --------------------------------------------------------------------------- #
# Name → oracle_id precedence (DEC-553)                                        #
# --------------------------------------------------------------------------- #
def test_full_name_beats_face_alias_regardless_of_load_order():
    """An MDFC back face must never hijack a standalone card's exact name.

    `Grave Researcher // Reanimate` aliases the key "reanimate", which is also
    the full name of the standalone sorcery. Whichever KB shard loaded first
    used to win the key, so gathering-shadow's Reanimate resolved to the MDFC
    and was scored on the wrong card's features."""
    mdfc = ("o_mdfc", "Grave Researcher // Reanimate")
    standalone = ("o_sorcery", "Reanimate")
    for order in ((mdfc, standalone), (standalone, mdfc)):
        n2o = L.build_name_to_oid(order)
        assert n2o["reanimate"] == "o_sorcery", f"face alias won for order {order}"
        # The MDFC keeps its own full name and its front-face alias.
        assert n2o["grave researcher reanimate"] == "o_mdfc"
        assert n2o["grave researcher"] == "o_mdfc"


def test_colliding_names_resolve_to_distinct_oids():
    """A deck holding BOTH the MDFC and the standalone must see two cards, not
    one — the pre-fix map collapsed them onto a single oracle_id."""
    n2o = L.build_name_to_oid(
        [("o_mdfc", "Grave Researcher // Reanimate"), ("o_sorcery", "Reanimate")]
    )

    def resolve(name):
        return next((n2o[k] for k in L.name_keys(name) if k in n2o), None)

    assert resolve("Reanimate") == "o_sorcery"
    assert resolve("Grave Researcher // Reanimate") == "o_mdfc"


def test_first_wins_still_holds_within_a_pass():
    """Genuine same-full-name and same-face-alias collisions keep first-wins."""
    assert L.build_name_to_oid([("a", "Reanimate"), ("b", "Reanimate")])["reanimate"] == "a"
    n2o = L.build_name_to_oid([("a", "Front A // Shared Face"), ("b", "Front B // Shared Face")])
    assert n2o["shared face"] == "a"


# --------------------------------------------------------------------------- #
# Graph: noise-pair exclusion + edge pruning                                   #
# --------------------------------------------------------------------------- #
def test_mana_add_mana_sink_is_excluded_noise():
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    by_oid, _ = _mini_kb()
    cards = [by_oid["o4"], by_oid["o5"]]  # Sol Ring (mana_add) + X spell (mana_sink)
    g = L.build_graph(cards, compat, fmeta, IDF)
    assert g["edges"] == []  # the one ubiquitous non-synergy never forms an edge


def test_real_synergy_forms_an_edge_with_labels():
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    by_oid, _ = _mini_kb()
    cards = [by_oid["o1"], by_oid["o2"]]  # sac_outlet + dies_trigger
    g = L.build_graph(cards, compat, fmeta, IDF)
    assert len(g["edges"]) == 1
    m = g["edges"][0]["matches"][0]
    assert "↔" in m["label"] and m["signal"] > 0  # explainable (DC-3 / TX-1)


# --------------------------------------------------------------------------- #
# Enumeration                                                                  #
# --------------------------------------------------------------------------- #
def test_enumerate_pairs_triples_cycles():
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    by_oid, _ = _mini_kb()
    # Triangle: sac_outlet — sac_fodder — dies_trigger — sac_outlet
    cards = [by_oid["o1"], by_oid["o2"], by_oid["o3"]]
    g = L.build_graph(cards, compat, fmeta, IDF)
    cands = L.enumerate_candidates(g, deep=True)
    assert len(cands["pairs"]) == 3
    assert len(cands["triples"]) == 1  # the closed triangle
    assert cands["truncated"]["deepFocused"] is False


def test_deep_false_returns_pairs_only():
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    by_oid, _ = _mini_kb()
    cards = [by_oid["o1"], by_oid["o2"], by_oid["o3"]]
    g = L.build_graph(cards, compat, fmeta, IDF)
    cands = L.enumerate_candidates(g, deep=False)
    assert cands["triples"] == [] and cands["cycles"] == []


# --------------------------------------------------------------------------- #
# Ranking / bands (RK-5, RK-6)                                                  #
# --------------------------------------------------------------------------- #
def test_band_is_coarse_and_within_tier():
    assert L.band_for(0.9) == "strong"
    assert L.band_for(0.1) == "speculative"
    # RK-6: band is not the tier — a "speculative" band is still Tier C, and a
    # "strong" band never promotes out of Tier C. The engine never emits a tier;
    # every finding is Tier C by construction (see the report consumer).
    assert L.band_for(0.9) != "A"


def test_crowd_prior_only_when_rates_present():
    by_oid, name_to_oid = _mini_kb()
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    names = ["Viscera Seer", "Blood Artist"]
    paste = L.analyze(names, by_oid, name_to_oid, compat, fmeta, edhrec_rates=None, idf=IDF)
    fleet = L.analyze(names, by_oid, name_to_oid, compat, fmeta,
                      edhrec_rates={"Viscera Seer": 40.0, "Blood Artist": 55.0}, idf=IDF)
    assert paste["crowdPriorApplied"] is False
    assert fleet["crowdPriorApplied"] is True
    assert paste["pairs"][0]["signals"]["crowd_prior"] is None
    assert fleet["pairs"][0]["signals"]["crowd_prior"] is not None


# --------------------------------------------------------------------------- #
# KB-gap: uncovered vs covered-featureless                                      #
# --------------------------------------------------------------------------- #
def test_uncovered_is_distinct_from_covered_featureless():
    by_oid, name_to_oid = _mini_kb()
    compat = L.compat_relation(ONT)
    fmeta = L.feature_meta(ONT)
    names = ["Viscera Seer", "Vanilla Bear", "Totally Not A Real Card 99"]
    rep = L.analyze(names, by_oid, name_to_oid, compat, fmeta, idf=IDF)
    # Vanilla Bear is covered (in KB) but featureless → NOT uncovered, just no edges.
    assert rep["uncovered"] == ["Totally Not A Real Card 99"]
    assert rep["counts"]["uncovered"] == 1


# --------------------------------------------------------------------------- #
# Shared config export                                                          #
# --------------------------------------------------------------------------- #
def test_export_config_has_compat_idf_and_constants():
    cfg = L.export_synergy_config(ONT, IDF)
    assert cfg["compat"]["sac_outlet"] == sorted(["sac_fodder", "dies_trigger"])
    assert cfg["noisePairs"] == [["mana_add", "mana_sink"]]
    assert cfg["constants"]["STRONG_BAND_CUT"] == L.STRONG_BAND_CUT
    assert cfg["constants"]["EDGE_MIN_SIGNAL"] == L.EDGE_MIN_SIGNAL


# --------------------------------------------------------------------------- #
# Integration smoke against the committed artifacts (skip if absent)           #
# --------------------------------------------------------------------------- #
def test_feature_index_round_trips_if_present():
    fi = ROOT / "data" / "combo-kb" / "feature-index.json"
    if not fi.exists():
        return
    by_oid, name_to_oid = L.load_index_from_feature_index(str(fi))
    assert len(by_oid) > 1000
    # A known aristocrats pairing resolves and produces at least one edge.
    ont = L.load_ontology()
    rep = L.analyze(["Blood Artist", "Viscera Seer"], by_oid, name_to_oid,
                    L.compat_relation(ont), L.feature_meta(ont), idf=L.load_feature_idf())
    assert rep["nodeCount"] == 2


def test_parity_fixture_matches_engine():
    """The committed parity fixture must equal a fresh engine run — guards against
    the fixture drifting from the Python source of truth (the TS test asserts the
    other half)."""
    fx = ROOT / "web" / "src" / "lib" / "__fixtures__" / "synergy-parity.json"
    fi = ROOT / "data" / "combo-kb" / "feature-index.json"
    if not (fx.exists() and fi.exists()):
        return
    fixture = json.loads(fx.read_text())
    by_oid, name_to_oid = L.load_index_from_feature_index(str(fi))
    ont = L.load_ontology()
    rep = L.analyze(fixture["names"], by_oid, name_to_oid, L.compat_relation(ont),
                    L.feature_meta(ont), edhrec_rates=None, deep=True, idf=L.load_feature_idf())

    def slim(c):
        return {"cards": c["cards"], "band": c["band"], "economies": c["economies"],
                "edges": sorted([{k: e[k] for k in
                                  ("from", "to", "fromFeature", "toFeature", "magnitude", "label")}
                                 for e in c["edges"]],
                                key=lambda e: (e["from"], e["to"], e["fromFeature"], e["toFeature"]))}
    assert [slim(c) for c in rep["pairs"]] == fixture["pairs"]
    assert [slim(c) for c in rep["triples"]] == fixture["triples"]
    assert rep["counts"] == fixture["counts"]

"""DEC-501 (DEC-476 Phase 3) — Tier-B loop verifier unit tests.

Pins the verifier's load-bearing, SOUNDNESS-critical behaviour: the closure model
(PRD 6.1-6.5), the (k, finite-zone bound) classification, the provenance gate
(plan 6b), the corroboration-vs-novel split (DB-7), the CLOSE_SAFE soundness
backstop (QE-4), deficit vectors (6.6 / DB-4), ordering-optimised prerequisites
(PR-3), the command-zone / guard set (IN-4), the provenance chain (DB-6), and mana
parsing. The regression guard against the Basalt+Thran false positive (two mana
rocks are NOT infinite mana) is the single most important test here — it protects
the worst failure class (QE-4.1, false Tier-B positive).
"""

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import combo_verifier_lib as V  # noqa: E402


# --------------------------------------------------------------------------- #
# Synthetic KB entries — deterministic, independent of the shipped pool.       #
# Modelled on the real deterministic-extraction output shape.                  #
# --------------------------------------------------------------------------- #
def _entry(oid, name, *, provides=(), wants=(), ambient=(), triggers=(),
           guards=(), events=(), activated=(), mana_cost=None, ci=(),
           prov="deterministic"):
    def items(seq):
        return [{"feature": f, "magnitude": m, "economy": eco,
                 "evidence": ev, "provenance": p or prov}
                for (f, m, eco, ev, p) in seq]
    return {
        "oracle_id": oid, "name": name, "color_identity": list(ci),
        "ontology_version": "1.0.1", "extractor_version": "det-1.0.1",
        "corpus_version": "2026-08-15T00:00:00+00:00",
        "provides": items(provides), "wants": items(wants), "ambient": items(ambient),
        "triggers": [{"trigger": t, "guarded": False, "provenance": prov} for t in triggers],
        "guards": [{"guard": g, "provenance": prov} for g in guards],
        "events_emitted": list(events),
        "costs": {"mana_cost": mana_cost, "mana_value": None,
                  "activated": [{"cost": c, "provenance": prov} for c in activated]},
    }


# A self-untapping mana rock: taps for 3, untaps for {3} (net 0 alone).
def basalt(prov="deterministic"):
    return _entry("basalt", "Basalt Monolith", prov=prov,
                  provides=[("mana_add", 3, "mana", "Add {C}{C}{C", prov)],
                  wants=[("mana_sink", 1, "mana", "{3}:", prov),
                         ("tap_ability", 1, "untap", "{T}:", prov)],
                  guards=["summoning_sick"], events=["untap"],
                  activated=["{T}", "{3}"], mana_cost="{3}")


# A triggered per-tap mana amplifier: +1 mana whenever you tap for {C}.
def forsaken(prov="deterministic"):
    return _entry("forsaken", "Forsaken Monument", prov=prov,
                  provides=[("mana_add", 1, "mana", "add an additional {C", prov)],
                  triggers=["Whenever you tap a permanent for {C}"],
                  guards=["control_requirement"], mana_cost="{5}")


# A plain mana rock (Thran Dynamo class): taps for 3, no untap, no trigger.
def thran():
    return _entry("thran", "Thran Dynamo",
                  provides=[("mana_add", 3, "mana", "Add {C}{C}{C", "deterministic")],
                  activated=["{T}"], mana_cost="{4}")


# --------------------------------------------------------------------------- #
# Closure + classification                                                     #
# --------------------------------------------------------------------------- #
def test_untap_mana_closes_infinite():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    assert v is not None and v.closes
    assert v.loop_class == "infinite" and v.k == 0
    assert v.ledger["mana"] == 1  # net +1 per cycle (3 + 1 amp - 3 untap)
    assert v.result_types and v.result_types[0].startswith("infinite_mana")
    assert v.accumulators == ["mana"]


def test_basalt_plus_thran_is_NOT_infinite():
    # THE critical QE-4 regression guard: two independent mana rocks are not an
    # infinite loop. Thran Dynamo is not a per-tap amplifier, so it must not count.
    v = V.verify_candidate([basalt(), thran()], in_curated=False)
    assert v is not None
    assert not v.closes, "two mana rocks must never verify as infinite mana"
    assert not v.novel_eligible


def test_basalt_alone_is_near_miss_with_deficit():
    v = V.verify_candidate([basalt()], in_curated=False)
    assert v is not None and not v.closes
    assert v.deficit and v.deficit[0]["resource"] == "mana"
    assert v.deficit[0]["shortfall"] == 1  # needs +1 mana to reach strict gain


# --------------------------------------------------------------------------- #
# Corroboration vs novel (DB-7 / DC-6)                                         #
# --------------------------------------------------------------------------- #
def test_corroboration_is_not_novel():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=True)
    assert v.closes and not v.novel_eligible  # curated => corroboration, not novel


def test_novel_eligible_when_not_curated():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    assert v.closes and v.novel_eligible


# --------------------------------------------------------------------------- #
# Provenance gate (plan decision 6b)                                           #
# --------------------------------------------------------------------------- #
def test_provenance_gate_caps_llm_amplifier():
    # The amplifier's mana_add is LLM-sourced => the gate must demote a would-be
    # Tier-B loop to Tier C with an explicit cap reason, never verify it.
    f = forsaken()
    for it in f["provides"]:
        if it["feature"] == "mana_add":
            it["provenance"] = "llm"
    v = V.verify_candidate([basalt(), f], in_curated=False)
    assert v is not None
    assert not v.closes and v.tier_capped is not None
    assert "provenance gate" in v.tier_capped and not v.novel_eligible


def test_deterministic_amplifier_not_capped():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    assert v.tier_capped is None


# --------------------------------------------------------------------------- #
# CLOSE_SAFE backstop + sac-recursion abstention (QE-4)                        #
# --------------------------------------------------------------------------- #
def test_sac_recursion_never_closes():
    outlet = _entry("altar", "Ashnod's Altar",
                    provides=[("mana_add", 2, "mana", "Add {C}{C", "deterministic"),
                              ("sac_outlet", 1, "sacrifice", "Sacrifice a creature:", "deterministic")],
                    events=["sacrifice"], activated=["Sacrifice a creature"], mana_cost="{3}")
    fodder = _entry("skel", "Reassembling Skeleton",
                    provides=[("sac_fodder", 1, "sacrifice", "return", "deterministic")],
                    activated=["{1}{B}"], mana_cost="{1}{B}")
    payoff = _entry("blood", "Blood Artist",
                    provides=[("dies_trigger", 1, "dies", "dies", "deterministic"),
                              ("drain", 1, "drain", "loses 1 life", "deterministic")],
                    triggers=["Whenever this creature or another creature dies"],
                    events=["dies"], mana_cost="{1}{B}")
    v = V.verify_candidate([outlet, fodder, payoff], in_curated=False)
    assert v is not None and v.template == "sac_recursion"
    assert not v.closes  # unsound to price the return cost => never verify
    assert v.loop_class == "engine"
    assert v.deficit and v.deficit[0]["shortfall"] is None  # KB-gap abstention


# --------------------------------------------------------------------------- #
# Prerequisites (PR-3): ordering optimisation + guard set (IN-4)               #
# --------------------------------------------------------------------------- #
def test_prerequisites_ordering_and_guards():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    pr = v.prerequisites
    # Best ordering taps for mana BEFORE paying the untap, so no floating mana is
    # required to start (min initial stock 0).
    assert pr["minInitialMana"] == 0
    assert "ordering" in pr and pr["ordering"]
    # Guard set carries both members' guards (summoning-sickness + control).
    assert "summoning_sick" in pr["guards"] and "control_requirement" in pr["guards"]


def test_ordering_optimisation_minimises_stock():
    # A synthetic loop that must pay 2 before producing 3 under the WORST ordering,
    # but 0 under the best (produce first). The optimiser must find 0.
    rock = _entry("r", "Rock",
                  provides=[("mana_add", 3, "mana", "Add {C}{C}{C", "deterministic")],
                  events=["untap"], activated=["{T}", "{2}"], mana_cost="{2}")
    amp = forsaken()
    v = V.verify_candidate([rock, amp], in_curated=False)
    assert v.prerequisites["minInitialMana"] == 0


# --------------------------------------------------------------------------- #
# Provenance chain (DB-6) + result types (RT-1)                                #
# --------------------------------------------------------------------------- #
def test_provenance_chain_records_versions():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    p = v.provenance
    assert p["ontologyVersion"] == "1.0.1"
    assert p["extractorVersion"] == "det-1.0.1"
    assert len(p["members"]) == 2
    assert "deterministic" in p["gate"]


# --------------------------------------------------------------------------- #
# Mana parsing                                                                 #
# --------------------------------------------------------------------------- #
def test_parse_mana():
    assert V.parse_mana("{3}") == 3
    assert V.parse_mana("{1}{B}") == 2
    assert V.parse_mana("{W}{U}{B}{R}{G}") == 5
    assert V.parse_mana("{C}{C}") == 2
    assert V.parse_mana("{X}") is None            # X is unpriceable
    assert V.parse_mana("Sacrifice a creature") is None  # non-mana component
    assert V.parse_mana("{T}") is None            # tap is not pure mana
    assert V.parse_mana("{G}, {T}") is None       # mana + tap => not pure mana
    assert V.parse_mana("") is None


# --------------------------------------------------------------------------- #
# Determinism (DB-5)                                                           #
# --------------------------------------------------------------------------- #
def test_determinism():
    a = V.verify_candidate([basalt(), forsaken()], in_curated=False).to_dict()
    b = V.verify_candidate([basalt(), forsaken()], in_curated=False).to_dict()
    assert a == b


def test_no_template_returns_none():
    plain = _entry("x", "Vanilla Bear",
                   provides=[("draw", 1, "draw", "draw a card", "deterministic")])
    assert V.verify_candidate([plain], in_curated=False) is None

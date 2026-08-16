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

import build_combo_kb as build  # noqa: E402
import combo_verifier_lib as V  # noqa: E402

_ONT = build.load_ontology()


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
# N1 — untap_mana self-scope + cost attribution (DEC-511, QE-4)                #
# --------------------------------------------------------------------------- #
# A mana rock whose priced untap targets ANOTHER permanent (Voltaic Key /
# Voltaic Construct / Kiora's Follower / Vizier of Tumbling Sands shape): it emits
# an `untap` event and adds mana, but the untap is NOT self-scoped.
def target_untap_rock():
    return _entry("vtr", "Voltaic Target Rock",
                  provides=[("mana_add", 3, "mana", "Add {C}{C}{C", "deterministic"),
                            ("untap_permanent", 1, "untap", "Untap target artifact", "deterministic")],
                  events=["untap"], activated=["{T}", "{2}"], mana_cost="{4}")


def test_target_untap_rock_is_not_self_untap():
    # Reviewer's synthetic N1 false positive: "adds 3 mana; {2}: untap target
    # artifact" + an amplifier verified as infinite mana under the old code because
    # untap_cost() never checked self-scope. It must now abstain (untap is directed
    # at another permanent — no intrinsic recurrence).
    m = V.MemberModel(target_untap_rock())
    assert m.untaps_other is True
    assert m.untap_cost() is None
    v = V.verify_candidate([target_untap_rock(), forsaken()], in_curated=False)
    assert not (v and v.closes), "a target-untapper must never seed infinite mana"


def test_ambiguous_untap_cost_abstains():
    # Cost-attribution gap (N1): a self-untapper with TWO distinct priced abilities
    # (untap {3} + an unrelated {1}) must not have its untap cost read as the min
    # ({1}) — that understates u and would fabricate closure (3 + amp - 1 > 0). With
    # the untap cost unattributable, the verifier abstains.
    ambiguous = _entry("asr", "Ambiguous Rock",
                       provides=[("mana_add", 3, "mana", "Add {C}{C}{C", "deterministic")],
                       events=["untap"], activated=["{T}", "{3}", "{1}"], mana_cost="{3}")
    assert V.MemberModel(ambiguous).untap_cost() is None
    v = V.verify_candidate([ambiguous, forsaken()], in_curated=False)
    assert not (v and v.closes), "unattributable untap cost must abstain, not close"


def test_single_priced_untap_still_attributes():
    # The attribution guard must not over-fire: Basalt has exactly one priced
    # (non-{T}) activated cost, {3}, so it is still read as the untap cost and the
    # real Basalt + Forsaken loop still closes.
    assert V.MemberModel(basalt()).untap_cost() == 3


# --------------------------------------------------------------------------- #
# N2 — blink_untap_mana requires a STRICT mana surplus (DEC-511, QE-4)         #
# --------------------------------------------------------------------------- #
def _blinker(cost):
    return _entry("blk", "Cheap Blinker",
                  provides=[("blink", 1, "blink", "exile then return it", "deterministic")],
                  activated=[cost], mana_cost="{3}")


def _etb_untap(n):
    return _entry("dst", "Untapper Drake",
                  provides=[("etb_trigger", 1, "etb", "when it enters", "deterministic"),
                            ("untap_permanent", n, "untap", "untap up to %d land(s)" % n, "deterministic")],
                  mana_cost="{4}")


def test_blink_break_even_is_not_infinite_mana():
    # Reviewer's synthetic N2 false positive: blink costs {1}, ETB untaps 1 land =>
    # net 0 mana per cycle. Break-even is a sustainable engine, NOT infinite mana;
    # the verifier must abstain (needs lands > blink_cost, not >=).
    v = V.verify_candidate([_blinker("{1}"), _etb_untap(1)], in_curated=False)
    assert not (v and v.closes), "break-even blink must never verify as infinite mana"


def test_blink_strict_surplus_closes_infinite_mana():
    # Boundary check: blink {1}, ETB untaps 2 lands => strict +1 mana per cycle =>
    # genuine infinite mana. Locks the > boundary from the other side.
    v = V.verify_candidate([_blinker("{1}"), _etb_untap(2)], in_curated=False)
    assert v is not None and v.closes
    assert v.template == "blink_untap_mana" and v.loop_class == "infinite"
    assert v.ledger["mana"] == 1


# --------------------------------------------------------------------------- #
# N3 — command-zone guard (IN-4, DEC-511)                                      #
# --------------------------------------------------------------------------- #
def test_command_zone_guard_emitted_for_commander_member():
    b = basalt()
    v = V.verify_candidate([b, forsaken()], in_curated=False, commander_oids={b["oracle_id"]})
    assert "command_zone" in v.prerequisites["guards"]


def test_no_command_zone_guard_without_commander():
    v = V.verify_candidate([basalt(), forsaken()], in_curated=False)
    assert "command_zone" not in v.prerequisites["guards"]


# --------------------------------------------------------------------------- #
# N4 — member ordering is deterministic (DB-5, DEC-511)                        #
# --------------------------------------------------------------------------- #
def test_member_order_is_oracle_id_sorted_regardless_of_input_order():
    a = V.verify_candidate([basalt(), forsaken()], in_curated=False).to_dict()
    b = V.verify_candidate([forsaken(), basalt()], in_curated=False).to_dict()
    assert a == b  # input order must not affect provenance.members or trace


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


# --------------------------------------------------------------------------- #
# Graveyard-return loop template (DEC-526)                                     #
# --------------------------------------------------------------------------- #
def _gr(oid, name, type_line, mv, *, provides=(), activated=(), guards=()):
    e = _entry(oid, name, provides=provides, activated=activated, guards=guards)
    e["type_line"] = type_line
    e["costs"]["mana_value"] = mv
    return e


def _reanimator(oid="suntitan", name="Sun Titan", bound=3, coven=False):
    return _gr(oid, name, "Creature — Giant", 6, guards=(["coven"] if coven else []),
               provides=[("etb_trigger", 1, "etb", "When this creature enters", "deterministic"),
                         ("etb_reanimate", bound, "reanimate",
                          "return target permanent card with mana value %d or less" % bound,
                          "deterministic")])


def _aura_fetcher(oid="boon", name="Boonweaver Giant", bound=99):
    return _gr(oid, name, "Creature — Giant Monk", 7,
               provides=[("etb_trigger", 1, "etb", "When this creature enters", "deterministic"),
                         ("aura_fetch", bound, "aura_fetch",
                          "search your library for an Aura card and put it onto the battlefield attached",
                          "deterministic")])


def _death_aura(oid="necro", name="Necrogen Communion", mv=2, aura=True):
    return _gr(oid, name, "Enchantment — Aura" if aura else "Enchantment", mv,
               provides=[("death_return", 1, "death_return",
                          "When enchanted creature dies, return that card to the battlefield",
                          "deterministic")])


def _exile_creature(oid="werefox", name="Werefox Bodyguard", mv=3):
    return _gr(oid, name, "Creature — Elf Fox Knight", mv,
               provides=[("etb_trigger", 1, "etb", "When this creature enters", "deterministic"),
                         ("exile_until_leaves", 1, "exile_return",
                          "exile up to one other target non-Fox creature until this creature leaves",
                          "deterministic")])


def _free_sac(oid="viscera", name="Viscera Seer"):
    return _gr(oid, name, "Creature — Vampire Wizard", 1,
               activated=["Sacrifice a creature"],
               provides=[("sac_outlet", 1, "sacrifice", "Sacrifice a creature:", "deterministic")])


def test_graveyard_return_closes_infinite_death_triggers():
    v = V.verify_candidate([_reanimator(), _death_aura(), _free_sac()], in_curated=False)
    assert v is not None and v.closes
    assert v.template == "graveyard_return"
    assert v.loop_class == "infinite" and v.k == 0
    assert v.result_types == ["infinite_death_triggers"]
    assert v.accumulators == ["death_triggers"]
    assert v.novel_eligible  # not curated + CLOSE_SAFE + strict gain + no deficit


def test_graveyard_return_respects_mv_bound():
    # Shepherd-class bound 2 cannot re-fetch a mana-value-3 partner ⇒ no close.
    v = V.verify_candidate(
        [_reanimator("shep", "Shepherd of the Cosmos", bound=2),
         _death_aura("gift", "Gift of Immortality", mv=3), _free_sac()],
        in_curated=False)
    assert not (v and v.closes)


def test_graveyard_return_needs_free_sac_outlet():
    # No free creature-sac outlet ⇒ the loop cannot iterate ⇒ no verdict.
    v = V.verify_candidate([_reanimator(), _death_aura()], in_curated=False)
    assert v is None


def test_graveyard_return_exile_creature_loop_closes():
    v = V.verify_candidate([_reanimator(), _exile_creature(), _free_sac()], in_curated=False)
    assert v is not None and v.closes and v.template == "graveyard_return"


def test_aura_fetcher_requires_aura_partner():
    # An aura-fetch reanimator closes with a death-return AURA …
    v = V.verify_candidate([_aura_fetcher(), _death_aura(aura=True), _free_sac()], in_curated=False)
    assert v is not None and v.closes
    # … but NOT with a plain (non-Aura) enchantment death-return (Angelic Renewal class) …
    v2 = V.verify_candidate(
        [_aura_fetcher(), _death_aura("ang", "Angelic Renewal", mv=2, aura=False), _free_sac()],
        in_curated=False)
    assert not (v2 and v2.closes)
    # … and NOT with an exile-until-leaves creature (it can only re-fetch an Aura).
    v3 = V.verify_candidate([_aura_fetcher(), _exile_creature(), _free_sac()], in_curated=False)
    assert not (v3 and v3.closes)


def test_coven_reanimator_abstains():
    v = V.verify_candidate(
        [_reanimator("redemption", "Redemption Choir", bound=3, coven=True),
         _death_aura(), _free_sac()],
        in_curated=False)
    assert v is not None and v.template == "graveyard_return"
    assert not v.closes and v.loop_class == "engine"
    assert v.deficit and v.deficit[0]["shortfall"] is None  # guarded abstain (QE-4)
    assert not v.novel_eligible


def test_free_creature_sac_excludes_mana_tap_and_non_creature():
    # Mana-gated, tap-gated, or artifact-only sac outlets are NOT free creature sacs.
    mana_sac = _gr("ms", "Costly Sac", "Creature — Zombie", 2,
                   activated=["{1}, Sacrifice a creature"],
                   provides=[("sac_outlet", 1, "sacrifice", "Sacrifice a creature:", "deterministic")])
    tap_sac = _gr("ts", "Tap Sac", "Creature — Zombie", 2,
                  activated=["{T}, Sacrifice a creature"],
                  provides=[("sac_outlet", 1, "sacrifice", "Sacrifice a creature:", "deterministic")])
    artifact_sac = _gr("as", "Ironworks", "Artifact", 2,
                       activated=["Sacrifice an artifact"],
                       provides=[("sac_outlet", 1, "sacrifice", "Sacrifice an artifact:", "deterministic")])
    assert not V.MemberModel(mana_sac).free_creature_sac()
    assert not V.MemberModel(tap_sac).free_creature_sac()
    assert not V.MemberModel(artifact_sac).free_creature_sac()
    assert V.MemberModel(_free_sac()).free_creature_sac()
    # None of these complete a graveyard-return loop for the reanimator + aura pair.
    for bad in (mana_sac, tap_sac, artifact_sac):
        v = V.verify_candidate([_reanimator(), _death_aura(), bad], in_curated=False)
        assert v is None or not v.closes


def _extract(name, type_line, oracle, mana_cost, cmc):
    """Real deterministic extraction (build_combo_kb) → a full KB entry, so the
    extraction-level fixes (DEC-530 F1) are exercised end-to-end through
    verify_candidate, not hand-waved with a pre-shaped synthetic entry."""
    card = {"name": name, "type_line": type_line, "oracle_text": oracle,
            "mana_cost": mana_cost, "cmc": cmc, "oracle_id": name,
            "color_identity": []}
    return build.build_entry(card, _ONT, "v")


def test_graveyard_return_opponent_restricted_exiler_never_closes():  # DEC-530 F1
    # Fairgrounds Warden exiles only a creature AN OPPONENT controls — it can never
    # exile the loop's own reanimator, so the extractor must not tag it and the loop
    # must not close. (Repro: Sun Titan + Fairgrounds Warden + Viscera Seer.)
    warden = _extract(
        "Fairgrounds Warden", "Creature — Human Soldier",
        "When this creature enters, exile target creature an opponent controls "
        "until this creature leaves the battlefield.", "{2}{W}", 3.0)
    assert not any(i["feature"] == "exile_until_leaves" for i in warden["provides"])
    v = V.verify_candidate([_reanimator(), warden, _free_sac()], in_curated=False)
    assert v is None or not v.closes
    # An any-target exiler (Fiend Hunter) with the SAME structure still closes.
    hunter = _extract(
        "Fiend Hunter", "Creature — Human Cleric",
        "When this creature enters, you may exile another target creature.\n"
        "When this creature leaves the battlefield, return the exiled card to the "
        "battlefield under its owner's control.", "{1}{W}{W}", 3.0)
    v2 = V.verify_candidate([_reanimator(), hunter, _free_sac()], in_curated=False)
    assert v2 is not None and v2.closes and v2.template == "graveyard_return"


def test_free_creature_sac_excludes_self_only_saccers():  # DEC-530 F2
    # 'Sacrifice this creature' can fire once on the outlet itself — it cannot be the
    # loop's repeatable free outlet for the OTHER creatures. (Repro: Sun Titan +
    # Fiend Hunter + Children of Korlis.)
    korlis = _gr("korlis", "Children of Korlis", "Creature — Human Rebel", 3,
                 activated=["Sacrifice this creature"],
                 provides=[("sac_outlet", 1, "sacrifice",
                            "Sacrifice this creature:", "deterministic")])
    elder = _gr("elder", "Sakura-Tribe Elder", "Creature — Snake Shaman", 2,
                activated=["Sacrifice this creature"],
                provides=[("sac_outlet", 1, "sacrifice",
                           "Sacrifice this creature:", "deterministic")])
    assert not V.MemberModel(korlis).free_creature_sac()
    assert not V.MemberModel(elder).free_creature_sac()
    # A generic 'Sacrifice a creature' outlet is still accepted.
    assert V.MemberModel(_free_sac()).free_creature_sac()
    # Neither self-saccer completes a graveyard-return loop.
    for bad in (korlis, elder):
        v = V.verify_candidate([_reanimator(), _exile_creature(), bad], in_curated=False)
        assert v is None or not v.closes


def test_graveyard_return_corroboration_not_novel():
    v = V.verify_candidate([_reanimator(), _death_aura(), _free_sac()], in_curated=True)
    assert v.closes and not v.novel_eligible

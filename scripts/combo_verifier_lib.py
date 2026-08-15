#!/usr/bin/env python3
"""Tier-B loop verifier — DEC-501 (DEC-476 Phase 3).

The deterministic (DB-5) closure checker for the Combo Lab. Given a small
candidate loop (2-3 cycle pieces + any number of ambient modifiers, DB-3), it
decides whether the members form a *closed loop* under the semantic model of PRD
6.1-6.5, classifies the verified loop by the pair (k, finite-zone bound) recorded
in the plan clarification, computes the deficit vector on failure (6.6 / DB-4),
computes Tier-B prerequisites with ordering optimization + command-zone guards
(PR-3 / IN-4), maps result types (RT-1), and records the full provenance chain
(DB-6 / TX-1) so any verdict audits back to the KB entries it consumed.

Soundness is the invariant, not recall. The worst failure class is a false
Tier-B positive (QE-4.1): the verifier must never label a loop "verified" that
does not close under the model. Two mechanisms enforce this:

  1. **Provenance gate (plan decision 6b, ENFORCED).** The verifier consumes only
     ``combo_kb_lib.tier_b_view`` items — deterministic or human-reviewed. If a
     member's loop-relevant item was produced by the LLM classifier (or a
     community tag), the candidate is *capped at Tier C* with a recorded reason;
     it never yields a Tier-B verdict until a human reviews the entry (KB-7).

  2. **Corroboration vs. novel split (DB-7 / DC-6).** A loop already in the
     curated corpus is reported at Tier A; the verifier's verdict is recorded as
     *corroboration* and can never inflate the tier — so corroboration is the
     safe path and is exactly what QE-1b measures. A loop NOT in the corpus that
     the verifier would call verified is a *novel* Tier-B finding; DC-6 says novel
     infinite discovery is rare, so the novel gate is stricter still (no
     unresolved cost anywhere in the cycle, strict resource gain, proven
     recurrence). ``verify_candidate`` returns both the raw closure result and the
     novel-eligibility flag; callers decide presentation.

Everything here is pure computation over the cached KB (NF-1: no generative call
on the query path). The TS mirror ``web/src/lib/comboVerify.ts`` re-implements the
same closure rules for paste mode; ``web/src/lib/__fixtures__/verify-parity.json``
+ ``tests/test_combo_verifier.py`` pin byte-parity.

DEC-476 Phase 3 (DEC-501). See docs/combo-verifier.md for the closure model and
the per-template soundness arguments.
"""

from __future__ import annotations

import glob
import itertools
import json
import os
import re
from typing import Optional

import combo_kb_lib as KB
import combo_synergy_lib as SYN

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENTRIES_DIR = os.path.join(ROOT, "data", "combo-kb", "entries")


def load_raw_kb_index(entries_dir: str = ENTRIES_DIR) -> tuple[dict[str, dict], dict[str, str]]:
    """Load the FULL raw KB entries the verifier needs (events_emitted, costs,
    per-item provenance — none of which survive the synergy layer's lean
    projection). Returns (oracle_id → raw entry, normalized name key → oracle_id),
    aliasing every DFC/split face via ``combo_synergy_lib.name_keys``."""
    by_oid: dict[str, dict] = {}
    name_to_oid: dict[str, str] = {}
    for shard in sorted(glob.glob(os.path.join(entries_dir, "*.json"))):
        for e in json.load(open(shard)):
            oid = e.get("oracle_id")
            if not oid:
                continue
            by_oid[oid] = e
            for k in SYN.name_keys(e.get("name", "")):
                name_to_oid.setdefault(k, oid)
    return by_oid, name_to_oid

# ─── Closure-model constants ─────────────────────────────────────────────────────
# The verifier scope (DB-3): 2-3 cycle pieces + any number of ambient modifiers.
MAX_CYCLE_PIECES = 3

# Finite zones (PRD 6.1 / ontology). A loop that net-consumes one of these without
# replenishing is *bounded*, not infinite (6.5.4). The bound is derived from the
# zone's typical Commander size when the per-iteration consumption is known.
FINITE_ZONES = ("library", "graveyard", "exile")
# A 99-card singleton library is the canonical finite bound source; the graveyard
# and exile bounds are loop-state-dependent and reported as "derivable" only when
# the per-iteration consumption is a known constant.
DEFAULT_LIBRARY_SIZE = 99

_PIP_RE = re.compile(r"\{([^}]+)\}")
_GENERIC_RE = re.compile(r"^\d+$")
_COLOR_PIPS = set("WUBRG")


# ─── Mana / cost parsing (deterministic) ─────────────────────────────────────────
_HYBRID = frozenset(
    {"W/U", "W/B", "U/B", "U/R", "B/R", "B/G", "R/G", "R/W", "G/W", "G/U",
     "2/W", "2/U", "2/B", "2/R", "2/G"}
)


def parse_mana(cost: str) -> Optional[int]:
    """The mana value of a cost string IFF the cost is *purely mana*; otherwise
    None.

    Soundness (QE-4): a cost with ANY non-mana component — a tap ({T}), an untap
    ({Q}), a sacrifice/discard/life-payment (textual), or an unpriceable amount
    ({X}, Phyrexian) — returns None, because the verifier must never treat such a
    cost as "free mana" and thereby fabricate a closed loop. Only "{3}", "{1}{B}",
    "{C}{C}" and the like return an integer. This is deliberately strict: the two
    false positives it exists to prevent are a tap-gated blink priced as 0 and a
    target-untapper's "{G}{T}" priced as 1.
    """
    if not cost:
        return None
    pips = _PIP_RE.findall(cost)
    # Any text remaining after removing the mana pips is a non-mana cost component.
    residue = _PIP_RE.sub("", cost)
    if residue.strip(" ,.:"):
        return None
    if not pips:
        return None
    total = 0
    for p in pips:
        pu = p.upper()
        if _GENERIC_RE.match(pu):
            total += int(pu)
        elif pu in _COLOR_PIPS or pu == "C":
            total += 1
        elif pu in _HYBRID:
            total += 2 if pu.startswith("2/") else 1
        else:
            return None  # {T}, {Q}, {X}, Phyrexian, energy, snow — not pure mana
    return total


def mana_add_pips(cost: str) -> Optional[int]:
    """Colorless/colored pip count produced by an 'Add {…}' clause (magnitude
    fallback). We prefer the KB ``magnitude`` (already a deterministic pip count);
    this is only used when a raw cost string must be re-priced."""
    return parse_mana(cost)


# ─── Feature model over a tier_b_view'd entry ────────────────────────────────────
class MemberModel:
    """The loop-relevant projection of one KB entry, AFTER the provenance gate.

    Only deterministic / human-reviewed items survive (``tier_b_view``); the set
    of fields the gate *capped* (dropped llm/community items from) is retained so a
    caller can explain why a candidate could not reach Tier B."""

    def __init__(self, entry: dict, gate: bool = True):
        # gate=True applies the Tier-B provenance gate (deterministic/human only);
        # gate=False keeps every item — used only to detect a would-be-Tier-B loop
        # that the gate demotes to Tier C, so the cap can be reported (not to verify).
        view = KB.tier_b_view(entry) if gate else entry
        self.gated = gate
        self.oracle_id: str = entry.get("oracle_id", "")
        self.name: str = entry.get("name", "")
        self.color_identity = list(entry.get("color_identity", []) or [])
        self.tier_b_capped = set(KB.tier_b_view(entry).get("tier_b_capped", []))
        self.ontology_version = entry.get("ontology_version")
        self.extractor_version = entry.get("extractor_version")
        self.corpus_version = entry.get("corpus_version")

        self.provides = view.get("provides") or []
        self.wants = view.get("wants") or []
        self.ambient = view.get("ambient") or []
        self.triggers = view.get("triggers") or []
        self.guards = [g.get("guard") for g in (view.get("guards") or [])]
        self.events_emitted = list(entry.get("events_emitted") or [])  # structural
        costs = view.get("costs") or {}
        self.mana_cost = costs.get("mana_cost")
        self.mana_value = costs.get("mana_value")
        self.activated = [c.get("cost") for c in (costs.get("activated") or [])]

    # -- feature helpers -----------------------------------------------------------
    def has_feature(self, fid: str) -> bool:
        return any(
            it.get("feature") == fid
            for it in (self.provides + self.wants + self.ambient)
        )

    def feature_magnitude(self, fid: str) -> int:
        best = 0
        for it in self.provides + self.wants + self.ambient:
            if it.get("feature") == fid:
                best = max(best, int(it.get("magnitude", 1) or 1))
        return best

    def feature_economy(self, fid: str) -> str:
        for it in self.provides + self.wants + self.ambient:
            if it.get("feature") == fid:
                return it.get("economy", "")
        return ""

    def mana_produced(self) -> int:
        """Best (max) single mana_add magnitude on this card — the mana it makes per
        activation of its mana ability."""
        return self.feature_magnitude("mana_add")

    def untap_cost(self) -> Optional[int]:
        """Generic-mana cost of a self-untap activated ability, or None if the card
        does not self-untap or the untap cost is unpriceable. Detected by an
        emitted ``untap`` event plus a pure-mana activated cost that is NOT the
        mana-production tap ({T})."""
        if "untap" not in self.events_emitted:
            return None
        best: Optional[int] = None
        for c in self.activated:
            if c is None:
                continue
            if c.strip() == "{T}":
                continue  # the tap-for-mana ability, not the untap
            m = parse_mana(c)
            if m is not None:
                best = m if best is None else min(best, m)
        return best


# ─── Verdict container ───────────────────────────────────────────────────────────
class Verdict:
    """A closure result for one candidate. ``closes`` is the model-level decision;
    ``tier`` is what the caller may legally present (capped by the provenance gate
    and the corroboration/novel split)."""

    def __init__(self):
        self.closes: bool = False
        self.template: str = ""
        self.k: Optional[int] = None            # per-iteration turn-phase budget cost
        self.loop_class: str = ""               # 'infinite' | 'engine' | ''
        self.finite_zone_bound: Optional[dict] = None  # {'zone','bound'} attribute
        self.result_types: list[str] = []      # RT-1 tags
        self.accumulators: list[str] = []       # resources with net > 0
        self.ledger: dict = {}                  # per-resource net delta (known ones)
        self.deficit: list[dict] = []           # 6.6 deficit vector on failure
        self.trace: list[str] = []              # human-legible loop trace (TX-1)
        self.prerequisites: dict = {}           # PR-3
        self.provenance: dict = {}              # DB-6 chain
        self.tier_capped: Optional[str] = None  # non-None => forced to Tier C
        self.novel_eligible: bool = False       # strict-gate pass for novel Tier B

    def to_dict(self) -> dict:
        return {
            "closes": self.closes,
            "template": self.template,
            "k": self.k,
            "loopClass": self.loop_class,
            "finiteZoneBound": self.finite_zone_bound,
            "resultTypes": self.result_types,
            "accumulators": self.accumulators,
            "ledger": {k: v for k, v in sorted(self.ledger.items())},
            "deficit": self.deficit,
            "trace": self.trace,
            "prerequisites": self.prerequisites,
            "provenance": self.provenance,
            "tierCapped": self.tier_capped,
            "novelEligible": self.novel_eligible,
        }


# ─── Closure templates ───────────────────────────────────────────────────────────
# Each template inspects the member models and, if the structural pattern is
# present, fills a Verdict — closing it iff the resource conditions of PRD 6.5 hold,
# and otherwise recording the deficit vector so the same structure surfaces as a
# Tier-B near-miss (NM-1 Tier B) and a UC3 failure explanation (TX-3). The
# per-template soundness argument lives in docs/combo-verifier.md.


# A "whenever you tap … for {C}"-style trigger that adds mana per tap event.
_AMPLIFIER_TRIGGER_RE = re.compile(
    r"tap[^.]*\bfor\b[^.]*\{|would produce[^.]*mana|produces?[^.]*mana[^.]*additional"
    r"|add(?:s)? an additional",
    re.IGNORECASE,
)


def _is_mana_amplifier(m: MemberModel) -> bool:
    """A member that adds mana on EVERY tap-for-mana event in the loop (Forsaken
    Monument, Mana Reflection-style), detected by a mana_add feature plus a
    per-tap/per-production trigger. A plain mana rock (no such trigger) taps once
    and is not an amplifier — the sound distinction that keeps untap_mana honest."""
    if m.mana_produced() <= 0:
        return False
    for t in m.triggers:
        if _AMPLIFIER_TRIGGER_RE.search(t.get("trigger", "") or ""):
            return True
    for it in m.provides + m.ambient:
        if it.get("feature") == "mana_add" and _AMPLIFIER_TRIGGER_RE.search(
            it.get("evidence", "") or ""
        ):
            return True
    return False


def _color_tag(members: list[MemberModel]) -> str:
    """Colorless when every modelled mana source's evidence names {C}; otherwise
    the generic 'mana' (we never over-claim a specific color from the coarse
    features)."""
    mana_items = [
        it for m in members for it in m.provides if it.get("feature") == "mana_add"
    ]
    if mana_items and all("{C}" in (it.get("evidence") or "") for it in mana_items):
        return "colorless"
    return "mana"


def template_untap_mana(members: list[MemberModel]) -> Optional[Verdict]:
    """T1 — self-untapping mana rock + a mana amplifier => infinite mana (k=0).

    Pattern: one member M is a mana rock that (a) taps for ``p`` mana and (b) has a
    pure-mana self-untap costing ``u`` (emitted ``untap`` event + priced activated
    cost). Base net per untap cycle is ``p - u`` (Basalt Monolith: 3 - 3 = 0). The
    loop closes iff a *second* mana contribution from another member raises the net
    strictly above zero — an ambient/triggered "add an additional {C}" amplifier
    (Forsaken Monument: +1 per tap-for-C). Recurrence is intrinsic (the rock
    untaps itself). No finite zone is consumed, so k=0 => infinite.
    """
    rocks = [m for m in members if m.mana_produced() > 0 and m.untap_cost() is not None]
    if not rocks:
        return None
    v = Verdict()
    v.template = "untap_mana"
    rock = max(rocks, key=lambda m: m.mana_produced())
    p = rock.mana_produced()
    u = rock.untap_cost() or 0
    # Amplifier mana per cycle — SOUNDNESS-CRITICAL (QE-4). Only a *triggered
    # per-tap mana amplifier* (Forsaken Monument: "Whenever you tap a permanent for
    # {C}, add an additional {C}") adds mana on every rock cycle. A standalone mana
    # rock (Thran Dynamo, Mana Vault) taps ONCE and is then tapped — it is NOT an
    # amplifier and must never be summed here, or every deck with two rocks would
    # falsely verify infinite mana.
    amp = sum(m.mana_produced() for m in members if m is not rock and _is_mana_amplifier(m))
    net = p + amp - u
    v.ledger = {"mana": net}
    v.trace = [f"{rock.name}: {{T}} → add {p} mana"]
    for m in members:
        if m is not rock and m.mana_produced() > 0:
            v.trace.append(f"{m.name}: +{m.mana_produced()} mana amplifier")
    v.trace.append(f"{rock.name}: pay {u} → untap {rock.name}")
    v.trace.append(f"net {net:+d} mana per cycle")
    if net > 0:
        v.closes = True
        v.k = 0
        v.loop_class = "infinite"
        v.accumulators = ["mana"]
        v.result_types = [f"infinite_mana:{_color_tag(members)}"]
    else:
        v.closes = False
        # Deficit: the per-iteration mana shortfall to reach strict gain (net>0).
        v.deficit = [{
            "resource": "mana",
            "shortfall": 1 - net,
            "note": f"loop nets {net:+d} mana per iteration; needs a mana amplifier "
                    f"or cheaper untap to reach strict gain",
        }]
    return v


def template_blink_value(members: list[MemberModel]) -> Optional[Verdict]:
    """T2/T3 — blink a creature with an ETB payoff (k=0 infinite ETB / mana).

    Pattern: one member B provides ``blink`` (exile-and-return, re-triggering ETBs)
    and another member E provides ``etb_trigger``. The blink returns E, re-firing
    its ETB each cycle (recurrence). Two closing cases:

      • E's ETB untaps mana lands (``untap_permanent``) for at least the blink's
        mana cost => infinite mana (Deadeye Navigator + Peregrine Drake).
      • E's ETB is a value payoff (token/draw/drain/counter) and the blink is free
        or mana-neutral => infinite ETB triggers of that payoff.

    If the blink costs mana that the ETB does not refund, the loop does NOT close;
    the deficit is the per-cycle mana leak (a value engine, not infinite).
    """
    blinkers = [m for m in members if m.has_feature("blink")]
    etbs = [m for m in members if m.has_feature("etb_trigger")]
    if not blinkers or not etbs:
        return None
    v = Verdict()
    v.template = "blink_value"
    blink = blinkers[0]
    # Blink activation cost: cheapest priced activated ability, else the mana_cost
    # is a one-time setup, not a per-cycle cost. A blink with only an unpriceable
    # cost is treated as unknown (conservative: does not close).
    blink_cost = None
    for c in blink.activated:
        m = parse_mana(c)
        if m is not None:
            blink_cost = m if blink_cost is None else min(blink_cost, m)
    # ETB that untaps lands for mana (infinite-mana case).
    for e in etbs:
        if e.has_feature("untap_permanent"):
            # Untap magnitude is a land count; each land makes >=1 mana. We can only
            # bound it below by the count, so require count >= blink_cost to close.
            lands = e.feature_magnitude("untap_permanent")
            # magnitude here is often 1 (the KB does not always capture the N);
            # be conservative — only close when a priced blink cost is provably met.
            if blink_cost is not None and lands >= blink_cost and lands >= 1:
                v.closes = True
                v.template = "blink_untap_mana"
                v.k = 0
                v.loop_class = "infinite"
                v.accumulators = ["mana"]
                v.result_types = [f"infinite_mana:{_color_tag(members)}"]
                v.ledger = {"mana": lands - blink_cost}
                v.trace = [
                    f"{blink.name}: pay {blink_cost} → blink {e.name}",
                    f"{e.name}: ETB → untap {lands} land(s)",
                    f"net {lands - blink_cost:+d} mana per cycle",
                ]
                return v
    # Value-payoff case: ETB emits a value economy; blink must be free/neutral.
    payoff = None
    for e in etbs:
        for fid in ("drain", "token_create", "draw", "counter_add", "damage"):
            if e.has_feature(fid):
                payoff = (e, fid)
                break
        if payoff:
            break
    if payoff is None:
        return None
    e, fid = payoff
    eco = e.feature_economy(fid)
    v.trace = [
        f"{blink.name}: {'pay ' + str(blink_cost) + ' → ' if blink_cost else ''}blink {e.name}",
        f"{e.name}: ETB → {eco or fid}",
    ]
    if blink_cost == 0:
        # Genuinely free activated blink (priced to 0 mana) => infinite ETB triggers.
        v.closes = True
        v.k = 0
        v.loop_class = "infinite"
        v.accumulators = [eco or fid]
        v.result_types = [_etb_result_type(fid)]
        v.ledger = {}
        v.trace.append("blink is free → infinite ETB triggers")
    elif blink_cost is None:
        # UNKNOWN blink cost. Never treat unknown as free (QE-4 false-positive
        # channel): abstain from closure and record the modelling gap as a deficit.
        v.closes = False
        v.loop_class = "engine"
        v.k = 1
        v.result_types = [_etb_result_type(fid)]
        v.deficit = [{
            "resource": "mana",
            "shortfall": None,
            "note": "blink activation cost is not modelled in the KB; cannot prove "
                    "closure — surfaced as a Tier-C candidate, not verified",
        }]
    else:
        # Positive priced blink cost. Whether that priced ability is actually the
        # blink (vs. an unrelated activated ability on the same card) is not encoded
        # in the KB, so we abstain rather than surface a possibly-misattributed
        # numeric deficit (QE-4). Recorded as a KB-gap diagnostic (QE-2).
        v.closes = False
        v.loop_class = "engine"
        v.k = 1
        v.result_types = [_etb_result_type(fid)]
        v.deficit = [{
            "resource": "mana",
            "shortfall": None,
            "note": "blink activation cost cannot be soundly attributed from the KB; "
                    "structure surfaced as a value engine, not a verified loop",
        }]
    return v


def _etb_result_type(fid: str) -> str:
    return {
        "drain": "infinite_etb_drain",
        "token_create": "infinite_tokens",
        "draw": "infinite_draw",
        "counter_add": "infinite_counters",
        "damage": "infinite_damage",
    }.get(fid, "infinite_etb_triggers")


def template_sac_recursion(members: list[MemberModel]) -> Optional[Verdict]:
    """T4 — aristocrats: sac outlet + recurring fodder + death payoff.

    Pattern: member O provides a ``sac_outlet``; member F provides ``sac_fodder``;
    optional payoff P provides ``dies_trigger``/``drain``. This is the classic
    value-engine structure (event trace: sacrifice → dies → payoff).

    SOUNDNESS (QE-4): whether the loop is infinite, bounded, or leaks mana depends
    on the *return cost of the fodder* and *which activated ability is the sac
    outlet* — neither of which the deterministic extractor captures reliably
    (Nim Deathmantle's "you may pay {4}" is a trigger, not an activated cost; a
    fodder's mana ability is not its return ability). Pricing this from the coarse
    features gives fabricated numbers. So this template only DETECTS the structure
    and abstains from any numeric claim: it records a k>0 value-engine reading with
    a KB-gap deficit (shortfall=None), a QE-2 ontology/extraction diagnostic. It
    never asserts closure (CLOSE_SAFE excludes it) and never surfaces a numeric
    deficit. A genuinely infinite aristocrats loop that IS in the curated corpus
    still shows at Tier A from Spellbook data.
    """
    outlets = [m for m in members if m.has_feature("sac_outlet")]
    fodder = [m for m in members if m.has_feature("sac_fodder")]
    if not outlets or not fodder:
        return None
    v = Verdict()
    v.template = "sac_recursion"
    v.closes = False
    v.loop_class = "engine"
    v.k = 1
    v.result_types = ["death_trigger_engine"]
    payoff = [m for m in members if m.has_feature("dies_trigger") or m.has_feature("drain")]
    v.trace = [
        f"{outlets[0].name}: sacrifice {fodder[0].name}",
        f"{fodder[0].name}: recurs (return cost not modelled in the KB)",
    ]
    if payoff:
        eco = "drain" if any(m.has_feature("drain") for m in payoff) else "dies"
        v.trace.append(f"{payoff[0].name}: death trigger → {eco}")
    v.deficit = [{
        "resource": "recurrence",
        "shortfall": None,
        "note": "aristocrats value-engine structure; the fodder's return cost and the "
                "sac outlet's cost are not soundly priceable from the KB, so closure "
                "is not verified (QE-2 diagnostic)",
    }]
    return v


# Template registry — order is deterministic; first template that matches the
# structure wins (they are mutually exclusive by their gating features).
TEMPLATES = (
    template_untap_mana,
    template_blink_value,
    template_sac_recursion,
)


# ─── Prerequisites (PR-3) ────────────────────────────────────────────────────────
def compute_prerequisites(members: list[MemberModel], verdict: Verdict) -> dict:
    """PR-3 Tier-B prerequisites: (a) minimal initial mana stock via ordering
    optimization, (b) the guard set (zone / timing / control / summoning-sickness /
    command-zone).

    Ordering optimization: the same loop can need 3 floating mana under one action
    order and 0 under another (PR-3). We model each priced action as (produce,
    cost) and, over every ordering of the loop's actions, compute the worst-case
    running mana deficit (the most negative running balance); the minimal initial
    stock is the smallest such worst-case across orderings. Cycle sizes are tiny
    (<= a few actions), so exhaustive permutation is cheap and deterministic.
    """
    # Build the priced action list from the members' mana production/consumption.
    actions: list[tuple[int, str]] = []  # (net_mana_delta, label)
    for m in members:
        p = m.mana_produced()
        if p:
            actions.append((p, f"{m.name}: add {p}"))
        uc = m.untap_cost()
        if uc:
            actions.append((-uc, f"{m.name}: untap (pay {uc})"))
        for c in m.activated:
            mc = parse_mana(c)
            if mc and mc > 0 and c.strip() != "{T}":
                # avoid double-counting the untap we already added
                if uc is not None and mc == uc:
                    continue
                actions.append((-mc, f"{m.name}: activate (pay {mc})"))

    min_stock = 0
    best_order: list[str] = []
    if actions:
        best = None
        # cap permutations for safety (cycle actions are few; 6! = 720)
        universe = actions[:6]
        for perm in itertools.permutations(universe):
            bal = 0
            worst = 0
            for delta, _ in perm:
                bal += delta
                worst = min(worst, bal)
            need = -worst
            if best is None or need < best:
                best = need
                best_order = [lbl for _, lbl in perm]
        min_stock = best or 0

    # Guard set. IN-4 command-zone: if a member is the deck commander, note that its
    # command-zone accessibility is a distinct guard (a commander is reliably
    # castable in a way a library card is not — CR 903.3d: control is battlefield).
    guards: list[str] = []
    seen: set[str] = set()
    for m in members:
        for g in m.guards:
            if g and g not in seen:
                seen.add(g)
                guards.append(g)
    return {
        "minInitialMana": min_stock,
        "ordering": best_order,
        "guards": sorted(guards),
        "note": "Correct under Laço's model; may be incomplete in comprehensive-"
                "rules edge cases (PR-5).",
    }


# ─── Provenance chain (DB-6 / TX-1) ──────────────────────────────────────────────
def provenance_chain(members: list[MemberModel]) -> dict:
    """DB-6: verdict → entry versions → extraction path. Records every member's
    oracle_id + the ontology/extractor/corpus versions the entry was built under, so
    any Tier-B claim is auditable back to its inputs. All items consumed are, by the
    provenance gate, ``deterministic`` or ``human-reviewed`` only."""
    ont = sorted({m.ontology_version for m in members if m.ontology_version})
    ext = sorted({m.extractor_version for m in members if m.extractor_version})
    corp = sorted({m.corpus_version for m in members if m.corpus_version})
    return {
        "members": [{"name": m.name, "oracleId": m.oracle_id} for m in members],
        "ontologyVersion": ont[0] if len(ont) == 1 else ont,
        "extractorVersion": ext[0] if len(ext) == 1 else ext,
        "corpusVersion": corp[0] if len(corp) == 1 else corp,
        "gate": "deterministic|human-reviewed only (combo_kb_lib.TIER_B_PROVENANCES)",
    }


# ─── Top-level verification ──────────────────────────────────────────────────────
def verify_candidate(entries: list[dict], in_curated: bool = False) -> Optional[Verdict]:
    """Verify one candidate loop. ``entries`` = the RAW KB entries for the members
    (verify_candidate applies the provenance gate). ``in_curated`` marks a loop
    already present in the curated corpus (DB-7) — its verdict is corroboration and
    can never inflate the tier.

    Returns None when no closure template matches the structure at all (not a loop
    candidate under the model). Otherwise returns a Verdict; ``closes`` says whether
    it closes, ``tier_capped`` (non-None) forces Tier C, and ``novel_eligible`` says
    whether a NOT-in-corpus verified loop clears the strict novel gate.
    """
    if not entries or len(entries) > MAX_CYCLE_PIECES + 8:  # + ambient headroom
        return None
    members = [MemberModel(e, gate=True) for e in entries]

    verdict = _run_templates(members)

    # Provenance-gate capping (plan decision 6b). If the GATED analysis does not
    # verify but the same structure WOULD close using LLM/community items the gate
    # dropped, surface it as a Tier-C candidate with an explicit cap reason — the
    # gate can only withhold "verified", never inflate it (QE-4).
    capped_fields = sorted({f for m in members for f in m.tier_b_capped})
    if capped_fields and (verdict is None or not verdict.closes):
        ungated = [MemberModel(e, gate=False) for e in entries]
        uv = _run_templates(ungated)
        if uv is not None and uv.closes:
            uv.closes = False  # the GATED (sound) view does not verify
            uv.tier_capped = (
                "capped at Tier C: loop-relevant field(s) "
                + ", ".join(capped_fields)
                + " came from LLM/community classification, not deterministic or "
                "human-reviewed extraction (plan decision 6b provenance gate); "
                "would verify once a human reviews the entry (KB-7)"
            )
            verdict = uv

    if verdict is None:
        return None

    # SOUNDNESS BACKSTOP (QE-4, single auditable gate). Only templates whose closure
    # argument is fully derivable from the coarse KB features — mana magnitudes +
    # priced activated costs — may assert a closed loop. sac_recursion and the
    # value-payoff blink case depend on return-cost / activation-cost attribution the
    # deterministic extractor does not capture, so a "closes" there would be an
    # unverified guess. Downgrade those to a k>0 value-engine near-miss rather than
    # claim an unsound infinite loop. (Corroboration of curated aristocrats loops is
    # a measured QE-1b limitation, not a correctness risk — the curated combo still
    # shows at Tier A from Spellbook data.)
    if verdict.closes and verdict.template not in CLOSE_SAFE:
        verdict.closes = False
        verdict.loop_class = "engine"
        if verdict.k in (None, 0):
            verdict.k = 1
        if not verdict.deficit:
            verdict.deficit = [{
                "resource": "recurrence",
                "shortfall": None,
                "note": "structure present but closure is not soundly derivable from "
                        "the coarse KB features; surfaced as a value engine, not a "
                        "verified loop",
            }]

    verdict.prerequisites = compute_prerequisites(members, verdict)
    verdict.provenance = provenance_chain(members)

    # (k, finite-zone bound) attribute — reported on both infinite and engine
    # classes, never a third exclusive class (plan clarification, PRD 6.5.4).
    if verdict.loop_class in ("infinite", "engine") and verdict.finite_zone_bound is None:
        verdict.finite_zone_bound = _derive_finite_bound(members, verdict)

    # Novel-eligibility (strict gate). Only a NOT-in-corpus, cleanly-closing loop
    # with strict resource gain, no capped provenance, AND produced by a template
    # whose closure is provable from the coarse features (NOVEL_SAFE) qualifies as a
    # novel Tier-B finding (DC-6 rarity + QE-4 false-positive avoidance). Templates
    # whose closure depends on KB data the extractor cannot price soundly
    # (sac-recursion return costs, blink activation costs) may still CORROBORATE a
    # curated combo — corroboration cannot inflate tier — but never claim a novel
    # verified loop on their own.
    verdict.novel_eligible = (
        verdict.closes
        and not in_curated
        and verdict.tier_capped is None
        and verdict.loop_class == "infinite"
        and bool(verdict.accumulators)
        and not verdict.deficit
        and verdict.template in NOVEL_SAFE
    )
    return verdict


# Templates whose closure argument is fully derivable from the coarse KB features
# (mana magnitudes + priced activated costs), so a verified verdict is sound. Any
# other template may classify a value engine / near-miss but never assert closure.
CLOSE_SAFE = frozenset({"untap_mana", "blink_untap_mana"})
NOVEL_SAFE = CLOSE_SAFE


def _run_templates(members: list[MemberModel]) -> Optional[Verdict]:
    """First closure template (deterministic order) whose structural pattern
    matches the members, or None if none apply."""
    for tmpl in TEMPLATES:
        v = tmpl(members)
        if v is not None:
            return v
    return None


def _derive_finite_bound(members: list[MemberModel], verdict: Verdict) -> Optional[dict]:
    """Finite-zone bound attribute (6.5.4). A loop that self-mills or exiles its own
    library each iteration is bounded by the library size. The KB does not yet model
    per-iteration library consumption as a scalar, so we report a bound only when a
    member self-mills a known constant; otherwise None (no finite zone consumed)."""
    for m in members:
        if m.has_feature("self_mill"):
            per = m.feature_magnitude("self_mill") or 1
            return {"zone": "library", "perIteration": per,
                    "bound": DEFAULT_LIBRARY_SIZE // per,
                    "note": f"self-mills ~{per}/iteration; bounded by a ~{DEFAULT_LIBRARY_SIZE}-card library"}
    return None


# ─── Ranking (RK-2 completion, RK-3 calibratable, RK-5 bands, RK-6 invariance) ───
# Phase 2 shipped a reduced-signal Tier-C ranking (magnitude + deck-fit + crowd
# prior). Phase 3 completes RK-2 for verified/engine findings by ADDING the two
# signals that only exist once a loop is modelled: mechanistic rate (accumulator
# delta per turn) and startup cost (from PR-3). Weights are CALIBRATED by
# scripts/qe1_regression.py (RK-3) against the curated corpus and a hand-labelled
# engine set (RK-4 bias control), never hand-vibed — the fitted weights are written
# to data/combo-kb/verifier-ranking.json and loaded here. Ranking never alters tier
# (RK-6); presentation is coarse bands only (RK-5).
DEFAULT_RANK_WEIGHTS = {
    "mechanistic_rate": 1.0,
    "startup_cost": 1.0,   # inverted signal (cheaper startup ranks higher)
    "magnitude": 1.0,
    "deck_fit": 1.0,
    "crowd_prior": 1.0,
}


def _rank_config_path() -> str:
    return os.path.join(ROOT, "data", "combo-kb", "verifier-ranking.json")


def load_rank_weights() -> dict:
    try:
        cfg = json.load(open(_rank_config_path()))
        return {**DEFAULT_RANK_WEIGHTS, **(cfg.get("weights") or {})}
    except FileNotFoundError:
        return dict(DEFAULT_RANK_WEIGHTS)


def rank_signals(verdict: Verdict) -> dict:
    """Per-finding ranking signals in [0,1]. Mechanistic rate: an infinite loop
    (k=0) accumulates without bound → saturates high; a k>0 engine's rate falls
    with k. Startup cost: cheaper minimal-stock + fewer pieces ranks higher
    (inverted, saturating)."""
    k = verdict.k
    acc = 0
    for r, d in verdict.ledger.items():
        if isinstance(d, (int, float)) and d > 0:
            acc = max(acc, d)
    if verdict.closes and k == 0:
        mech = 1.0
    elif k and k > 0:
        mech = 1.0 / (1.0 + k)
    else:
        mech = 0.3 if verdict.deficit else 0.0
    startup = verdict.prerequisites.get("minInitialMana", 0) or 0
    pieces = len(verdict.provenance.get("members", [])) or 1
    startup_sig = 1.0 / (1.0 + 0.25 * startup + 0.25 * (pieces - 2))
    mag = min(1.0, acc / 3.0) if acc else (0.5 if verdict.closes else 0.2)
    return {
        "mechanistic_rate": round(mech, 4),
        "startup_cost": round(startup_sig, 4),
        "magnitude": round(mag, 4),
    }


def rank_composite(verdict: Verdict, deck_fit: float, crowd_prior: Optional[float],
                   weights: Optional[dict] = None) -> float:
    """Weighted composite for ordering only (RK-5: never shown as a scalar)."""
    w = weights or load_rank_weights()
    s = rank_signals(verdict)
    s["deck_fit"] = round(max(0.0, min(1.0, deck_fit)), 4)
    crowd_applied = crowd_prior is not None
    s["crowd_prior"] = round(max(0.0, min(1.0, crowd_prior)), 4) if crowd_applied else 0.0
    num = sum(w[k] * s[k] for k in ("mechanistic_rate", "startup_cost", "magnitude", "deck_fit"))
    den = w["mechanistic_rate"] + w["startup_cost"] + w["magnitude"] + w["deck_fit"]
    if crowd_applied:
        num += w["crowd_prior"] * s["crowd_prior"]
        den += w["crowd_prior"]
    return round(num / den, 6) if den else 0.0


# ─── Candidate enumeration for verification (DC-5 promotion) ─────────────────────
# The Tier-C synergy graph deliberately excludes the mana_add↔mana_sink pairing as
# noise (combo_synergy_lib.NOISE_PAIRS) — but that pairing is exactly the untap-mana
# loop *seed*. So Tier-B cannot reuse the Tier-C graph as its sole candidate source
# (it would never see infinite-mana rocks). Instead we enumerate small groups gated
# by each template's seed features. Enumeration is bounded (feature-gated subsets +
# a per-deck budget) and deterministic (sorted).
ENUM_BUDGET = 4000


def enumerate_verification_candidates(
    deck_entries: list[dict], budget: int = ENUM_BUDGET
) -> list[list[dict]]:
    """Member-entry groups (2-3 pieces) to feed the verifier, gated by the closure
    templates' seed features. Deterministic; capped at ``budget`` groups. The cap,
    if hit, is disclosed by the caller (never silent)."""
    ent = sorted(deck_entries, key=lambda e: e.get("oracle_id", ""))
    models = [(e, MemberModel(e, gate=True)) for e in ent]

    def gated(pred):
        return [e for e, m in models if pred(m)]

    untappers = gated(lambda m: m.mana_produced() > 0 and m.untap_cost() is not None)
    amplifiers = gated(_is_mana_amplifier)
    blinkers = gated(lambda m: m.has_feature("blink"))
    etbs = gated(lambda m: m.has_feature("etb_trigger"))
    outlets = gated(lambda m: m.has_feature("sac_outlet"))
    fodders = gated(lambda m: m.has_feature("sac_fodder"))
    payoffs = gated(lambda m: m.has_feature("dies_trigger") or m.has_feature("drain"))

    seen: set[frozenset] = set()
    out: list[list[dict]] = []

    def add(group: list[dict]) -> bool:
        key = frozenset(g.get("oracle_id", "") for g in group)
        if len(key) < 1 or key in seen:
            return True
        seen.add(key)
        out.append(group)
        return len(out) < budget

    # untap-mana: a self-untap rock only ever closes with a *triggered mana
    # amplifier* (Forsaken Monument), so enumerate rock × amplifier pairs only — not
    # rock × every mana source (which produced only supersets + noise). A rock with
    # no amplifier in the deck is a near-miss the deficit vector already explains, so
    # emit it as a singleton candidate too.
    for r in untappers:
        amps = [m for m in amplifiers if m is not r]
        if not amps:
            add([r])  # near-miss: nets p-u, deficit names the missing amplifier
        for a in amps:
            if not add([r, a]):
                return out
    # blink + ETB (+ payoff / untapper as third)
    for b in blinkers:
        for e in etbs:
            if e is b:
                continue
            if not add([b, e]):
                return out
            for p in payoffs + untappers:
                if p is b or p is e:
                    continue
                if not add([b, e, p]):
                    return out
    # sac outlet + fodder (+ death payoff)
    for o in outlets:
        for f in fodders:
            if f is o:
                continue
            if not add([o, f]):
                return out
            for p in payoffs:
                if p is o or p is f:
                    continue
                if not add([o, f, p]):
                    return out
    return out


def verify_deck_candidates(
    candidate_member_lists: list[list[dict]],
    curated_member_keys: Optional[set] = None,
) -> list[dict]:
    """Verify a batch of candidate loops for one deck. ``candidate_member_lists`` is
    a list of member-entry lists (from the Tier-C candidate generator, promoted per
    DC-5). ``curated_member_keys`` is a set of frozensets of oracle_ids that the
    curated corpus already reports (DB-7) so we mark corroboration. Returns a list of
    verdict dicts (only for candidates that matched a template)."""
    curated_member_keys = curated_member_keys or set()
    out: list[dict] = []
    for entries in candidate_member_lists:
        key = frozenset(e.get("oracle_id", "") for e in entries)
        in_curated = key in curated_member_keys
        v = verify_candidate(entries, in_curated=in_curated)
        if v is None:
            continue
        d = v.to_dict()
        d["inCurated"] = in_curated
        d["memberIds"] = sorted(key)
        out.append(d)
    return out

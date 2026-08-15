#!/usr/bin/env python3
"""Shared Combo Lab knowledge-base helpers: provenance vocabulary + Tier-B gate.

The provenance gate (plan decision 6b, board default = ENFORCED) is the load-
bearing rule of Phase 1: a Tier-B (computed / "verified under the model")
verdict in Phase 3 may consume ONLY knowledge-base items whose provenance is
deterministic or human-reviewed. LLM- and community-tag-sourced items cap a
finding at Tier C until a human reviews them. This module is the single place
that encodes that rule so the build script, the classifier, the tests, and the
Phase-3 verifier all agree.

DEC-476 Phase 1 (DEC-488). See docs/combo-kb-schema.md.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Provenance vocabulary (KB-4). Every KB field/item records which extraction
# path produced it, so any downstream claim audits back to its inputs.
# ---------------------------------------------------------------------------
PROV_DETERMINISTIC = "deterministic"   # mechanical regex over oracle/type/cost
PROV_COMMUNITY_TAG = "community-tag"   # Scryfall Tagger stream (DR-2)
PROV_LLM = "llm"                       # automated per-card classification (KB-5)
PROV_HUMAN = "human-reviewed"          # human sign-off (KB-7 elevated review)

ALL_PROVENANCES = frozenset(
    {PROV_DETERMINISTIC, PROV_COMMUNITY_TAG, PROV_LLM, PROV_HUMAN}
)

# The gate. Only these provenances may feed a Tier-B verdict. Conservative by
# construction: it can only WITHHOLD a "verified" label, never inflate one
# (QE-4 worst-failure-class ordering). Human review promotes any item into this
# set; the classifier and Tagger streams do not.
TIER_B_PROVENANCES = frozenset({PROV_DETERMINISTIC, PROV_HUMAN})

# KB fields that carry provenance-bearing item lists.
ITEM_FIELDS = ("provides", "wants", "ambient", "triggers", "guards")


def is_tier_b_eligible(provenance: str) -> bool:
    """True iff an item with this provenance may feed a Tier-B verdict."""
    return provenance in TIER_B_PROVENANCES


def tier_b_view(entry: dict) -> dict:
    """Filter a KB entry down to the items a Tier-B verdict may legally consume.

    Returns a shallow copy whose item lists retain only deterministic/
    human-reviewed items, plus a ``tier_b_capped`` set naming every field that
    had at least one dropped (llm/community-tag) item — a finding that would
    have relied on a dropped item must be capped at Tier C (PRD EI-4 / plan 6b).
    """
    view = dict(entry)
    capped = set()
    for field in ITEM_FIELDS:
        items = entry.get(field) or []
        kept = [it for it in items if is_tier_b_eligible(it.get("provenance", ""))]
        if len(kept) != len(items):
            capped.add(field)
        view[field] = kept
    # Costs: mana cost/value are structural (deterministic); activated-ability
    # costs carry their own provenance.
    costs = entry.get("costs") or {}
    if costs:
        activated = costs.get("activated") or []
        kept_cost = [c for c in activated if is_tier_b_eligible(c.get("provenance", ""))]
        if len(kept_cost) != len(activated):
            capped.add("costs")
        view["costs"] = {**costs, "activated": kept_cost}
    view["tier_b_capped"] = sorted(capped)
    return view


def provenance_summary(entry: dict) -> dict:
    """Tally item provenances across an entry (for meta histograms / QA)."""
    tally = {p: 0 for p in ALL_PROVENANCES}
    for field in ITEM_FIELDS:
        for it in entry.get(field) or []:
            p = it.get("provenance", "")
            if p in tally:
                tally[p] += 1
    for c in (entry.get("costs") or {}).get("activated") or []:
        p = c.get("provenance", "")
        if p in tally:
            tally[p] += 1
    return {p: n for p, n in tally.items() if n}


def entry_is_covered(entry: dict) -> bool:
    """A card 'covered' by the KB has an entry with at least the structural
    deterministic fields present. Coverage (stage-1/2 gate) is existence of an
    entry, not completeness of LLM enrichment."""
    return bool(entry) and "oracle_id" in entry and "field_provenance" in entry

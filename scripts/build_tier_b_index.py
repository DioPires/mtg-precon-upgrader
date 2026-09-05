#!/usr/bin/env python3
"""Build the committed Tier-B verifier index for paste mode — DEC-516 (DEC-476 Phase 4).

The Phase-3 verifier (`combo_verifier_lib`) runs over the FULL raw KB entries
(`data/combo-kb/entries/*.json`, ~41 MB) because closure depends on fields the
synergy layer's lean projection (`feature-index.json`) drops: per-item provenance,
`events_emitted`, activated costs, triggers, guards. Fleet mode precomputes verdicts
into per-deck `tier-b-loops.json`; paste mode cannot — the pasted deck is unknown at
build time. So the browser needs the loop-relevant raw fields to run the verifier on
a pasted decklist.

Shipping all 41 MB to the browser is untenable. This script emits a compact
derivative, `data/combo-kb/tier-b-index.json`, carrying ONLY the fields the TS mirror
(`web/src/lib/comboVerify.ts`) needs, and ONLY for cards that can ever be a *candidate
member* under the closure templates. A card is a candidate member iff, under the
provenance gate (gate=True, exactly as `enumerate_verification_candidates` gates), it
is one of: a self-untapping mana rock, a per-tap mana amplifier, a blinker, an ETB
source, a sac outlet, sac fodder, or a death payoff (dies_trigger / drain). Plain mana
rocks, vanilla creatures, etc. can never seed a loop and are omitted — that trims
31,830 cards to ~10 k.

Per card we store every loop-relevant item WITH its provenance (so the TS mirror can
reconstruct both the gated and un-gated MemberModel views the cap logic needs), the
raw `events_emitted` and activated costs (read gate-blind by the verifier), a
precomputed `untaps_other` flag (the N1 self-scope guard), and a precomputed
`tier_b_capped` set (the exact provenance-gate cap over the FULL entry, so the TS
mirror's cap precondition is byte-faithful without shipping the dropped llm items).

The artifact is a pure function of the KB corpus (byte-stable across reruns): the
KB `ontology_version` / `extractor_version` / `corpus_version` are uniform across the
corpus, so they live once in `meta` (not per card), and `generatedAt` is normalised to
the corpus version (never a wall-clock stamp), matching build_tier_b_candidates.py.

Usage:
  uv run python scripts/build_tier_b_index.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

import combo_kb_lib as KB
import combo_synergy_lib as SYN
import combo_verifier_lib as V

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENTRIES_DIR = os.path.join(ROOT, "data", "combo-kb", "entries")
OUT_PATH = os.path.join(ROOT, "data", "combo-kb", "tier-b-index.json")
META_PATH = os.path.join(ROOT, "data", "combo-kb", "meta.json")
MATCHER_INDEX = os.path.join(ROOT, "data", "spellbook", "matcher-index.json")

# Loop-relevant features: the only feature ids any closure template or its helpers
# read (untap_mana / blink_value / sac_recursion + _color_tag + _derive_finite_bound).
# Items with any OTHER feature never affect a verdict, so they are dropped from the
# stored item lists (the exact tier_b_capped set is still precomputed over the FULL
# entry, so a dropped non-loop llm item still trips the cap precondition faithfully).
LOOP_FEATURES = frozenset(
    {
        "mana_add",
        "blink",
        "etb_trigger",
        "sac_outlet",
        "sac_fodder",
        "dies_trigger",
        "drain",
        "token_create",
        "draw",
        "counter_add",
        "damage",
        "self_mill",
        "untap_permanent",
        # graveyard-return loop features (DEC-526)
        "etb_reanimate",
        "aura_fetch",
        "death_return",
        "exile_until_leaves",
    }
)

# The graveyard-return feature subset — cards carrying one of these are the only
# records that need `tl` / `mv` (they can be a reanimator or partner; DEC-526).
_GR_FEATURES = frozenset({"etb_reanimate", "aura_fetch", "death_return", "exile_until_leaves"})

NOTE = (
    "Loop-relevant raw KB projection for the paste-mode Tier-B verifier "
    "(web/src/lib/comboVerify.ts). `cards` = one full loop-relevant record per KB "
    "card that is EITHER a candidate member (gate=True closure-template seed) OR a "
    "card that appears in a Spellbook combo (so a curated combo resolves with all its "
    "pieces, including non-seed bystanders like Rings of Brighthearth / Voltaic "
    "Construct whose activated costs + guards the prerequisite math reads — matching "
    "build_tier_b_candidates.build_deck). The runtime enumerator gates candidate "
    "groups by feature exactly as the Python enumerator does, so a non-seed record "
    "never forms a fresh group — it only ever joins a curated group. Items carry "
    "provenance so the TS mirror applies the "
    "provenance gate itself; `cap` is the exact tier_b_view cap over the full entry; "
    "`uo` is the N1 untaps-other self-scope guard. Pure function of the KB corpus + "
    "the committed matcher index."
)


def is_candidate_member(m: V.MemberModel) -> bool:
    """Exactly the union of the seven feature gates in
    combo_verifier_lib.enumerate_verification_candidates (all under gate=True), so the
    index contains every card the fleet enumerator can place in a candidate group."""
    return (
        (m.mana_produced() > 0 and m.untap_cost() is not None)
        or V._is_mana_amplifier(m)
        or m.has_feature("blink")
        or m.has_feature("etb_trigger")
        or m.has_feature("sac_outlet")
        or m.has_feature("sac_fodder")
        or m.has_feature("dies_trigger")
        or m.has_feature("drain")
        # graveyard-return seeds (DEC-526): most already carry etb_trigger, but a bare
        # death_return enchantment (Angelic Renewal) has no other loop feature.
        or m.has_feature("etb_reanimate")
        or m.has_feature("aura_fetch")
        or m.has_feature("death_return")
        or m.has_feature("exile_until_leaves")
    )


def project_items(raw_list: list[dict] | None) -> list[dict]:
    """Loop-relevant items only, compact. `v` (evidence) is kept ONLY on mana_add
    items — the sole place the verifier reads evidence (_color_tag's `{C}` test and
    the amplifier trigger regex). Magnitude/economy are omitted at their defaults."""
    out: list[dict] = []
    for it in raw_list or []:
        feat = it.get("feature")
        if feat not in LOOP_FEATURES:
            continue
        rec: dict = {"f": feat, "p": it.get("provenance", "")}
        mag = it.get("magnitude", 1)
        if mag not in (1, None):
            # featureMagnitude truncation guard (DEC-522 item 4): magnitudes must be
            # integral so the TS mirror's Math.floor / `|| 1` math (comboVerify
            # .featureMagnitude, deriveFiniteBound) stays byte-identical to Python.
            if isinstance(mag, float) and not mag.is_integer():
                raise SystemExit(
                    f"ERROR: non-integral feature magnitude {mag!r} on feature "
                    f"{feat!r} — the Tier-B verifier assumes integral magnitudes; "
                    "update the schema before shipping."
                )
            rec["m"] = mag
        eco = it.get("economy", "")
        if eco:
            rec["e"] = eco
        if feat == "mana_add":
            # FULL evidence, never truncated: the verifier reads it verbatim in
            # _color_tag ("{C}" test) and _is_mana_amplifier (regex). Truncation could
            # drop a "{C}" or an amplifier phrase and break byte-parity with Python.
            rec["v"] = it.get("evidence") or ""
        out.append(rec)
    return out


def build_record(entry: dict) -> dict:
    """Compact per-card record; ungated view (all provenance) — the TS mirror gates."""
    m = V.MemberModel(entry, gate=False)
    rec: dict = {
        "n": entry.get("name", ""),
        "pr": project_items(entry.get("provides")),
        "wa": project_items(entry.get("wants")),
        "am": project_items(entry.get("ambient")),
    }
    ci = entry.get("color_identity") or []
    if ci:
        rec["ci"] = ci
    # type_line + mana_value: the graveyard-return template (DEC-526) reads is_creature /
    # is_aura (from tl) and the partner mana value (mv) against the reanimator bound —
    # but ONLY on cards carrying a graveyard-return feature (a non-GR card is never a
    # reanimator/partner, so the verifier never consults its tl/mv). Ship them only
    # there, keeping the index lean (build_tier_b_index's ship-only-what-is-needed rule).
    if any(
        it.get("feature") in _GR_FEATURES
        for it in (entry.get("provides") or [])
    ):
        tl = entry.get("type_line")
        if tl:
            rec["tl"] = tl
        mv = entry.get("cmc")
        if mv is not None:
            rec["mv"] = mv
    # FULL trigger text, never truncated: _is_mana_amplifier runs a regex over it.
    tr = [
        {"t": t.get("trigger") or "", "p": t.get("provenance", "")}
        for t in (entry.get("triggers") or [])
    ]
    if tr:
        rec["tr"] = tr
    gu = [
        {"g": g.get("guard"), "p": g.get("provenance", "")}
        for g in (entry.get("guards") or [])
    ]
    if gu:
        rec["gu"] = gu
    ev = entry.get("events_emitted") or []
    if ev:
        rec["ev"] = ev
    costs = entry.get("costs") or {}
    co: dict = {}
    mc = costs.get("mana_cost")
    if mc:
        co["mc"] = mc
    ac = [
        {"c": c.get("cost"), "p": c.get("provenance", "")}
        for c in (costs.get("activated") or [])
    ]
    if ac:
        co["ac"] = ac
    if co:
        rec["co"] = co
    if m.untaps_other:
        rec["uo"] = True
    cap = sorted(KB.tier_b_view(entry).get("tier_b_capped", []))
    if cap:
        rec["cap"] = cap
    return rec


def load_combo_oids() -> set[str]:
    """Oracle-ids referenced by any Spellbook combo (the master matcher index). A
    non-member card in this set can be a curated-combo bystander, so it needs a
    name-only stub for the curated-group render to match Python."""
    mi = json.load(open(MATCHER_INDEX))
    return {c.get("o") for c in mi.get("cards", {}).values() if c.get("o")}


def main(argv: list[str]) -> int:
    print("loading raw KB entries …", file=sys.stderr)
    combo_oids = load_combo_oids()
    cards: dict[str, dict] = {}
    member_count = 0
    indexed_names: list[tuple[str, str]] = []
    versions: dict[str, set] = {"ov": set(), "xv": set(), "cv": set()}
    for shard in sorted(glob.glob(os.path.join(ENTRIES_DIR, "*.json"))):
        for entry in json.load(open(shard)):
            oid = entry.get("oracle_id")
            if not oid:
                continue
            m = V.MemberModel(entry, gate=True)
            is_member = is_candidate_member(m)
            if not is_member and oid not in combo_oids:
                continue  # neither a loop seed nor a possible curated bystander
            # Both seeds and bystanders get a FULL loop-relevant record: the
            # prerequisite math + templates read a bystander's activated costs,
            # guards, and untap_permanent (e.g. Voltaic Construct). The enumerator's
            # feature gates keep non-seeds out of fresh candidate groups.
            cards[oid] = build_record(entry)
            if is_member:
                member_count += 1
            indexed_names.append((oid, entry.get("name", "")))
            versions["ov"].add(entry.get("ontology_version"))
            versions["xv"].add(entry.get("extractor_version"))
            versions["cv"].add(entry.get("corpus_version"))

    # Versions are uniform across the corpus; assert it so a future non-uniform KB
    # surfaces loudly instead of silently picking one (parity would break otherwise).
    for key, label in (("ov", "ontology"), ("xv", "extractor"), ("cv", "corpus")):
        if len(versions[key]) != 1:
            print(
                f"ERROR: non-uniform {label}_version across the KB: {sorted(versions[key])} — "
                "the tier-b-index meta stores a single version; update the schema.",
                file=sys.stderr,
            )
            return 1

    corpus_version = next(iter(versions["cv"]))
    # Exact full names claim their key before any face alias — an MDFC back face
    # otherwise hijacks a standalone card's name (DEC-553).
    names = SYN.build_name_to_oid(indexed_names)
    out = {
        "meta": {
            "schema": "combo-lab-tier-b-index",
            "ontologyVersion": next(iter(versions["ov"])),
            "extractorVersion": next(iter(versions["xv"])),
            "corpusVersion": corpus_version,
            # Pure function of the corpus (N4 / DB-5): normalised to corpus_version,
            # not a wall-clock stamp, so reruns are byte-identical.
            "generatedAt": corpus_version,
            "recordCount": len(cards),
            "memberCount": member_count,
            "bystanderCount": len(cards) - member_count,
            "provenanceGate": "deterministic|human-reviewed only (combo_kb_lib.TIER_B_PROVENANCES)",
            "note": NOTE,
        },
        "cards": {k: cards[k] for k in sorted(cards)},
        "names": {k: names[k] for k in sorted(names)},
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    size_mb = os.path.getsize(OUT_PATH) / 1e6
    print(
        f"wrote {OUT_PATH} — {len(cards)} records ({member_count} seeds, "
        f"{len(cards) - member_count} bystanders), {len(names)} name keys, "
        f"{size_mb:.2f} MB (corpus {corpus_version})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

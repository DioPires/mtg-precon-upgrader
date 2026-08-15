#!/usr/bin/env python3
"""Precompute per-fleet-deck Tier-B loop verdicts (fleet mode).

DEC-501 (DEC-476 Phase 3). Runs the deterministic verifier (`combo_verifier_lib`)
over each fleet deck and writes `data/commanders/{id}/tier-b-loops.json` — a
standalone per-deck file like `spellbook-combos.json` / `synergy-candidates.json`,
loaded by the Combo Lab route in fleet mode.

Candidate sources (union, deduped):
  1. **Curated corpus (DB-7 + QE-1b):** every curated combo present in the deck
     (from `spellbook-combos.json` included[]) → verified for *corroboration*. A
     corroborated loop stays Tier A; the computed verdict is recorded as
     corroboration, never a fresh Tier-B claim (DB-7). This is what QE-1b measures.
  2. **Feature-gated enumeration (DC-5):** small groups seeded by the closure
     templates (untap-mana rocks, blink+ETB, sac outlet+fodder). The Tier-C graph
     cannot serve here — it excludes the mana_add↔mana_sink loop seed as noise.

Findings are bucketed by presentation tier:
  - `verifiedCorroborated` — closes AND already curated (Tier A, corroborated).
  - `verifiedNovel` — closes, NOT curated, clears the strict novel gate (Tier B).
    DC-6: expected to be rare.
  - `engines` — closes as a k>0 value engine, OR near-miss with a deficit vector
    (Tier B near-miss / Tier-C candidate; NM-1 Tier B, TX-3).
  - `capped` — would close but the provenance gate demotes it to Tier C (6b).

No EDHREC scalar is written (decision 4 exposure gate); the crowd prior only nudges
ranking order. Everything shipped is coarse bands + explainable traces (RK-5/TX-1).

Usage:
  uv run python scripts/build_tier_b_candidates.py [--deck ID ...]
  (no --deck ⇒ every fleet deck in data/index.json)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

import combo_synergy_lib as SYN
import combo_verifier_lib as V

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMANDERS = os.path.join(ROOT, "data", "commanders")
EDHREC_DIR = os.path.join(ROOT, "priv_data", "edhrec")
MATCHING_MODEL = "tier-b-verifier-v1 (deterministic closure model, PRD 6.1-6.5)"

MODEL_NOTE = (
    "Tier B — machine-verified under Laço's game model (PRD 6.1-6.5), NOT a "
    "comprehensive-rules proof (EI-2). A goldfish is assumed (NG1). Verdicts consume "
    "only deterministic / human-reviewed KB items (provenance gate, plan 6b). "
    "Corroborated loops remain Tier A (Commander Spellbook); novel loops are rare "
    "by design (DC-6). Ranking is calibrated (RK-3) but presented as coarse bands "
    "only (RK-5)."
)


def fleet_ids() -> list[str]:
    idx = json.load(open(os.path.join(ROOT, "data", "index.json")))
    return [c["id"] for c in idx.get("commanders", [])]


def load_rates(deck_id: str) -> dict[str, float] | None:
    path = os.path.join(EDHREC_DIR, f"{deck_id}.json")
    if not os.path.exists(path):
        return None
    return json.load(open(path)).get("rates") or None


def curated_member_keys(deck_id: str, name_to_oid: dict[str, str]) -> set[frozenset]:
    """Oracle-id sets for curated combos present in the deck (DB-7). Combos whose
    cards do not all resolve to KB entries are skipped (they cannot be verified)."""
    path = os.path.join(COMMANDERS, deck_id, "spellbook-combos.json")
    if not os.path.exists(path):
        return set()
    sc = json.load(open(path))
    keys: set[frozenset] = set()
    for combo in sc.get("included", []):
        oids = []
        ok = True
        for card in combo.get("cards", []):
            oid = None
            for k in SYN.name_keys(card.get("name", "")):
                if k in name_to_oid:
                    oid = name_to_oid[k]
                    break
            if oid is None:
                ok = False
                break
            oids.append(oid)
        if ok and 2 <= len(oids) <= V.MAX_CYCLE_PIECES + 8:
            keys.add(frozenset(oids))
    return keys


def build_deck(deck_id: str, ctx: dict) -> dict:
    by_oid = ctx["by_oid"]
    name_to_oid = ctx["name_to_oid"]
    deck = json.load(open(os.path.join(COMMANDERS, deck_id, "deck.json")))
    names = [c["name"] for c in deck.get("decklist", [])]
    commander = deck.get("commander")
    commanders = []
    if commander:
        names.append(commander)
        commanders = [p.strip() for p in str(commander).split("//") if p.strip()]

    # Resolve decklist → raw entries (deduped by oracle_id).
    entries: dict[str, dict] = {}
    for raw in names:
        for k in SYN.name_keys(raw):
            if k in name_to_oid:
                entries[name_to_oid[k]] = by_oid[name_to_oid[k]]
                break
    deck_entries = list(entries.values())

    curated = curated_member_keys(deck_id, name_to_oid)

    # Candidate groups: curated member sets (as entry lists) + feature-gated enum.
    groups: list[list[dict]] = []
    seen: set[frozenset] = set()
    for key in curated:
        grp = [by_oid[o] for o in key if o in by_oid]
        if len(grp) == len(key):
            groups.append(grp)
            seen.add(key)
    enum = V.enumerate_verification_candidates(deck_entries)
    enum_capped = len(enum) >= V.ENUM_BUDGET
    for grp in enum:
        key = frozenset(g["oracle_id"] for g in grp)
        if key not in seen:
            seen.add(key)
            groups.append(grp)

    # EDHREC crowd prior (fleet mode; order-only nudge, no scalar shipped).
    rates = load_rates(deck_id)
    norm_rates = (
        {SYN.normalize_name(k): v for k, v in rates.items()} if rates else None
    )
    weights = ctx["weights"]

    verdicts = []
    kb_gap_abstentions = 0
    for grp in groups:
        key = frozenset(g["oracle_id"] for g in grp)
        v = V.verify_candidate(grp, in_curated=(key in curated))
        if v is None:
            continue
        member_names = [g.get("name", "") for g in grp]
        crowd = None
        if norm_rates is not None:
            rs = [norm_rates.get(SYN.normalize_name(n), 0.0) for n in member_names]
            crowd = (min(rs) / 100.0) if rs else 0.0
        composite = V.rank_composite(v, deck_fit=0.5, crowd_prior=crowd, weights=weights)
        rec = _render(v, member_names, composite, key in curated)
        rec["_ids"] = key
        verdicts.append((v, rec, key))

    # Superset suppression: a closing loop that strictly contains a smaller closing
    # loop is the same loop plus bystanders — keep the minimal set only.
    closing_keys = sorted((k for v, r, k in verdicts if v.closes), key=len)
    minimal: list[frozenset] = []
    for k in closing_keys:
        if not any(m < k for m in minimal):
            minimal.append(k)
    minimal_set = set(minimal)

    buckets = {"verifiedCorroborated": [], "verifiedNovel": [], "engines": [], "capped": []}
    for v, rec, key in verdicts:
        if v.tier_capped:
            buckets["capped"].append(rec)
        elif v.closes:
            if key not in minimal_set:
                continue  # a non-minimal superset of another verified loop
            if key in curated:
                buckets["verifiedCorroborated"].append(rec)
            elif v.novel_eligible:
                buckets["verifiedNovel"].append(rec)
            else:
                # closes but neither curated nor novel-eligible — present as an
                # engine, never as a verified novel loop.
                buckets["engines"].append(rec)
        else:
            # Only surface engines/near-misses with a CONCRETE numeric deficit; a
            # shortfall of None is a KB-gap abstention (cost unmodelled), a QE-2
            # diagnostic — not an actionable user-facing near-miss.
            concrete = [d for d in v.deficit if d.get("shortfall") is not None]
            if concrete or (v.loop_class == "engine" and v.closes):
                buckets["engines"].append(rec)
            else:
                kb_gap_abstentions += 1

    for b in buckets.values():
        b.sort(key=lambda r: (-r["_rank"], r["cards"]))
        for r in b:
            r.pop("_rank", None)
            r.pop("_ids", None)

    return {
        "meta": {
            "deckId": deck_id,
            "source": "Tier-B loop verifier (combo_verifier_lib), DEC-501",
            "corpusVersion": ctx["corpus_version"],
            "ontologyVersion": ctx["ontology_version"],
            "extractorVersion": ctx["extractor_version"],
            "generatedAt": ctx["generated_at"],
            "matchingModel": MATCHING_MODEL,
            "closureModel": "PRD 6.1-6.5 + (k, finite-zone bound) clarification",
            "provenanceGate": "enforced (deterministic|human-reviewed only)",
            "crowdPriorApplied": norm_rates is not None,
            "enumBudgetHit": enum_capped,
            "note": MODEL_NOTE,
        },
        "commander": commanders,
        "counts": {
            "verifiedCorroborated": len(buckets["verifiedCorroborated"]),
            "verifiedNovel": len(buckets["verifiedNovel"]),
            "engines": len(buckets["engines"]),
            "capped": len(buckets["capped"]),
            "candidatesConsidered": len(groups),
            "curatedPresent": len(curated),
            "kbGapAbstentions": kb_gap_abstentions,
        },
        **buckets,
    }


def _render(v: V.Verdict, member_names: list[str], composite: float, in_curated: bool) -> dict:
    d = v.to_dict()
    band = "verified" if d["closes"] else ("engine" if d["loopClass"] == "engine" else "candidate")
    return {
        "cards": sorted(member_names),
        "closes": d["closes"],
        "template": d["template"],
        "loopClass": d["loopClass"],
        "k": d["k"],
        "band": band,
        "resultTypes": d["resultTypes"],
        "finiteZoneBound": d["finiteZoneBound"],
        "trace": d["trace"],
        "deficit": d["deficit"],
        "prerequisites": d["prerequisites"],
        "provenance": d["provenance"],
        "tierCapped": d["tierCapped"],
        "corroboration": in_curated,
        "_rank": composite,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", action="append", help="Deck id (repeatable); default all fleet")
    args = ap.parse_args(argv)

    ids = args.deck or fleet_ids()
    unknown = [d for d in ids if not os.path.exists(os.path.join(COMMANDERS, d, "deck.json"))]
    if unknown:
        print(f"unknown deck id(s): {unknown}", file=sys.stderr)
        return 1

    print("loading raw KB index …", file=sys.stderr)
    by_oid, name_to_oid = V.load_raw_kb_index()
    kb_meta = json.load(open(os.path.join(ROOT, "data", "combo-kb", "meta.json")))
    ctx = {
        "by_oid": by_oid,
        "name_to_oid": name_to_oid,
        "weights": V.load_rank_weights(),
        "corpus_version": kb_meta.get("corpus_version"),
        "ontology_version": kb_meta.get("ontology_version"),
        "extractor_version": kb_meta.get("extractor_version"),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    for deck_id in ids:
        out = build_deck(deck_id, ctx)
        out_path = os.path.join(COMMANDERS, deck_id, "tier-b-loops.json")
        with open(out_path, "w") as f:
            json.dump(out, f, sort_keys=True, indent=2, ensure_ascii=False)
            f.write("\n")
        c = out["counts"]
        print(
            f"  [{deck_id}] corroborated {c['verifiedCorroborated']} "
            f"novel {c['verifiedNovel']} engines {c['engines']} capped {c['capped']} "
            f"(curated present {c['curatedPresent']}, candidates {c['candidatesConsidered']})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

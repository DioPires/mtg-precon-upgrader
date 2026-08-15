#!/usr/bin/env python3
"""QE-1a — C-layer regression: does the Tier-C engine propose known combos?

DEC-491 (DEC-476 Phase 2), PRD QE-1(a). The curated Spellbook corpus is the
standing labeled dataset. For a sample of curated 2-card combos, build a synthetic
deck of exactly the two cards and check whether the C-layer proposes that pair as
a synergy candidate. Reports **recall** — the fraction of sampled combos the
C-layer surfaces.

Per QE-2 a miss is a *diagnostic*, not a failure: a C-layer miss localizes an
ontology gap (the two cards' mechanical relationship isn't in the provides/wants
model yet). So this script reports the rate and lists misses; it does not demand
100%. It exits non-zero only on a hard error (missing inputs), so it is safe to
run in CI as a tracked metric.

The engine is driven from `feature-index.json` (the paste-mode input), so this
regresses the exact data the shipped client consumes.

Usage:
  uv run python scripts/qe1a_synergy_regression.py [--sample N] [--min-recall F]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import combo_synergy_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MATCHER_INDEX = os.path.join(ROOT, "data", "spellbook", "matcher-index.json")


def curated_two_card_combos(matcher: dict) -> list[dict]:
    """Curated variants that are exactly two real cards (no templates, no
    commander-only requirement) — the cleanest C-layer targets."""
    cards = matcher["cards"]
    out = []
    for v in matcher["variants"]:
        if v.get("r"):  # has a template requirement — skip (not a pure card pair)
            continue
        if len(v.get("u", [])) != 2:
            continue
        names = [cards[str(cid)]["n"] for cid in v["u"] if str(cid) in cards]
        if len(names) != 2:
            continue
        out.append({"id": v["id"], "names": names, "pop": v.get("pop", 0)})
    return out


def evaluate(sample: int) -> dict:
    by_oid, name_to_oid = L.load_index_from_feature_index()
    ont = L.load_ontology()
    compat = L.compat_relation(ont)
    fmeta = L.feature_meta(ont)
    idf = L.load_feature_idf()
    matcher = json.load(open(MATCHER_INDEX))

    combos = curated_two_card_combos(matcher)
    # Deterministic sample: highest-popularity combos first (the ones users care
    # about most, and the ones an ontology gap would most embarrassingly miss).
    combos.sort(key=lambda c: (-c["pop"], c["id"]))
    if sample and sample < len(combos):
        combos = combos[:sample]

    hits: list[dict] = []
    misses: list[dict] = []
    both_covered = 0
    for combo in combos:
        n1, n2 = combo["names"]
        # Only meaningful when both cards are covered *and* featureful; a combo
        # whose cards carry no modelled features cannot form a C-layer edge (that
        # is an ontology-gap diagnostic, tallied under misses).
        rep = L.analyze(
            combo["names"], by_oid, name_to_oid, compat, fmeta,
            edhrec_rates=None, deep=False, idf=idf,
        )
        proposed = any(set(p["cards"]) == {n1, n2} for p in rep["pairs"])
        rec = {**combo, "nodes": rep["nodeCount"], "edges": rep["edgeCount"]}
        if rep["nodeCount"] == 2:
            both_covered += 1
        (hits if proposed else misses).append(rec)

    total = len(combos)
    recall = len(hits) / total if total else 0.0
    # Recall among combos where both cards are even featureful (isolates ontology
    # gaps in the *relation* from gaps in per-card feature extraction).
    covered_hits = sum(1 for h in hits if h["nodes"] == 2)
    covered_recall = covered_hits / both_covered if both_covered else 0.0
    return {
        "total": total,
        "hits": len(hits),
        "misses": len(misses),
        "recall": round(recall, 4),
        "bothFeatureful": both_covered,
        "recallAmongFeatureful": round(covered_recall, 4),
        "missSample": [
            {"id": m["id"], "names": m["names"], "nodes": m["nodes"]} for m in misses[:20]
        ],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=400, help="Top-N combos by popularity (0=all)")
    ap.add_argument("--min-recall", type=float, default=0.0,
                    help="Fail (exit 2) if recall-among-featureful is below this (QE-2: diagnostics, default 0)")
    args = ap.parse_args(argv)

    if not os.path.exists(MATCHER_INDEX):
        print(f"missing {MATCHER_INDEX}", file=sys.stderr)
        return 1

    res = evaluate(args.sample)
    print(json.dumps({k: v for k, v in res.items() if k != "missSample"}, indent=2))
    print(f"\nQE-1a C-layer recall: {res['hits']}/{res['total']} = {res['recall']:.1%} "
          f"(among featureful: {res['recallAmongFeatureful']:.1%})")
    if res["missSample"]:
        print("\nOntology-gap diagnostics (sample of misses — QE-2):")
        for m in res["missSample"]:
            tag = "featureful, no edge" if m["nodes"] == 2 else "a card is featureless/uncovered"
            print(f"  {m['names'][0]} + {m['names'][1]}  [{tag}]")

    if res["recallAmongFeatureful"] < args.min_recall:
        print(f"\nFAIL: recall-among-featureful {res['recallAmongFeatureful']:.1%} "
              f"< --min-recall {args.min_recall:.1%}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

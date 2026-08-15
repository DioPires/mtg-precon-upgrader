#!/usr/bin/env python3
"""Precompute per-fleet-deck Tier-C synergy candidates (fleet mode).

DEC-491 (DEC-476 Phase 2). Runs the Tier-C engine (`combo_synergy_lib`) over each
fleet deck's decklist and writes `data/commanders/{id}/synergy-candidates.json` —
a standalone per-deck file like `spellbook-combos.json`, loaded by the Combo Lab
route in fleet mode.

Crowd prior (RK-2, plan decision 4): fleet mode folds the deck's EDHREC inclusion
rates into the ranking. The raw rates live in gitignored `priv_data/edhrec/` and
are NEVER shipped; only the resulting coarse RK-5 band and the matched edges are
committed. No EDHREC-derived scalar is written (the board's public-deployment
terms-exposure gate stays maximally respected, and RK-5 forbids false-precision
scalars anyway). Paste mode (the client engine) omits the prior entirely.

Usage:
  uv run python scripts/build_synergy_candidates.py [--deck ID ...]
  (no --deck ⇒ every fleet deck in data/index.json)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

import combo_synergy_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMANDERS = os.path.join(ROOT, "data", "commanders")
EDHREC_DIR = os.path.join(ROOT, "priv_data", "edhrec")
MATCHING_MODEL = "tier-c-synergy-v1 (provides/wants graph, idf-weighted, reduced-signal)"


def fleet_ids() -> list[str]:
    idx = json.load(open(os.path.join(ROOT, "data", "index.json")))
    return [c["id"] for c in idx.get("commanders", [])]


def load_rates(deck_id: str) -> dict[str, float] | None:
    path = os.path.join(EDHREC_DIR, f"{deck_id}.json")
    if not os.path.exists(path):
        return None
    return json.load(open(path)).get("rates") or None


def _strip(cand: dict) -> dict:
    """Ship coarse band + explainable edges only — never the numeric signals
    (RK-5 false-precision + EDHREC-exposure gate)."""
    return {
        "cards": cand["cards"],
        "edges": cand["edges"],
        "economies": cand["economies"],
        "band": cand["band"],
    }


def build_deck(deck_id: str, ctx: dict) -> dict:
    deck_path = os.path.join(COMMANDERS, deck_id, "deck.json")
    deck = json.load(open(deck_path))
    names = [c["name"] for c in deck.get("decklist", [])]
    commander = deck.get("commander")
    commanders = []
    if commander:
        # Feed the FULL commander name (name_keys aliases every face); split parts
        # are display metadata only.
        names.append(commander)
        commanders = [p.strip() for p in str(commander).split("//") if p.strip()]

    rates = load_rates(deck_id)
    rep = L.analyze(
        names,
        ctx["by_oid"],
        ctx["name_to_oid"],
        ctx["compat"],
        ctx["fmeta"],
        edhrec_rates=rates,
        deep=True,
        idf=ctx["idf"],
    )
    return {
        "meta": {
            "deckId": deck_id,
            "source": "Tier-C synergy engine (combo_synergy_lib), DEC-491",
            "corpusVersion": ctx["corpus_version"],
            "ontologyVersion": ctx["ontology_version"],
            "generatedAt": ctx["generated_at"],
            "matchingModel": MATCHING_MODEL,
            "crowdPriorApplied": rep["crowdPriorApplied"],
            "deepFocused": rep["truncated"]["deepFocused"],
            "note": "Tier C — heuristic / speculative synergy signals, never verified "
            "combos (EI-4). Ranking is provisional and unvalidated against RK-3 until "
            "the Phase-3 calibration; coarse bands only (RK-5). Crowd prior (EDHREC) "
            "folded into ranking; raw rates not shipped.",
        },
        "commander": commanders,
        "counts": rep["counts"],
        "uncovered": rep["uncovered"],
        "pairs": [_strip(c) for c in rep["pairs"]],
        "triples": [_strip(c) for c in rep["triples"]],
        "cycles": [_strip(c) for c in rep["cycles"]],
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

    print("loading KB index …", file=sys.stderr)
    by_oid, name_to_oid = L.load_kb_index()
    ont = L.load_ontology()
    kb_meta = json.load(open(os.path.join(ROOT, "data", "combo-kb", "meta.json")))
    ctx = {
        "by_oid": by_oid,
        "name_to_oid": name_to_oid,
        "compat": L.compat_relation(ont),
        "fmeta": L.feature_meta(ont),
        "idf": L.load_feature_idf(),
        "corpus_version": kb_meta.get("corpus_version"),
        "ontology_version": kb_meta.get("ontology_version"),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    for deck_id in ids:
        out = build_deck(deck_id, ctx)
        out_path = os.path.join(COMMANDERS, deck_id, "synergy-candidates.json")
        with open(out_path, "w") as f:
            json.dump(out, f, sort_keys=True, indent=2, ensure_ascii=False)
            f.write("\n")
        c = out["counts"]
        prior = "prior" if out["meta"]["crowdPriorApplied"] else "NO-prior"
        print(
            f"  [{deck_id}] pairs {c['pairs']}/{c['pairsTotal']} "
            f"triples {c['triples']}/{c['triplesTotal']} cycles {c['cycles']}/{c['cyclesTotal']} "
            f"uncovered {c['uncovered']} ({prior})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

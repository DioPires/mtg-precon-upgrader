#!/usr/bin/env python3
"""DEC-526 surgical merge — add the graveyard-return ontology v1.1 features to the
committed KB entries WITHOUT a destructive full rebuild.

A plain ``build_combo_kb.py`` pass is deterministic-only and rewrites every entry,
which would wipe the committed LLM enrichment (the DEC-506 waves: 1236 llm items,
needs_llm_count 0) and drift the corpus version. This pass instead reads the current
mirror, recomputes ONLY the four new deterministic provides features
(etb_reanimate / aura_fetch / death_return / exile_until_leaves) + the coven guard via
the real extractor, and appends any match to the existing entry — preserving every
existing item (llm included), the corpus version, and needs_llm. It bumps
ontology_version to 1.1.0 fleet-wide and refreshes the meta histograms.

Idempotent: a feature already present on an entry is never re-added.

Usage: uv run python scripts/merge_dec526_features.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_combo_kb as B  # noqa: E402
import combo_kb_lib as KB  # noqa: E402

NEW_FEATURES = {"etb_reanimate", "aura_fetch", "death_return", "exile_until_leaves"}
ENTRIES_DIR = os.path.join(ROOT, "data", "combo-kb", "entries")
META_PATH = os.path.join(ROOT, "data", "combo-kb", "meta.json")
NEW_ONT_VERSION = "1.1.0"


def main() -> int:
    ont = B.load_ontology()
    assert ont["version"] == NEW_ONT_VERSION, ont["version"]
    mirror = {c["oracle_id"]: c for c in json.loads(open(B.MIRROR_FILE).read()) if c.get("oracle_id")}

    prov_hist: Counter = Counter()
    feat_hist: Counter = Counter()
    n = n_needs_llm = 0
    n_reanim = n_aura = n_death = n_exile = n_coven = 0

    for shard_path in sorted(glob.glob(os.path.join(ENTRIES_DIR, "*.json"))):
        entries = json.load(open(shard_path))
        for ce in entries:
            ce["ontology_version"] = NEW_ONT_VERSION
            card = mirror.get(ce.get("oracle_id"))
            if card is not None:
                fresh = B.build_entry(card, ont, ce.get("corpus_version") or "")
                have = {it["feature"] for it in ce.get("provides", [])}
                for it in fresh["provides"]:
                    if it["feature"] in NEW_FEATURES and it["feature"] not in have:
                        ce.setdefault("provides", []).append(it)
                        have.add(it["feature"])
                        n_reanim += it["feature"] == "etb_reanimate"
                        n_aura += it["feature"] == "aura_fetch"
                        n_death += it["feature"] == "death_return"
                        n_exile += it["feature"] == "exile_until_leaves"
                gnames = {g["guard"] for g in ce.get("guards", [])}
                for g in fresh["guards"]:
                    if g["guard"] == "coven" and "coven" not in gnames:
                        ce.setdefault("guards", []).append(g)
                        gnames.add("coven")
                        n_coven += 1
                if ce.get("provides"):
                    ce.setdefault("field_provenance", {})["provides"] = "deterministic"
                if ce.get("guards"):
                    ce.setdefault("field_provenance", {})["guards"] = "deterministic"
                ce["provenance_summary"] = KB.provenance_summary(ce)
            # meta tallies
            for p, c in (ce.get("provenance_summary") or {}).items():
                prov_hist[p] += c
            for it in ce.get("provides", []) + ce.get("wants", []) + ce.get("ambient", []):
                feat_hist[it["feature"]] += 1
            n_needs_llm += int(ce.get("needs_llm", False))
            n += 1
        entries.sort(key=lambda e: e["oracle_id"])
        with open(shard_path, "w") as f:
            f.write(json.dumps(entries, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    meta = json.load(open(META_PATH))
    meta["ontology_version"] = NEW_ONT_VERSION
    meta["needs_llm_count"] = n_needs_llm
    meta["deterministic_signal_count"] = n - n_needs_llm
    meta["provenance_histogram"] = dict(sorted(prov_hist.items()))
    meta["feature_histogram"] = dict(sorted(feat_hist.items(), key=lambda kv: -kv[1]))
    with open(META_PATH, "w") as f:
        f.write(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    print(f"merged {n} entries → ontology {NEW_ONT_VERSION}; corpus {meta.get('corpus_version')}")
    print(f"  new-feature adds: etb_reanimate={n_reanim} aura_fetch={n_aura} "
          f"death_return={n_death} exile_until_leaves={n_exile} coven_guard={n_coven}")
    print(f"  needs_llm={n_needs_llm}  provenance={dict(prov_hist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

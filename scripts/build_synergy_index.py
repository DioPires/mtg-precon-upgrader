#!/usr/bin/env python3
"""Build the compact Tier-C feature-index the paste-mode web engine loads.

DEC-491 (DEC-476 Phase 2). Emits `data/combo-kb/feature-index.json` — a compact
per-card projection of the merged combo-KB carrying only what the client synergy
engine (`web/src/lib/synergyMatch.ts`) needs: name, color identity, and the
provides/wants/ambient feature items with scalar magnitudes.

EVERY covered card is included, even featureless ones (empty p/w/a). That is what
lets paste mode distinguish a *covered-but-featureless* card (no combo economy —
contributes no edges) from a genuinely *uncovered* one (KB-gap caveat, DC-6):
uncovered = name resolves to no index entry at all.

Sibling `feature-index.meta.json` carries the version stamps (DR-7) and is read
first (cheap) so the full index fetch can be corpus-version cache-busted.

Usage:  uv run python scripts/build_synergy_index.py
"""

from __future__ import annotations

import datetime
import glob
import json
import os

import combo_synergy_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KB_DIR = os.path.join(ROOT, "data", "combo-kb")
ENTRIES_DIR = os.path.join(KB_DIR, "entries")
OUT_INDEX = os.path.join(KB_DIR, "feature-index.json")
OUT_META = os.path.join(KB_DIR, "feature-index.meta.json")
OUT_CONFIG = os.path.join(KB_DIR, "synergy-config.json")


def _feats(entry: dict, field: str) -> list[list]:
    """[[feature, magnitude], ...] — compact, magnitudes preserved (KB-2)."""
    return [
        [it["feature"], it.get("magnitude", 1)]
        for it in entry.get(field, []) or []
        if it.get("feature")
    ]


def build() -> tuple[dict, dict]:
    cards: dict[str, dict] = {}
    featureful = 0
    for shard in sorted(glob.glob(os.path.join(ENTRIES_DIR, "*.json"))):
        for e in json.load(open(shard)):
            p, w, a = _feats(e, "provides"), _feats(e, "wants"), _feats(e, "ambient")
            row = {"n": e["name"], "ci": "".join(e.get("color_identity", []) or [])}
            if p:
                row["p"] = p
            if w:
                row["w"] = w
            if a:
                row["a"] = a
            if p or w or a:
                featureful += 1
            cards[e["oracle_id"]] = row

    kb_meta = json.load(open(os.path.join(KB_DIR, "meta.json")))
    meta = {
        "schema": "combo-kb-feature-index",
        "ontologyVersion": kb_meta.get("ontology_version"),
        "extractorVersion": kb_meta.get("extractor_version"),
        "corpusVersion": kb_meta.get("corpus_version"),
        "cardCount": len(cards),
        "featurefulCount": featureful,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": "Compact per-card provides/wants/ambient projection of the combo-KB. "
        "Every covered card is present; featureless cards carry no p/w/a. "
        "uncovered (KB-gap, DC-6) = a name with no entry here at all.",
    }
    return {"cards": cards}, meta


def main() -> int:
    index, meta = build()
    with open(OUT_INDEX, "w") as f:
        json.dump(index, f, sort_keys=True, separators=(",", ":"))
        f.write("\n")
    with open(OUT_META, "w") as f:
        json.dump(meta, f, sort_keys=True, indent=2)
        f.write("\n")
    config = L.export_synergy_config(L.load_ontology(), L.load_feature_idf())
    with open(OUT_CONFIG, "w") as f:
        json.dump(config, f, sort_keys=True, indent=2, ensure_ascii=False)
        f.write("\n")
    size_mb = os.path.getsize(OUT_INDEX) / 1e6
    print(f"feature-index: {meta['cardCount']} cards ({meta['featurefulCount']} featureful), "
          f"{size_mb:.2f} MB -> {OUT_INDEX}")
    print(f"synergy-config: {len(config['compat'])} features -> {OUT_CONFIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

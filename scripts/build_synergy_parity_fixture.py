#!/usr/bin/env python3
"""Regenerate the Python↔TS Tier-C parity fixture.

DEC-552. `web/src/lib/__fixtures__/synergy-parity.json` pins the authoritative
Python engine output for one fixed 12-card paste-mode list. Both halves of the
parity gate read it: `tests/test_combo_synergy.py::test_parity_fixture_matches_engine`
(Python must still emit it) and `web/src/lib/synergyMatch.test.ts` (the TS mirror
must reproduce it).

The fixture is derived from `data/combo-kb/{feature-index,ontology,meta}.json`, so
any combo-KB change that moves the feature histogram or the ontology invalidates
it. Run `build_synergy_index.py` FIRST (it re-emits feature-index.json and
synergy-config.json from the current KB), then this. Neither script touches the KB
entries, so neither can wipe LLM enrichment.

Usage:  uv run python scripts/build_synergy_index.py
        uv run python scripts/build_synergy_parity_fixture.py
"""

from __future__ import annotations

import json
import os

import combo_synergy_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "web", "src", "lib", "__fixtures__", "synergy-parity.json")

COMMENT = (
    "AUTHORITATIVE Python-engine output (paste mode: no crowd prior, deep scan). "
    "web/src/lib/synergyMatch.test.ts asserts the TS mirror reproduces this exactly."
)

# A deliberately dense aristocrats/token list: every economy the ontology models
# for this archetype fires, so the fixture exercises pairs, triples and 4-cycles
# plus the deep-scan caps rather than a thin slice of the engine.
NAMES = [
    "Genesis Chamber",
    "Molten Gatekeeper",
    "Rose Room Treasurer",
    "Impact Tremors",
    "Purphoros, God of the Forge",
    "Witty Roastmaster",
    "Blood Artist",
    "Zulaport Cutthroat",
    "Ashnod's Altar",
    "Viscera Seer",
    "Grave Pact",
    "Eternal Witness",
]

# The TS engine renders exactly these four keys per candidate; `signals` is
# Python-internal and stays out of the fixture (see renderCandidate in
# web/src/lib/synergyMatch.ts).
CANDIDATE_KEYS = ("cards", "edges", "economies", "band")


def build() -> dict:
    by_oid, name_to_oid = L.load_index_from_feature_index()
    ont = L.load_ontology()
    rep = L.analyze(
        NAMES,
        by_oid,
        name_to_oid,
        L.compat_relation(ont),
        L.feature_meta(ont),
        edhrec_rates=None,
        deep=True,
        idf=L.load_feature_idf(),
    )

    def slim(c: dict) -> dict:
        return {k: c[k] for k in CANDIDATE_KEYS}

    return {
        "_comment": COMMENT,
        "names": NAMES,
        "counts": rep["counts"],
        "uncovered": rep["uncovered"],
        "nodeCount": rep["nodeCount"],
        "edgeCount": rep["edgeCount"],
        "truncated": rep["truncated"],
        "pairs": [slim(c) for c in rep["pairs"]],
        "triples": [slim(c) for c in rep["triples"]],
        "cycles": [slim(c) for c in rep["cycles"]],
    }


def main() -> int:
    fixture = build()
    with open(OUT, "w") as f:
        json.dump(fixture, f, sort_keys=True, indent=2)
        f.write("\n")
    c = fixture["counts"]
    print(
        f"synergy-parity: {fixture['nodeCount']} nodes / {fixture['edgeCount']} edges, "
        f"{c['pairs']} pairs, {c['triples']} triples, {c['cycles']} cycles -> {OUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

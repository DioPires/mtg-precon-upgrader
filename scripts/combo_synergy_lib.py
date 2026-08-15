#!/usr/bin/env python3
"""Tier-C synergy engine — DEC-491 (DEC-476 Phase 2).

The single source of truth for the Combo Lab's heuristic (Tier-C) layer. Builds a
deck-scoped provides/wants graph from the merged combo-KB (`data/combo-kb/`) using
the ontology's ``pairs_with`` compatibility relation, enumerates pair / triple /
4-cycle candidates (DC-2, DC-5), and ranks them by a reduced-signal score
(magnitude + deck-fit, plus an EDHREC crowd prior in FLEET MODE ONLY — plan
decision 4). Presentation is coarse bands only (RK-5); ranking never alters tier
(RK-6). Everything here is Tier C — speculative / synergy, never verified-combo
language (EI-4).

Provenance: Tier-C MAY consume ``llm`` items (the Tier-B provenance gate in
`combo_kb_lib.tier_b_view` is a Phase-3 concern). This module deliberately reads
all feature items regardless of provenance.

The paste-mode web engine (`web/src/lib/synergyMatch.ts`) mirrors this file; keep
the two in sync. `tests/test_combo_synergy.py` + the vitest parity test guard it.
"""

from __future__ import annotations

import glob
import json
import os
import re
import unicodedata
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KB_DIR = os.path.join(ROOT, "data", "combo-kb")
ENTRIES_DIR = os.path.join(KB_DIR, "entries")
ONTOLOGY_PATH = os.path.join(KB_DIR, "ontology.json")

# Output caps — deterministic, and NEVER silent: analyze() returns *_total counts
# alongside the capped lists so the report can say "showing N of M".
PAIR_CAP = 80
TRIPLE_CAP = 40
CYCLE_CAP = 30

# Deep-scan enumeration bound (NF-3): triangles and 4-cycles are walked only over
# the subgraph induced by the strongest DEEP_EDGE_LIMIT edges by weight. Dense
# aristocrats/token decks otherwise yield 10^4–10^5 cycles and blow the
# interactive-latency budget. Restricting to the top edges is deterministic and
# focuses the deep scan on the strongest couplings; the restriction is disclosed
# via a `focused` flag rather than silently applied. Pairs are never restricted.
DEEP_EDGE_LIMIT = 200
# Belt-and-suspenders ceilings in case the focused subgraph is still dense.
TRIANGLE_ENUM_BUDGET = 20000
CYCLE_ENUM_BUDGET = 20000

# Provisional reduced-signal weights (RK-2 partial). Phase-2 ranking is
# unvalidated against RK-3 until the Phase-3 calibration re-fit; these are equal-
# ish placeholders, not hand-tuned, and only ever drive the coarse RK-5 band.
W_MAGNITUDE = 1.0
W_DECK_FIT = 1.0
W_CROWD_PRIOR = 1.0

# Edge weight normalization scale (saturating): higher IDF-weight ⇒ rarer, more
# specific matched features ⇒ stronger magnitude signal.
EDGE_WEIGHT_SCALE = 6.0

# Coarse RK-5 band cut. A composite in [0, 1]; above the cut is "strong", else
# "speculative". Two within-Tier-C bands — the epistemic tier stays C either way.
STRONG_BAND_CUT = 0.5

# The one ubiquitous non-synergy: "adds mana" ↔ "mana sink" is present in every
# deck (anything that costs mana pairs with anything that makes it) and carries no
# insight. It is a Tier-B loop *fuel* relationship (untap↔mana_add is the loop
# seed, kept), not a Tier-C synergy. Excluded from Tier-C display by construction.
# Kept deliberately small and documented — general noise is handled by IDF weight.
NOISE_PAIRS = frozenset({frozenset({"mana_add", "mana_sink"})})

# Minimum IDF-weighted signal for an edge to survive into the graph — prunes the
# weakest couplings so triangle/cycle enumeration stays sparse and fast.
EDGE_MIN_SIGNAL = 3.0

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


# ─── Name normalization (mirror of web/src/lib/spellbookMatch.ts) ────────────────
def normalize_name(name: str) -> str:
    if not name:
        return ""
    ascii_ = unicodedata.normalize("NFKD", name)
    ascii_ = "".join(c for c in ascii_ if not unicodedata.combining(c))
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", ascii_.lower())).strip()


def name_keys(name: str) -> list[str]:
    """Normalized full name plus every face key for split/DFC/adventure cards.

    The schema aliases every face so a decklist naming either face resolves (e.g.
    "The Invincible Iron Man" for `Tony Stark // The Invincible Iron Man`). Mirror
    of nameKeys() in web/src/lib/synergyMatch.ts."""
    keys: list[str] = []
    full = normalize_name(name)
    if full:
        keys.append(full)
    if "//" in name:
        for face in name.split("//"):
            fk = normalize_name(face)
            if fk and fk not in keys:
                keys.append(fk)
    return keys


# ─── Ontology compatibility relation ─────────────────────────────────────────────
def load_ontology(path: str = ONTOLOGY_PATH) -> dict:
    return json.load(open(path))


def feature_meta(ontology: dict) -> dict[str, dict]:
    """feature id → {label, economy, role_hint, kind}. First definition wins for
    ids that appear under multiple kinds (label is the same)."""
    meta: dict[str, dict] = {}
    for f in ontology.get("features", []):
        fid = f["id"]
        meta.setdefault(
            fid,
            {
                "label": f.get("label", fid),
                "economy": f.get("economy", ""),
                "role_hint": f.get("role_hint", ""),
                "kind": f.get("kind", ""),
            },
        )
    return meta


def load_feature_idf(meta_path: str | None = None) -> dict[str, float]:
    """Inverse document frequency per feature from the KB pool histogram
    (`meta.json`). Rare features (token_doubler, trigger_doubler, blink) score
    high; ubiquitous ones (mana_sink, etb_trigger) score low. This is what keeps
    the ranking from drowning in generic couplings (KB-2 "unrankable candidate
    soup"). Missing histogram ⇒ uniform 1.0."""
    import math

    path = meta_path or os.path.join(KB_DIR, "meta.json")
    try:
        meta = json.load(open(path))
    except FileNotFoundError:
        return {}
    n = meta.get("card_count", 0) or 0
    hist = meta.get("feature_histogram", {}) or {}
    if not n or not hist:
        return {}
    return {f: math.log(n / (1 + c)) for f, c in hist.items()}


def compat_relation(ontology: dict) -> dict[str, frozenset[str]]:
    """Symmetric closure of the ontology's ``pairs_with`` edges: a feature X is
    compatible with feature Y iff Y ∈ pairs_with(X) OR X ∈ pairs_with(Y). The raw
    data is directionally authored (a payoff lists its sources); the symmetric
    closure captures the pairing regardless of which side recorded it."""
    adj: dict[str, set[str]] = {}
    for f in ontology.get("features", []):
        a = f["id"]
        adj.setdefault(a, set())
        for b in f.get("pairs_with", []) or []:
            adj.setdefault(b, set())
            adj[a].add(b)
            adj[b].add(a)
    return {k: frozenset(v) for k, v in adj.items()}


# ─── KB entry loading (lean in-memory index) ─────────────────────────────────────
def _lean_entry(e: dict) -> dict:
    """Keep only what the synergy layer needs; drop oracle text / triggers / costs."""
    def feats(field: str) -> list[dict]:
        return [
            {"feature": it["feature"], "magnitude": it.get("magnitude", 1)}
            for it in e.get(field, []) or []
            if it.get("feature")
        ]

    return {
        "oracle_id": e["oracle_id"],
        "name": e["name"],
        "ci": list(e.get("color_identity", []) or []),
        "provides": feats("provides"),
        "wants": feats("wants"),
        "ambient": feats("ambient"),
    }


def load_index_from_feature_index(
    path: str | None = None,
) -> tuple[dict[str, dict], dict[str, str]]:
    """Load (oracle_id → lean entry, name key → oracle_id) from the compact
    `feature-index.json` — the SAME input the TS paste-mode engine consumes. Used
    by the paste-mode-equivalent Python path (QE-1a, parity fixture) so both
    engines are driven by byte-identical feature data."""
    path = path or os.path.join(KB_DIR, "feature-index.json")
    raw = json.load(open(path))["cards"]
    by_oid: dict[str, dict] = {}
    name_to_oid: dict[str, str] = {}
    for oid, row in raw.items():
        entry = {
            "oracle_id": oid,
            "name": row["n"],
            "ci": list(row.get("ci", "")),
            "provides": [{"feature": f, "magnitude": m} for f, m in row.get("p", [])],
            "wants": [{"feature": f, "magnitude": m} for f, m in row.get("w", [])],
            "ambient": [{"feature": f, "magnitude": m} for f, m in row.get("a", [])],
        }
        by_oid[oid] = entry
        for k in name_keys(entry["name"]):
            name_to_oid.setdefault(k, oid)
    return by_oid, name_to_oid


def load_kb_index(entries_dir: str = ENTRIES_DIR) -> tuple[dict[str, dict], dict[str, str]]:
    """Load the full KB into (oracle_id → lean entry, normalized name key → oracle_id).

    The name map aliases every DFC/split face so a decklist naming either face
    resolves. Featureless cards are still indexed (they are *covered* — they just
    contribute no edges), so callers can distinguish covered-but-featureless from
    genuinely uncovered (KB-gap caveat, DC-6)."""
    by_oid: dict[str, dict] = {}
    name_to_oid: dict[str, str] = {}
    for shard in sorted(glob.glob(os.path.join(entries_dir, "*.json"))):
        for e in json.load(open(shard)):
            lean = _lean_entry(e)
            oid = lean["oracle_id"]
            by_oid[oid] = lean
            for k in name_keys(lean["name"]):
                name_to_oid.setdefault(k, oid)
    return by_oid, name_to_oid


def export_synergy_config(ontology: dict, idf: dict[str, float]) -> dict:
    """The shared config both engines consume so only algorithm logic is
    duplicated across Python and TS, never the data/constants. Emitted to
    `data/combo-kb/synergy-config.json` by build_synergy_index.py and read by
    `web/src/lib/synergyMatch.ts` — the single source of truth for the compat
    relation, IDF, labels, economies, noise pairs, and the numeric constants."""
    fmeta = feature_meta(ontology)
    compat = compat_relation(ontology)
    return {
        "schema": "combo-synergy-config",
        "ontologyVersion": ontology.get("version"),
        "compat": {k: sorted(v) for k, v in sorted(compat.items())},
        "idf": {k: round(v, 4) for k, v in sorted(idf.items())},
        "labels": {k: fmeta[k]["label"] for k in sorted(fmeta)},
        "economies": {k: fmeta[k]["economy"] for k in sorted(fmeta)},
        "noisePairs": sorted(sorted(p) for p in NOISE_PAIRS),
        "constants": {
            "EDGE_MIN_SIGNAL": EDGE_MIN_SIGNAL,
            "EDGE_WEIGHT_SCALE": EDGE_WEIGHT_SCALE,
            "DEEP_EDGE_LIMIT": DEEP_EDGE_LIMIT,
            "STRONG_BAND_CUT": STRONG_BAND_CUT,
            "PAIR_CAP": PAIR_CAP,
            "TRIPLE_CAP": TRIPLE_CAP,
            "CYCLE_CAP": CYCLE_CAP,
            "W_MAGNITUDE": W_MAGNITUDE,
            "W_DECK_FIT": W_DECK_FIT,
            "W_CROWD_PRIOR": W_CROWD_PRIOR,
            "IDF_FALLBACK": 2.0,
        },
    }


# ─── Deck resolution ─────────────────────────────────────────────────────────────
def resolve_deck(
    names: Iterable[str], by_oid: dict[str, dict], name_to_oid: dict[str, str]
) -> tuple[list[dict], list[str]]:
    """Resolve card names to KB entries. Returns (resolved entries, uncovered names).

    ``uncovered`` = a name that resolves to no KB entry at all (KB-gap caveat,
    distinct from IN-6 unresolvable lines, which fail *parsing* upstream). Deduped
    by oracle_id so a singleton deck yields one node per card."""
    resolved: dict[str, dict] = {}
    uncovered: list[str] = []
    seen_uncovered: set[str] = set()
    for raw in names:
        oid = None
        for k in name_keys(raw):
            if k in name_to_oid:
                oid = name_to_oid[k]
                break
        if oid is None:
            key = normalize_name(raw)
            if key and key not in seen_uncovered:
                seen_uncovered.add(key)
                uncovered.append(raw)
            continue
        resolved.setdefault(oid, by_oid[oid])
    return list(resolved.values()), uncovered


def card_features(entry: dict) -> dict[str, int]:
    """All feature ids on a card → max magnitude seen for that feature."""
    out: dict[str, int] = {}
    for field in ("provides", "wants", "ambient"):
        for it in entry.get(field, []) or []:
            f = it["feature"]
            out[f] = max(out.get(f, 0), it.get("magnitude", 1))
    return out


# ─── Provides/wants graph ────────────────────────────────────────────────────────
def build_graph(
    cards: list[dict],
    compat: dict[str, frozenset[str]],
    fmeta: dict,
    idf: dict[str, float],
) -> dict:
    """Undirected synergy graph over deck cards. An edge exists between two cards
    when a feature of one is compatible with a feature of the other, the pair is
    not a NOISE_PAIR, and the edge's IDF-weighted signal clears EDGE_MIN_SIGNAL.
    Each edge records its matched feature pairs with magnitudes and human labels
    (DC-3 / TX-1: every synergy is explainable as its matched edges)."""
    nodes = [c for c in cards if card_features(c)]
    feats = [card_features(c) for c in nodes]
    edges: list[dict] = []
    adj: dict[int, set[int]] = {i: set() for i in range(len(nodes))}
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            matches = _match_features(feats[i], feats[j], compat, fmeta, idf)
            if not matches:
                continue
            weight = _edge_weight(matches)
            if weight < EDGE_MIN_SIGNAL:
                continue
            edges.append({"i": i, "j": j, "matches": matches, "weight": weight})
            adj[i].add(j)
            adj[j].add(i)
    return {"nodes": nodes, "features": feats, "edges": edges, "adj": adj}


def _pair_signal(x: str, y: str, magnitude: int, idf: dict[str, float]) -> float:
    """IDF-weighted signal for one matched feature pair. Falls back to a flat 2.0
    per feature when no IDF is available so the relation still ranks by magnitude."""
    ix = idf.get(x, 2.0)
    iy = idf.get(y, 2.0)
    return magnitude * (ix + iy)


def _match_features(
    fa: dict[str, int],
    fb: dict[str, int],
    compat: dict[str, frozenset[str]],
    fmeta: dict,
    idf: dict[str, float],
) -> list[dict]:
    """Compatible (feature_a, feature_b) pairs between two cards' feature sets,
    minus NOISE_PAIRS, each carrying its IDF-weighted signal."""
    matches: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for x, mx in fa.items():
        cx = compat.get(x, frozenset())
        for y, my in fb.items():
            if x == y:
                continue  # no feature pairs with itself in the ontology
            if y not in cx:
                continue
            if frozenset({x, y}) in NOISE_PAIRS:
                continue
            key = tuple(sorted((x, y)))
            if key in seen:
                continue
            seen.add(key)
            magnitude = max(mx, my)
            matches.append(
                {
                    "from_feature": x,
                    "to_feature": y,
                    "magnitude": magnitude,
                    "signal": round(_pair_signal(x, y, magnitude, idf), 4),
                    "label": f"{fmeta.get(x, {}).get('label', x)} ↔ "
                    f"{fmeta.get(y, {}).get('label', y)}",
                    "economy": fmeta.get(x, {}).get("economy", ""),
                }
            )
    return matches


def _edge_weight(matches: list[dict]) -> float:
    return round(sum(m["signal"] for m in matches), 4)


# ─── Candidate enumeration (DC-2, DC-5) ──────────────────────────────────────────
def enumerate_candidates(graph: dict, deep: bool = True) -> dict:
    """Pairs (all edges), triples (triangles), 4-cycles (simple 4-cycles).

    Triangles and 4-cycles are cycle enumeration over the sparse typed graph — NOT
    card-subset brute force (C(100,4) is prohibited, NM-4/DC-5). ``deep=False``
    returns pairs only (the default UI view; triples/cycles sit behind the
    deep-scan action, OQ-3). Enumeration is bounded by TRIANGLE/CYCLE_ENUM_BUDGET;
    hitting a budget sets a truncation flag rather than silently dropping work."""
    edges = graph["edges"]
    edge_map = {(e["i"], e["j"]): e for e in edges}

    pairs = [{"members": [e["i"], e["j"]], "edges": [(e["i"], e["j"])], "weight": e["weight"]}
             for e in edges]

    triples: list[dict] = []
    cycles: list[dict] = []
    tri_trunc = False
    cyc_trunc = False
    focused = False
    if deep:
        # Focus the deep scan on the strongest DEEP_EDGE_LIMIT edges (disclosed).
        ranked = sorted(edges, key=lambda e: (-e["weight"], e["i"], e["j"]))
        if len(ranked) > DEEP_EDGE_LIMIT:
            ranked = ranked[:DEEP_EDGE_LIMIT]
            focused = True
        edge_set = {(e["i"], e["j"]) for e in ranked}
        adj: dict[int, set[int]] = {}
        for e in ranked:
            adj.setdefault(e["i"], set()).add(e["j"])
            adj.setdefault(e["j"], set()).add(e["i"])
        # Triangles: i<j<k all pairwise connected.
        for (i, j) in sorted(edge_set):
            if len(triples) >= TRIANGLE_ENUM_BUDGET:
                tri_trunc = True
                break
            for k in sorted(adj[i] & adj[j]):
                if k > j:
                    tri_edges = [_ekey(i, j), _ekey(i, k), _ekey(j, k)]
                    triples.append(
                        {
                            "members": [i, j, k],
                            "edges": tri_edges,
                            "weight": round(sum(edge_map[e]["weight"] for e in tri_edges), 4),
                        }
                    )
        # Simple 4-cycles i-j-k-l-i with i the smallest vertex; dedupe by node set.
        seen4: set[tuple[int, ...]] = set()
        for i in sorted(adj):
            if len(cycles) >= CYCLE_ENUM_BUDGET:
                cyc_trunc = True
                break
            # Sorted neighbor iteration everywhere ⇒ enumeration order is fully
            # deterministic and matches the TS mirror (which cannot rely on
            # CPython set iteration order).
            for j in sorted(n for n in adj[i] if n > i):
                for k in sorted(adj[j]):
                    if k <= i:
                        continue
                    for l in sorted(adj[k]):
                        if l <= i or l == j or l not in adj[i]:
                            continue
                        quad = tuple(sorted((i, j, k, l)))
                        if quad in seen4:
                            continue
                        seen4.add(quad)
                        ce = [_ekey(i, j), _ekey(j, k), _ekey(k, l), _ekey(l, i)]
                        cycles.append(
                            {
                                "members": [i, j, k, l],
                                "edges": ce,
                                "weight": round(
                                    sum(edge_map[e]["weight"] for e in ce if e in edge_map), 4
                                ),
                            }
                        )
    return {
        "pairs": pairs,
        "triples": triples,
        "cycles": cycles,
        "truncated": {"triples": tri_trunc, "cycles": cyc_trunc, "deepFocused": focused},
    }


def _ekey(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


# ─── Ranking (RK-1, RK-2 reduced-signal, RK-5 bands, RK-6 tier invariance) ───────
def deck_feature_histogram(cards: list[dict]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for c in cards:
        for f in card_features(c):
            hist[f] = hist.get(f, 0) + 1
    return hist


def _magnitude_signal(weight: float) -> float:
    # Saturating in the edge's IDF-weighted signal so one rare-feature coupling
    # scores high but no single edge runs away with the ranking.
    return 1.0 - 1.0 / (1.0 + max(weight, 0.0) / EDGE_WEIGHT_SCALE)


def _deck_fit_signal(member_feats: list[dict[str, int]], hist: dict[str, int]) -> float:
    if not hist:
        return 0.0
    top = max(hist.values())
    feats = set()
    for mf in member_feats:
        feats.update(mf.keys())
    if not feats:
        return 0.0
    return sum(hist.get(f, 0) / top for f in feats) / len(feats)


def _crowd_prior_signal(names: list[str], edhrec_rates: dict[str, float] | None) -> float:
    if not edhrec_rates:
        return 0.0
    rates = []
    norm = {normalize_name(k): v for k, v in edhrec_rates.items()}
    for n in names:
        rates.append(norm.get(normalize_name(n), 0.0))
    if not rates:
        return 0.0
    # Geometric-ish: reward candidates whose *every* card is a crowd staple.
    return min(rates) / 100.0


def score_candidate(
    cand: dict, graph: dict, hist: dict[str, int], edhrec_rates: dict[str, float] | None
) -> dict:
    members = cand["members"]
    member_feats = [graph["features"][m] for m in members]
    names = [graph["nodes"][m]["name"] for m in members]
    mag = _magnitude_signal(cand["weight"])
    fit = _deck_fit_signal(member_feats, hist)
    crowd = _crowd_prior_signal(names, edhrec_rates)
    crowd_applied = edhrec_rates is not None
    denom = W_MAGNITUDE + W_DECK_FIT + (W_CROWD_PRIOR if crowd_applied else 0.0)
    composite = (
        W_MAGNITUDE * mag + W_DECK_FIT * fit + (W_CROWD_PRIOR * crowd if crowd_applied else 0.0)
    ) / denom
    return {
        "magnitude": round(mag, 4),
        "deck_fit": round(fit, 4),
        "crowd_prior": round(crowd, 4) if crowd_applied else None,
        "composite": round(composite, 4),
    }


def band_for(composite: float) -> str:
    """Coarse RK-5 band WITHIN Tier C. Never a scalar to the user; the tier stays
    C regardless (RK-6)."""
    return "strong" if composite >= STRONG_BAND_CUT else "speculative"


# ─── Top-level analysis ──────────────────────────────────────────────────────────
def _render_candidate(cand: dict, graph: dict, signals: dict) -> dict:
    nodes = graph["nodes"]
    edge_map = {(e["i"], e["j"]): e for e in graph["edges"]}
    names = [nodes[m]["name"] for m in cand["members"]]
    rendered_edges = []
    economies: set[str] = set()
    for (a, b) in cand["edges"]:
        e = edge_map.get((a, b))
        if not e:
            continue
        for m in e["matches"]:
            rendered_edges.append(
                {
                    "from": nodes[a]["name"],
                    "to": nodes[b]["name"],
                    "fromFeature": m["from_feature"],
                    "toFeature": m["to_feature"],
                    "magnitude": m["magnitude"],
                    "label": m["label"],
                }
            )
            if m["economy"]:
                economies.add(m["economy"])
    return {
        "cards": sorted(names),
        "edges": sorted(
            rendered_edges,
            key=lambda r: (r["from"], r["to"], r["fromFeature"], r["toFeature"]),
        ),
        "economies": sorted(economies),
        "band": band_for(signals["composite"]),
        "signals": signals,
    }


def analyze(
    names: Iterable[str],
    by_oid: dict[str, dict],
    name_to_oid: dict[str, str],
    compat: dict[str, frozenset[str]],
    fmeta: dict,
    edhrec_rates: dict[str, float] | None = None,
    deep: bool = True,
    idf: dict[str, float] | None = None,
) -> dict:
    """Full Tier-C report for a decklist. ``edhrec_rates`` present ⇒ fleet mode
    (crowd prior applied); absent ⇒ paste mode (prior omitted, and the report
    records that so the UI note is accurate — plan decision 4)."""
    if idf is None:
        idf = load_feature_idf()
    cards, uncovered = resolve_deck(names, by_oid, name_to_oid)
    graph = build_graph(cards, compat, fmeta, idf)
    hist = deck_feature_histogram(graph["nodes"])
    cands = enumerate_candidates(graph, deep=deep)

    def rank(items: list[dict], cap: int) -> tuple[list[dict], int]:
        scored = []
        for c in items:
            sig = score_candidate(c, graph, hist, edhrec_rates)
            scored.append((sig["composite"], _render_candidate(c, graph, sig)))
        scored.sort(key=lambda t: (-t[0], t[1]["cards"]))
        return [r for _, r in scored[:cap]], len(scored)

    pairs, pairs_total = rank(cands["pairs"], PAIR_CAP)
    triples, triples_total = rank(cands["triples"], TRIPLE_CAP)
    cycles, cycles_total = rank(cands["cycles"], CYCLE_CAP)

    return {
        "crowdPriorApplied": edhrec_rates is not None,
        "nodeCount": len(graph["nodes"]),
        "edgeCount": len(graph["edges"]),
        "uncovered": sorted(uncovered),
        "truncated": cands["truncated"],
        "counts": {
            "pairs": len(pairs),
            "pairsTotal": pairs_total,
            "triples": len(triples),
            "triplesTotal": triples_total,
            "cycles": len(cycles),
            "cyclesTotal": cycles_total,
            "uncovered": len(uncovered),
        },
        "pairs": pairs,
        "triples": triples,
        "cycles": cycles,
    }

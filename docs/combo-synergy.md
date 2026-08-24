# Combo Lab Tier-C Synergy Engine (DEC-476 Phase 2 / DEC-491)

The heuristic (Tier-C) layer of the Combo Lab. Given a decklist it builds a
provides/wants graph from the merged combo-KB, enumerates pair / triple / 4-cycle
synergy candidates, and ranks them by a reduced-signal score presented as coarse
bands. Everything here is **Tier C — speculative / synergy signals, never
verified combos** (PRD §6.7, EI-1/EI-4). This document is the contract; it
implements PRD DC-1..DC-6, RK-1/RK-2(partial)/RK-5/RK-6, DR-4, TX-1/TX-2 (Tier C),
QE-1(a), NF-3 (enumeration slice), and plan decisions 4/6.

## 1. Two surfaces, one model

Mirrors the Phase-0 split (fleet precompute + paste client-side) so both surfaces
agree and EDHREC never reaches the browser:

| Surface | Engine | Crowd prior | Input |
|---|---|---|---|
| **Fleet mode** | `scripts/combo_synergy_lib.py` (build time) | **applied** (EDHREC, baked into ranking) | `data/commanders/{id}/synergy-candidates.json` |
| **Paste mode** | `web/src/lib/synergyMatch.ts` (browser) | **omitted** (plan decision 4) | `data/combo-kb/feature-index.json` in memory |

`combo_synergy_lib.py` is the single source of truth; `synergyMatch.ts` is a
faithful mirror. The shared `data/combo-kb/synergy-config.json` (compat relation,
IDF, labels, economies, noise pairs, numeric constants) is consumed by **both**,
so only algorithm logic is duplicated across languages, never the data/constants.
Parity is pinned by `web/src/lib/__fixtures__/synergy-parity.json` (authoritative
Python output) asserted from both `tests/test_combo_synergy.py` and
`web/src/lib/synergyMatch.test.ts`.

## 2. Provides/wants graph (DC-1, DC-3)

- **Nodes:** deck cards with at least one modelled feature (provides ∪ wants ∪
  ambient), resolved by oracle identity with every DFC face aliased.
- **Edges:** two cards are connected when a feature of one is compatible with a
  feature of the other under the ontology's `pairs_with` relation (symmetric
  closure). Each edge records its matched feature pairs with magnitudes and a
  human label ("Sacrifice outlet ↔ Death payoff") — every synergy is explainable
  as its matched edges (DC-3 / TX-1). Edgeless "these cards are good together" is
  impossible by construction.

### Noise control (avoids KB-2 "candidate soup")

Two mechanisms keep the ranking out of the generic-coupling hairball:

1. **IDF weighting.** Each matched pair's signal is `magnitude × (idf(x) +
   idf(y))`, where IDF is the pool inverse-document-frequency from
   `meta.json`'s feature histogram. Rare features (`token_doubler`,
   `trigger_doubler`, `blink`) dominate; ubiquitous ones (`mana_sink`,
   `etb_trigger`) are damped.
2. **Noise-pair exclusion.** The single ubiquitous non-synergy `mana_add ↔
   mana_sink` (present in every deck: anything that costs mana pairs with anything
   that makes it) is excluded from Tier-C display. It is Tier-B loop *fuel*
   (`untap ↔ mana_add` is the loop seed, kept), not a Tier-C synergy. This is the
   only hard-coded exclusion; general noise is IDF's job.

Edges below `EDGE_MIN_SIGNAL` are pruned so the graph stays sparse.

## 3. Candidate enumeration (DC-2, DC-5, NF-3)

- **Pairs:** every surviving edge.
- **Triples:** triangles (three cards pairwise connected) — a two-card match
  completed by a third capability.
- **4-cycles:** simple 4-cycles in the graph — the Tier-B cap contingency (plan
  §Tier-B cycle-piece cap), funded here, matured in Phase 3.

This is cycle enumeration over the sparse typed graph — **not** card-subset brute
force (C(100,4) is prohibited, NM-4/DC-5). For NF-3 interactive latency, the deep
scan (triples + 4-cycles) is bounded to the subgraph induced by the strongest
`DEEP_EDGE_LIMIT` edges; the restriction is disclosed via a `deepFocused` flag,
never silently applied. Paste mode defaults to **pairs only** (instant); triples
and 4-cycles sit behind the UI deep-scan action (OQ-3).

## 4. Ranking v1 — reduced signal (RK-1, RK-2, RK-5, RK-6)

Composite = weighted mean of the available signals:

- **magnitude** — saturating in the edge's IDF-weighted signal.
- **deck fit** — alignment of the candidate's features with the deck's aggregate
  feature histogram (a mill synergy ranks higher in a mill deck).
- **crowd prior** — EDHREC co-occurrence, **fleet mode only** (decision 4). Paste
  mode omits the term and the ranking explanation says so.

Mechanistic rate and startup cost are **dark** until Phase 3 (they need the
verifier's vectors) and join with a re-fit then. **Phase-2 ranking is provisional
and unvalidated against RK-3 until the Phase-3 calibration.** Presentation is two
coarse bands within Tier C — `strong` / `speculative` (RK-5) — never a
falsely-precise scalar. The band is **not** the tier: every finding stays Tier C
regardless of band (RK-6).

### EDHREC exposure (decision 4 hard gate)

Raw EDHREC rates live in gitignored `priv_data/edhrec/` and are **never shipped**.
The fleet precompute folds the prior into the ranking; the committed
`synergy-candidates.json` carries only the coarse band and the matched edges — no
EDHREC-derived scalar. Public-deployment terms exposure remains a board
re-review, out of this phase's scope.

## 5. KB-gap caveat (DC-6)

A card that resolves by name but has **no KB / feature-index entry** is marked
`uncovered` in the report — distinct from IN-6 unresolvable lines (a name that
resolves to no card at all, handled by the parser). The feature-index includes
every covered card (featureless ones carry no features), so a covered-but-
featureless card (no combo economy) is correctly *not* flagged uncovered — it
simply contributes no edges. An uncovered card is disclosed, never guessed.

## 6. Build pipeline

| Step | Script | Output |
|---|---|---|
| Feature index + shared config | `build_synergy_index.py` | `data/combo-kb/feature-index.json` (+ `.meta.json`), `synergy-config.json` |
| Parity fixture | `build_synergy_parity_fixture.py` | `web/src/lib/__fixtures__/synergy-parity.json` |
| Fleet precompute | `build_synergy_candidates.py [--deck ID]` | `data/commanders/{id}/synergy-candidates.json` |
| EDHREC cache (fleet, gitignored) | `fetch_edhrec_rates.py --deck ID` | `priv_data/edhrec/{id}.json` |
| QE-1a C-layer regression | `qe1a_synergy_regression.py` | recall metric + ontology-gap diagnostics |

**After ANY combo-KB change (ontology, extractor, or entries), re-run the first
two in order** — `build_synergy_index.py`, then `build_synergy_parity_fixture.py` —
and then `build_synergy_candidates.py` for the fleet. Skipping either of the first
two silently splits the two surfaces: paste mode keeps serving the old features
while fleet mode (which reads the KB entries directly) uses the new ones. That is
exactly what DEC-552 fixed — the ontology v1.1 graveyard-return primitives landed
in DEC-526/DEC-530 without a re-emit, so `synergy-config.json` was missing four
features and every IDF weight was computed off a stale histogram. Neither script
touches the KB entries, so neither can wipe LLM enrichment.

`tests/test_combo_synergy.py::test_parity_fixture_matches_engine` is the drift
alarm: it fails whenever the committed fixture no longer equals a fresh Python
run. The fix is always to re-emit (Python is the source of truth), never to relax
the assertion. Bump `web/src/data/loader.ts` `STORAGE_PREFIX` if the committed
bundle shape changes (done: v109 → v110 for the `synergyCandidates` member).

## 7. QE-1a — C-layer regression (QE-1 a-slice)

`qe1a_synergy_regression.py` samples curated 2-card combos from the Spellbook
matcher index, builds a synthetic deck of the two cards, and checks whether the
C-layer proposes the pair. It reports **recall** and lists misses as
**ontology-gap diagnostics** (QE-2: a C-layer miss localizes an ontology gap, not
a bug). It is a tracked metric, not a pass/fail gate (`--min-recall` default 0) —
recall against a v1 reduced-signal ontology is expected to be partial, and every
miss is a candidate for Phase-1's QE-3 gap review (extending the ontology is
DEC-488's domain, not this phase's).

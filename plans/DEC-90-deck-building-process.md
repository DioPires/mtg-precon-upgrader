# DEC-90 — Deck Building Process Overview

**Status:** Plan revision **r3** — P7 (foundation-first taxonomy + metrics) approved by board on 2026-05-04 and sequenced before P6 deck-by-deck adoption (DEC-99). DEC-99 is blocked by DEC-114 (P7 tracker).

## The Problem

When analysing a new deck or reviewing an existing one we routinely overlook printed cards. Symptoms:

- Recommendations skew to staples/recent prints we already remember.
- The recommendation engine (`scripts/generate_recommendations.py`) **scores cards we already have in scope** — it does not enumerate the full commander-legal universe matching deck criteria.
- No archetype → query mapping forces a broad sweep before review.
- Owned-cards CSV (`priv_data/owned_formatted.csv`, 4,206 rows) is referenced as an overlay but not as a *discovery* source for adds.

## Root cause

Discovery is *recall-led* (we query for cards we think of) instead of *retrieval-led* (we enumerate every commander-legal card matching deck criteria, then filter).

Agreed standard from `agents-files/global/AGENTS.md`: *"Retrieval over recall — verify domain facts against specs, docs, or APIs before relying on training knowledge."* We're violating this for card discovery.

## Resolved direction (board-confirmed via interaction `de4c1ade`, 2026-05-02)

| Question | Answer |
|---|---|
| Scope | **C — Hybrid: mirror + playbook + candidate-pool generator** |
| Storage of `candidates.json` | **Commit, trimmed payload, top-200** |
| Refresh cadence | **On-demand trigger, fully automated execution** |

(Other options A / B / D evaluated in [revision r0 history](#revision-history) below.)

## Implementation plan (revision r1)

### Phase 1 — Local Scryfall mirror

- Add `scripts/refresh_scryfall_mirror.py`:
  - Hits `https://api.scryfall.com/bulk-data` to discover the `oracle_cards` URL + `updated_at`.
  - Downloads to `priv_data/scryfall-oracle.json` (gitignored) only if remote is newer than local. Stores `priv_data/scryfall-oracle.meta.json` with `updated_at` for staleness checks.
  - Filters to commander-legal at write time (`legalities.commander == "legal"`) to keep the local file lean.
- Update `.gitignore` to exclude `priv_data/scryfall-oracle.json` and `priv_data/scryfall-oracle.meta.json`.
- No new runtime dependencies — `urllib` + `json` from stdlib.

### Phase 2 — Archetype playbook

- Author `docs/discovery-playbook.md`:
  - Per archetype (graveyard reanimator, tokens/go-wide, voltron, infect/poison, eldrazi/ramp, +1/+1 counters, lands matter, spellslinger, etc.), document the canonical Scryfall queries that surface candidates.
  - Each entry: archetype name → bullet list of `oracle_text` patterns + `type_line` constraints + CMC envelopes.
  - Tag each existing deck with one or more archetype labels in `data/commanders/{id}/deck.json` under a new optional `archetypes` field. (Backwards-compatible additive; absent ⇒ falls back to `commander_color_identity` + manual review.)
- Cross-link from `AGENTS.md` so the playbook is referenced from the standing process.

### Phase 3 — Candidate pool generator

- Add `scripts/generate_candidate_pool.py`:
  - Reads `data/commanders/{id}/deck.json` → extracts color identity, archetype tags, current CMC distribution.
  - Loads local mirror; filters cards by color identity ⊆ deck identity, commander-legal, archetype query matches.
  - Scores each candidate (0–100):
    - Archetype keyword density in oracle text (0–40)
    - CMC fit vs deck curve (0–20)
    - Owned flag from `priv_data/owned_formatted.csv` (0–15)
    - Game Changer status weighted by deck bracket (0–15)
    - Already-in-decklist demotion (caps at 5 so present cards still rank but yield to alternatives)
  - Trims to **top-200** with payload `{name, cmc, mana_cost, type_line, oracle_text, score, score_breakdown, owned, game_changer}`.
  - Writes `data/commanders/{id}/candidates.json` with `generated_at`, `scryfall_mirror_updated_at`, `methodology_version` headers.

### Phase 4 — One-shot orchestrator

- Add `scripts/refresh_card_pool.py [--deck DECK_ID | --all]`:
  - Calls `refresh_scryfall_mirror.py` (no-op if fresh).
  - Calls `generate_candidate_pool.py` per target deck.
  - Prints summary line per deck: `dark-dominion: 200 candidates, 17 new since last run, top score 87`.
  - Idempotent — re-running with no upstream changes is a no-op.

### Phase 5 — Deck-review workflow integration

- Update `AGENTS.md` (project) with a "Deck Review Checklist" section:
  - Run `scripts/refresh_card_pool.py --deck {id}` before review.
  - Diff `decklist` vs top-N of `candidates.json`.
  - Any top-N candidate not in the decklist must be explicitly considered; cuts require a reason captured in deck `sources` or review notes.

### Phase 6 — Deck-by-deck adoption (board-requested 2026-05-02)

Infrastructure (P1–P5) is landed. P6 tracks **operational adoption** — applying the candidate-pool review to every deck so the new workflow becomes the default, not just available.

- Per-deck adoption pass (one child issue per deck under P6 tracker):
  1. Confirm `archetypes` tag is correct on `data/commanders/{id}/deck.json` (already present on all 9 decks; re-check fit).
  2. Run `python scripts/refresh_card_pool.py --deck {id}`.
  3. Walk the top 50 of `candidates.json`; for each card not in the decklist, decide **include / defer / reject** with a one-line reason.
  4. Verify any add via `scryfall_card_by_name` MCP before recommending.
  5. Land swaps as separate commits with `sources` attribution; close the per-deck adoption issue with a summary of include/defer/reject counts.
- P6 tracker rolls up status across all 9 decks: `dark-dominion`, `eternal-agony`, `eternal-harvest`, `genesis-protocol`, `mutant-multiplication`, `the-white-forge`, `titan-convergence`, `verdant-tide`, `creeping-corruption`.
- Smoke validation (the original Phase 6 scope) was absorbed into P3-P5 via the `dark-dominion` canary captured in run `d08b39d8` / status comment `f059bbfc`. No standalone smoke phase remains.

### Phase 7 — Role taxonomy, deck metrics, weakness-driven enrichment (board-requested 2026-05-04)

P6 adoption surfaced that scoring candidates without a deck-state model produces top-N lists detached from what the deck actually needs. P7 builds the missing foundation so candidate-pool review can prioritize gaps, not just raw scores. **DEC-99 (P6) is blocked by DEC-114 (P7 tracker).**

P7 sub-phases (issue tree under DEC-114):

- **P7.1 — Role taxonomy + metric formula docs** (DEC-115). Write [`docs/role-taxonomy.md`](../docs/role-taxonomy.md) (15-role closed set, schema spec for `primary_role` / `secondary_role` / `commanderRoles` / `wincon_style` / `is_mdfc_land`) and [`docs/deck-metrics.md`](../docs/deck-metrics.md) (5 deterministic metrics + global blend + per-bracket targets). Cross-link from project AGENTS.md.
- **P7.2 — Schema migration** (DEC-116). Migrate existing `role` field on `decklist[]` to `primary_role` (+ optional `secondary_role`). Add `commanderRoles` to deck root. Mark MDFCs with `is_mdfc_land`. No semantic changes — pure rename + structural additions.
- **P7.3 — Heuristic auto-tagger** (DEC-117). `scripts/tag_deck_roles.py` — proposes `primary_role` / `secondary_role` from Scryfall oracle text + archetype hints. Outputs a diff for human review; never writes without confirmation. Flags ambiguous cards.
- **P7.4 — Per-deck role tagging passes** (DEC-118). Run auto-tagger across all 9 decks, human-confirm each diff, commit per-deck. Required before P7.5 can produce meaningful metrics.
- **P7.5 — Metrics computer** (DEC-119). `scripts/compute_deck_metrics.py` — produces `data/commanders/{id}/metrics.json` per the formulas in [`docs/deck-metrics.md`](../docs/deck-metrics.md). Idempotent; runs as part of `refresh_card_pool.py`.
- **P7.6 — Wire `gaps[]` derivation** (DEC-120). `gaps[]` is computed by P7.5 (any role with `per_role_score < 70`) and persisted in `metrics.json` only — never duplicated to `deck.json`.
- **P7.7 — Option-D candidate enrichment** (DEC-121). Update `scripts/generate_candidate_pool.py` to read `metrics.json`'s `gaps[]` and rerank the top 200: candidates whose `primary_role` (heuristically inferred from oracle text) matches a gap get a +20 boost. Each candidate's payload gains `gap_addressed` so reviewers can see *why* a card surfaced.

After P7.7 lands, DEC-99 (P6) unblocks and per-deck adoption resumes — but each adoption pass now has a metrics.json and gaps[] driving review, not just raw scores.

## Effort estimate

~3.5 dev-days infra (P1 0.5 / P2 1.0 / P3 1.5 / P4 0.25 / P5 0.25, all landed in `fd03a81`).
P6 adoption: ~0.5–1.0 dev-day per deck × 9 decks, paced by board priority — not a single sprint.
P7: ~3 dev-days (P7.1 0.25 / P7.2 0.25 / P7.3 0.5 / P7.4 0.5 [auto-tag is fast; human review is the bottleneck] / P7.5 0.75 / P7.6 0.25 / P7.7 0.5).

## Out of scope (for this issue)

- Auto-applying candidate-pool suggestions to decklists (would still need board approval).
- UI changes to surface candidates in the Grimoire app.
- Changing the existing `recommendations.json` scoring methodology.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scoring tuned to current heuristics misses subtle archetypes | P6 per-deck adoption surfaces noise across archetypes; tune weights once we have signal from ≥3 decks |
| Mirror file becomes stale silently | `generated_at` + `scryfall_mirror_updated_at` headers in every output; orchestrator surfaces age |
| Repo bloat from many decks | Top-200 cap + trimmed payload; revisit if total exceeds 5 MB |
| Wizards/Scryfall license concerns | Trimmed payload + non-commercial repo; mirrors existing precedent in `card-metadata.json` |

## Revision history

- **r0 (2026-05-02 18:16 UTC):** Initial proposal with options A / B / C / D and 5 open questions. Comment `f51d4561`.
- **r0a (2026-05-02 19:03 UTC):** Q2 storage recommendation (commit, top-200) added. Comment `c503afd9`.
- **r0b (2026-05-02 19:05 UTC):** Q3 cadence resolved (on-demand + automated). Comment `c73f5a30`.
- **r1 (2026-05-02 19:06 UTC):** Board confirmed C / commit / on-demand via interaction `de4c1ade`. Plan finalized; awaiting explicit go.
- **r2 (2026-05-02 23:30 UTC):** Board requested formal P6 tracking deck-by-deck adoption (comment `f30c6b9d`). Replaced original P6 (smoke validation, already absorbed into canary) with per-deck adoption tracker.
- **r3 (2026-05-04 06:00 UTC):** Board approved foundation-first P7 (role taxonomy → deck metrics → gaps → enrichment) sequenced before P6 resumes. Created DEC-114 (P7 tracker) + DEC-115..121 (sub-phases). Set DEC-99 `blockedByIssueIds = [DEC-114]`. P7.1 docs landed alongside this revision.

## Approval gate

The board's issue description states: *"don't do anything without my approval ... only when ... I give my explicit approval, then we can proceed with changes."*

Per Paperclip protocol I'm raising a `request_confirmation` interaction targeting plan revision **r1**. Implementation does not begin until that is accepted.

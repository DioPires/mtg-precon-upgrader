## DEC-935 / DEC-937 — bracket-band re-fit on the fixed goldfish

**Recommendation: shift the two turn-band tables in `data/bracket-philosophy.md` one turn later (True B4 at T7, the straddle at T8, True B3 at T9, B2 by T10), rename the T8 row to what it is — the fleet body where labels 3, 3+ and 4- overlap — and move the strategy-ceiling reads one turn later to match. Labels do not change. The proxy stays a floor that can promote and never demote.**

Basis: DEC-937 fixed the goldfish's mana double-spend (one pool per turn; commits `0fb0664`, `3e07488`). Every deck re-exported. Extract: `agents/ceo/analysis/dec937-fleet-t50.json` (HEAD `3e07488` files; best of `comboLethal` / `lethalProxy` per turn; T50 = first turn at or above 50%).

### 1. What the fix did to the fleet

| Label | Decks | T50 before → after (DEC-559 extract → DEC-937) | Median before → after |
|---|---|---|---|
| 3 | creeping 8→8, hidden-legion 9→9, verdant-tide 7→8, witherbloom 9→9, zada 8→8 | | 8 → 8 |
| 3+ | slivers 8→8, tidal-legion 7→8 | | 7.5 → 8 |
| 4- | gathering-shadow 6→7, armory 7→8, gandalf 7→8, hoard 8→8, stampede 9→8*, anvil none→9*, titan 8→9, shield 10→10, white-forge 10→10 | | 8 → 8 |
| 4 | broodfire 6→9*, eternal-agony 9→9, eternal-harvest 9→9, exponential 9→10, grave-dividends none→none | | 9 → 9 |

\* deck changed between the two extracts (stampede DEC-933 swap, anvil DEC-533 remake, broodfire DEC-935 remake), not only the fix.

Two readings. First, the fix moved the fast tail by exactly one turn (every deck that read T6 or T7 now reads T7 or T8) and left the slow tail alone (T9–T10 decks did not move — by then the real pool is large enough). Second, the label medians did not separate before and do not separate now: labels 3, 3+ and 4- all sit at T8, label 4 at T9 because its members are the known blind-spot decks (value-incremental and combo styles the goldfish undercounts). The old table's anchor sentence — "fleet medians shift about one turn per bracket step" — was never true of the fleet's own labels and should go.

### 2. Why the tables must move: row membership on the fixed curves

| Row (current table) | Decks on the OLD curves | Decks on the FIXED curves |
|---|---|---|
| True B4 (≥50% T6) | gathering-shadow, broodfire (Mirror Entity line) | none |
| Soft B4 / straddle (≥50% T7) | armory, gandalf, tidal, verdant | gathering-shadow |
| True B3 (≥50% T8) | creeping, zada, slivers, hoard, titan | armory, gandalf, hoard, stampede, tidal, slivers, verdant, creeping, zada |
| Soft B3 (40–50% T8) | hidden-legion, witherbloom, eternal-agony, eternal-harvest, exponential, stampede | broodfire, eternal-agony, eternal-harvest, titan |
| B2 band (<40% T8, ≥50% T10) | shield, white-forge | **hidden-legion (label 3), witherbloom (label 3)**, exponential, shield, white-forge, anvil |
| Sub-B2 | grave-dividends | grave-dividends |

Left as is, the table reads two label-3 decks as "B2 band" and puts the DEC-369 bar decks (armory, gandalf, tidal) in "True B3" — a demotion signal the caveat says the proxy must never send, and one that would trigger blind-spot audits for decks whose curves barely moved. The True-B4 row becomes unreachable, which also makes this deck's own brewing gate ("until the goldfish confirms the turn-6 kill rate") unreachable for every deck in the fleet.

### 3. The proposed tables (one-turn shift, T8 row renamed)

| Reading | Classification |
|---|---|
| ≥ 60% at T5–T6 | Approaching B5 / cEDH territory |
| ≥ 50% at T7 | **True B4** — reliable T6–T8 win window (fleet: gathering-shadow) |
| < 50% at T7, ≥ 50% at T8 | **Fleet body — labels 3, 3+ and 4- overlap here.** The proxy does not separate them; split on GC count, fast mana, tutor density and interaction quality (DEC-369 policy). Fleet: armory, gandalf, hoard, stampede, tidal, slivers, verdant, creeping, zada |
| < 50% at T8, ≥ 50% at T9 | **True B3 on the proxy** — fleet: broodfire, eternal-agony, eternal-harvest, titan, anvil, hidden-legion, witherbloom. Four of these carry a 4/4- label: the blind-spot list below explains each |
| 40–50% at T9 | **Soft B3** — B3 label holds if the T7 reading is ≥ ~5% |
| < 40% at T9, ≥ 50% at T10 | **B2 band** — fleet: exponential-growth, shield-doctrine, the-white-forge (all 4/4-, all on the blind-spot list) |
| < 50% at T10 | **Sub-B2 payoff** — run `validate_strategy_ceiling.py` and the blind-spot audit (fleet: grave-dividends) |

Row check against the pre-fix classification: no deck moves down a row. Four decks whose T50 did not move (creeping, zada, slivers, hoard: 8 → 8) move up one row, from "True B3" to the body row — that is the one distortion of a uniform shift, and renaming the T8 row to "fleet body" rather than "Soft B4" keeps it from reading as a promotion. gathering-shadow keeps True B4; armory, gandalf, tidal and verdant keep their straddle row; hidden-legion, witherbloom, eternal-agony and eternal-harvest land in True B3 (they were Soft B3); the three B2-band decks and grave-dividends are unchanged.

Caveat 1 (floor, promote-only) stays and gets the current blind-spot list: shield-doctrine (equipment voltron, no equip path), the-white-forge and eternal-agony and eternal-harvest (value-incremental), grave-dividends (combo, pieces held back), exponential-growth (token combat), and — until DEC-938 lands — broodfire-hatchery (hatch engine unmodelled). Caveat 2 (B2 band extrapolated) stays; the fleet still has no label-2 deck.

### 4. Everything else that reads these turns

| Consumer | Change | Owner |
|---|---|---|
| `data/bracket-philosophy.md` B4 table, B2/B3 table, anchor paragraph, caveat 1, calibration pointer (`dec559-fleet-t50.json` → `dec937-fleet-t50.json`), note that the Tier X/Y/Z "T6 gain" estimates predate the fix | doc edit | CEO (Tier 0, declared) |
| `scripts/validate_strategy_ceiling.py`: payoff reads `CL@T6` / `LP@T7` with `PAYOFF_FLOOR` 15% and `FAST_PAYOFF` 50% at `CL@T5` → read `CL@T7` / `LP@T8` and `CL@T6`; update its docstring and `docs/deck-metrics.md` where the check is described | 2-line script change + doc | Simulation Engineer (tiny issue DEC-935-C; hidden-legion's new warning at 13.2% LP@T7 disappears at LP@T8 36.5%) |
| `scripts/compute_deck_metrics.py` `win_turn` (best 15% / typical 50%, `WIN_TURN_DRAG` 3:0 4:1 5:2) | none — percent thresholds, turn-agnostic; `global_health` unchanged on all 21 decks after the fix | — |
| `data/commanders/broodfire-hatchery/deck.json` brewing sentence ("turn-6 kill rate") | "turn-7" per the new True-B4 row; apply with DEC-938's cache bump | CEO at the DEC-938 review |
| DEC-559 calibration extract | superseded by `dec937-fleet-t50.json` (committed with this note) | done |
| Sim-eng follow-up: the combo gate is checked after filler casts (a real pilot holds mana) | candidate cast-priority change; not part of this decision | board, later |

### 5. Decision asked of the board

Approve the one-turn shift and the T8 "fleet body" row as written in section 3. On approval I edit `data/bracket-philosophy.md`, open DEC-935-C for the strategy-ceiling reads, and fold the broodfire brewing sentence into the DEC-938 review. No bracket label changes.

**Parent:** DEC-925 (Reality Fracture prerelease). **Deadline: 2026-09-24 end of day.** The board's event is Fri 25 or Sat 26 Sep. The CEO needs the results on Thursday to write the ranking report.

**Goal.** Build a Monte Carlo simulator of Reality Fracture (set `fra`) Sealed pools (6 Play Boosters + 1 promo) and report, for each of the 10 two-color pairs, how often a pool supports a viable deck in that pair. The CEO supplies card grades; you build the collation model, the echoed-pair table, the deck evaluator, and the report.

## Inputs (already in the repo, untracked, under `agents/ceo/analysis/dec925/`)

- `fra_all_cards.json`: Scryfall `set:fra unique=cards` (285 cards: 270 main set + 10 common dual lands + 5 basics). Fields you need: `name`, `rarity`, `colors` (or `card_faces[0].colors`), `type_line`, `watermark`, `layout`, `collector_number`, `oracle_text`.
- `grades.json`: CEO-authored, schema below. Until it lands, generate a placeholder with `grade: 5` for every non-basic card so the pipeline runs end to end. Do not invent grades.
- `notes.md`: the verified facts this spec is based on.

## Grade schema (`grades.json`, one entry per non-basic card, 280 entries)

```json
{"name": "Card Name", "grade": 6, "grade_synergy": 8, "needs": "jace", "needs_threshold": 4, "provides": ["jace"], "roles": ["removal"], "note": "short reason"}
```

- `grade`: 0 to 10 Sealed grade on its own. `grade_synergy` (optional): grade when the deck has at least `needs_threshold` cards whose `provides` includes `needs`. Tags in use: `jace`, `graveyard`, `heartwood`, `lifegain`, `surveil`, `artifact`, `prowess`, `planeswalker`.
- `roles`: subset of `removal`, `bomb`, `threat`, `trick`, `fixing`, `engine`, `filler`. `removal` = kills or exiles or neutralizes a creature; `bomb` = grade 8 or higher.

## Collation model (per Play Booster, 14 game cards)

Source: WotC "Collecting Reality Fracture" and the mtgscribe Play Booster fact sheet (2026-09-08); they agree. Encode as a config file next to the script so the next set only needs a new config.

| Slot | Content |
|---|---|
| 1 to 5 | common, uniform over the 71 non-land commons |
| 6 | common 98.18%; Special Guest 1.82% (10 off-set cards). **Assumption:** draw a common instead; state it in the report header. |
| 7 | non-paired uncommon, uniform over the 43 |
| 8 | common 23%, non-paired uncommon 74%, other 3%. **Assumption:** fold the 3% into uncommon. |
| 9 to 11 | echoed pairs. Draw one rarity for the pair with U 88.9% / R 6.7% / M 1.4%, pick one pair of that rarity uniformly, add both halves. Third card: draw rarity again with the same weights, pick one echoed-pair card of that rarity uniformly. **Assumption:** the third card is independent of the pair. |
| 12 | rare 74.4%, mythic 14.8%, booster-fun variants 10.8%. **Assumption:** the variants are still rares or mythics from the set, so normalize to R 83.4% / M 16.6% over the 50 non-paired rares and 20 non-paired mythics. |
| 13 | traditional foil, any card: C 49.5% / U 40.5% / R 6% / M 1.2% (normalize the 2.8% remainder proportionally). Uniform within rarity over the full main set including paired cards. |
| 14 | land: dual 43.6% (uniform over the 10 common duals), basic otherwise. Basics are excluded from the pool (unlimited supply at the event). |

Promo: 1 card. **Assumption:** uniform over the 64 rares + 26 mythics. The board will confirm from the pack; keep it a config flag.

Sanity target from the CEO's arithmetic (per pack, excluding basics): C 6.71, U 4.81, R+M 1.31, duals 0.436. A test must reproduce these within ±0.05 over 50k packs.

## Echoed-pair table (`echoed_pairs.json`)

WotC states 86 echoed-pair cards = 43 pairs: 66 U, 14 R, 6 M; each pair is two cards of the same rarity for one character (Multiverse half and Echoverse half). Scryfall marks 46 cards with `watermark` `echoverse` or `desparked` (some pairs have both halves marked). A first-name match resolves 33 pairs; the "Way of the ..." cycle and name changes need manual work. Build the table from a primary source (WotC card image gallery or the Collecting article's pair list) and cite it in the file. Hard checks (tests): exactly 43 pairs; 66/14/6 by rarity; both halves same rarity; every card exists in `fra_all_cards.json` main numbering; no card in two pairs; non-paired counts come out to 43 U / 50 R / 20 M. If a check fails, stop and report; do not force the numbers.

## Deck evaluation (per pool, per pair)

1. Eligible cards for pair XY: non-land cards whose colors are a subset of {X, Y} (colorless included). Effective grade = `grade_synergy` when the eligible set holds at least `needs_threshold` cards providing `needs`; else `grade`.
2. Splash: allow up to 2 extra cards from a third color with effective grade ≥ 7 when the pool has at least 2 fixers for that color. A fixer is a dual land that makes that color, Room of Refuge, or any basic-landcycling card. State this rule in the report.
3. Deck = top 23 eligible cards by effective grade. If fewer than 23 exist, fill with grade 1.
4. Metrics: `score` = mean effective grade of the 23; `playables` = eligible cards with grade ≥ 4; `removal` = deck cards with role `removal`; `bombs` = deck cards with grade ≥ 8.
5. Viable = playables ≥ 23 and removal ≥ 3 and bombs ≥ 1.

## Outputs

- `scripts/sealed_sim.py`, run with `uv run python scripts/sealed_sim.py --config agents/ceo/analysis/dec925/collation.json --cards ... --grades ... --pools 100000 --seed 20260925 --out agents/ceo/analysis/dec925/sim_results.json`. Runtime target under 3 minutes.
- `sim_results.json` and `sim_results.md` with: per pair P(viable), mean score, P(pair has the highest score in the pool), P(top 2); per color mean playables and mean removal; distributions of R+M count and dual count per pool; the assumptions header. Also emit the same tables for the placeholder grades so the CEO can diff placeholder vs real.
- Tests under `tests/` (run with `uv run --with pytest python -m pytest`): slot weights sum to 1; per-pack expectation check; pair-together check (slots 9 and 10 always one full pair); echoed-pair table checks above; seed determinism.

Do not touch `data/`, `web/`, or any `deck.json`. No new dependencies; the standard library (or numpy if already in the project) is enough.

## Handoff

When done, post a comment with: commit hash, the `sim_results.md` table for the placeholder run, the pair-table source, and every assumption you had to add. Then PATCH the issue: `assigneeAgentId` to the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` to `in_review`, and `executionPolicy.monitor.nextCheckAt` set 2 hours ahead (the review path). If a check fails or a source is missing, comment and hand back the same way with `blocked` instead.

planned-by: CEO

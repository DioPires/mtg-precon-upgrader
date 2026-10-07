# DEC-946 — Turbulent Crater / Shore / Wetlands placement assessment

Date: 2026-10-07. Author: CEO. Status: proposal (no deck.json edits until the board accepts each line).

## 1. The cards (Scryfall-verified 2026-10-07)

All eight Turbulent lands share one text: "This land enters tapped unless your opponents control eight or more lands." Each carries two basic land types.

| Card | Colors | Types | Set | Owned | Committed to |
|---|---|---|---|---|---|
| Turbulent Crater | B/R | Swamp Mountain | FRC | 1 | hoard-and-bleed (DEC-929) |
| Turbulent Shore | W/U | Plains Island | FRC | 0 | — |
| Turbulent Wetlands | U/B | Island Swamp | FRC | 0 | — |
| Turbulent Fen / Moor / Springs / Steppe / Wilderness | BG / WB / UR / RW / GU | typed | SOC | 3 / 4 / 3 / 3 / 5 | 9 decks run one each |

No G/R or G/W Turbulent land exists yet.

## 2. How good is the cycle in a 4-player game (our model)

Three opponents need eight lands between them.

- If every opponent hits every land drop: untapped from **your turn 4** in seat 1, **turn 3** in seat 4. Never untapped on turns 1–2.
- Monte Carlo, 20k trials, each opponent misses a land drop 10% of turns: seat 1 → T4 78%, T5 100%. Seat 4 → T3 78%, T4 100%.
- At a 20% miss rate: seat 1 → T4 44%, T5 93%.

So the cycle is a **typed dual that is reliably untapped from the mid game on, independent of your own board**. Ranking inside our fleet's manabases:

1. Always untapped: shocks (pay 2), fetches, pain lands, pathways, filter lands, Command Tower class.
2. Early untapped only: fast lands (T1–3), reveal lands (while the hand holds a typed card).
3. **Turbulent lands** ≈ slow lands: tapped T1–3, untapped after.
4. Battle lands (need 2 basics on your side) — worse than Turbulent in every deck below 12 basics.
5. Always tapped: triomes, tri-lands, Path of Ancestry, Bojuka Bog.

The manabase audit agrees: in eternal-agony, Turbulent Crater is the top owned fixing land (score 31), above every untapped rainbow land (29).

The board's "some of the best lands for commander" read holds for tier 3 and below. They do not beat tier 1. Their edge over slow lands is the two basic types: fetchable, and they switch on type-gated lands (Castle Locthwain, Tainted Peak, Dragonskull Summit, Cabal Coffers).

## 3. Battle-land uptime in the decks that run them (hypergeometric, our model)

Probability that two or more basics are already on your battlefield when the battle land enters, by turn, assuming all basics drawn get played:

| Deck | Basics / 99 | T2 | T3 | T4 | T5 | T7 |
|---|---|---|---|---|---|---|
| gathering-shadow | 5 | 5% | 6% | 8% | 9% | 13% |
| gandalf-party-guest | 11 | 22% | 26% | 31% | 35% | 44% |
| eternal-agony | 15 | 35% | 41% | 47% | 52% | 62% |

Compare Turbulent: 0% through T3 (seat 1), then 78–100%.

## 4. Deck-by-deck verdicts

### Turbulent Crater (B/R)

- **hoard-and-bleed** — already in (DEC-929, commit 723ae74). The one owned copy is committed here (board ruling 2026-08-22: brewing decks count).
- **eternal-agony (B4, production) — INCLUDE, line A: +Turbulent Crater / −Foreboding Ruins.**
  Same two colors. Foreboding Ruins has no land types and is untapped only when you reveal a Swamp or Mountain card from hand: 18 typed cards in 99 → roughly 70% on T1–2, falling as the hand empties, which is exactly when Crater turns on. Crater's Swamp type feeds four lands already in the deck: Cabal Coffers (when Urborg is not out), Tainted Peak, Castle Locthwain, Dragonskull Summit, and Bloodstained Mire can fetch it. B/R Karsten counts are already met (B 31/20, R 21/18), so this is an untapped-reliability and type-count upgrade. Leechridden Swamp stays — DEC-464 placed it as a their-turn bleeder for Valgavoth. The board already made the same Ruins cut in hoard-and-bleed (DEC-931 line J). Needs 1 purchased copy. Side note: the deck sits at 37 lands vs a 39.9 target — a separate land-count question.
- **gathering-shadow — DEFER Crater.** R is the lightest color (16 pips vs B 32 / U 25). The only unconditional tapped land is Bojuka Bog (graveyard-hate coverage, keep). Smoldering Marsh as a cut was rejected on DEC-688. Revisit only if a B/R slot opens.
- **hidden-legion / slivers (5c) — REJECT.** A two-color land fixes less than the triome or tri-land it would replace; both audits rank five-color untapped lands (Exotic Orchard, City of Brass, Mana Confluence) as the real upgrades there.

### Turbulent Wetlands (U/B)

- **gathering-shadow (4-, brewing) — INCLUDE, line B: +Turbulent Wetlands / −Sunken Hollow.**
  Identical colors and identical types (Island Swamp), so every type-gated land and the sim's typed sets carry over one for one. Sunken Hollow's two-basic clause is met 5–13% of the time in this 5-basic deck (table above). Wetlands is untapped 78–100% from T4 (seat 1) or T3 (seat 4). Strict upgrade. Needs 1 purchased copy. Post-approval: update `scripts/mana_simulation_gathering_shadow.py` typed sets and untapped rule, same pattern as Turbulent Springs at DEC-688. Swap counter: 0 rounds since the DEC-689 re-assessment; this would be round 1.
- **creeping-corruption (B3, production) — INCLUDE (weaker), line D: +Turbulent Wetlands / −Seaside Citadel.**
  Seaside Citadel is always tapped, has no types, and makes G/W/U. Wetlands makes U/B — the deck's two mid-demand colors (U 19, B 21 pips; W is 8) — and its Island and Swamp types are reachable by four of the deck's five fetches (Polluted Delta, Verdant Catacombs, Flooded Strand, Marsh Flats). Cost: one fewer G source (G Karsten 25/16, ample) and one fewer W source (W 21/14, ample). Needs 1 purchased copy. Post-approval: update `scripts/mana_simulation_creeping_corruption.py` typed sets, same pattern as Turbulent Moor.
- **hidden-legion / slivers — REJECT** (same reason as Crater).

### Turbulent Shore (W/U)

- **gandalf-party-guest (4-, brewing) — INCLUDE, line C: +Turbulent Shore / −Prairie Stream.**
  Identical colors and types (Plains Island). Prairie Stream's two-basic clause is met 22–44% of the time in this 11-basic deck; Shore is untapped 78–100% from T4/T3. Strict upgrade, and it completes the deck's Turbulent trio (Springs and Steppe are already in). Needs 1 purchased copy. Alternative cut if the board prefers: Skycloud Expanse (cannot make mana on its own). Swap counter: three swap commits since DEC-547 (419183f, 47d6bcd, 393a638); applying C makes four, so a Trigger-2 re-assessment is due unless one already ran.
- **shield-doctrine (4-, brewing) — DEFER.** W/U is already covered by Hallowed Fountain, Seachrome Coast, Adarkar Wastes, Sea of Clouds, Glacial Fortress and Flooded Strand. The only tapped land is Axgard Armory (Equipment tutor, theme piece). The deck is 37 lands vs a 39.6 target: Shore is the first land to add if the board opens a nonland slot — separate review.
- **creeping-corruption — DEFER.** W is the deck's lightest color (8 pips); line D (Wetlands) is the better use of the slot.
- **hidden-legion / slivers — REJECT** (same reason).

## 5. Purchases and returns if all four lines pass

- Buy: Turbulent Crater ×1, Turbulent Wetlands ×2, Turbulent Shore ×1. Not in the local price index (new FRC printings); price is information only, not a decision factor.
- Cut cards return to the owned pool: Foreboding Ruins (owned 2), Sunken Hollow (owned 4), Prairie Stream (owned 3), Seaside Citadel (owned 1).

## 6. Post-approval hygiene (CEO-executed, per accepted line)

refresh_card_pool → manabase_check → compute metrics → update the deck's `mana_simulation_*.py` model → export_simulation_results `--deck` → compute_tokens → the three Combo Lab artifacts → validate_deck_json → cache bump → commit + push.

## 7. Evidence trail

- Scryfall: all eight Turbulent lands, Valgavoth, Leechridden Swamp, Foreboding Ruins, Sunken Hollow, Prairie Stream, Seaside Citadel, Smoldering Marsh, Skycloud Expanse, Path of Ancestry (2026-10-07).
- `scripts/manabase_check.py --deck {id}` for eternal-agony, hoard-and-bleed, gathering-shadow, creeping-corruption, shield-doctrine, gandalf-party-guest, hidden-legion, slivers.
- Probability models: run scratch (hypergeometric + 20k-trial Monte Carlo), figures quoted above.
- Prior rulings honored: DEC-688 (Smoldering Marsh cut rejected), DEC-464 (Leechridden Swamp placement), DEC-929/930 (Crater in hoard-and-bleed), 2026-08-22 board ruling (brewing decks count as committed).

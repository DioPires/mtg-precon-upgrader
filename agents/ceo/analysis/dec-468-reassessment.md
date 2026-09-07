# DEC-468 — Tidal Legion Trigger-2 Re-assessment

**Date**: 2026-09-07 · **Assessor**: CEO · **Verdict: PASS — no swaps proposed. Swap-round counter resets to 0.**

Trigger 2 fired at 3 board-approved swap rounds since the DEC-401/DEC-414 build baseline. By assessment time the deck had a 4th round: DEC-416 (0517f91), DEC-462 (e51ab10), DEC-467 incl. round 2 (39c6b44, 1725c46, 769fab7), DEC-469 (fa953f2). This assessment covers all four. The DEC-471 sim-model update (db4b285) is also in the baseline.

## 1. Metrics + sim (fresh run, 2026-09-07 mirror)

| Metric | Value | Note |
|---|---|---|
| global_health | 93 ± 2 (norm 93) | issue quoted 95 pre-DEC-469; current committed basis |
| manabase_health | 79 | Karsten U 34.7 vs 20 required (ratio 1.0, full credit); 36.7 of 37.7 effective lands untapped; effective count 37.7 vs 39.2 formula target costs the land_count component |
| role_coverage | 111 | only sub-100 role: ramp 8.0 vs target 10 (score 80) |
| curve | 97 | avg MV 2.77 vs 2.9 archetype target |
| interaction_density | 120 | weighted 36.5 vs target 10 — deliberate (spell-dense vision) |
| gameplan_cohesion | 31 | see §3 |
| resilience | 100 | recursion 2/2, redundancy 3 lines, protection covered |
| gaps[] | 0 | — |
| sim deckHealthScore | 78.2, grade A | sim generated 2026-07-28, current with the 99 (no decklist change since fa953f2) |
| sim detail | kept-first 89.0%, commander median T3, curve-out 58.2%, mana "strong" | — |
| strategy ceiling | shell 79 / payoff 58.6% LP@T7 — ok, no flags | — |

Re-sim not needed: the decklist is unchanged since the sim's generation date.

## 2. Bar check (≥ B3+/4-)

**Pass.** Declared 3+, 3 GCs (Fierce Guardianship, Cyclonic Rift, Sol Ring) = exactly at the ≤3 cap for brackets ≤3+. Global 93, sim grade A, interaction 36.5 weighted, curve 2.77 — comfortably at the B3+ bar per data/bracket-philosophy.md. Standing note (DEC-467): any future GC add forces a 4- relabel.

## 3. Cohesion question (issue: 34→28 in DEC-467; now 31)

**No compensating proposal.** Cohesion's in_set_pct (31%) pattern-matches on-board archetype payoffs; the spellslinger patterns match 0 deck cards because the board deliberately cut the on-board spell-payoff creatures (Archmage Emeritus, Deekah, Curiosity Crafter) in DEC-467 and moved the payoff to the command zone — Namor mints the tokens himself. The metric cannot see command-zone engines. Real payoff throughput is validated independently: lethal-proxy 58.6% @T7, sim grade A, strategy-ceiling clean. Re-adding a payoff creature (Kitsa/Talrand class) would raise the number while reversing the board's spell-dense direction. The one owned copy of top scorer Kitsa, Otterball Elite (score 65.2) is committed to gandalf-party-guest (brewing) in any case.

## 4. Manabase audit (lands 37 + 1 MDFC; DEC-469 took 39→38)

**No land swaps.** Karsten U 34.7 vs 20 required. Only Lonely Sandbar enters tapped (cycling utility — acceptable). Effective 37.7 vs 39.2 formula target is tolerable at avg MV 2.77 in mono-blue; mulligan/curve-out sim numbers confirm ("strong", 89% keeps). Owned fixing candidates (Nykthos 31%, Otawara 30% EDHREC) deferred: Harbinger of the Seas blanks our own nonbasics to Islands, which caps utility-land value (already acknowledged in deck prose).

## 5. Stale-reference sweep

**0 hits.** Grep of strategyOverview, 6 category descriptions, 10 synergy descriptions, and 3 win-condition texts against all 30+ cards cut across v1.1→DEC-469. Validator: 172 card references clean. Prose counts re-verified: "thirteen counterspells" = 13 primary-role counterspells ✓; "twelve cantrips and draw spells" = 7 card-draw + 5 cantrip-utility ✓.

## 6. Top-50 candidate triage (candidates.json regenerated 2026-09-07, top score 65.2)

Grouped; every entry not in the 99 is dispositioned. Oracle text verified via Scryfall for all cards discussed substantively.

- **Reject — board-cut earlier this cycle, don't re-propose**: Archmage Emeritus (#3, DEC-467 r2), Chrome Host Seedshark (#9, v1.2), Dirgur Focusmage (#11, v1.3), Leitmotif Composer (#26, v1.3), Rite of Replication (#28, v1.2.1), Deduce (#59, v1.1).
- **Reject — creatures that never trigger Namor** (Faerie Mastermind precedent, DEC-467 r2; the scorer's tokens-go-wide patterns over-credit them): Elementalist Adept (#2), Lightshell Duo (#4), Glaring Fleshraker (#6), Deluge Virtuoso (#10), Drake Hatcher (#12), Flux Channeler (#13), Trawler Drake (#15), Amphin Mutineer (#18), Owlin Spiralmancer (#30), Corsairs of Umbar (#35), Council of Reeds (#36), Exhibition Tidecaller (#50) and similar creature filler in #31–#49.
- **Reject — artifact/token-artifact archetype noise, no deck fit**: Lux Artillery (#5), Wizard's Staff (#7), Golem Foundry (#25), Lithoform Engine (#29), Academy Manufactor (#32), Horn of Gondor (#42), Titan Forge (#48), Arcade Cabinet (#33), equipment/vehicle entries (#34, #40, #45).
- **Reject — proliferate/storm/off-plan spells**: Brain Freeze (#20, storm mills — no payoff here), Lost Isle Calling (#22), Uncover the Moon-Letters (#27), Blue Sun's Twilight (#57).
- **Defer (real fits, hold for a future round)**:
  - *Kitsa, Otterball Elite* (#1, 65.2) — 2-MV spellslinger payoff, {2},{T} copies our instant/sorcery (prowess reaches power 3 trivially at 57 spells). Copy is not a cast, so it never re-triggers Namor (CR 707.10), but doubling a counterspell or draw spell is real. Sole owned copy sits in gandalf-party-guest (brewing) — not free.
  - *Valley Floodcaller* (#17, owned, free) — flash for noncreature spells is redundant with Leyline of Anticipation; its untap/pump line names Birds/Frogs/Otters/Rats, all absent here. Defer as a Leyline backup only if the board wants redundancy.
  - *Emperor Mihail II* (#8, unowned, 47.8% EDHREC) — cast Merfolk from library top + {1} per Merfolk cast for a token. Scales with Merfolk-spell density, which the board thinned to ~10; weak in the current build, strong if the creature count ever rises.
  - *Narset's Reversal* (#19, unowned, 38.6%) — copy + bounce, tempo-perfect and mints a Merfolk ({U}{U}); candidate for a future interaction upgrade round.

## 7. EDHREC closing diff (256 rates fetched 2026-09-07; every ≥40% miss dispositioned)

| Card | Incl. | Call | Reason |
|---|---|---|---|
| Attuma, Atlantean Warlord | 75.2% | Reject | board cut, DEC-467 r2 |
| Merfolk Sovereign | 66.4% | Reject | board cut, DEC-467 r2 |
| Merrow Reejerey | 58.7% | Reject | board cut, DEC-467 |
| High Tide | 58.3% | Defer | burst ritual; 1 pip = 1 Merfolk, but deck has no untap/X-finisher shell to convert the burst; revisit if one enters |
| Pongify | 57.4% | Reject | functional duplicate of Rapid Hybridization; spot removal already 8 vs target 6 |
| Seafloor Oracle | 52.4% | Defer | Merfolk-combat-damage draw is real but overlaps Kindred Discovery's attack trigger; 4-MV creature vs. the thinned-creature vision |
| Bident of Thassa | 51.0% | Reject | board cut, DEC-467 |
| Emperor Mihail II | 47.8% | Defer | see §6 |
| Summon: Leviathan | 45.7% | Reject | 6 MV; chapter I would bounce our Roaming Throne (Golem, not an exempt type); conflicts with the multiplier |
| Opt | 43.7% | Reject | board cut, DEC-414 |
| Stonybrook Banneret | 43.6% | Defer | reduces only Merfolk/Wizard spells — most of our 57 spells are neither |
| Deeproot Waters | 41.6% | Defer | triggers on ~10 Merfolk casts only; Namor's own engine outclasses it at current density |
| Mana Drain | 40.2% | Reject | board already chose Hinder over a Mana Drain buy (DEC-467 r2) |

Below the line, noted: Wanderwine Prophets (29.6%) stays blocked (board, DEC-414).

## 8. Rubric items with no findings

- Archetype recipes (DEC-238): spellslinger + tokens-go-wide both `live`; recipe-class deltas (spell payoffs, token engines) surfaced through the candidate pool and closing diff and are dispositioned above. No additional includes.
- Combo Lab artifacts: no decklist change this assessment → no regeneration required.
- Win-from-this-board goldfish (step 11): not triggered — gaps 0, no ceiling flag.

## Disposition

PASS. No swaps proposed, no deck.json edits made. Hygiene refresh committed (candidates.json, metrics.json, EDHREC rates cache). Swap-round counter: reset to 0 at this report's commit. Next Trigger-2 fires after 3 new board-approved rounds.

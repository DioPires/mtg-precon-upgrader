# DEC-532 — New Orzhov deck (video-based) — Strategy Analysis

Status: research phase (heartbeat 1, 2026-08-17). CEO working doc.
Replaces: Quill of Casualties (`silverquill-the-disputant`, WB Aristocrats Drain / Casualty, bracket 4-) — board wants it taken apart.

## Source video

"1 Deck, 27 Dollars, 600 Infinite COMBOS" — Commander Challenge (Gage), published 2026-08-12,
https://www.youtube.com/watch?v=1Yusxsud5BE — full transcript reviewed 2026-08-17.
Creator's list: https://moxfield.com/decks/ebYubPoAMk-2j7JDDa9_xA (issue text carries the 100).

## The deck's strategy (from full transcript)

Challenge: more infinite combos than dollars (~$28, 600 counted lines), while staying a real bracket-4 deck.
The architecture that achieves it is a **modular loop network**, not discrete 2-card combos:

1. **Sacrifice outlet** — commander Bartolomé del Presidio ({W}{B}, "Sacrifice another creature or artifact: put a +1/+1 counter on Bartolomé"). Backup outlet in the 99: Dimir House Guard (also transmute-4 tutor). Video reasoning [15:02–16:25]: outlet-in-CZ beats payoff-in-CZ (Elas il-Kor was the considered alternative) because the outlet drives mid-game value from every death-trigger creature, not only the combo turn.
2. **Loop half A — recursive ETB creatures** (7): Sun Titan, Angel of Indemnity, Redemption Choir (loop with *every* half-B card); Shepherd of the Cosmos (loops with the MV-2 half-B cards); Boonweaver Giant, Brotherhood Outcast, Danitha, Benalia's Hope (loop with the *aura* half-B cards; Boonweaver tutors the aura from deck/yard, Danitha cheats it from hand).
3. **Loop half B — "return the dead creature" auras/enchantments** (9): Necrogen Communion, Kaya's Ghostform, Gift of Immortality, Angelic Renewal, Minion's Return, Changing Loyalty, Fungal Fortitude + interaction-bodies Fiend Hunter and Werefox Bodyguard (these two loop only with the A1 trio).
4. **Finishers (aristocrat drains)** (6): Zulaport Cutthroat, Bastion of Remembrance, Marionette Apprentice, Agent of the Iron Throne, Ninja Teen, Scavenger's Talent (level 2 = also mill-out wincon inside the loop).
   Loop math [39:57]: Sun Titan alone = 9 loop bases × 6 payoffs × 2 outlets = 108 lines; whole network ≈ 600. Each extra sac outlet ≈ +300 lines.
5. **Card advantage = self-mill + recursion, not draw** [17:39–22:06]: Stitcher's Supplier, Undead Butler, Unseal the Necropolis, Corpse Churn, Another Chance, Funeral Rites, Diresight, Corpse Augur, Crow of Dark Tidings, Paramecia Coloniex, Gnawing Vermin, Millikin, The Warring Triad, Throne of the Grim Captain + mill lands (Conduit Pylons ×"3 versions" class, Mariposa Military Base, Dakmor Salvage). Combos "work best with one part in the graveyard, one in hand" — hence Final Parting is a perfect tutor and recursion spells that cast from the yard (Unburial Rites flashback, Sevinne's Reclamation) are preferred.
6. **Interaction priorities** [24:22–25:36]: (a) answers to graveyard hate carried on enchantments/artifacts/lands — the deck's #1 hoser class; (b) permanent-based, recurrable interaction; (c) interaction that doubles as combo pieces (Fiend Hunter, Werefox Bodyguard, Leonin Relic-Warder, the arrest-auras Bound in Gold / Intercessor's Arrest which also protect the yard by tapping down activated hate).
7. **Speed target** [30:05–32:23]: goldfished 10 games — **T5 win 50%, T6 40% = mid bracket 4**. Creator: "+$50 would push it to high B4 and much more consistent"; recursion package named the most upgradable part [33:42].

## Spellbook baseline (video list, run 2026-08-17)

Saved: `dec532-spellbook-baseline.json`.
- **32 registered combos included — every one uses Bartolomé del Presidio as the outlet.** Commander-dependency (DEC-474 L9) is the deck's structural weakness: a Darksteel Mutation-class lock turns off all 32 registered lines (Dimir House Guard is the only in-99 outlet and Spellbook doesn't register it).
- **416 near-miss combos.** Missing-card frequency is dominated by sac outlets, each unlocking ~27–33 registered combos alone: Ashnod's Altar 33, Altar of Dementia 33, Viscera Seer 33, Phyrexian Altar 33, Blasting Station 32, Carrion Feeder 32, Yahenni 32, Woe Strider 32, Shilgengar 32, Bloodflow Connoisseur 32, Umbral Collar Zealot 27, Phantom Train 27. Next class: more half-B auras (Unholy Indenture / Unhallowed Pact / Shade's Form, +4 each). Reanimation enchantments (Animate Dead / Necromancy / Dance of the Dead), Karmic Guide, Luminous Broodmoth appear as single-combo adds.

## Upgrade thesis (no budget cap; same strategy, same speed class, ≥ same combo density)

All candidates below oracle-verified via Scryfall 2026-08-17 (`dec532-upgrade-candidates-oracle.json`); all WB-legal.

1. **Premium sac outlets (biggest win — density + L9 resilience).** Viscera Seer ({B}, scry filters toward missing halves), Carrion Feeder ({B}), Woe Strider (escapes itself back = own loop resilience), Yahenni (free outlet + haste), Phyrexian Altar / Ashnod's Altar (loops now also make infinite mana → any X/drain line), Altar of Dementia (loop = mill-out wincon with zero payoff needed — collapses the pyramid to 2 pieces + outlet), Phyrexian Tower (outlet on a land — survives creature wipes and Bartolomé locks). Each of the first ~6 adds ~30 registered combos; adding 5–6 outlets should push included combos from 32 to ~180–200 while directly fixing commander-dependency.
2. **Recursion package** (creator's own "most upgradable"): Reanimate, Animate Dead (is itself a half-B-style aura + combo piece with Leonin Relic-Warder + an altar = infinite mana), Necromancy (instant-speed mode), Dance of the Dead, Victimize (sac + double reanimate = on-plan), Karmic Guide (+Reveillark class loops half-A). Cuts from: Valgavoth's Faithful (creator's named first cut), Summon Undead, Infernal Offering, possibly Dread Return stays (flashback from yard is on-plan).
3. **Tutors**: Demonic Tutor, Vampiric Tutor, Enlightened Tutor (fetches auras AND altars), Diabolic Intent (sac = on-plan), Buried Alive + Entomb (put the "graveyard half" exactly where it wants to be). Keep Final Parting (both halves at once), keep Demonic Bargain probably not (exile-13 anti-synergy with our own yard — evaluate).
4. **Payoff quality**: Blood Artist, Cruel Celebrant, Elas il-Kor in the 99 (also the board-mentioned alternative commander), Nadier's Nightblade (opponent-token deaths too). Keep the cheap ones only as needed to hold ≥6 payoffs; Ninja Teen likely a cut (weakest), Scavenger's Talent stays (mill wincon + on-plan).
5. **Card advantage**: keep the mill engine (it IS the strategy); add Esper Sentinel (creator explicitly priced it out at [5:31]), Black Market Connections, Bolas's Citadel (top-of-library = pseudo-yard for this curve; life is a resource here). Necropotence rejected — skips draw AND exiles discards; anti-synergy with a mill/recursion engine.
6. **Interaction/protection**: Swords to Plowshares, Anguished Unmaking, Despark, Damn; Grand Abolisher + Silence to protect the combo turn; Teferi's Protection. Keep the recurrable-permanent principle: Leonin Relic-Warder stays (now also an infinite-mana combo with Animate Dead + altar), Seal from Existence stays, Bound in Gold / Intercessor's Arrest / Disenchant / Generous Gift → re-evaluate against the premium suite. Hoser coverage (DEC-474 L6): graveyard hate rides on artifacts (Grafdigger's Cage, Soul-Guide Lantern), enchantments (Rest in Peace), lands (Bojuka Bog, Scavenger Grounds) — suite must answer artifact + enchantment + land types; current list relies on white removal, keep that property.
7. **Mana base + fast mana** (B4 principles, `data/bracket-philosophy.md`): Sol Ring (absent from the budget list!), Mana Vault, Chrome Mox, Mox Diamond, Lotus Petal, Dark Ritual; Godless Shrine, Marsh Flats + WB-legal fetches, Vault of Champions, Concealed Courtyard, Shattered Sanctum, Isolated Chapel, Caves of Koilos, Brightclimb Pathway, Urborg, Takenuma (recursion land), Ancient Tomb, Phyrexian Tower, High Market. Cut: tapped budget lands (Orzhov Basilica, Hidden Grotto, The Warring Triad? — Warring Triad is a mill rock not a land; evaluate), Path of Ancestry (near-zero tribal payoff). Keep mill/utility lands that carry the engine: Dakmor Salvage, Conduit Pylons?, Bojuka Bog, Memorial to Folly?, Rogue's Passage (commander-damage backup) — decide in iteration.

**Speed guardrail**: board wants the same strategy and speed (T5-ish wins, mid/high B4), with better consistency and resilience — not a cEDH turn-3 deck. Fast-mana quantity should be tuned to consistency, not explosiveness (Sol Ring/Mana Vault yes; skip Grim Monolith-class overdrive).

## Commander decision (to iterate next heartbeat)

- **Keep Bartolomé del Presidio (lean)**: free (no mana activation), instant-speed, twice-repeatable outlet in CZ = the hinge of all 32→~200 registered lines; +1/+1 growth = commander-damage backup (Rogue's Passage); the video's own reasoning for outlet-over-payoff in CZ stands and gets *stronger* with premium payoffs in the 99.
- **Elas il-Kor alternative**: payoff-in-CZ makes "loop + outlet" win immediately without drawing a payoff, and Bartolomé-loop alone needs a combat step to convert counters. Counterpoint: with 6+ payoffs and 7+ outlets in the 99 the marginal case is thin, and Elas as commander loses the mid-game outlet value engine. Decide with density math (count winning 3-piece boards under each CZ choice) next heartbeat.
- Third options (Teysa Karlov etc.) rejected: neither outlet nor payoff density hinge.

## Commander decision (SETTLED, heartbeat 2, 2026-08-17)

**Keep Bartolomé del Presidio as commander; put Elas il-Kor in the 99.**

Density math. A winning board is outlet + loop-half-A + loop-half-B + payoff (4 functional pieces); the command zone supplies one for free.
- Bartolomé in CZ: the 3 drawn pieces are loopA + loopB + payoff. Upgraded 99 holds 6 payoffs.
- Elas in CZ: the 3 drawn pieces are outlet + loopA + loopB. Upgraded 99 would hold 8 outlets (7 + Bartolomé demoted to the 99).
Hypergeometrically that is a near-wash (6 vs 8 in the scarce class; loop pieces are ~19 either way). The tie-breakers all favor Bartolomé:
1. Elas il-Kor goes in the 99 as a payoff either way a payoff can — so the Bartolomé build gets Elas's guaranteed-drain effect anyway once drawn; the Elas build cannot put "free instant-speed outlet" in the CZ (Bartolomé in the 99 is just outlet #8).
2. Bartolomé's activation is free and instant-speed: it protects every combo creature from exile/steal at zero mana, and converts every death into mid-game value from turn 2 (the video's outlet-over-payoff argument, [15:02–16:25]).
3. Altar of Dementia and the drain payoffs make the "no payoff drawn" case thin, and infinite counters + Rogue's Passage is a real backup win.
4. Same strategy as the source video (board asked for same strategy/speed).
Commander-dependency (DEC-474 L9) is now covered either way: 7 in-99 outlets + Phyrexian Tower + High Market keep the loop network alive under a Darksteel Mutation-class lock.

## Final 99 draft (heartbeat 2) — 67 nonland + 32 lands

New-card oracle checks: `dec532-upgrade-candidates-oracle.json` (73 cards) + heartbeat-2 collection lookup (Skullclamp, Fracture, Silent Clearing, Scrubland, Brightclimb Pathway, Bloodstained Mire, Flooded Strand — all legal, all WB-identity or colorless).

**Loop half A — recursive-ETB creatures (9):** Sun Titan, Angel of Indemnity, Redemption Choir (Coven-gated — note in guide), Shepherd of the Cosmos, Boonweaver Giant, Brotherhood Outcast, Danitha Benalia's Hope (all 7 kept) + Karmic Guide, Reveillark (classic pair; Reveillark rebuys the power-≤2 crowd: Viscera Seer, Carrion Feeder, Blood Artist, Cruel Celebrant, Zulaport, Elas, Stitcher's, Fiend Hunter...).

**Loop half B — death-return auras (9):** Necrogen Communion, Kaya's Ghostform, Gift of Immortality, Angelic Renewal, Minion's Return, Fungal Fortitude (kept) + Animate Dead, Necromancy (reanimation auras; each also = registered infinite loop with Leonin Relic-Warder, and infinite mana with an altar out). Cut: Changing Loyalty (weakest of the class; replicate is mana-hungry).

**Interaction bodies that loop (3):** Fiend Hunter, Werefox Bodyguard, Leonin Relic-Warder.

**Sac outlets (7 + commander + 2 lands):** Viscera Seer, Carrion Feeder, Woe Strider, Yahenni Undying Partisan, Phyrexian Altar, Ashnod's Altar, Altar of Dementia (+ Phyrexian Tower, High Market in the mana base). Cut: Dimir House Guard (4 MV, outclassed; transmute role covered by real tutors).

**Drain payoffs (6):** Zulaport Cutthroat, Bastion of Remembrance, Scavenger's Talent (kept — level 2 is the mill wincon) + Blood Artist (triggers on ANY creature death — ~×4 frequency vs own-only under the 4-player model, DEC-477), Cruel Celebrant, Elas il-Kor Sadistic Pilgrim. Cut: Agent of the Iron Throne, Ninja Teen, Marionette Apprentice (weakest three once premium payoffs land).

**Self-mill + draw engine (11):** Stitcher's Supplier, Undead Butler, Crow of Dark Tidings, Corpse Augur, Unseal the Necropolis, Corpse Churn, Funeral Rites (kept) + Skullclamp (1-toughness aristocrat bodies = 2 cards per {1}; equip-kill IS a sac-adjacent death for all drain payoffs), Esper Sentinel (creator priced it out at [5:31]), Black Market Connections. Cut: Diresight, Another Chance, Gnawing Vermin, Millikin, Paramecia Coloniex, The Warring Triad (mana-filter rock, not engine), Throne of the Grim Captain (T-mill-2 too slow), Noble's Purse, Bolas's Citadel (deferred — 6 MV clunker risk; revisit post-sim).

**Recursion spells (6):** Sevinne's Reclamation, Unburial Rites, Dread Return, Body Snatcher (kept) + Reanimate, Victimize (sac two = on-plan double reanimate). Cut: Summon Undead, Infernal Offering, Wake the Dead, Demonic Bargain (exile-13 fights our own yard).

**Tutors (7):** Final Parting (kept — hand+yard split is the deck's ideal) + Demonic Tutor, Vampiric Tutor, Enlightened Tutor (auras AND altars AND Skullclamp), Diabolic Intent (sac = on-plan), Buried Alive, Entomb.

**Interaction/protection (7):** Generous Gift (answers hoser LANDS), Seal from Existence, Dusk // Dawn (Dusk spares our sub-3-power board; Dawn rebuys it) (kept) + Swords to Plowshares, Anguished Unmaking, Fracture (artifact/enchantment/PW — hoser coverage), Grand Abolisher (combo-turn protection). Cut: Disenchant (→Fracture), Bound in Gold, Intercessor's Arrest.
Hoser coverage (DEC-474 L6): graveyard hate on artifacts (Fracture, Anguished Unmaking, Leonin Relic-Warder, Generous Gift), enchantments (same four + Seal from Existence), lands (Generous Gift), creatures (Swords, Fiend Hunter, Werefox). All four permanent types answered; Relic-Warder + Seal are recurable permanents per the video's own principle.

**Rocks/fast mana (5):** Arcane Signet, Talisman of Hierarchy (kept) + Sol Ring, Dark Ritual, + keep curve low. Cut: Orzhov Signet, Mind Stone, Charcoal Diamond, Prismatic Lens, Wayfarer's Bauble, Noble's Purse. Speed guardrail respected: no Mana Vault/Chrome Mox/Mox Diamond overdrive.

**Lands (32):** Command Tower, Bojuka Bog, Dakmor Salvage, Rogue's Passage (kept) + Godless Shrine, Scrubland, Marsh Flats, Bloodstained Mire, Flooded Strand, Concealed Courtyard, Shattered Sanctum, Isolated Chapel, Caves of Koilos, Brightclimb Pathway, Vault of Champions, Silent Clearing, Urborg Tomb of Yawgmoth, Takenuma Abandoned Mire, Phyrexian Tower, High Market, Ancient Tomb, 6 Plains, 5 Swamp. Cut: Ash Barrens, Exotic Orchard, Great Hall of the Citadel, Hidden Grotto, Memorial to Folly, Myriad Landscape, Orzhov Basilica, Path of Ancestry, Tainted Field, Conduit Pylons + Surveillance Room (both are {1}-gated any-color surveil lands — cute but slow; verified oracle 2026-08-17), Mariposa Military Base (rad-counter draw land, NOT a mill land — misread in video notes).

## Iteration 2 (heartbeat 2) — Spellbook re-run + EDHREC closing diff → FINAL

**Spellbook on draft v1** (`dec532-spellbook-draft99.json`): **204 included combos** (baseline 32, target ~150 — exceeded). Only **29 of 204 route through Bartolomé** (was 32/32) — commander-dependency (L9) fixed. All 204 produce infinite death triggers + infinite ETB (any drain payoff converts to a win); 31 also make infinite colorless mana, 29 infinite mill (Altar of Dementia standalone-wincon lines).

**Near-miss triage (top single-card unlocks, DEC-474 L7):**
- Dance of the Dead (+22) — **COMPLETE**: cheap, strictly on-plan (reanimation aura = loop-B + Relic-Warder + altar lines). Swapped in for Corpse Churn (Corpse Churn appears in 0 included combos → final = 204 + 22 = **226 included**, derived arithmetically; near-miss entries missing exactly this card).
- Junji, the Midnight Sky (+32) — DEFER: real card, but 5 MV loop piece; curve discipline, density already 6× baseline. First-in if sim wants more loop-A.
- Felidar Guardian (+23) — DEFER: blink sub-theme, off the death-loop plan.
- Plague of Vermin (+24) — REJECT: 7 MV, off-plan.
- Blasting Station (+19) — DEFER: outlet+payoff in one but clunky; density covered.
- Changing Loyalty (+16) — REJECT for slots: weakest loop-B member, replicate is mana-hungry.
- Umbral Collar Zealot (+19), Sister Hospitaller (+16), Metamorphosis Fanatic (+16), Archon of Falling Stars (+15), Unholy Indenture (+13) — DEFER: same loop classes, redundant with in-deck members; density already at target.

**EDHREC closing diff (DEC-402, fetched 2026-08-17, every ≥40% absentee called):**
- Deadly Dispute 48% — **INCLUDE** (oracle-verified {1}{B} instant: sac artifact/creature, draw 2 + Treasure; instant-speed, on-plan). Swapped in for Funeral Rites (0 combo usage; yard-filling covered by Entomb/Buried Alive/Final Parting + 5 mill permanents + Dakmor).
- Ichor Wellspring 50% / Mephitic Draught 43% / Greedy Freebooter 42% — REJECT: EDHREC's artifact-sac value sub-theme; our build is the creature loop network.
- Marionette Apprentice 50% — DEFER: 7th payoff; first re-add if sim shows payoff-density gap.
- Corpse Knight 43% — DEFER: ETB-side payoff, coverage redundant (every loop makes both ETB and death triggers).
- Village Rites 42% — DEFER: Deadly Dispute takes the instant sac-draw slot.
- Path to Exile 40% — DEFER: interaction suite at 7 + recurable bodies is adequate for a combo deck.
- Orzhov Signet 45% — REJECT: rock count tuned to 32-land/low-curve build (Sol Ring, Arcane Signet, Talisman, Dark Ritual).
- Tainted Field 52% / Shineshadow Snarl 42% / Orzhov Basilica 42% — REJECT: premium base (Scrubland/Godless Shrine/fetches/Pathway) strictly better.

**~~FINAL 99~~ SUPERSEDED 2026-08-17 (parallel-run artifact — "Endless Procession"). NON-COMPLIANT with board constraints in comment 93e761b0 (external outlets/tutors/payoff: Phyrexian Altar, Altar of Dementia, Woe Strider, Yahenni, Demonic Tutor, Vampiric Tutor, Entomb, Cruel Celebrant). FE build halted via hold issue 8708ca3d. The authoritative proposal is the "FINAL DRAFT 99" (Grave Dividends, all-Quill) section below. Kept for the record:**
- Loop A (9): Sun Titan, Angel of Indemnity, Redemption Choir, Shepherd of the Cosmos, Boonweaver Giant, Brotherhood Outcast, Danitha Benalia's Hope, Karmic Guide, Reveillark
- Loop B (9): Necrogen Communion, Kaya's Ghostform, Gift of Immortality, Angelic Renewal, Minion's Return, Fungal Fortitude, Animate Dead, Necromancy, Dance of the Dead
- Interaction bodies (3): Fiend Hunter, Werefox Bodyguard, Leonin Relic-Warder
- Outlets (7): Viscera Seer, Carrion Feeder, Woe Strider, Yahenni Undying Partisan, Phyrexian Altar, Ashnod's Altar, Altar of Dementia
- Payoffs (6): Zulaport Cutthroat, Bastion of Remembrance, Scavenger's Talent, Blood Artist, Cruel Celebrant, Elas il-Kor Sadistic Pilgrim
- Mill/draw (9): Stitcher's Supplier, Undead Butler, Crow of Dark Tidings, Corpse Augur, Unseal the Necropolis, Skullclamp, Esper Sentinel, Black Market Connections, Deadly Dispute
- Recursion (6): Sevinne's Reclamation, Unburial Rites, Dread Return, Body Snatcher, Reanimate, Victimize
- Tutors (7): Final Parting, Demonic Tutor, Vampiric Tutor, Enlightened Tutor, Diabolic Intent, Buried Alive, Entomb
- Interaction/protection (7): Generous Gift, Seal from Existence, Dusk // Dawn, Swords to Plowshares, Anguished Unmaking, Fracture, Grand Abolisher
- Rocks/ritual (4): Sol Ring, Arcane Signet, Talisman of Hierarchy, Dark Ritual
- Lands (32): Command Tower, Bojuka Bog, Dakmor Salvage, Rogue's Passage, Godless Shrine, Scrubland, Marsh Flats, Bloodstained Mire, Flooded Strand, Concealed Courtyard, Shattered Sanctum, Isolated Chapel, Caves of Koilos, Brightclimb Pathway, Vault of Champions, Silent Clearing, Urborg Tomb of Yawgmoth, Takenuma Abandoned Mire, Phyrexian Tower, High Market, Ancient Tomb, 6 Plains, 5 Swamp
Nonland total 9+9+3+7+6+9+6+7+7+4 = 67; 67 + 32 lands = 99 ✓. Commander: Bartolomé del Presidio.

## Board constraints (comment 93e761b0, 2026-08-17)

1. 5–6 premium sac outlets — choose from Quill of Casualties.
2. Recursion + tutor upgrades — choose from Quill.
3. Premium payoffs — choose from Quill; external only if much stronger.

## FINAL DRAFT 99 (2026-08-17, heartbeat 2) — proposed to board

- Commander: **Bartolomé del Presidio** (kept). Spellbook data settles the CZ question: Bartolomé personally registers 32 lines from the CZ; payoffs are ambient in the loop network, so Elas-in-CZ adds zero registered lines while losing the always-on outlet. Elas il-Kor joins the 99 as a payoff.
- Full list + adds/cuts posted as DEC-532 proposal comment (source of truth). 85 named cards + 7 Plains + 7 Swamp; 35 lands / 64 nonland.
- All 46 adds vs the video list are Quill-sourced (verified programmatically) — zero external cards.
- **Spellbook on draft: 159 included** (`dec532-spellbook-draft99.json`, run without Reassembling Skeleton) **+ 5 Skeleton-only near-misses = 164 final** (video baseline 32). 127 of 159 lines work without the commander (baseline 0) — DEC-474 L9 commander-dependency fixed.
- Outlet line counts: Viscera Seer 33, Ashnod's Altar 33, Carrion Feeder 32, Bartolomé 32, Umbral Collar Zealot 27, LRW+Animate Dead/Necromancy 2. Yawgmoth registers 0 but is a mana-free outlet + draw engine (pay 1 life, sac: −1/−1 counter + draw).
- Near-miss triage: non-Quill outlets (Phyrexian Altar/Altar of Dementia 33, Yahenni/Woe Strider/Blasting Station/Bloodflow/Shilgengar 32, Phantom Train 27) REJECTED per board constraint. Half-B aura class (Unholy Indenture/Unhallowed Pact/Shade's Form +19 each) DEFERRED as an optional density lever. Dance of the Dead 16 deferred (external). Forsaken Miner 5 (Quill) deferred (Corpse Augur's draw preferred).
- EDHREC closing diff (DEC-402) done vs `dec532-edhrec-bartolome.json` (1,855 decks, population dominated by the $28 video build): Cruel Celebrant 68% REJECT (payoff parity, board rule 3); Ichor Wellspring 50%, Mephitic Draught 43%, Greedy Freebooter 42%, Village Rites 42%, Corpse Knight 43% REJECT (budget-skew / covered by premium suite); Tainted Field 52%, Shineshadow Snarl 42%, Orzhov Basilica 42%, Rogue's Passage 42% REJECT (mana quality / drain payoffs make combat backup unneeded); Reassembling Skeleton 32% INCLUDE (Quill, +5 combos, swapped for Gnawing Vermin).
- GC count 1 (Enlightened Tutor); propose bracket 4. Hoser note: land-based gy hate answered only by Generous Gift (accepted, stated to board).
- Proposed name: Grave Dividends (alternatives offered).

## Re-review round (2026-08-17, board comment 7867da27)

Board: no sign-off yet; banned Demonic Tutor, Vampiric Tutor, Altar of Dementia, Esper Sentinel; asked for a consistency/reliability/power re-review of the FINAL DRAFT 99.

- **Banned four: absent from the 99** (script-verified). They only existed in the superseded Endless Procession list.
- **Sourcing re-verified**: 99 exact, no dupes; 46 adds all in Quill's deck.json; rest are video keeps. Zero external. GC = 1 (Enlightened Tutor).
- **Fresh Spellbook run on the exact 99** (`dec532-spellbook-final99-review.json`): **164 included** (matches proposal). **131/164 commander-free** (proposal said 127 — partial-run artifact; 131 is authoritative). 154 lines zero-mana once assembled; 158 3-piece, 2 2-piece (Animate Dead/Necromancy + LRW). Outlet lines: Ashnod's 34, Viscera Seer 34, Carrion Feeder 33, Bartolomé 33, Umbral Collar Zealot 28. All 164 → infinite death+ETB; 66 also infinite Bartolomé counters. Near-miss ceiling: all top unlocks are external/banned → 164 is the constraint-max.
- **Oracle re-checks (18 cards)**: two prior notes corrected in the deck's favor — Mariposa Military Base IS a self-mill land (rad counters mill their owner); Changing Loyalty has flash + steal-on-death vs opponents. Colorless-land nit (Volrath's/High Market/Mariposa vs the Rogue's Passage cut) reviewed: justified, all three carry on-plan engine functions.
- **Verdict: 99 unchanged.** Comment 90c70cd2 posted; fresh confirmation 6fb2998e pending (old gate 15e06706 expired on board comment).
- **Build incident**: FE had started the dead Endless Procession build in the working tree (Quill deleted locally, index/loader/taxonomy edited; NOTHING committed). CEO restored all tracked files to HEAD 2026-08-17; untracked FE scratch (`data/commanders/endless-procession/`, `priv_data/tmp_build_endless.py`) left in place, inert. Board asked to cancel build issue 228630bf; hold 8708ca3d still active.

## Remaining work

1. ~~Density math / commander pick~~ done. ~~Draft 99~~ done. ~~Spellbook re-run~~ done. ~~EDHREC closing diff~~ done.
2. Board approval via request_confirmation on DEC-532 (pending).
3. On approval: delegate file build to Founding Engineer via child issue (new-deck pipeline per `reference_new_deck_build_pipeline`: deck.json, index.json entry placed before first brewing deck, compute_tokens, validate_deck_json, refresh_card_pool, metrics, sim, STORAGE_PREFIX cache-key bump) **plus Quill dismantle** (remove/retire `silverquill-the-disputant`) in the same leg.
4. CEO validation of built files before closing (board requirement): validate_deck_json, check GC recount, manabase_check, sim/metrics sanity, stale-ref sweep of Quill references fleet-wide.

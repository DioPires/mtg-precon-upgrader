## DEC-1215: add Galactus, skip Summon: Bahamut (Broodfire Hatchery, B4)

**Recommendation: add Galactus, Devourer of Worlds and cut Zacama, Primal Calamity (line A). Do not add Summon: Bahamut.**

**Tier 0.** This is a single-card review, and I run those myself under DEC-461. I edited no deck file. The swap waits for your verdict on the card.

### Proposed lines (approve at most one)

- [ ] **A (recommended): +Galactus, Devourer of Worlds / −Zacama, Primal Calamity.** One big body replaces another. In practice, only Atla's reveal puts either card onto the battlefield. Galactus is the better card to reveal: it is bigger, it flies, it is indestructible, and it exiles a permanent.
- [ ] **B (alternative): +Galactus / −Llanowar Elves.** Atla's reveals get better, but the start gets slower. The chance of a turn-2 mana accelerant falls from 40.5% to 35.0% on the play.

### The cards (oracle text from the mirror, prices and rulings from Scryfall, 2026-10-20)

- **Galactus, Devourer of Worlds** {10}, colorless legendary creature, 12/12. Flying, trample, indestructible. "When Galactus enters, exile target permanent." It must attack the opponent with the most life in each combat if able. Set: Marvel Super Heroes Commander (msc, 2026-06-26). Not a Game Changer. Owned (1 copy, in no other deck). EUR 4.11.
- **Summon: Bahamut** {9}, colorless Enchantment Creature (Saga Dragon), 9/9 flying. Chapters I and II: destroy up to one target nonland permanent. Chapter III: draw two cards. Chapter IV: it deals damage equal to the total mana value of your other permanents to each opponent. Then you sacrifice it. Set: Final Fantasy (fin, 2025-06-13). Not a Game Changer. Not owned. EUR 26.29.

### Why Galactus fits

1. **Nobody casts Zacama or Galactus.** The goldfish sim gives a median of 7 available mana on turn 10 (p75: 9). Source: `simulation.json`, 100,000 games, 2026-10-06. So Zacama (9) and Galactus (10) arrive only from Atla's reveal or Raph & Mikey's reveal.
2. **Zacama's best line does nothing on a reveal.** Its text reads "When Zacama enters, if you cast it, untap all lands you control." Atla does not cast it. A revealed Zacama is a 9/9 trampler with three abilities. Each ability costs {2} plus one colored mana, and that is the same {2} that makes an Egg.
3. **Galactus arrives as removal.** Its exile trigger fires once each time it enters. That can be on your turn or at an opponent's end step (a Seedborn hatch). Galactus is legendary, so Annie Joins Up makes the trigger fire twice. Elesh Norn adds one more. One reveal can exile up to 3 permanents. It hits any permanent type, including lands and planeswalkers. Zacama's {2}{G} destroys only artifacts and enchantments.
4. **It brings its own evasion.** At each combat, Zopandrel makes it 24/24. Xenagos then makes it 48/48 with haste. That one flying trampler kills an opponent at 40 life by itself, without Garruk's Uprising or Ajani's Anguish. The same line on Zacama gives 36 trample damage on the ground.
5. **It survives the board wipes (checklist step 10).** Indestructible covers destroy wipes and damage wipes. A −X/−X wipe needs X of 12 or more (Toxic Deluge costs 12 life). Zacama dies to all of these unless Avacyn (destroy) or Vigor (damage) is on the battlefield.
6. **The numbers move a little.** Each figure compares the current 99 with the same 99 after line A.
   - Mean printed power of a revealed creature: 5.78 to 5.89 (27 creature cards both ways).
   - Average nonland mana value: 4.242 to 4.258.
   - Removal-spot count: 7 to 7.5 (target 8), if Galactus is tagged `wincon` / `removal-spot`.
   - The goldfish sim does not model flying, indestructible or the exile, so I expect the sim to read flat.

### Costs and limits

- **The forced attack.** Galactus must attack the opponent with the most life in every combat if able. It cannot stay back to block. It cannot pick off a weak player either. This deck attacks in every combat anyway, so I rate this a small cost.
- **Hate (checklist step 7).** Grafdigger's Cage stops a Galactus reveal, as it stops every reveal. A Torpor Orb effect stops its exile but not the 12/12. Under a Cage, each card must be hard-cast before it can answer the Cage: Zacama for 9 mana (its untap then pays for {2}{G}), Galactus for 10 mana (its exile hits the Cage). The hoser suite does not change: Aura Shards, Krosan Grip, Force of Vigor, Boseiju and Beast Within.
- **Tutors.** Galactus is colorless, so Natural Order cannot find it. Zacama is green, so it can. Natural Order still has six green bombs in the 99: Craterhoof, Worldspine, Apex Altisaur, Zopandrel, Vigor and Vaultborn Tyrant. Worldly Tutor finds either card.
- **A dead draw.** A Galactus in hand is as dead as a Zacama in hand (10 against 9 mana value). Greater Good can discard it. Unlike Worldspine Wurm and Blightsteel Colossus, it does not shuffle back into the library.
- **EDHREC.** Zacama is on 53.4% of Atla decks (rates fetched 2026-09-29), and it was on your original list. Galactus is not on the Atla page. I cut Zacama for reason 2: decks play it for the untap, and Atla never casts it.
- **Combos.** Zacama is in 0 included Spellbook lines. It is in 3 near-misses, and each one needs a card outside the 99 (Temur Sabertooth, Sanctum of Eternity, Monk Gyatso). Neither new card is in the corpus. The Combo Lab loses nothing.
- **Commander dependency (checklist step 9).** No change. If a Darksteel Mutation effect locks Atla, Raph & Mikey can still reveal Galactus.

### Why not Summon: Bahamut

1. **Its finisher is noncombat damage.** Chapter IV is a burn to each opponent. On a typical board (Atla, Sol Ring, Arcane Signet, an Altar, Rhythm of the Wild and two hatched bombs) it deals about 30 to each opponent. Round 5 rejected noncombat finishers (Fling, Chandra's Ignition, Kazuul's Fury) because they are off your "big creature enters, big creatures attack" pattern.
2. **It is slow.** Lore counters go on as your precombat main phase begins (Scryfall ruling, 2025-06-06). A reveal on your turn 6 deals its damage on turn 9. A reveal at the end step before turn 6 deals it on turn 8. In the median goldfish game the deck is lethal by turn 8 (lethalProxy reaches 64.0% at turn 8).
3. **It is fragile.** It is a 9/9 flyer with no trample and no indestructible. Both creature removal and enchantment removal kill it. It also sacrifices itself after chapter IV.
4. **Its best part overlaps Galactus.** Chapter I removes a nonland permanent when it enters. Galactus does that with exile, and Annie doubles it. Bahamut's real extras are a second removal one turn later, two cards, and Enlightened Tutor access (it is an enchantment).
5. **It costs EUR 26.29, and you do not own it.** You own Galactus.

If you want Bahamut anyway, say so on this issue and I will name a second cut.

### Discovery trail

- `candidates.json` (2026-10-12, top 200): neither card is in it. Galactus has no EDHREC rate for Atla.
- Spellbook: 0 combos with either new card.
- Game Changers: neither card is on the list. The count stays at 7, and the deck stays bracket 4.
- Swap counter: this would be round 2 since the round-5 reset (round 6 was round 1). Trigger 2 does not fire.

### On apply (after approval)

1. Edit `deck.json`. Swap the decklist entry: Galactus gets `primary_role: wincon` and `secondary_role: removal-spot`. Add a Galactus highlight. Remove Zacama from `guideContent.strategyOverview` and from its deck category. Add the source entries (`scryfall` and `ai-inferred`).
2. Add Galactus to `card-metadata.json`.
3. Run `validate_deck_json`, `compute_tokens`, `refresh_card_pool`, the metrics script, the sim and the three Combo Lab scripts.
4. Bump the loader cache key, commit and push.

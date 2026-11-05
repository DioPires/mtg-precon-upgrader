## DEC-1226: add both cards, each as a one-for-one swap

**Recommendation: add Necklace of Girion to Verdant Tide and cut Patchwork Banner (line A). Add Dragon-Cursed Halls to Hoard and Bleed and cut Fountainport (line B). Both are small upgrades, not gap fills, and you must buy both cards.**

**Tier 0.** Single-card reviews are mine under DEC-461. I edited no deck file. Each swap waits for your vote on the card below.

### The cards (oracle text from the mirror; set, price and rulings from Scryfall, 2026-11-05)

- **Necklace of Girion** {2}{G}, legendary artifact. "Whenever you cast a green spell and whenever a Forest you control enters, put a +1/+1 counter on target creature you control." {T}: Add {G}. The Hobbit Eternal (hoc, 2026-08-14), rare. Not a Game Changer. Not owned. EUR 11.53. It is not on Eladamri's EDHREC page (fetched 2026-09-29), and that page lists every card at 5.0% or more.
- **Dragon-Cursed Halls**, land. {T}: Add {C}. "{1}, {T}: Until end of turn, target creature gains 'Whenever this creature deals combat damage to a player, create a Treasure token.'" Same set, rare. Not a Game Changer. Not owned. EUR 5.23. It is on 47.1% of Smaug decks (EDHREC, fetched 2026-09-28).
- Scryfall has no ruling for either card. Neither card is in a Commander Spellbook combo.
- Both decks are healthy and show no gaps: Verdant Tide scores 89 and Hoard and Bleed scores 97. So each card replaces a working card. It does not fill a hole.

### A. Necklace of Girion in Verdant Tide: yes, cut Patchwork Banner

Why it fits:

1. **It triggers almost every turn.** 58 of the 65 nonland cards are green, and so is Eladamri. 25 of the 34 lands are Snow-Covered Forests. Six ramp cards put seven Forests onto the battlefield: Nature's Lore, Three Visits, Skyshroud Claim (two), Cultivate, Fabled Passage and Elven Passage. Each Verdant Kraken tentacle is a Forest too, so the Kraken adds four counters a round in a four-player game.
2. **Marwyn turns counters into mana.** Marwyn taps for {G} equal to its power, so each counter on Marwyn adds one mana to every Marwyn tap. Dionus untaps Marwyn once a turn, and then each counter adds two mana a turn. The deck already lists this as the "Marwyn Counter Engine" synergy. Today only Elves that enter grow Marwyn. With the Necklace, every green spell and every Forest grows it.
3. **Counters raise the deck's other power-scaled cards.** Disciple of Freyalise draws cards equal to the power of the creature it sacrifices. Tyvar's pump adds the greatest power among your creatures. The Great Henge costs less by that same number.
4. **It survives a creature wipe.** Most of the deck's mana comes from creatures. After a Toxic Deluge, the Necklace still taps for {G}.

**My estimate of the rate.** The goldfish sim gives a mean of 4.4 to 5.7 mana on turns 4 to 6 (100,000 games, 2026-10-06). The average nonland mana value is 3.43. So the deck casts about 1.5 green spells a turn before the elf mana bursts, and it plays a Forest on about three turns in four. I expect 2 to 3 counters a turn from the turn after the Necklace lands. The sim does not model the Necklace, so this figure is my estimate, not a sim result.

Why Patchwork Banner is the cut:

- **It fills the same slot.** It is a 3-mana artifact that taps for one mana and grows creatures. Its "any color" mana does nothing in a mono-green deck.
- **Its pump is smaller over time.** It gives +1/+1 to Elves only, and the pump ends when the Banner leaves. With 4 to 6 Elves on the battlefield, that is +4 to +6 power. The Necklace passes that total in its second or third turn. It can also grow non-Elves (Beasts, Insects, Treefolk, Wurms), and its counters stay if the Necklace is destroyed.
- **The deck already has four Elf lords** that give other Elves +1/+1: Elvish Archdruid, Imperious Perfect, Leaf-Crowned Visionary and Dwynen.
- **No rule protects it.** It came in with the first owned-card swaps (`aefdb94c`), so the recent-cut rule does not apply. You own 5 copies (Owned.csv).
- **No combo uses it.** Verdant Tide has 0 included Spellbook combos.

Costs and limits:

- **Nothing finds it.** All four tutors find creatures only: Worldly Tutor, Finale of Devastation, Nature's Rhythm and Formidable Speaker. Eladamri cannot cast it from the top of the library or put it onto the battlefield. You get it only from a normal draw, the same as the Banner.
- **The cheat plan does not trigger it.** Eladamri's reveal and Ghalta's entry put creatures onto the battlefield without casting them.
- **The counter is not optional.** Skullclamp wants 1/1s that die at once, so put the counters on Marwyn or on a large creature, not on a Clamp target.
- **It competes with the commander on turn 3.** Eladamri's median cast turn is 3 (87.1% by turn 3).
- **The metrics do not move.** Ramp goes from 15.5 to 16.5 against a target of 10. Ramp is already above target, so its score stays at the cap. Payoff is not a scored role.
- **Price:** EUR 11.53 to buy. The Banner goes back to the collection.

### B. Dragon-Cursed Halls in Hoard and Bleed: yes, cut Fountainport

**The old rejection does not apply to this swap.** DEC-543 rejected the Halls as "a colorless-only land against 36 black and 29 red pips", and DEC-930 repeated that. The objection is about cutting a colored land. Fountainport also makes only colorless mana and also enters untapped. If one replaces the other, no black or red source count changes. Colorless-only lands stay at 4 of 40 land cards: High Market, Fountainport, Treasure Vault and Volatile Fault.

Why the Halls is better than Fountainport here:

1. **It makes a Treasure for much less mana.** The Halls costs {1} plus its own tap, so 2 mana for 1 Treasure. Fountainport costs {4} plus its own tap, so 5 mana for 1 Treasure. The Treasure gives back one mana either way, so the net cost is 1 mana against 4.
2. **The commander is the target.** Smaug is a 5/5 flyer in the command zone. The goldfish sim has Smaug on the battlefield in 57.7% of games by turn 5, 79.5% by turn 7 and 85.9% by turn 8 (100,000 games). Goldspan Dragon, Mirkwood Bats and Hellkite Tyrant also fly. Professional Face-Breaker has menace.
3. **You can wait for blockers.** The ability has no timing limit. Pay for it after blockers are declared, on a creature that nobody blocked.
4. **The Treasure feeds the whole engine.** When you spend it on a spell, Smaug draws a card. When it enters, Reckless Fireweaver and Weftstalker Ardent each deal 1 damage to each opponent. When you sacrifice it, Marionette Apprentice, Mayhem Devil and Mirkwood Bats each make opponents lose life. Xorn adds a second Treasure, and Academy Manufactor makes a Clue, a Food and a Treasure instead. Professional Face-Breaker makes one more Treasure from the same hit.

What you give up with Fountainport:

- **It works without combat.** Its {2} mode sacrifices a spare token to draw a card. Its {3} mode makes a 1/1 Fish to sacrifice. Both are instant-speed uses for spare mana late in the game.
- **The Halls rewards attacks, and this deck does not plan to attack.** DEC-566 ruled against an attack pivot because the deck wins by casting spells, not by combat. The Halls does not reverse that ruling. It takes a land slot, not a spell slot. It pays off on the occasional Smaug and Goldspan attacks that DEC-566 says the deck already makes.
- **Attacking taps the deck's best blocker.** Every Smaug attack already has this cost. The Halls only gives one more reason to attack.
- **Price:** EUR 5.23 to buy.

**Not offered: the Halls for a basic Swamp or Mountain.** That is the swap DEC-543 rejected. It costs a colored source and moves colorless-only lands from 4 to 5 of 40, against 45 black and 25 red pips (my count today, the same as DEC-930's).

### Next step

Vote on the card below. A and B are independent. When you approve one, I apply it inline (DEC-461), run the validator and the metrics refresh, and report the numbers.

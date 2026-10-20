## DEC-1215 — Galactus and Summon: Bahamut for Broodfire Hatchery

**Recommendation: add Galactus, Devourer of Worlds and cut Worldspine Wurm. Summon: Bahamut is a good card but only a sidegrade in this deck; I recommend skipping it and offer it as an optional line for Apex Altisaur.** Tier 0, CEO-executed card review (DEC-461 standing exception). Nothing is applied. Both cards verified on Scryfall this run (oracle mirror 2026-10-08, rulings from the API). Neither card is a Game Changer, so the count stays at 7.

### 1. What both cards have in common here

- Both are colourless creatures. Atla's reveal hits them, Raph & Mikey's attack reveal hits them, and Worldly Tutor puts either one on top before an Egg dies. Enlightened Tutor also finds Bahamut, because it is an enchantment.
- Both have printed power 7 or more, so Tifa's untap and extra combat fire on them. Vaultborn Tyrant, Garruk's Uprising, Guardian Project and The Great Henge each draw on them.
- Neither fills the deck's one gap (recursion, 0 of 3). Health is 79, below the 85 gate, but neither card answers the gap, so each one must beat the card it replaces.
- So I swap a 9+ drop for a 9+ drop. The creature count stays at 27, the count of cards at mana value 6 or more stays at 16, and the count of creatures with printed power 7 or more stays at 8 (the prose number). The hatch odds and the opening-hand clunk do not change.

### 2. Line A — Galactus, Devourer of Worlds: recommended

**Card.** {10}, 12/12 Legendary Creature — Elder Alien. Flying, trample, indestructible. When Galactus enters, exile target permanent. Galactus attacks an opponent with the most life among your opponents each combat if able (unless you control Silver Surfer, Galactus's Herald). **Owned: 1 copy, in no deck, so it is free.**

**Why it beats Worldspine Wurm in this deck:**

1. **It removes something the moment it lands.** The exile hits any permanent: a blocker, a hoser, an opposing commander. It is a legendary creature, so Annie Joins Up adds one more trigger; Elesh Norn adds one more because a permanent entering causes it. With both, that is three exiles. Worldspine removes nothing.
2. **It flies and tramples.** Ground creatures cannot block it, and a chump block by a flier costs it only the blocker's toughness.
3. **It is indestructible.** It survives destroy wraths, damage and fights. Worldspine's insurance is weaker on the same wrath: three 5/5 tramplers and a shuffle back into the library.
4. **The kill turn reads the same.** Zopandrel makes it 24/24 flying trample; Xenagos on top makes it 48/48; Raphael gives it double strike. That is lethal to one player through any blocker, as Worldspine is today.
5. **From Raph & Mikey** it enters tapped and attacking, and the exile resolves before blockers are declared, so it removes a blocker first.

**Costs, stated:**

- Printed power 12 against 15. The goldfish reads power only, so its lethal proxy may dip a little. It cannot see the removal, the flying or the indestructible.
- The forced attack picks the target. Galactus must attack the opponent with the most life in every combat. You cannot aim it at a low-life opponent, and you cannot keep it back as a blocker. Indestructible makes the attack itself low-risk.
- Worldspine shuffles back into the library when it goes to a graveyard from anywhere (including a Greater Good discard), so it can be hatched again. Blightsteel Colossus and Vigor keep that trait; Galactus does not have it.
- Galactus is colourless, so Natural Order cannot fetch it; Worldspine was a Natural Order target. Craterhoof, Zopandrel, Vigor, Ghalta and Mavren, Zacama and Apex Altisaur stay as targets.
- In hand it costs 10 generic against Worldspine's {8}{G}{G}{G}. Both are hard to cast; Galactus is one cheaper and any mana pays for it.
- It is not a Dinosaur, so Palani's Hatcher gives it no haste (the same as Worldspine). Rhythm of the Wild, Surrak and Goreclaw, Xenagos and Lightning Greaves do.

**Projection** (in memory, no files written; Galactus tagged `threat`, `removal-spot` secondary, the same primary role as Worldspine): global 79 / 83 → 79 / 83; role 95 → 96; curve 41 → 42 (average mana value 4.24 → 4.23); removal-spot 7 → 7.5 of 8; gaps: recursion only, unchanged.

**Community read** (EDHREC Atla page, snapshot 2026-08-22): Worldspine Wurm is in 35% of Atla decks (7,160 of 20,615). Galactus is in 3.3% (120 of 3,640), but it was printed in June 2026 and it is trending.

**Prose at apply time:** Worldspine has 15 references in `deck.json`, including the 60/60 example in "Hatch and Swing", the shuffle-back sentence and the Natural Order list. Each is rewritten.

### 3. Line B — Summon: Bahamut: optional, I recommend skipping it

**Card.** {9}, 9/9 Enchantment Creature — Saga Dragon, flying. I, II: destroy up to one target nonland permanent. III: draw two cards. IV (Mega Flare): it deals damage equal to the total mana value of other permanents you control to each opponent. You sacrifice it after IV. **Not owned; €26.29 on Scryfall, information only.**

**What it does here:**

- Chapter I fires as it enters (the first lore counter goes on without the stack). So a hatch is one free removal, at instant speed if the Egg dies on an opponent's turn under Seedborn Muse.
- Chapter II comes on your next turn, III on the turn after, and IV on the third of your turns after it lands. Then you sacrifice it.
- Mega Flare counts tokens and lands as 0. Example board: Atla 4 + Sol Ring 1 + Arcane Signet 2 + Rhythm of the Wild 3 + Ashnod's Altar 3 + Thornbite Staff 2 + Zopandrel 7 + Vaultborn Tyrant 7 = 29 damage to each opponent. It ignores blockers.
- Enlightened Tutor can find it, which gives that tutor a removal target that Atla delivers.
- Under Maskwood Nexus, every creature is an Egg, so the sacrifice after IV is an Egg dying and Atla hatches the next creature.

**Why it is only a sidegrade:**

- Its best turns come late. The deck usually wins on the hatch turn or the turn after. On that turn Bahamut is a 9/9 flier with no trample and one removal.
- It leaves on its own after chapter IV. Avacyn's indestructible does not stop a sacrifice.
- Mega Flare is a noncombat finisher. In DEC-935 the deck moved away from noncombat finishers (Fling and Chandra's Ignition were rejected for that reason). Here the damage rides on a combat body, so I do not reject the card for it, but it is that play pattern.
- It is not on the EDHREC Atla page (265 cards, snapshot 2026-08-22), a year after its June 2025 release.
- I do not count Elesh Norn on chapter I. Chapter I triggers on the lore counter, and I could not confirm from the rulings that Norn doubles it.

**The cut if you take it: Apex Altisaur.** Both cost 9. Apex is the deck's only creature that sweeps creatures (it fights on entry and again each time it is dealt damage), and it has no trample or evasion of its own. Bahamut answers any nonland permanent (artifact, enchantment, planeswalker), twice, and it flies. The cost: removal-board falls 3 → 2 of 3 and that gap returns. Winds of Abandon (overloaded) and Settle the Wreckage stay as the one-sided sweeps. Apex is a Dinosaur and gets haste from Palani's Hatcher; Bahamut does not.

**Projection:** global 79 / 83 → 76 / 83; role 95 → 91; interaction 120 → 111; gaps: removal-board and recursion.

**Considered and not offered as the Bahamut cut:**

- **Zacama, Primal Calamity.** The metrics stay flat (79 / 83), but Zacama is the most-played bomb on the Atla page (53%), and it is the one top-end card that is cheap to cast from hand: it untaps your lands when you cast it.
- **Krosan Grip.** The guide names it as the split-second answer to Grafdigger's Cage, which stops Atla outright. A hatched Bahamut cannot answer Cage, because Cage stops the hatch. The curve also drops 41 → 34 (a 17th card at mana value 6 or more).
- **Worldspine Wurm.** Line A takes it.
- **Draw, ramp and protection pieces.** Each role is at or below its target (draw 8 of 10, ramp 9 of 10, protection 4 of 4).

### 4. Both lines together

Lines A and B are independent. Both together (−Worldspine Wurm, −Apex Altisaur): global 79 / 83 → 77 / 83; gaps removal-board and recursion. The power-7-or-more count stays at 8 (Galactus 12 and Bahamut 9 replace Worldspine 15 and Apex 10).

### 5. If approved

Apply the approved lines in `data/commanders/broodfire-hatchery/deck.json`; rewrite the prose (Worldspine 15 references, Apex 4); add `card-metadata.json` entries; run the validator, Game Changer check, tokens, the three Combo Lab artifacts, the strategy-ceiling check, the simulation export, the metrics, the candidate pool and the cache-key bump. Swap round 2 since the round-5 reset; Trigger 2 fires at round 3. Galactus comes out of the owned pool; Bahamut would need a purchase.

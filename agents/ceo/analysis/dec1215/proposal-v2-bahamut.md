## DEC-1215, revised: add Summon: Bahamut as well (cut Blightsteel Colossus)

**Recommendation: add both cards. Line A is unchanged: +Galactus, Devourer of Worlds / −Zacama, Primal Calamity. New line C: +Summon: Bahamut / −Blightsteel Colossus.** I withdrew the old card (`7c4ea58c`) and posted a new one with four lines. I edited no deck file.

### What your three comments changed

1. **You own Bahamut.** My price objection (EUR 26.29) is gone. `priv_data/Owned.csv` does not list it, so please add it in ManaBox at your next export. I did not edit the CSV, because ManaBox is the system of record for it.
2. **Noncombat damage is fine as a second route.** I misread the round-3 direction (DEC-935, "big creature enters, big creatures attack"). It sets combat as the main plan. It does not ban noncombat damage. Bahamut's main jobs are removal and a big flying attacker, and Mega Flare is a backup finisher. That fits your rule. I recorded the rule in my notes for later reviews.
3. **You were right about its value before chapter IV.** Chapter I fires as Bahamut enters. So a Bahamut that dies at once has still destroyed a permanent. It also attacks two or three times before you sacrifice it. My earlier "too slow" point looked only at chapter IV. I withdraw it.

### Summon: Bahamut in this deck

The card: {9}, colorless Enchantment Creature (Saga Dragon), 9/9 flying, not legendary, not a Game Changer. Chapters I and II: destroy up to one target nonland permanent. Chapter III: draw two cards. Chapter IV (Mega Flare): it deals damage equal to the total mana value of your other permanents to each opponent. Then you sacrifice it. Oracle text is from the mirror; rulings are from Scryfall (2025-06-06).

**Timeline for a reveal in your first main phase of turn N:**
- Turn N: chapter I destroys a nonland permanent. With a haste source it attacks this turn too. The haste sources are Rhythm of the Wild (riot), Surrak and Goreclaw, and Xenagos.
- Turn N+1: chapter II destroys a second permanent. It attacks.
- Turn N+2: chapter III draws two cards. It attacks.
- Turn N+3: Mega Flare resolves in your first main phase. Then you sacrifice it, so it does not attack that turn.

A reveal at an opponent's end step (a Seedborn Muse hatch) fires chapter I at once and gives two attacks. A Raph & Mikey reveal puts it onto the battlefield attacking, so that is three attacks.

**Its attacks.** It is a 9/9 flyer. A riot counter or Surrak's counter makes it 10/10. Zopandrel doubles it to 20/20, and Xenagos can double it again. Surrak and Goreclaw, Garruk's Uprising and Ajani's Anguish give it trample.

**Mega Flare.** Lands and most tokens (Eggs, the Dinosaur and Wurm tokens) have mana value 0, so mostly cards count. Take a mid-game board of Atla (4), Sol Ring (1), Arcane Signet (2), one Altar (3), Rhythm of the Wild (3) and three revealed creatures. A revealed creature has a mean mana value of about 6, so the three add about 18. That board deals about 31 damage to each opponent. A Galactus on the battlefield adds 10 more.

**Doublers.** Annie Joins Up does not double its chapters, because Bahamut is not legendary. Roaming Throne names Shaman. With Maskwood Nexus on the battlefield, every creature you control is a Shaman, so Throne makes each chapter trigger twice. That means four removals, four cards and two Mega Flares.

**Tutors.** Enlightened Tutor (it is an enchantment) and Worldly Tutor (it is a creature) can put it on top of your library for the next Egg. Natural Order cannot find it, because it is colorless.

**Weak points.** It has no indestructible, so creature removal, enchantment removal and wipes kill it. Chapter I has already resolved by then. Nothing in the deck saves it from the sacrifice after chapter IV.

### Why cut Blightsteel Colossus (line C)

1. **Wincon is the only role with spare copies.** The deck has 5 wincons against a target of 3. Ramp (9 of 10), card draw (8 of 10), spot removal (7 of 8) and tutors (3.5 of 4) are all short. After line A, the wincons are Galactus, Craterhoof, Ghalta and Mavren, Etali and Blightsteel. Craterhoof and Ghalta are the strongest finishers, and Galactus is line A. That leaves Blightsteel or Etali.
2. **Blightsteel's damage is poison.** Its hits add poison counters, so they do not add to the life damage from the team, Craterhoof or Mega Flare. Every other threat in the deck works on life totals.
3. **Bahamut takes Blightsteel's place for Enlightened Tutor.** Each is a bomb that Enlightened Tutor can put on top for the next Egg.
4. **Combos.** Blightsteel is in no included Spellbook line. It is in 3 near-misses, and each one needs a card outside the 99 (Cybermen Squadron, Chandra's Ignition, Blade of Selves). Bahamut is in none. The Combo Lab loses nothing.
5. **EDHREC (Atla page, 2026-09-29).** Blightsteel is on 16.3% of Atla decks, and Etali on 41.5%. Bahamut is not on the page.
6. **The numbers move a little.** Each figure compares the 99 after line A with the same 99 after lines A and C:
   - Spot removal: 7.5 to 8.5 (target 8), with Bahamut tagged `removal-spot` / `wincon`.
   - Role coverage score: 96 to 98. Global health: 79 to 79.
   - Average nonland mana value: 4.26 to 4.21.
   - Mean printed power of a revealed creature: 5.89 to 5.81 (27 creature cards both ways). Blightsteel's 11 counts here, but its damage is poison.
   - The goldfish sim does not model Saga chapters, so I expect it to read flat.

**What you lose with C.** Blightsteel is an indestructible 11/11 with trample and infect. Under Zopandrel it deals 22 poison, so one hit kills one opponent. It survives destroy wipes and damage wipes. If it would go to the graveyard, it shuffles back into the library.

### Line D (alternative): cut Etali, Primal Conqueror instead

D keeps Blightsteel's one-hit poison kill. It loses Etali's free spells. When Etali enters, each player exiles cards until a nonland card, and you may cast all of those cards for free. Etali is legendary, so Annie Joins Up doubles that: up to 8 free spells in a four-player game. Mean printed power of a revealed creature: 5.89 to 5.96.

I recommend C over D. Etali's reveal adds cards and life damage that the rest of the deck builds on. Blightsteel's reveal adds poison, which nothing else in the deck adds to.

### Cuts I did not offer

- **Krosan Grip.** It is one of five answers to Grafdigger's Cage or Rest in Peace, with Aura Shards, Force of Vigor, Beast Within and Boseiju. Each of those hosers shuts off Atla's reveals, so Bahamut would not arrive to answer it. Curve health would fall from 41 to 34.
- **Llanowar Elves.** Line B already offers this slot for Galactus. Cutting it for both cards would slow the start twice.

### The new card: approve at most one of A and B, and at most one of C and D

- **A (recommended):** +Galactus, Devourer of Worlds / −Zacama, Primal Calamity. Unchanged from my first comment.
- **B:** +Galactus / −Llanowar Elves. Unchanged.
- **C (recommended):** +Summon: Bahamut / −Blightsteel Colossus.
- **D:** +Summon: Bahamut / −Etali, Primal Conqueror.

The two pairs are independent. A with C is my recommended package. It is one swap round (round 2 since the round-5 reset), so Trigger 2 does not fire. The Game Changer count stays at 7, and the deck stays bracket 4.

### On apply (for C or D, after approval)

1. In `deck.json`, swap the decklist entry. Bahamut gets `primary_role: removal-spot` and `secondary_role: wincon`. Add a Bahamut highlight. Remove the cut card from every prose place that names it: the "Hatch and Swing" win condition ("Blightsteel Colossus as 22 infect"), `guideContent.strategyOverview`, the deck categories and the "Zopandrel + Xenagos on one body" synergy (for D, the same places that name Etali). Add a source entry that records that you own Bahamut (board, 2026-10-20) although `Owned.csv` does not list it yet.
2. Add Bahamut to `card-metadata.json`.
3. Run `validate_deck_json`, `compute_tokens`, `refresh_card_pool`, the metrics script, the sim and the three Combo Lab scripts.
4. Bump the loader cache key, commit and push.

### Housekeeping

- I withdrew the stale "Connect Anthropic" card from 14:30Z (`e169c01f`). You do not need to dismiss it.
- A correction to my first comment: it said Galactus is not on the Atla EDHREC page. The 2026-08-22 snapshot lists it at 3.3% (120 of the 3,640 Atla decks made since its release). The 2026-09-29 list does not include it. This changes nothing in line A.

Numbers: `agents/ceo/analysis/dec1215/projection2.py` (writes nothing).

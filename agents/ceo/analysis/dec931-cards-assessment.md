# DEC-931 — Cards assessment (20 Reality Fracture cards)

**Outcome:** 10 swaps proposed across 7 decks, 8 cards deferred with notes, 6 cards rejected with reasons. No `deck.json` was edited. Every oracle text below comes from Scryfall (collection lookup on 2026-09-29); every deck number comes from the repo (`deck.json`, `metrics.json`, `manabase_check.py`, refreshed `candidates.json`).

Facts that apply to all 20 cards:

- All 20 are Reality Fracture (set `fra`). Scryfall release date is 2026-10-02, and Scryfall already lists them as Commander-legal. Scryfall has no rulings for any of them yet.
- None of the 20 is a Game Changer (checked against `data/game-changers.json`).
- Ownership (`priv_data/Owned.csv`): only Haunted Ridge is owned (1 copy, set WHO), and that copy sits in eternal-agony. The other 19 are not owned.
- Candidate pools refreshed today for eternal-harvest, broodfire-hatchery, tidal-legion, titan-convergence, stampede-acres, gandalf-party-guest, grave-dividends, verdant-tide. Three target cards surfaced: The Theorist (tidal-legion #185), Emrakul, the Exigent Doom (titan-convergence #148), Vraska, Soul of Stone (gandalf-party-guest #125). The scorer does not model opponent-scaled passive draw or cast-trigger land untaps, so low ranks are expected for these three.
- Prices are information only (Scryfall EUR, 2026-09-29): The Theorist 19.73, Emrakul 17.11, Darklight Phoenix 9.83, Omnipresence 4.29, Verdant Kraken 2.78, Haunted Ridge 2.38, Overgrown Farmland 1.66, Overwrite 1.52, Loyal Tutor 1.02; the rest are under EUR 1.

## Proposed swaps (board accepts or blocks each line)

### A. tidal-legion: + The Theorist, Jace Beleren / − Quick Study

- Oracle: 2UU planeswalker, loyalty 3. "At the beginning of each opponent's draw step, you draw a card." +1: 1/1 blue Illusion. −2: for each opponent, return up to one artifact or creature that player controls to hand. −6: draw three, then counters.
- Trigger frequency (DEC-477): the passive fires on opponents' turns, so ×3 per turn cycle. Three free cards per cycle for one 4-mana permanent.
- Namor: the cost has two blue pips, so casting it creates 2 Merfolk tokens. The Illusion tokens are not Merfolk and do not grow Namor.
- The −2 is opponent-scaled: it bounces up to three permanents at once.
- Protection: tidal-legion runs 13 counterspells and makes 1/1 chump blockers every turn, which is the right shell for a 3-loyalty walker. The Theorist is not a Game Changer, so the deck stays at 3 GC (the DEC-467 B3+ cap).
- Cut: Quick Study ({2}{U} instant, draw two). One blue pip, one-shot, no board presence. The Theorist replaces it with a repeating draw engine at the same colour weight. DEC-468 rejects and defers do not include either card.
- Swap-round counter: DEC-468 reset tidal-legion to 0; this is round 1.

### B. gandalf-party-guest: + Vraska, Soul of Stone / − Storm-Kiln Artist

- Oracle: URW 3/3 Legendary Creature — Gorgon **Wizard**. "Artifact creatures you control have vigilance. Whenever you cast a noncreature spell, create a 1/1 colorless Sculpture Treasure artifact creature token with '{T}, Sacrifice this token: Add one mana of any color.'"
- Gandalf, Party Guest reads "X is twice the number of legendary Wizards you control." Vraska is a legendary Wizard, so she adds 2 to Gandalf's free-cast ceiling every combat.
- The deck has 36 noncreature spells plus Gandalf's free cast each turn. Every one of them now makes a body that is also a Treasure. Harmonic Prodigy doubles Wizard triggers, so with Prodigy out each spell makes two tokens.
- Cut: Storm-Kiln Artist ({3}{R} Dwarf Shaman, Magecraft: Treasure on instant or sorcery). Vraska costs one less, triggers on every noncreature spell (artifacts and enchantments too, not only instants and sorceries), leaves a creature behind, and counts for Gandalf. Storm-Kiln is not a Wizard and does not count.
- Swap-round counter: gandalf-party-guest has had DEC-547 (2 rounds), DEC-570, DEC-687 since its last assessment that I can see in the log; count against the last assessment baseline on apply. Trigger-2 has probably already fired.

### C. titan-convergence: + Emrakul, the Exigent Doom / − It That Betrays

- Oracle: {10} 12/12 Legendary Eldrazi. "When you cast this spell, untap all lands you control. Flying, trample. Ward—Sacrifice three permanents. {3}, Exile this card from your hand: Target land gains '{T}: Add {C}{C}' until this card is cast from exile. You may cast this card for as long as it remains exiled."
- Zhulodok gives "Cascade, cascade" to colorless spells with mana value 7 or more **cast from your hand**. Emrakul cast from hand at MV 10 cascades twice. Emrakul cast from exile via its own ability does **not** cascade (not cast from hand). Note this in the deck guide if accepted.
- The cast trigger untaps all lands. With Urza's Tron (7 mana from 3 lands), Eldrazi Temple, Ancient Tomb and Shrine of the Forsaken Gods in the deck, the untap refunds most or all of the 10 mana on the same turn, before the two cascades resolve.
- The hand-exile mode is a 3-mana ramp piece (one land gains {T}: Add {C}{C} for the rest of the game, like a second Eldrazi Temple) that also protects Emrakul from discard and wheels.
- Cut: It That Betrays ({12} 11/11, annihilator 2, steals nontoken permanents opponents sacrifice). Same cascade payload (both are MV ≥ 7), but Emrakul costs 2 less, refunds its own mana, is evasive, and has a mode when you cannot reach 10. It That Betrays' steal clause only fires off opponents' sacrifices (mostly our own annihilator triggers).
- The deck's `gaps[]` (card-draw, removal-spot, removal-board, recursion) are not touched by either card.
- Swap-round counter: two DEC-467 rounds since the DEC-394 relabel; this would be round 3, so Trigger-2 fires. Count against the last assessment baseline on apply.

### D. stampede-acres: + Verdant Kraken / − Frontline Rush

- Oracle: {4}{G}{G}{G} 6/6 Plant Kraken. "At the beginning of each player's upkeep, you create a 3/3 green Forest Tentacle land creature token. (It has '{T}: Add {G}.' It's affected by summoning sickness until your next turn.)"
- Trigger frequency: **each player's** upkeep, so ×4 per turn cycle under the 4-player model.
- Each token is a land entering the battlefield. That is landfall for three cards already in the deck: Felidar Retreat (2/2 Cat or team +1/+1 and vigilance), Springheart Nantuko (Insect or a copy), Scute Swarm (1/1 Insect, or a Scute Swarm copy with six or more lands). Four landfall triggers per cycle from one permanent.
- Each token is a token creature. Anointed Procession and Mondrak, Glory Dominus double it. Baylen's abilities say "Tap two/three/four untapped tokens you control" — that is a cost of Baylen's ability, not the token's own {T} ability, so summoning sickness does not stop it (CR 302.6 only restricts the creature's own {T} abilities). Kraken tokens fuel Baylen the turn they arrive.
- After sickness, each token also taps for {G}: the card ramps every turn.
- Colour: GGG. Stampede's Karsten count is G 23.0 against a 14 requirement (`manabase_check.py`), so the pips are covered.
- Cut: Frontline Rush ({R}{W} instant: two 1/1 Goblins, or +X/+X to one creature). Lowest-ceiling token maker in the deck.
- Swap-round counter: DEC-581 reset stampede to 0; DEC-685 (a5832e2) and DEC-929 (0b4dd9f) are rounds 1 and 2. **Any accepted line in D, E or F makes round 3 and fires Trigger-2**; I will file the re-assessment issue on apply.

### E. stampede-acres: + Rockfall Vale / − Jungle Shrine

- Rockfall Vale: "This land enters tapped unless you control two or more other lands. {T}: Add {R} or {G}." Untapped from the third land drop onward. EDHREC inclusion for Baylen: 20.9% (`priv_data/edhrec/stampede-acres.json`).
- Jungle Shrine is flagged by `manabase_check.py` as one of two lands that always enter tapped. Dropping it moves W from 27 to 26 sources (requirement 18), and R from 19 to 20. All three Karsten counts stay clear.

### F. stampede-acres: + Overgrown Farmland / − Path of Ancestry

- Overgrown Farmland: "This land enters tapped unless you control two or more other lands. {T}: Add {G} or {W}." EDHREC inclusion for Baylen: 27.0%.
- Path of Ancestry is the other always-tapped land in stampede. Its scry needs a spell that shares a type with Baylen (Rabbit Warrior); the deck has no other Rabbits, so the scry almost never fires. R drops from 19 to 18 sources (requirement 13). Still clear.

### G. broodfire-hatchery: + Identity Echo / − Rishkar's Expertise

- Oracle: {2}{R} Enchantment. "{3}{R}: Exile target creature or planeswalker you control. Reveal cards from the top of your library until you reveal a creature or planeswalker card. Put that card onto the battlefield and the rest on the bottom of your library in a random order. Activate only as a sorcery."
- This is Atla's hatch effect on a permanent that is not Atla. Exile an Egg token or a mana dork, flip the next bomb. Sorcery speed and 4 mana per flip, so it is slower than the altars, but it does not need Atla on the battlefield.
- Commander-dependency check (DEC-474 L8): under Darksteel Mutation or Imprisoned in the Moon, Atla stays on the battlefield as an inert permanent and the deck's whole plan stops. Identity Echo keeps the plan running, and it also answers the lock directly: a mutated Atla is still a creature you control, so exiling her sends her to the command zone (the commander replacement applies to exile) and you recast her. Broodfire currently has no other answer of this shape; its `gaps[]` entry is recursion 0/2.
- Permanent type (DEC-474 L10): an enchantment engine dodges creature removal and wipes.
- Cut: Rishkar's Expertise ({4}{G}{G} sorcery: draw cards equal to greatest power, free-cast MV ≤ 5). One-shot draw at 6 mana in a deck that already runs Garruk's Uprising, Guardian Project, Shamanic Revelation, Sylvan Library, Skullclamp, Idol of Oblivion and Caretaker's Talent for cards.
- Swap-round counter: the DEC-574 note says the next approved round trips Trigger-2 for broodfire. Any accepted line in G or H fires it.

### H. broodfire-hatchery: + Rockfall Vale (second copy) / − Warstorm Surge

- `manabase_check.py`: broodfire has 36 lands against a 40.9 target, Karsten G 21.0 against a 20 requirement (the tightest in the fleet among these decks). EDHREC inclusion for Atla: 30.6%.
- This line adds a land (36 → 37) rather than swapping a land, because the land count is the deficit. Rockfall Vale adds a G and an R source untapped from turn 3.
- Cut: Warstorm Surge ({5}{R}). It is the third ETB-damage payoff behind Terror of the Peaks and Purphoros, and the most expensive. The Hatch-and-Burn win condition keeps two payoffs plus Solphim.
- If the board prefers to keep Warstorm Surge, the alternative cut is Guardian Project; say so on the line.

### I. eternal-harvest: + Darklight Phoenix / − Forsaken Miner

- Oracle: {3}{B} 3/2 Phoenix. "Flying, haste. At the beginning of combat on your turn, if two or more creatures died this turn, return this card from your graveyard to the battlefield."
- Loop each turn: in the first main phase, sacrifice Phoenix and one other creature to a free outlet (Ashnod's Altar, Phyrexian Altar, Altar of Dementia, Yawgmoth, Warren Soultrader, Greater Good). Two creatures have died this turn, so Phoenix returns at beginning of combat and attacks for 3 in the air with haste. Repeat next turn.
- Payoff: two death triggers every turn for free. That is 2 Meren experience counters, 2 Blood Artist / Zulaport Cutthroat / Bastion of Remembrance drains (each hits all three opponents), and Drivnod doubles all of them. It also feeds Sephiroth's four-deaths-in-a-turn clause.
- Any creature death counts, including tokens and opponents' creatures. Meren's end-step return is not used up on Phoenix, so Meren still returns something else.
- Skullclamp note: Phoenix is 3/2; Skullclamp makes it 4/1 and does not kill it. Use the altars, not the Clamp, for the loop.
- Cut: Forsaken Miner ({B} 1/1, can't block, returns from graveyard for {B} when you commit a crime). Eternal-harvest commits few crimes (Assassin's Trophy is the main one; reanimation spells target our own graveyard and are not crimes), so the Miner's return clause is rarely live. Phoenix is a recurring body with a condition the deck meets every turn.
- Swap-round counter: DEC-558, DEC-571, DEC-572 and DEC-929 have all touched this deck; count against the last assessment baseline on apply.

### J. hoard-and-bleed: + Haunted Ridge (second copy) / − Foreboding Ruins

- Haunted Ridge: "This land enters tapped unless you control two or more other lands. {T}: Add {B} or {R}." EDHREC inclusion for Smaug: 42.3%. The owned copy is locked in eternal-agony, so this is a second copy.
- Foreboding Ruins enters untapped only if you reveal a Swamp or Mountain card from hand. Hoard-and-bleed has 10 basics in 38 lands, so the reveal fails often after the first turns. Haunted Ridge is untapped from the third land onward with no card requirement.
- Manabase health is already 91, so this is a small tempo gain, not a fix. Low priority.
- Swap-round counter: DEC-930 reset hoard-and-bleed to 0 at 723ae74; this is round 1.

## Deferred (no swap now, note on file)

- **Dark Matter Manipulator** ({B} 1/2, ETB mill three, +2/+0 per seven cards in graveyard) for eternal-harvest. A good Meren fodder body: at 1 experience Meren returns it every end step for mill three per turn. Deferred because Forsaken Miner is the only fodder slot weaker than it, and line I takes that slot. Next in line if another slot opens.
- **Liliana the Repentant** ({1}{B} 2/2; mill two whenever another creature or planeswalker you control enters; Exhaust {5}{B} reanimate once) for eternal-harvest. Real graveyard fuel (Bitterblossom upkeep tokens, dorks, Meren returns each add a mill two), but the 6-mana one-shot reanimate is slow and the deck already fills the yard with Buried Alive, Entomb, Overlord of the Balemurk, Colossal Grave-Reaver and Altar of Dementia. No slot weaker than her that is not already taken.
- **Vraska, the Cutting Glare** ({B}{B}{G} 4/4 deathtouch; ETB if you control six or more lands, destroy target permanent an opponent controls, they create a Treasure) for eternal-harvest or creeping-corruption. Meren returns her (MV 3) for a Vindicate every end step once the land gate is met, but eternal-harvest runs 35 lands and sees about 4.6 lands in its first 13 cards before ramp (my estimate), so the gate is under 50% on turn 6. The current suite (Assassin's Trophy, Toxic Deluge, Reclamation Sage, Haywire Mite, Plaguecrafter, Massacre Wurm, Deadly Rollick) covers the hoser classes without a gate. Revisit if the deck goes to 37+ lands.
- **Overwrite the Multiverse** ({4}{B}{B} sorcery: exile all creatures, then Empower Jace X where X is the number exiled) for eternal-agony. A 6-mana exile-all with a Jace token that draws about three cards over three turns (X is around 10 on a 4-player board). Eternal-agony already holds Blasphemous Act and Toxic Deluge, and its card-draw gap is better served by cheaper draw. Third-wipe slot, not now.
- **Repurposed Enforcer** ({1}{W} 3/2; on attack, Empower Jace X where X is creatures you control) for anvil-chorus. With 6 to 10 creatures each attack loads 6 to 10 loyalty on the Jace token, and the token's "−3: Draw a card" then pays out 2 to 3 cards per attack. Own-attack gated (×1 per cycle), the Enforcer is a Human Soldier (no Fíli Dwarf token), and a 3/2 attacker into three opponents' boards dies often. Value is real but not above the current slots.
- **Overgrown Farmland** for creeping-corruption, slivers, hidden-legion. In the 4- and 5-colour decks the tapped tri-lands and fetchable typed duals do more work than a 2-colour slow land. Stampede-acres (line F) is the home.
- **Verdant Kraken second home: verdant-tide.** Eladamri can cheat it from hand or top, and the tokens are Forests (Roiling Canopy would trigger on each) and Craterhoof bodies. Stampede-acres (line D) gets the copy because of the landfall and Baylen interactions; add a second copy for verdant-tide only if the board wants two.
- **Emrakul, the Exigent Doom second home: broodfire-hatchery.** Hatching Emrakul off an Egg gives a 12/12 flying trample ward body but skips the cast trigger. Worldspine Wurm (15/15 trample) already fills that role. Titan-convergence (line C) is the home.

## Rejected (with reason)

- **Jace, Reality Sculptor** as a tidal-legion alternate win. Verified text: loyalty 5. "+1: Empower Jace X, where X is the number of Islands you control." "0: Exile all but the bottom card of each opponent's library. Activate only if there are twenty-five or more loyalty counters among Jaces you control." Empower Jace puts the X counters on a **separate Jace token** (Token Planeswalker — Jace, enters with 0 loyalty, "−1: Surveil 1", "−3: Draw a card"; not legendary, so no legend-rule clash). Jace himself only gains the +1.
  - Tidal-legion has 28 Islands in 37 lands (27 basics plus Mystic Sanctuary), so about 5 Islands on the battlefield on turn 6.
  - Loyalty path, X = 5 (Jace + token): turn cast 6+5 = 11; next 7+10 = 17; next 8+15 = 23; next 9+20 = 29. The 0 becomes legal on the fifth turn Jace is on the battlefield. With X = 7 it is the fourth turn (13, 21, 29). With X = 10 it is the third turn (16, 27). The Theorist (line A) adds one loyalty per turn to the total and shortens nothing by a full turn in the common cases.
  - The 0 does not win by itself. Each opponent keeps one card, draws it at their next draw step, and loses only when they must draw from an empty library, two of their draw steps later. Cephalid Coliseum (in the deck, threshold needed) can target one opponent for three draws and end that one player at once. Nothing in the deck forces the other two to draw.
  - Total: about six turns from cast to win, on a 5-mana planeswalker that has to survive three opponents' attacks with only its −3 (attackers get −5/−0 until your next turn) as defence. Tidal-legion's existing wins (Namor commander damage, lord-boosted Merfolk alpha) close faster and use the same mana. Reject as a win condition. The only Namor synergy is two Merfolk tokens on cast.
- **Stinging Vitriol** ({B}{R} sorcery: 2 damage to target opponent, they reveal hand, you pick a nonland card, they discard). A one-for-one against one of three opponents. It is a sorcery on our turn, so it never triggers Valgavoth (his trigger is "during each of their turns"), and it is not a Treasure spell for Smaug. Reject fleet-wide.
- **Puppet Crafting** ({1}{G} Aura: enchanted artifact or non-Aura enchantment becomes a 5/5 Construct creature; {4}{G} regrowth). No green deck in the fleet animates rocks or enchantments as a plan; a 5/5 Sol Ring is a random threat, not a synergy. Reject.
- **Loyal Tutor** ({W} instant: search for a planeswalker, put it on top of your library). It costs your next draw, and the white decks hold one or two planeswalkers each (the-white-forge: Karn, the Great Creator and Tezzeret, Cruel Captain; stampede and broodfire: Elspeth, Storm Slayer; creeping-corruption: Vraska, Betrayal's Sting). A 1-mana top-deck tutor for a one- or two-card target set does not beat the existing tutors. Reject.
- **Omnipresence** ({5}{G}{G}{G} enchantment: cast spells with MV ≤ creatures you control from hand for free). Eight mana. Verdant-tide's Eladamri already casts creatures from the top of the library, Omnipresence only frees spells from hand, and the deck makes 15+ mana from Priest of Titania, Marwyn and Elvish Archdruid by the time it could resolve this; The Great Henge already fills the free-cast role. Stampede-acres has the same win-more profile. Exponential-growth is out: a spell cast without paying its mana cost has X = 0, so the Hydras would enter dead. Reject fleet-wide.
- **Roiling Canopy** for verdant-tide. Type line is "Land" only, not Forest, so Fabled Passage, Nature's Lore, Three Visits and Skyshroud Claim cannot find it and it does not add to any Forest count. It enters tapped, and its trigger (+3/+3 to one creature when a Forest enters with five other Forests) is one combat trick per land drop. `manabase_check.py` puts verdant-tide at 34.7 lands against a 40.1 target; the fix is more untapped lands (a Snow-Covered Forest, or the owned Boseiju, Who Endures), not a tapped utility land. Reject.

## Hygiene and follow-ups

- `refresh_card_pool.py` rewrote `candidates.json` and the timestamp fields of `metrics.json` for the eight decks listed above. This is the DEC-90 pre-review refresh, not a deck change. I have not committed it; it goes in with the apply commit.
- On apply, for every accepted line: `refresh_card_pool.py`, `compute_tokens.py` for the decks whose token makers change (Verdant Kraken adds the Forest Tentacle token, Vraska Soul of Stone the Sculpture Treasure, The Theorist the Illusion; Frontline Rush and Storm-Kiln Artist leave), the three Combo Lab artifacts, `validate_deck_json.py`, the sim rerun, and the guide-prose sweep for cut cards (It That Betrays appears in the Annihilator Lockout text; Warstorm Surge appears in Hatch-and-Burn).
- Trigger-2 re-assessment issues to file on apply: stampede-acres (round 3), broodfire-hatchery (DEC-574 note). Count titan-convergence, gandalf-party-guest and eternal-harvest against their last assessment baselines and file if they reach 3.
- The cards release 2026-10-02. Nothing physical happens before then.

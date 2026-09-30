## DEC-935 — Broodfire Hatchery combat remake: proposal (nothing applied)

**Recommendation: keep the Egg engine, remove the enters-the-battlefield damage layer and the Mirror Entity combo, and put 9 combat amplifiers in their place.** Nine swaps below, one verdict per line on the item-verdict card. No file has changed. Tier 2, CEO-executed under the DEC-461 standing exception (card review).

### 1. Design in one paragraph

Atla stays the same engine: an Egg dies, a bomb enters. What changes is what the bomb does next. Today the bomb enters and Warstorm Surge, Terror of the Peaks, Purphoros and Solphim convert its arrival into damage. After the remake the bomb enters with haste and attacks, and the untap-and-extra-combat cards turn one hatch into two or three attack steps. The loop the board asked for is: sacrifice an Egg in main phase 1 or at the start of combat, the hatched creature has haste (Rhythm of the Wild, Hammer of Purphoros, Xenagos, or Palani's Hatcher with Maskwood Nexus, which makes every creature a Dinosaur), it attacks; Aurelia, Combat Celebrant or Tifa untap every creature you control, which includes Atla, so you pay {2} and tap her again for a second Egg, kill it with a free outlet, and the new bomb attacks in the extra combat. Xenagos and Zopandrel double power on the way in.

Two things I deliberately keep. The five free outlets (Ashnod's Altar, Phyrexian Altar, Goblin Bombardment, Skullclamp, High Market) are the hatching speed. The Thornbite Staff + Ashnod's Altar loop stays because its output is now a combat kill: every creature in the library hatches, and with a haste source they all attack.

### 2. Swap checklist (9 lines)

Each add was oracle-verified on Scryfall this heartbeat. "Free copy" means owned and not in any other deck (brewing decks lock too, DEC-544 rule). Trigger frequencies use the DEC-477 four-player basis.

- [ ] **ADD Xenagos, God of Revels / CUT Warstorm Surge** — at the start of your combat one creature gains haste and +X/+X where X is its power. This is the "double power" the board named, on an indestructible enchantment (creature only at devotion 7). Fires ×1 per turn cycle. A hatched Worldspine Wurm attacks as a 30/30 trampler. Not owned. Enlightened Tutor finds it (it is an enchantment).
- [ ] **ADD Rhythm of the Wild / CUT Terror of the Peaks** — riot gives every nontoken creature haste on entry, which covers every hatch. Also stops counterspells on the creatures you cast. EDHREC 51% on the Atla page; deferred at DEC-934 only because the deck was not a combat deck. Not owned.
- [ ] **ADD Zopandrel, Hunger Dominus / CUT Solphim, Mayhem Dominus** — a 4/6 reach body Atla can hatch that doubles power and toughness of your creatures at the start of each combat. Fires ×4 per turn cycle (your combat and each opponent's), so it also doubles your blockers. Solphim only doubles noncombat damage, which the remake removes. Not owned.
- [ ] **ADD Aurelia, the Warleader / CUT Purphoros, God of the Forge** — a hatchable 3/4 flyer with haste. On her first attack she untaps all your creatures (Atla included) and adds a combat phase. Fires ×1 per turn cycle. Not owned.
- [ ] **ADD Combat Celebrant / CUT Mirror Entity** — 3 mana. Exert on attack: untap all other creatures and add a combat phase. Cheapest extra combat in the colours, and the untap includes Atla. Free copy owned. Mirror Entity leaves because its value here was the X=0 "kill the board, hatch the library" combo line, which is the play pattern the board wants to leave.
- [ ] **ADD Tifa, Martial Artist / CUT Idol of Oblivion** — 4-mana 4/4 Naya legend. Whenever one or more creatures with power 7 or greater deal combat damage to a player, untap all your creatures and, in the first combat of your turn, add a combat phase. Nine of the deck's bombs have power 7 or more. Free copy owned. Idol was the weakest draw piece (EDHREC 7.9%) and only untaps on our turn.
- [ ] **ADD Ghalta and Mavren / CUT Birthing Pod** — 12/12 trample for 7 that Atla can hatch. Whenever you attack, create a tapped and attacking X/X Dinosaur with trample, X = greatest power among the other attackers. EDHREC 49%; rejected at DEC-544 as attack-gated, which is now the plan. Fires ×1 per turn cycle. Not owned. Pod leaves because the bombs sit at mana value 7 to 12, so the chain never lines up, and the deck keeps five other tutors.
- [ ] **ADD Karlach, Fury of Avernus / CUT Chord of Calling** — 5-mana 5/4. In the first combat of the turn, untap all attackers, give them first strike, and add a combat phase. Fires ×1 per turn cycle. Not owned. Chord leaves because tutor coverage is saturated (score 120) and the deck keeps Worldly, Enlightened, Eladamri's and Natural Order (Natural Order can sacrifice an Egg as its cost, which also hatches).
- [ ] **ADD Hammer of Purphoros / CUT Blasphemous Act** — 3-mana haste anthem on an enchantment artifact, the second global haste source next to Rhythm. Free copy owned. Blasphemous Act leaves because a combat deck is the one that loses most to a symmetric 13-damage wipe; Winds of Abandon (overload) and Apex Altisaur stay as the one-sided answers. Alternative cut for this line if the board wants to keep the wipe: Shamanic Revelation (projection below).

### 3. Numbers (zero-write projection, `agents/ceo/analysis/dec935-projection.py`, same inputs as the DEC-934 baseline)

| Measure | Today | 9 swaps (cut Blasphemous Act) | 9 swaps (cut Shamanic Revelation instead) |
|---|---|---|---|
| global_health / normalized | 85 / 87 | 81 / 85 | 82 / 84 |
| role_coverage | 102 | 95 | 98 |
| curve_health (avg MV) | 74 (3.94) | 68 (3.98) | 61 (4.05) |
| interaction_density | 120 | 114 | 120 |
| gameplan_cohesion | 40 | 37 | 37 |
| resilience_health | 70 | 70 | 70 |
| gaps[] | 1 (recursion) | 2 (removal-board 2/3, recursion) | 1 (recursion) |
| Karsten sources G / R / W (required) | 22/20, 17/13, 17/14 | 22/14, 17/16, 17/14 | same |

The drop is the metric model reading a strategy change, not a weaker deck: the curve target (3.5) still comes from the ramp-big-mana and aristocrats tags, three of the adds are 6–7 mana bodies meant to be hatched rather than cast, and the recursion gap is the combo-style resilience target that a `wincon_style` retag to combat will move. The red requirement rises from 13 to 16 against 17 red sources; the manabase passes but a red-source swap for a green one (Karplusan Forest is already in; a Cinder Glade over a Forest is the DEC-934 deferred land) is the first follow-up if the board wants margin.

Game Changers: no add or cut is a Game Changer. The count stays at 7 (Seedborn Muse, Aura Shards, Smothering Tithe, Worldly Tutor, Enlightened Tutor, Natural Order, Jeska's Will).

### 4. Considered and not proposed this round

Owned, free copies, deferred for a second wave once the board sees how the nine play: Breath of Fury (aura; when the enchanted creature connects, sacrifice it, move the aura, untap all, extra combat; under Maskwood Nexus the sacrificed creature is an Egg, so each loop also hatches), Akroma's Will (one-shot double strike or full protection, first pick for a protection slot), Pathbreaker Ibex (Overrun on each attack, 6 mana; behind Zopandrel), Etali, Primal Storm (EDHREC 59%; free spells on attack are card advantage, not an amplifier), Berserk, Anger, Crashing Drawbridge, Fiery Emancipation (1 free copy of 2; triple damage is the strongest amplifier in the pool, but {R}{R}{R} at 6 against 17 red sources; the board can promote it over Hammer of Purphoros if it accepts the colour risk).

Owned but locked: Aggravated Assault (shield-doctrine), Unnatural Growth (verdant-tide; also {G}{G}{G}{G}). Both would take a board decision to move a copy.

Not owned, deferred: Moraug, Fury of Akoum (landfall extra combat; 37 lands plus 3 fetches and 3 ramp spells fire it most turns), Samut, Voice of Dissent (flash haste anthem that also untaps Atla for {W}), Urabrask the Hidden, Fires of Yavimaya, Ogre Battledriver, Zetalpa, Old Gnawbone, Gishath (only six real Dinosaurs without Maskwood).

Rejected: Concordant Crossroads and Dictate of the Twin Gods (symmetric), Relentless Assault, World at War, Seize the Day, Fury of the Horde (one-shot sorceries; the deck wants its amplifiers on permanents, DEC-474 L10), Port Razer and Scourge of the Throne (damage- or life-total-gated), Godo (no Equipment), Hellkite Charger (7 mana per extra combat), Grand Warlord Radha and Neheb (mana engines the deck does not need). The DEC-934 rejects stand.

### 5. What happens after the board's verdicts

For every approved line I apply the swap, then: retag `wincon_style` combo → combat (this moves the resilience targets; I will report the before/after), keep `archetypes` as is (the playbook has no combat tag; ramp-big-mana and aristocrats still describe the shell), rewrite `guideContent`, `deckCategories`, `winConditions`, `highlights` and `synergies` for the combat plan (the current prose is built around the damage converters and the Mirror Entity lines), run compute_tokens, the three Combo Lab artifacts, the validator, the strategy-ceiling check, and a sim re-run after adding the new cards to card-metadata.json. Then the EDHREC closing diff on the final 99, the manabase audit, and a cache-key bump.

Hygiene note: `refresh_card_pool.py` ran this heartbeat and regenerated candidates.json and metrics.json for the deck (same 99, same numbers). The two files show as modified in the working tree; nothing in deck.json changed.

Files: `agents/ceo/analysis/dec935-combat-sweep.py` (owned-pool sweep), `dec935-mirror-query.py` (oracle lookups), `dec935-projection.py` (numbers above).

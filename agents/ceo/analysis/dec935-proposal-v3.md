## DEC-935 v3 — Samut analysed, lines 13–14 dropped, proposal corrected after an adversarial review

**Outcome: 13 revised lines, three of them new (Samut, Hazoret's Champion; Annie Joins Up; Rising of the Day), two earlier adds withdrawn (Hammer of Purphoros, Karlach), Elesh Norn kept.** The adversarial review found four wrong claims and three cards I had missed; every correction is listed in section 3. Verdict card 3e621816 is withdrawn and replaced by a 13-line card. Nothing is applied.

### 1. Samut, Hazoret's Champion (board's question)

Verified on Scryfall: {1}{R}, 2/2 Legendary Creature — Human Warrior Cleric, "Creatures you control have haste." Nothing else.

**Recommendation: take her as a new line (line 13), not as a replacement for a proposed add.** Reasoning:
- Haste is the plan's single point of failure. A hatched bomb without haste waits a turn. Global haste sources after the original 12 lines were only Rhythm of the Wild and Hammer of Purphoros. Chance to have seen at least one of two by turn 5 (11 cards): 21%. With three (Rhythm, Rising of the Day, Samut): 30%. Counting Enlightened Tutor (finds the two enchantments) and Worldly Tutor / Eladamri's Call (find Samut) as virtual copies: about 45%. The fallback that needs no haste at all is hatching at instant speed on the end step before your turn with Ashnod's Altar, Phyrexian Altar or Goblin Bombardment, which Seedborn Muse makes routine (Atla untaps on every opponent's turn).
- Against Hammer of Purphoros: same effect one mana cheaper and one red pip fewer (Hammer's {R}{R} at 3 was the only thing pushing the model's red requirement from 13 to 16 sources). Cost: a 2/2 body dies to wipes and pings where Hammer needed artifact or enchantment removal. Against Rising of the Day: Rising is an enchantment and pumps 13 legendary creatures +1/+0; Samut is cheaper and, being a creature, Atla can hatch her (an enchantment never hatches).
- Against Samut, Voice of Dissent ({3}{R}{G}, flash, other creatures have haste, {W},{T}: untap another creature): the 5-drop's untap-Atla line is real, but the board asked for efficiency; the 2-drop wins the slot and Voice of Dissent stays deferred.
- So the haste layer becomes Rhythm of the Wild (riot; nontoken creatures only), Rising of the Day and Samut, plus Xenagos (one target per combat), Palani's Hatcher with Maskwood Nexus, and the own-haste bodies (Craterhoof, Aurelia, Raph & Mikey). Hammer is dropped.

### 2. Lines 13 and 14 rejected

Raph & Leo, Sibling Rivals and Fiery Emancipation are out, per the board. Their proposed cuts (Nesting Dragon, Caretaker's Talent) are reused below.

### 3. Adversarial review — what was wrong and what changed

I ran an independent reviewer over both proposals with the instruction to verify every claim against Scryfall oracle text and rulings. Findings, most severe first, with the fix applied:

1. **Xenagos timing (wrong).** Xenagos targets "another target creature" when its beginning-of-combat trigger goes on the stack, so a creature hatched in response (an Egg killed at the start of combat, or Palani's Hatcher's own beginning-of-combat sacrifice) cannot be that combat's target. Fix: hatch in main phase 1 for Xenagos, or take the next combat's trigger (Xenagos fires again at each extra combat's beginning-of-combat step). Zopandrel is untargeted and doubles whatever is on the battlefield when it resolves, so hatch-in-response works with it. Resolution order matters: Zopandrel first, then Xenagos, turns Worldspine Wurm 15 → 30 → 60.
2. **"Nine bombs with power 7 or more" (wrong).** The count is 6 today (Worldspine 15, Blightsteel 11, Apex 10, Zacama 9, Avacyn 8, Etali 7) and 8 after the lines (plus Ghalta and Mavren 12, Raph & Mikey 7). Zopandrel, Xenagos and Craterhoof lift the rest over Tifa's threshold, and Tifa herself is 7/7 when she attacks all three opponents.
3. **Elesh Norn "does nothing in combat" (wrong).** She doubles Craterhoof's trigger (+2N/+2N and trample, the deck's finisher), Palani's Hatcher (four Eggs), Etali and Apex on entry, the Vaultborn / Garruk's Uprising / Guardian Project draws, and blanks every opponent's enters-the-battlefield trigger. She stays. Raphael takes Nesting Dragon's slot instead.
4. **Blasphemous Act (overstated).** With Vigor or Avacyn on the battlefield it is a one-sided wipe (Vigor turns it into +13/+13 counters on the team). Removal-board falls to 2 of 3 without it. I still recommend the cut, because those two cards are 2 of 99 and a combat deck is the one that draws a symmetric wipe at the wrong time; Winds of Abandon (overload), Apex Altisaur and Zacama's repeatable creature kill remain. It is now line 13's cut, so the board can keep the wipe by rejecting line 13 alone. Projection for both branches below.
5. **Missed cards.** Three beat proposed adds at the same job and are now lines: Rising of the Day (owned ×3, free; replaces Hammer), Annie Joins Up (owned ×1, free; line 8, replaces the Karlach line), Samut (line 13). Also surfaced: Doors of Durin (owned ×2; a Raph & Mikey-class hatch on an artifact, "whenever you attack, scry 2, reveal the top card, creature enters tapped and attacking"), Windcrag Siege (Mardu mode doubles every trigger caused by an attacking creature), Wulfgar of Icewind Dale (same, on a body), Berserkers' Onslaught and True Conviction (double-strike anthems on enchantments), Unnatural Growth (a second Zopandrel on an enchantment). All deferred, reasons in section 6.
6. **Trigger rates (wrong on two lines).** Xenagos and Ghalta and Mavren fire once per combat phase on your turn, so ×2–4 per turn cycle under this plan, not ×1. Zopandrel fires at each combat, yours and each opponent's, and each extra combat doubles again (30 → 60 → 120 across three combats).
7. **Haste uptime not quantified.** Now in section 1. Rulings note: there is no main phase between Tifa's combats, so hatches between combats must be instant-speed (Atla plus a free outlet is fine); Aggravated Assault and a hard-cast Raphael need a main phase.
8. **"Five free outlets" (overstated).** Truly free and repeatable: Ashnod's Altar, Phyrexian Altar, Goblin Bombardment. Skullclamp costs {1} to equip and High Market is once per turn. Zopandrel and Mondrak each add a paid two-creature outlet.
9. **Birthing Pod reasoning (overstated).** The chain exists after the adds (4 → 5 → 6 → 7 → 8 → 9 all populated). The cut stands on the right grounds: sorcery speed, {1}{G/P} plus a body per use, and each rung trades a creature for a creature while Atla adds them for free.
10. **Mirror Entity reasoning (inconsistent).** The X=0 line is the same output as the Thornbite loop I keep. The sound reason for the cut: Eggs keep defender under Mirror Entity, so the deck's many bodies still cannot attack, and X above 0 shrinks the bombs. It is a bad combat pump here.
11. **Nesting Dragon needs an explicit reject line** (48% on the Atla page): rejected because its Eggs need a land drop, are red (not Natural Order fodder), and it is the one Egg engine that is neither free nor tied to Atla's untap; Raphael takes the slot.
12. **Raphael's sneak (overstated).** Sneak returns an unblocked attacker to hand and works only in the declare-blockers step of your turn; the realistic fodder is a 3/3 Dinosaur token or Combat Celebrant, never a bomb. Hard-casting him for {2}{R}{R} in main phase 1 is the normal line.
13. **Mana (ok with caveat).** With Hammer gone the model's red requirement is 13 against 17 sources. Aurelia's {2}{R}{R}{W}{W} is a hatch target, not a cast target.
14. **Unmentioned upside.** Annie Joins Up doubles every legendary creature's triggers with no Maskwood dependency: Atla hatches twice per Egg, Aurelia and Tifa each add two combats, Zopandrel doubles twice (×4), Xenagos fires twice (15 → 30 → 60), Raph & Mikey and Ghalta and Mavren trigger twice per attack. Roaming Throne stacks on top (each "additional time" adds one more).

Confirmed correct by the review: every add and cut oracle text and cost; Aurelia, Combat Celebrant and Tifa untap Atla; Rhythm's riot applies to creatures put onto the battlefield from the library (nontoken only); Hatcher plus Maskwood gives every other creature haste; Roaming Throne naming Shaman doubles Raph & Mikey under Maskwood; Tifa fires off Blightsteel's infect damage; Natural Order can sacrifice a green Egg and the death hatches; Game Changers stay at 7; ownership and EDHREC figures.

### 4. Revised lines (one verdict each on the new card)

- [ ] **1. ADD Xenagos, God of Revels / CUT Warstorm Surge** — haste and +X/+X (X = its power) to one creature at each of your beginning-of-combat steps; fires again in every extra combat. Hatch in main phase 1 to use it that combat. Not owned.
- [ ] **2. ADD Rhythm of the Wild / CUT Terror of the Peaks** — riot: each hatched nontoken creature enters with haste (or a counter); creature spells can't be countered. Not owned.
- [ ] **3. ADD Zopandrel, Hunger Dominus / CUT Solphim, Mayhem Dominus** — hatchable 4/6 reach; doubles power and toughness of your creatures at each combat, yours and each opponent's, and again in every extra combat. Not owned.
- [ ] **4. ADD Aurelia, the Warleader / CUT Purphoros, God of the Forge** — hatchable 3/4 flying haste; first attack each turn untaps every creature you control (Atla included) and adds a combat. Not owned.
- [ ] **5. ADD Combat Celebrant / CUT Mirror Entity** — {2}{R} 4/1; exert on attack: untap all other creatures (Atla included), add a combat. Free copy owned. Mirror Entity out: Eggs keep defender, and X above 0 shrinks the bombs.
- [ ] **6. ADD Tifa, Martial Artist / CUT Idol of Oblivion** — {1}{R}{G}{W} 4/4; a power-7-or-more creature connects: untap all your creatures, and in the first combat add a combat. Eight such bodies after the lines. Free copy owned.
- [ ] **7. ADD Ghalta and Mavren / CUT Birthing Pod** — hatchable 12/12 trample; each time you attack, a tapped-and-attacking X/X trampler (X = greatest power among the other attackers). Not owned.
- [ ] **8. ADD Annie Joins Up / CUT Chord of Calling** — {1}{R}{G}{W} legendary enchantment; 5 damage to a creature or planeswalker on entry, and every legendary creature's triggered ability triggers an additional time (Atla, Aurelia, Tifa, Zopandrel, Xenagos, Raph & Mikey, Ghalta and Mavren). Free copy owned. Replaces the Karlach line (Karlach deferred: fifth extra-combat source, no doubling).
- [ ] **9. ADD Rising of the Day / CUT Caretaker's Talent** — {2}{R} enchantment; creatures you control have haste, legendary creatures +1/+0 (13 legendaries after the lines). Free copy owned (×3). Replaces Hammer of Purphoros. Caretaker's Talent out: one draw per turn and a tokens-only pump; card-draw role falls to 6 of 10 (see numbers).
- [ ] **10. ADD Raph & Mikey, Troublemakers / CUT Identity Echo** — {5}{R/G}{R/G} 7/7 trample haste; each attack reveals until a creature and puts it onto the battlefield tapped and attacking (that creature was not declared as an attacker, so attack triggers do not fire for it). Not owned.
- [ ] **11. ADD Raphael, the Nightwatcher / CUT Nesting Dragon** — {2}{R}{R} 2/3; attacking creatures you control have double strike; hatchable, unlike Berserkers' Onslaught. Not owned. Nesting Dragon reject line in section 3, item 11.
- [ ] **12. ADD Aggravated Assault / CUT Shamanic Revelation** — {2}{R} enchantment; {3}{R}{R}, sorcery speed, no limit: untap all your creatures, add a combat and a main phase. Purchase (the owned copy is in shield-doctrine).
- [ ] **13. ADD Samut, Hazoret's Champion / CUT Blasphemous Act** — see section 1. Reject this line to keep Blasphemous Act.

### 5. Numbers (`agents/ceo/analysis/dec935-projection-v4.py`, zero-write, DEC-934 inputs)

| Measure | Today | 13 lines | 12 lines (keep Blasphemous Act, no Samut) |
|---|---|---|---|
| global_health / normalized | 85 / 87 | 81 / 84 | 81 / 83 |
| role_coverage | 102 | 93 | 98 |
| card-draw (count of 10) | 90 (9) | 60 (6) | 60 (6) |
| removal-spot | 75 | 81 | 81 |
| removal-board | 100 | 67 | 100 |
| curve_health (avg MV) | 74 (3.94) | 63 (3.97) | 55 (4.08) |
| interaction_density | 120 | 118 | 120 |
| gaps[] | 1 | 3 (card-draw, removal-board, recursion) | 2 |
| Karsten need / sources: R, G, W | 13/17, 20/22, 14/17 | 13/17, 14/22, 14/17 | same |

Card-draw at 6 (Sylvan Library, Skullclamp, Greater Good, Guardian Project, Garruk's Uprising, Vaultborn Tyrant) is a real gap on the model. The deck's card advantage is the hatch itself (each Egg is a free creature, and Guardian Project and Vaultborn draw on each one), which the role count does not see. If the board prefers the metric, reject line 9 and the haste layer is Rhythm plus Samut. Retagging `wincon_style` to combat after approval leaves global at 81 and raises the recursion target from 2 to 3. Game Changers stay at 7.

### 6. Deferred and rejected (with reasons)

Deferred, second wave after the 13 play: Doors of Durin (owned ×2; hatch on attack, on an artifact; behind Raph & Mikey because it hatches only when the top card is a creature after the scry), Windcrag Siege and Wulfgar (attack-trigger doublers; Annie already doubles the legendary ones), Karlach, Fury of Avernus, Samut, Voice of Dissent, Hammer of Purphoros, Unnatural Growth (buy; second doubler on an enchantment, {G}{G}{G}{G}), Berserkers' Onslaught and True Conviction (double strike on enchantments; Raphael chosen because Atla can hatch him), Moraug, Urabrask, Fires of Yavimaya, Ogre Battledriver, Zetalpa, Old Gnawbone, Gishath, Breath of Fury, Akroma's Will, Pathbreaker Ibex, Etali Primal Storm, Berserk, Anger, Hard-Won Jitte, Skateboard.

Rejected: Raph & Leo and Fiery Emancipation (board), Concordant Crossroads and Dictate of the Twin Gods (symmetric), one-shot extra-combat sorceries, Port Razer, Scourge of the Throne, Godo, Hellkite Charger, Radha, Neheb, Krang, Slash, Nesting Dragon (line 11).

### 7. After the verdicts

Apply approved lines, retag `wincon_style` combat, rewrite guide prose (17 references to Mirror Entity alone), compute_tokens, three Combo Lab artifacts, validator, strategy-ceiling, card-metadata plus sim re-run, EDHREC closing diff, manabase audit, cache bump.

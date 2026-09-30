## DEC-935 — 11 approved lines applied; the two rejected lines re-evaluated

**Applied (verdict card 5e9a7eeb):** all 11 approved swaps are in `data/commanders/broodfire-hatchery/deck.json`, the guide prose is rewritten for the combat plan, `wincon_style` is now `combat`, and the full post-swap pipeline has run (tokens, Combo Lab artifacts, validator, strategy-ceiling, card metadata, 100k-game sim, metrics, candidate pool, manabase audit, EDHREC closing diff, cache key v137). Commit follows this comment. Game Changers stay at 7.

### 1. Numbers after the swaps

| Measure | Before (c96ddb4) | After | Note |
|---|---|---|---|
| global_health / normalized | 85 / 87 | 81 / 84 | as projected |
| role coverage | 102 | 94 | card-draw 7/10, removal-board 2/3 |
| curve (avg MV) | 74 (3.94) | 63 (3.97) | three 7-drops meant to be hatched |
| interaction density | 120 | 118 | |
| gaps[] | 1 | 2 | removal-board 2/3; recursion 0/3 (combat-style target) |
| Karsten need / sources R, G, W | 13/17, 20/22, 14/17 | 13/17, 14/22, 14/17 | red requirement unchanged |
| sim deckHealth | 67.0 (B) | 65.0 (C) | comboConsistency 76 → 52, commanderIndependence 8 → 22 |
| comboLethal T6 / T7 / T8 | 46.3 / 53.5 / 59.3 | 6.0 / 8.0 / 10.6 | the Mirror Entity one-card line is gone |
| lethalProxy T6 / T7 / T8 | 8.0 / 26.1 / 49.4 | 11.4 / 31.9 / 56.5 | combat pressure up |
| strategy-ceiling | ok | ok | |

**Read the sim with care.** The goldfish model is blind to haste, extra combats, power doublers and token combat, so it cannot see most of what this deck now does; it reads the remade deck as "B3–B4 borderline" on the reality-check table (best statistic 31.9% at T7, 56.5% at T8) where the old build scored on a one-card combo it could count. If the board wants sim numbers that mean something for this deck, the fix is an engineering issue: model extra combat phases, power doublers and haste anthems in the goldfish. I can open that as a child issue on request. The deck stays tagged brewing either way.

### 2. Combo Lab

Five verified lines now: the four Atla loops (Maskwood Nexus with each free outlet; Thornbite Staff + Ashnod's Altar) and one new combat line the sync found: **Ghalta and Mavren + Aggravated Assault + Phyrexian Altar** — attack with five or more other creatures, choose the Vampire mode for X 1/1 lifelinkers, sacrifice them to the Altar for five mana, activate Aggravated Assault in the next main phase, repeat: infinite combats. The Spellbook corpus advanced during the sync (13:11 → 15:11), so the whole fleet was re-emitted on the new corpus; only this deck's included list changed. Samut, Hazoret's Champion is not in the local combo knowledge base yet (a coverage miss, harmless: the synergy builder just cannot see her).

### 3. EDHREC closing diff on the final 99 (rates fetched 2026-09-29, Atla page)

No includes. Every card at or above 40% not in the list has a standing disposition: Cultivate 63.5, Rampant Growth 55.6, Kodama's Reach 43.7 — reject, tapped-basic ramp class (DEC-544); Jungle Shrine 59.7 — reject, always tapped; Etali, Primal Storm 59.1 — defer (card advantage on attack, not an amplifier; first pick for a bomb slot); Cinder Glade 54.4, Canopy Vista 49.9, Sunpetal Grove 41.8 — defer, lands (no colour deficit; Karsten passes in all three colours); Zetalpa 51.2 — defer; Ghalta, Primal Hunger 48.5 — reject (DEC-934); Ghalta, Stampede Tyrant 46.2 — defer (hand-to-battlefield; the deck keeps its creatures in the library); Sundering Growth 45.1 — defer, interaction slot; Gishath 42.0 — defer (six real Dinosaurs without Maskwood); Swiftfoot Boots 41.9 — reject (Greaves covers Atla); Dinosaur Egg 41.6 — reject (DEC-934); Heroic Intervention 40.8 — cut at DEC-574, named override stands. Of the adds, Rhythm of the Wild (51.0%), Ghalta and Mavren (49.2%) and Annie Joins Up (34.6%) are on the page; the rest are below the page's cut-off.

### 4. Manabase audit

37 lands (36 untapped; Jetmir's Garden is the only unconditional tapped land), 3 fetches, Karsten G 22/14, R 17/13, W 17/14. The 41-land target counts the nine 7-plus-mana bombs as castable; the DEC-934 castable-mana-value argument for 37 still holds and is stronger now (three more 7-drops that are hatched, not cast). Cinder Glade over a Forest stays the first land change if the board wants it.

### 5. The two rejected lines, re-evaluated

**Line 11 — "if we cut Nesting Dragon, do we end up with too few Egg producers?"** Counting with Atla on the battlefield (she has to be, or nothing hatches):

| Egg source | Eggs per turn cycle | Needs |
|---|---|---|
| Atla | 1 on your turn ({2}); +3 with Seedborn Muse (one per opponent untap step); +1 per Aurelia / Combat Celebrant / Tifa untap; +1 per creature death with Thornbite Staff | {2} each |
| Mondrak, Elspeth | ×2 each on every Egg above (×4 with both) | — |
| Palani's Hatcher | 2 on entry, then one hatch at the beginning of every combat on your turn, extra combats included | — |
| Maskwood Nexus | every creature is an Egg; {3},{T} for a Shapeshifter Egg | — |
| Nesting Dragon | 1 Dragon Egg per land drop (about 0.8 per turn at 37 lands + 3 fetches) | a land drop |
| Raph & Mikey | a hatch per attack with no Egg at all | an attack |

So no: without Nesting Dragon the deck still makes 2 to 8 Eggs per turn cycle off Atla alone once Seedborn or a doubler is out, and Annie Joins Up / Roaming Throne turn each Egg into two or three creatures. The bottleneck is outlets and mana, not Eggs. What Nesting Dragon uniquely adds is a free Egg per land drop that also blocks (a 0/2 that dies to a chump block and hatches on the opponent's turn) and a 2/2 flier per death. That is real, and it is the only Egg source that scales with land drops for free, so I now recommend **keeping Nesting Dragon** and taking Raphael's slot from the tutor suite instead:

- [ ] **A. ADD Raphael, the Nightwatcher / CUT Eladamri's Call** — Raphael: {2}{R}{R} 2/3, attacking creatures you control have double strike; hatchable. Eladamri's Call is the one tutor that puts a creature in hand rather than on top (Worldly Tutor, which is the next hatch) or onto the battlefield (Natural Order); Enlightened Tutor covers the enchantments. Tutor role 5 → 4 (score 112 → 100, still at target), card draw untouched, Egg producers untouched.

**Line 9 — "we need card draw."** Understood: Caretaker's Talent stays, card draw stays at 7 of 10. The question left is whether the third haste anthem is worth a non-draw slot. Two team-wide anthems (Rhythm, Samut) give a 21% chance of having seen one by turn 5 on their own, about 38% counting the tutors that find them; a third anthem lifts that to 30% / 45%. The cheapest non-draw slot is the sixth protection piece (protection sits at 6 against a target of 4):

- [ ] **B. (optional) ADD Rising of the Day / CUT Clever Concealment** — Rising: {2}{R} enchantment, creatures you control have haste, legendary creatures +1/+0 (13 legendaries). Owned ×3, free. Clever Concealment is the deck's best answer to a wipe (phase the board out at instant speed, convoke), so this is a real trade: haste consistency against wipe insurance. Flawless Maneuver (free, indestructible), Avacyn and Vigor remain. If the board prefers the insurance, reject B and the haste layer is Rhythm + Samut + Xenagos + Hatcher/Maskwood.

Nothing from this section is applied; the card that follows this comment carries the two lines.

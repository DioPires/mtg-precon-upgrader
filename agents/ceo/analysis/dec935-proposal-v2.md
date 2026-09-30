## DEC-935 follow-up — Raph & Mikey added, buy-agnostic re-rank, 12 firm lines + 2 optional

**Raph & Mikey, Troublemakers goes in (line 10).** I missed it: my sweep printed the first 40 of 992 attack-trigger hits with no ranking key (the local Scryfall mirror carries no EDHREC rank), and it fell outside the window. Fixed with a targeted sweep for "reveal until a creature" and "tapped and attacking" effects plus a full pass over the Teenage Mutant Ninja Turtles set on Scryfall, which also surfaced Raphael, the Nightwatcher and Raph & Leo, Sibling Rivals. All three verified on Scryfall.

**Buy-agnostic re-rank: the original nine lines stand as written.** Each was ranked on power first; ownership decided only one tie (Hammer of Purphoros over Fires of Yavimaya, same function). Aggravated Assault moves from "locked" to a firm line now that buying a second copy is fine.

The earlier verdict card (8dfacb16) was cancelled by your comment. A new card with all 14 lines follows this comment. Nothing is applied.

### New lines (verified on Scryfall this heartbeat; trigger rates on the DEC-477 four-player basis)

- [ ] **10. ADD Raph & Mikey, Troublemakers / CUT Identity Echo** — {5}{R/G}{R/G} 7/7 trample, haste. Whenever they attack, reveal until a creature card and put it onto the battlefield tapped and attacking. That is Atla's hatch on an attack trigger, and it attacks the turn it hatches. Fires ×1 per combat, so each extra combat (Aurelia, Karlach, Tifa, Celebrant, Aggravated Assault) is one more hatch. Power 7 turns on Tifa. Under Maskwood Nexus every creature is every type, so Roaming Throne (naming Shaman) doubles both Atla's trigger and this one. Identity Echo does the same job at sorcery speed for {3}{R} per use and exiles one of our creatures to do it.
- [ ] **11. ADD Raphael, the Nightwatcher / CUT Elesh Norn, Mother of Machines** — {2}{R}{R} 2/3; attacking creatures you control have double strike. Doubles every attacker's damage and the first-strike hit connects before blockers can be reset. Sneak {1}{R}{R}: cast him during the declare-blockers step by returning an unblocked attacker, so he lands after blocks. Example with the Xenagos target: Worldspine Wurm 15/15 → 30/30 → 60 trample damage. Elesh Norn leaves because her doubling was built for the enters-the-battlefield converters; Craterhoof, Etali, Apex and Vaultborn still like her, but she is a 5-mana body that does nothing in combat.
- [ ] **12. ADD Aggravated Assault / CUT Shamanic Revelation** — {2}{R} enchantment; {3}{R}{R}: untap all your creatures and add a combat phase, as a sorcery, no limit per turn. The most reliable repeatable extra-combat piece in the colours, on an enchantment, and Enlightened Tutor finds it. The owned copy is in shield-doctrine, so this is a purchase. Shamanic Revelation is the weakest draw spell in the list (5-mana sorcery, no board effect).

Optional, board's call (both push the curve and draw scores further, table below):

- [ ] **13. ADD Raph & Leo, Sibling Rivals / CUT Nesting Dragon** — {1}{R/W}{R/W} 2/4. First attack each turn: untap one or two attacking creatures, add a combat phase. A Combat Celebrant that does not exert and survives a 1-damage ping. Nesting Dragon is a 5-mana engine that needs land drops and makes 0/2 defenders; next to five free outlets and Atla's own Eggs it is the slowest Egg source.
- [ ] **14. ADD Fiery Emancipation / CUT Caretaker's Talent** — {3}{R}{R}{R}: sources you control deal triple damage. The strongest single amplifier available: any hatched 7-power body one-shots a player with it. Cost is the colour: the deck has 17 red sources and this is a triple-pip 6-drop next to Avacyn ({W}{W}{W}) and Worldspine ({G}{G}{G}); I would pair it with a Forest → Cinder Glade swap. One free copy owned. Caretaker's Talent is the cut because its draw is once per turn and its level 3 pumps only tokens.

### Numbers (zero-write projection, `agents/ceo/analysis/dec935-projection.py`)

| Measure | Today | 9 lines | 12 lines | 12 + optional 13–14 |
|---|---|---|---|---|
| global_health / normalized | 85 / 87 | 81 / 85 | 80 / 84 | 79 / 83 |
| role_coverage | 102 | 95 | 93 | 92 |
| card-draw role (count / 10) | 90 (9) | 80 (8) | 70 (7) | 60 (6) |
| curve_health (avg MV) | 74 (3.94) | 68 (3.98) | 62 (4.00) | 57 (4.02) |
| removal-board | 100 | 67 | 67 | 67 |
| gaps[] | 1 | 2 | 2 | 3 (adds card-draw) |

Same reading as before: the curve target comes from the ramp-big-mana and aristocrats tags, and the 7-drops (Zopandrel, Ghalta and Mavren, Raph & Mikey) are meant to be hatched, not cast. Card draw after 12 lines is Sylvan Library, Skullclamp, Greater Good, Caretaker's Talent, Guardian Project, Garruk's Uprising and Vaultborn Tyrant, plus the library flips from Atla, Raph & Mikey and Etali. Game Changers unchanged at 7.

### Also seen in the TMNT pass, not proposed

Krang, Utrom Warlord (colorless 9-drop whose anthem is artifact-only; reject), Slash, Reptile Rampager (an enters-the-battlefield pinger; off plan), Hard-Won Jitte and Skateboard (single-creature double strike / haste; defer behind the team-wide sources), Sally Pride, Triceraton Commander, The Neutrinos, Michelangelo, Improviser (hand-to-battlefield on damage; the deck keeps its creatures in the library; defer).

### After the verdicts

Same pipeline as comment 539d3c63 section 5: apply approved lines, retag `wincon_style` combo → combat, rewrite the guide prose for the combat plan, compute_tokens, the three Combo Lab artifacts, validator, strategy-ceiling, card-metadata + sim re-run, EDHREC closing diff, manabase audit (with the Cinder Glade question if line 14 is approved), cache bump.

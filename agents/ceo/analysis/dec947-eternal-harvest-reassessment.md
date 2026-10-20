## DEC-947 — eternal-harvest (Meren, B4) Trigger-2 re-assessment: verdict NO CARD SWAP, one role retag

**Tier 0 (CEO-executed per DEC-461).** No deck files edited. Every number below comes from today's pipeline run (2026-10-07) or an in-memory projection; I label the projections.

### Checklist (board accepts or blocks line by line)

- [ ] **Retag Yawgmoth, Thran Physician and Priest of Forgotten Gods with `secondary_role: card-draw`** — data-accuracy fix, no card changes. Both are repeatable draw engines under the DEC-478 rule ("a permanent that draws over multiple turns qualifies"). Oracle (Scryfall, 2026-10-07): Yawgmoth "Pay 1 life, Sacrifice another creature: Put a -1/-1 counter on up to one target creature and draw a card." Priest "{T}, Sacrifice two other creatures: ... You add {B}{B} and draw a card." The goldfish sim already counts both as draw engines (13 sources, 85.9% of games have one by turn 7); the metrics role census did not. In-memory projection, no files written: role coverage 88 → 90, `gaps[]` 1 → 0, global 87/91 flat. Recommended.
- [ ] **Optional, not recommended: +Grim Haruspex / −Altar of Dementia** — offered because the issue named Haruspex as the next-in-line draw card. Projection: role coverage 88 → 90, gap closes, every other score flat. I rank it below the retag because the deck already has 12 nonland draw cards and Haruspex duplicates Liliana's static (draw per nontoken death, ×1 per death, own-board trigger, not opponent-scaled under DEC-477). Costs: Haruspex is unowned (about EUR 2.55 at DEC-572, information only); Altar of Dementia is embedded in 10 prose references and 3 Spellbook near-miss lines (0 included combos).

### Card-draw gap triage (scope item 2)

Verdict: **tag-weight artifact.** The deck has 12 nonland cards with draw text (Skullclamp, Plumb the Forbidden, Greater Good, Liliana, Braids, Black Market Connections, Simulacrum Shaper, Yawgmoth, Priest, Teval's Judgment, Archon of Cruelty, Sephiroth) plus Castle Locthwain and Nurturing Peatland. The metric counts 6.5 because only 6 carry the `card-draw` primary tag and one carries it secondary. The sim's draw-engine reliability (13 sources, median first engine on turn 1) says the deck draws fine. Line 1 fixes the census; line 2 is the fill option. DEC-572 defers re-checked: Grim Haruspex (line 2), Arcane Signet (still defer: The Soul Stone holds the rock slot, 8 nonland mana sources, sim mana adequacy "strong", Karsten passes B 26.1/20 and G 22.0/16).

### Bar check and pipeline (scope item 1)

| Item | Value |
|---|---|
| Bracket / Game Changers | 4 / 0 |
| metrics global (normalized) | 87 ±5 (91) — unchanged from DEC-945 |
| components | mana 70, roles 88, curve 96, interaction 120, cohesion 50, resilience 100 |
| sim health (100k, at da621d7) | 73.4 B — mana 73.8, threats 80.8, interaction 73.1, combo 52.5, cmd-independence 83.8 |
| strategy ceiling | ok (shell 70, payoff 44.8%) |
| Spellbook | 13 included, 73 in-CI near-misses |
| validator | green (prior run at da621d7; no deck change since) |

Bar ≥ B3+/4- holds. The sim was run at commit da621d7 on this exact 99, so I did not re-run it. Card-pool refresh: mirror current, EDHREC rates fresh (2026-10-07), candidates unchanged (200).

### Candidates top-50 and EDHREC ≥40% triage (steps 3–4, DEC-402 closing diff)

- Viscera Seer 67.4% — defer: outlet-saturated (Ashnod's, Phyrexian, Altar of Dementia, Yawgmoth, Priest, Warren Soultrader, Greater Good, Birthing Pod, Sephiroth, Fiend Artisan).
- Arcane Signet 57.6% — defer (see above).
- Accursed Marauder 54.6% — defer: unowned; Plaguecrafter fills the edict-on-a-body slot.
- Tainted Wood 54.6% — reject stands (locked to witherbloom-the-balancer).
- Grim Haruspex 49.4% — line 2.
- Carrion Feeder 47.0% — DEC-929 board cut; not reopened.
- Cankerbloom 46.3% — defer: interaction at 120% of target; Reclamation Sage and Haywire Mite already cover artifact/enchantment on recurable bodies.
- Protean Hulk 45.9% — defer: unowned; no Hulk pile in the 99.
- Syr Konrad 44.4% — defer: the one copy is locked to eternal-agony.
- Fleshbag Marauder 42.8%, Golgari Rot Farm 41.1% — DEC-572 rejects stand.
- Candidate #1 Cauldron of Essence (70.7, 32.3%) — DEC-572 board reject stands; the one copy is locked to witherbloom-the-balancer.
- Jarad, Wight of the Reliquary, Woe Strider, Umbral Collar Zealot — defer: more sacrifice outlets into a saturated suite.
- Deathrite Shaman — reject: exiles our own graveyard cards, against the reanimator plan.
- Junji — defer: Kokusho holds the Meren-loop dragon slot; Butcher of Malakir — defer: 7 MV Grave Pact copy, Drivnod already doubles Grave Pact.
- Moldervine Reclamation (31.5%, owned) — defer: enchantment-based draw-on-death is the durable form (step 10), but 5 MV with no board impact is slow for B4; revisit only if the board chooses to fill the gap and prefers an enchantment over Haruspex.
- Pitiless Plunderer, Fauna Shaman — defer: 0 free copies (owned minus all deck demands incl. brewing).
- Dread Return — defer: five reanimation effects plus Meren already.
- Remaining top-50 entries score ≤ 56.7 with no EDHREC rate (scorer filler): reject.

### Spellbook near-miss triage (scope item 4)

73 in-CI near-misses on corpus 2026-10-07T13:11. All are the same three shapes the deck already completes: Warren Soultrader + Gravecrawler + a drain payoff (we run Blood Artist, Zulaport, Bastion, Sephiroth), Yawgmoth + a counter payoff (we run the Mikaeus lines), and Mikaeus + altar + Plague Belcher. No missing card is both owned and free (Pitiless Plunderer 0 free, Cauldron of Essence locked). Verdict for all 73: retain as redundant shapes, complete none.

### Stale-reference sweep (scope item 3)

Clean. Three cards were cut across the three rounds (not five: DEC-931 cut only Culling the Weak from this deck). Carrion Feeder, Culling the Weak and Harvester of Souls appear only inside source-attribution `detail` strings that record the swaps; no highlight, synergy, win-condition or strategy text still names them.

### Checklist steps 7–11

- **Hoser coverage (7):** hate class is graveyard hate. Enchantment hosers (Rest in Peace, Leyline of the Void): Assassin's Trophy, Boseiju, Reclamation Sage, Haywire Mite. Artifact hosers (Grafdigger's Cage, Soul-Guide Lantern): the same four. Land hosers (Scavenger Grounds): Trophy, Boseiju. Sage and Mite are creature-based, so Meren re-buys them. Covered.
- **Manabase (8):** Karsten passes both colors; 4 unconditionally tapped lands (Underground Mortuary, Bojuka Bog, Hagra Broodpit, Crypt of Agadeem). Land count 36.1 vs the 39.6 formula target drives the mana score of 70, but sim mana adequacy is "strong" with 8 nonland mana sources. Defers: Exotic Orchard (opponent-dependent colors), Necroblossom Snarl (conditional tapped), Grim Backwoods (5-mana draw activation is too slow; outlet-saturated).
- **Commander dependency (9):** sim commander independence 83.8. Avacyn, Liliana, Colossal Grave-Reaver, Grave Researcher and Living Death run the sacrifice plan with Meren locked under Darksteel Mutation; Trophy, Boseiju, Sage and Mite remove the aura.
- **Permanent-type durability (10):** applied as the tiebreaker in the Moldervine Reclamation note.
- **Win-from-this-board goldfish (11):** not triggered (no wincon gap; ceiling check clean).

### On apply (after approval)

Line 1: edit the two `secondary_role` fields, run validate_deck_json, compute_deck_metrics, refresh_card_pool, bump the loader cache key, commit, push. No sim or Combo Lab change (no card moved). Line 2 (if chosen): full swap pipeline (tokens, card-metadata, sim, Combo Lab ×3, prose cleanup for Altar of Dementia). Swap-round counter resets at the closing commit either way.

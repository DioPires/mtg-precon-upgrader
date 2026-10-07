## DEC-948 — gandalf-party-guest (Arcane Convocation, Gandalf, Party Guest, 4-) Trigger-2 re-assessment: verdict NO CARD SWAP, five prose fixes, one optional land line

**Tier 0 (CEO-executed per DEC-461).** No deck files edited. Every number below comes from today's pipeline run (2026-10-07, mirror 2026-10-07T09:01) on commit 6499cab, or an in-memory projection. I label the projections.

### Checklist (board accepts or blocks line by line)

- [ ] **A — Prose accuracy fixes (five edits, no card change). Recommended.** All five are stale or wrong numbers in `guideContent` and one synergy title; the validator cannot see them because it only checks card arrays.
  1. Draw Engines: "The One Ring ... (22nd legend for Mox Amber)". Mox Amber reads "legendary creatures and planeswalkers you control" (Scryfall, 2026-10-07). The One Ring is an artifact and never feeds it. Reword to "an indestructible legendary artifact" and drop the Mox Amber claim.
  2. Mana Engine says "Mox Amber (22 legends keep it live)"; the synergy card says "Mox Amber is live off 21 legends". The true feeder count is 19 legendary creatures in the 99 (18 legendary Wizards plus Sakashima), 20 with Gandalf on the battlefield. Use 19/20 in both places.
  3. Mana Engine, Eiganjo sentence: "with 18 other legendary creatures in the 99". The 99 holds 19 legendary creatures (DEC-541 source already records 19). Change to 19.
  4. Mana Engine pip census "55U/23R/13W" is stale after DEC-687 (Force of Will) and DEC-547 (Austere Command, Narset's Reversal). `manabase_check.py` today reads U 52 / R 29 / W 17. Update the three numbers.
  5. Interaction & Protection: "Four counterspells (Force of Will ..., Mana Sculpt ..., Fierce Guardianship and Muddle's counter mode ...)". The category's four counterspells are Force of Will, Mana Sculpt, Dovin's Veto and Fierce Guardianship; Muddle the Mixture sits in Tutors & Selection. Name Dovin's Veto in the parenthetical and keep Muddle as a fifth, out-of-category counter.
- [ ] **B — Optional, not recommended: +Island / −Step Through (39th land).** Offered because the issue asked for a land-count ruling. In-memory projection, no files written: global 88 → 89 (normalized 93 → 95), manabase 70 → 78, role coverage 101 → 98 (tutor count 5 → 4), cohesion 29 → 28, curve 95 → 96, interaction and resilience flat, gaps stay 0. I rank it below "no change" because the sim says the mana is already adequate (details under Manabase) and the deck's engine is spell density: every nonland slot is a Gandalf free-cast candidate or a council body. Step Through is the least-cost cut if the board wants the land anyway: its 5-mana main mode is the weakest card text in the 99, and the wizardcycling tutor only finds Naru Meha or Dualcaster, which Mystical Tutor, Solve the Equation, Merchant Scroll and Muddle the Mixture already cover for the spell half of each combo.

Every other line of the rubric closes without a card change. Detail follows.

### Correction to the issue text

The issue says "GC count (3)". The deck holds **4 Game Changers**: Fierce Guardianship, Mystical Tutor, The One Ring, and Force of Will (DEC-687, commit 393a638, which moved the count 3 → 4 and is recorded in the deck `sources`). `check_game_changers.py --offline` today: fleet recount 0 problems, TypeScript mirror in sync (53 cards). Bracket 4- is uncapped, so no cap question arises. Austere Command is in the deck (DEC-547 round 7 add, Free-Cast Payoffs category); nothing to sweep.

### Before/after table vs the DEC-547 baseline (commit 419183f)

| Item | DEC-547 baseline (419183f) | Now (6499cab) |
|---|---|---|
| metrics global (normalized) | 88 ±2 (93) | 88 ±2 (93) |
| manabase / roles / curve | 70 / 101 / 97 | 70 / 101 / 95 |
| interaction / cohesion / resilience | 120 / 29 / 100 | 120 / 29 / 100 |
| gaps[] | 0 | 0 |
| sim health (100k games) | 76.3 A | 76.4 A |
| sim mana / threats / interaction / combo / cmd-indep | 76.9 / 98.2 / 86.2 / 57.9 / 51.2 | 77.7 / 98.2 / 86.2 / 56.7 / 51.2 |
| lethalProxy T6 / T7 / T8 | 27.8 / 53.0 / 73.4 | 6.8 / 29.8 / 60.4 |
| comboLethal T6 / T7 / T8 | 20.4 / 27.1 / 33.7 | 14.5 / 21.8 / 29.4 |
| commander cast median turn (goldfish) | 3 | 4 |

Attribution of the deltas:
- Curve 97 → 95 is DEC-687: Force of Will (MV 5) replaced Counterspell (MV 2). Board-directed; expected.
- The lethal and commander-cast drops are **the DEC-944 goldfish model change, not the three swap rounds.** The simulation committed at 311a1a4 (DEC-944 cast-priority, before the DEC-946 land swap) already reads lethalProxy 6.8 / 29.8 / 60.4, comboLethal 14.5 / 21.8 / 29.4 and commander median turn 4 on the same card list. The DEC-946 land swap then moved sim health 76.1 → 76.4 (mana 76.8 → 77.7), the only deck-driven sim movement since the baseline.
- Sim and metrics were both generated today on this exact 99 (metrics 14:38 UTC, sim 100k games), so I did not re-run them.

### Bar check and pipeline

| Item | Value |
|---|---|
| Bracket / Game Changers | 4- / 4 (uncapped) |
| strategy ceiling | ok (shell 70, payoff 21.8% comboLethal at T7) |
| validator | green, 219 card references |
| Spellbook | 13 included, 120 near-misses shown of 414, corpus 2026-10-07T13:11 |
| card pool | mirror current, EDHREC rates fresh (2026-10-07), candidates unchanged (200) |

Bar ≥ B3+/4- holds: fast mana (Sol Ring, Mox Amber, Mana Sculpt refund, six rocks), free interaction (Force of Will, Fierce Guardianship, Clever Concealment convoke, Eiganjo channel), four tutors plus a transmute, and four two-card combo engines with 13 Spellbook-verified lines.

### Manabase audit (step 8)

`manabase_check.py`: lands 37.5 (formula target 39.8), all 37.5 untapped-weighted, Karsten passes every color: R 21.7/16, U 26.7/18, W 20.0/16. The sim agrees the base works: mana adequacy "adequate", 0–1-land openers 7.9%, first-seven keep rate 90.2%, castable on curve 89.8% by turn 3 and 96.7% by turn 4, enters-tapped share 2.6% on turn 1. The 70 manabase score is the land-count term alone. Line B is the only way to move it; I defer it for the reasons above.

Land candidates reviewed (owned, free copies): Scorched Geyser (4 free) — reject, its two-basic clause is the same trap DEC-946 just removed with Prairie Stream (11 basics in 38 lands). The Grey Havens (1 free) — reject, colored mana only from legendary creature cards in the graveyard; this deck does not fill its graveyard with legends. Spectator Seating (1 free) — defer, untapped in the pod but R/W only and both colors already pass Karsten. Path of Ancestry (9 free, 58.7%), Mystic Monastery (2 free, 45.8%), Raugrin Triome (locked, 46.8%) — reject, enter tapped. Reliquary Tower (1 free, 50.3%) — defer, colorless in a 52-U-pip deck. Three Tree City, Cascade Bluffs, Battlefield Forge, Nykthos — 0 free copies.

### Candidates top-50 and EDHREC ≥40% triage (steps 3–4, DEC-402 closing diff)

Prior decisions honored (DEC-472, DEC-541, DEC-562, DEC-570, DEC-687 reject and defer lists, all on file):
- Fiery Inscription (candidate #1, 15.6%), Guttersnipe (#2), Erebor Flamesmith, Firebrand Archer, Electrostatic Field, Chandra's Emberling — reject stands (DEC-562): every included combo makes copies, and cast-gated burn never fires on a copy (CR 707.10). Fiery Inscription also tempts the Ring with zero Ring payoffs in the 99.
- The Emperor of Palamecia 63.2%, Raise the Palisade 60.8%, Alisaie Leveilleur 50.4%, Alphinaud Leveilleur 49.3%, Venat 43.5%, Full Throttle — DEC-541 rejects stand.
- Urza's Ruinous Blast 49.7% — swap-round-2 reject stands (exiles our own storm engine).
- Path to Exile 59.8% — DEC-562 defer stands; 0 free copies today (6 owned, 7 committed).
- Gandalf of the Secret Fire 37.5% (#9) — DEC-562 defer stands; unowned.
- Counterspell 53.2% — reject: the board cut it for Force of Will at DEC-687.

New this pass (all oracle-verified via Scryfall, 2026-10-07):
- Jori En, Ruin Diver 62.8% — defer: unowned. Best unowned fit on the page: 3-MV legendary Wizard (+2 to Gandalf's X) that draws on the second spell each turn, which the free combat cast makes routine. First in line if the board ever opens a purchase.
- Alania, Divergent Storm 58.1% (owned, 1 free) — defer: 5 MV legendary Otter Wizard that copies the first instant and first sorcery each turn at the price of an opponent's card. Copies trigger magecraft (Storm-Kiln, Archmage Emeritus, Deekah) but not the cast-gated payoffs (Vivi, Gandalf Goblins' Bane, Whirlwind of Thought, Archmage of Runes). Projection: −Whirlwind of Thought 88 flat, −Step Through 87. No clean cut, and the 5-drop slot already holds Gandalf the Grey and Jeskai Revelation.
- Gale, Waterdeep Prodigy 55.9% — defer: unowned; recasts graveyard instants and sorceries once per cast from hand, then exiles them.
- Frantic Search 53.0% (1 free) — defer: free off Gandalf at X ≥ 3, nets mana and a magecraft trigger, but a 2-for-2 loot advances the combo plan less than the tutor suite does. No slot.
- Improvisation Capstone 49.3%, Insurrection 43.9%, Inspired Ultimatum 40.3% (all unowned, MV 7–8) and Aminatou's Augury 41.9% (1 free, MV 8) — reject: free-cast at X = 8 needs four legendary Wizards on board, the ~15% uptime class that cut Magma Opus (DEC-547 Monte Carlo).
- Big Score 44.5% (3 free) — reject: discard as an additional cost in a deck that wants spells in hand for the combat trigger.
- Gogo, Master of Mimicry 42.0% — defer: unowned; copies Gandalf's combat trigger X times for {X}{X}, a real second-cast engine worth a look if purchased.
- Talrand, Sky Summoner 41.3% — reject: unowned token plan; Kykar and Deekah cover the body-per-spell role.
- Glamdring, Foe-hammer 40.2% (2 free) — defer: cost reduction equals equipped power, and the council bodies are small; five cost reducers already run.
- Sea of Clouds 40.5% — defer: unowned.
- Vraska, Soul of Stone (#7, 1 free) — defer: 3-MV legendary Wizard making a Sculpture Treasure per noncreature spell. Duplicates Storm-Kiln Artist on a more fragile token type (artifact creature, dies to wipes). Projection flat (88) only against Whirlwind of Thought, which the permanent-type rule (step 10) protects as the enchantment draw engine.
- Kykar, Zephyr Awakener (#14, 1 free), Ral, Crackling Wit (#16, 1 free), Harnesser of Storms (#39, 1 free) — defer: 3–4 MV engines below the incumbents; Ral would be a second Mox Amber feeder.
- Young Pyromancer, Monastery Mentor, Deluge Virtuoso, Tetsuko Umezawa — reject: token or tempo bodies outside the plan.
- Return the Favor (2 free), Reiterate (0 free) — defer: copy spells that appear once each in the near-miss list; the deck already runs Narset's Reversal in that role.
- Remaining top-50 entries (Black Bolt, Inkshape Demonstrator, Lux Artillery, Mica, Muddle the Ever-Changing and the 51.6-score block) carry no EDHREC rate and matched only the archetype pattern: reject as scorer filler.

### Spellbook near-miss triage

120 near-misses shown on corpus 2026-10-07T13:11. Three shapes: (1) more blink or copy spells for the Naru Meha / Dualcaster engines (Cloudshift, Ephemerate, Essence Flux, Splash Portal, Heat Shimmer, Saw in Half, Molten Duplication, Rite of Replication and kin); (2) alternate payoffs for the same engines (Approach of the Second Sun ×4, Chain of Smog ×3); (3) untap engines (Mind Over Matter, Peregrine Drake, Tidespout Tyrant, Hullbreaker Horror with Mox Amber). Only Splash Portal and Rite of Replication are owned with a free copy; both are redundancy for lines the deck already completes twice over (Ghostly Flicker and Displace). Verdict for all 120: retain as redundant shapes, complete none.

### Stale-reference sweep

Card names: clean. Harmonized Crescendo, Magma Opus, Prairie Stream, Counterspell, Hurkyl, Vendilion Clique, Dig Through Time, Blasphemous Act, Chaos Warp, Lotus Petal, Mystic Confluence, Baxter Building and Study Hall appear only inside source-attribution `detail` strings that record the swaps. No highlight, synergy, win-condition or category text names a cut card. The "Plains → Eiganjo" round left the basic count correct (2 Plains). Numbers: the five drifts in line A.

### Checklist steps 7, 9, 10, 11

- **Hoser coverage (7):** hate classes are (a) creature wipes and spot removal on the council, and (b) spell-tax or activated-ability locks (Rule of Law and Deafening Silence on enchantments; Cursed Totem on an artifact; Drannith Magistrate does not bite, since Gandalf casts from hand). Enchantment answers: Generous Gift, Tear, Austere Command (enchantments mode), Venser. Artifact answers: Generous Gift, Wear, Prismari Command, Flame of Anor, Austere Command (artifacts mode), Venser. Creature-side protection: Guardian of Faith, Clever Concealment, Sevinne's Reclamation, and the counters. Every permanent type that carries a hoser has at least two answers. Covered.
- **Commander dependency (9):** sim commander dependency 48.8 "moderate", self-sufficiency 87.0; only the Fury Storm line needs Gandalf. Under a Darksteel Mutation or Song of the Dryads lock, Dualcaster + Twinflame and the Naru Meha loops still win, and Generous Gift, Tear, Austere Command or Venser (bounce Gandalf to hand, then command zone) reset him. Covered.
- **Permanent-type durability (10):** applied as the tiebreaker in the Vraska and Alania notes (Whirlwind of Thought stays as the enchantment draw engine).
- **Win-from-this-board goldfish (11):** not triggered (gaps 0, ceiling check clean).

### On apply (after approval)

Line A: edit the five prose strings in `deck.json` (no card arrays touched), run `validate_deck_json`, bump the loader cache key, commit, push. No metrics, sim or Combo Lab change. Line B (if chosen): full swap pipeline (decklist, sim model land table, 100k re-sim, metrics, card pool, Combo Lab ×3, prose edit to the Tutors & Selection category). The swap-round counter resets at the closing commit either way.

planned-by: CEO / executed-by: CEO

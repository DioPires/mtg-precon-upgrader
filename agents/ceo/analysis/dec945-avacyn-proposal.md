## DEC-945 — Avacyn, Angel of Horror for Eternal Harvest (Meren, B4): recommend YES, one swap

**Tier 0 (single-card assessment, CEO-executed per DEC-461).** No deck files edited. This is a proposal; the swap waits for board approval.

### Proposed swap

- [ ] **+Avacyn, Angel of Horror / −Harvester of Souls** — Avacyn turns every nontoken creature into repeatable sacrifice fodder; Harvester is one more draw trigger in a deck that already has nine draw sources. Same slot class (6+ MV creature reanimation target), so the top end stays at 7 cards at 6+ MV.

### The card (oracle verified on Scryfall, 2026-10-07)

{5}{B}{B}{B}, 8/8 flying, deathtouch. "Whenever Avacyn or another nontoken creature you control dies, return that card to the battlefield under your control at the beginning of the next end step." Reality Fracture Commander (set code `frc`, released 2026-10-02, verified via the Scryfall sets API). Not a Game Changer; deck stays at 0 GC, bracket 4 unchanged.

### Why she fits (trigger frequency per DEC-477, vanilla 4-player model)

1. **Every nontoken creature becomes fodder up to 4 times per turn cycle.** The return trigger fires once per death, with no per-turn cap. A creature that returns at the beginning of an end step can be sacrificed again during that same end step to an instant-speed outlet, and the new trigger returns it at the next player's end step. Own end step + 3 opponent end steps = 4 deaths per creature per cycle. Instant-speed outlets in the 99 that enable this: Ashnod's Altar, Phyrexian Altar, Greater Good, Yawgmoth (1 life each), Priest of Forgotten Gods. Spore Frog and Sakura-Tribe Elder sacrifice themselves, so they need no outlet.
2. **Kill math, Kokusho.** 4 deaths per cycle × 5 life = 20 life from each opponent per cycle with a free outlet; Drivnod doubles Kokusho's death trigger, so 40 per cycle = lethal from 40 in one cycle. Today Meren recurs Kokusho once per cycle (5 life). Blood Artist, Zulaport Cutthroat and Bastion of Remembrance add 1 per death on top; Gray Merchant re-enters each end step for a devotion drain.
3. **Spore Frog fogs every opponent's combat.** Frog sacrificed in opponent A's combat returns at A's end step, so it is ready for B, then C. That is 3 fogs per cycle instead of Meren's 1. Sakura-Tribe Elder alone fetches up to 4 basics per cycle (the deck has 11). Plaguecrafter re-enters each end step for 4 edicts per cycle; Eternal Witness re-enters for 4 regrowths.
4. **Board-wipe insurance.** Scryfall ruling (2026-08-21): if Avacyn dies at the same time as other nontoken creatures, she triggers for each of them. Our Toxic Deluge and Living Death become one-sided; an opponent's destroy wipe returns our board at end step.
5. **Resilient engine (checklist step 10).** She is a creature, but destroy and -X/-X effects only delay her one end step. Only exile, bounce, theft or a counter answer her permanently. Mikaeus skips Humans; Avacyn covers Meren, Yawgmoth, Plaguecrafter, Eternal Witness and Zulaport. Meren can go to the graveyard instead of the command zone and return free of tax at end step.
6. **Commander-dependency (step 9).** She runs the sacrifice plan with Meren locked under a Darksteel Mutation effect; Meren is not needed for any of the lines above.

### Costs and limits

- **8 MV.** Goldfish sim (simulation.json) median available mana: 6 at turns 7–8, 7 at turns 9–10. A hard cast is a turn 9+ play in the median game. She rides the same cheat infrastructure as Archon of Cruelty: Reanimate (8 life), Animate Dead, Victimize, Living Death, Grave Researcher's Reanimate copy, Colossal Grave-Reaver's mill trigger, The Soul Stone harnessed, Meren at 8 experience; Entomb and Buried Alive bin her. Birthing Pod cannot reach 8 (no 7-drop in the 99).
- **Not a combo piece.** Commander Spellbook query on today's corpus with Avacyn added to the 99: 0 included combos, 0 near-miss combos involve her. She is a value engine, so comboConsistency will not move and the goldfish sim will not model her value. Expect sim health flat and metrics curve score to dip slightly (average MV 3.0 → about 3.02 after the swap).
- **Graveyard hate.** The return goes through the graveyard. Rest in Peace or an exile-in-response (Bojuka Bog class) turns her off, the same exposure as the rest of the deck (hoser check, step 7).
- **Tokens are not covered.** Bitterblossom Faeries and Teval's Zombies stay one-shot fodder.

### Discovery trail

- EDHREC Meren page: Avacyn at 9.9% (rates fetched 2026-09-28, before the 2026-10-02 release, so low confidence). Harvester of Souls is below the page's listing floor.
- candidates.json (2026-09-29, top-200): Avacyn absent. Scorer miss on a 5-day-old card.
- Spellbook: Harvester of Souls is in 0 included combos, 0 Tier B loops, 0 synergy candidates. Cutting it costs no Combo Lab line. It is embedded in 1 highlight, 1 synergy (with Meren and Mikaeus) and the Card Advantage category; I update that prose on apply.
- Ownership-blind ranking first (DEC-472): Avacyn > Harvester on power in this shell. Ownership: Avacyn not in Owned.csv; Harvester owned (2 copies). Price, information only (Scryfall 2026-10-07): Avacyn EUR 8.77 / USD 15.66.
- Alternative cut if the board wants to keep Harvester: Liliana, Dreadhorde General (6 MV, 15.3% EDHREC, not reanimatable). I rank Harvester as the weaker slot because Liliana's static draw and -4 wipe both scale with Avacyn.

### On apply (after approval)

1. Edit deck.json: decklist swap (Avacyn `primary_role: engine`, `secondary_role: payoff`), highlight, 2 synergies (Avacyn + Kokusho + Drivnod; Avacyn + Spore Frog), prose cleanup for Harvester, source `scryfall` + `ai-inferred`.
2. Run `validate_deck_json`, `compute_tokens`, `refresh_card_pool`, metrics, sim (add Avacyn to card-metadata.json first), the three Combo Lab scripts, bump the loader cache key, commit and push.
3. Swap counter for eternal-harvest after this round: 3 since DEC-572 (DEC-929, DEC-931, this) → Trigger-2 re-assessment issue gets filed on apply.

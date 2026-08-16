## DEC-533 proposal — Dark Dominion remake: "Sauron, the Dark Lord" amass + Ring-temptation

**Recommendation: approve the 99 below.** Tier 2, CEO-executed per DEC-461. This is a full strategy remake, so I present one decklist proposal instead of per-card swap lines. Veto any line you dislike and I will re-balance around it.

**Headline numbers** (all verified this heartbeat):
- Projected metrics (in-memory, zero writes): **global_health 90, normalized 95, zero gaps** — current deck: 85 / 92 with 4 gaps.
- Components (current → proposed): manabase 82→81, role coverage 82→96, curve 95→93, interaction 118→120, cohesion 29→36, resilience 88→102.
- **74 of 99 cards carry a Tolkien-set printing** (LTR, LTC, HOB "The Hobbit", HOC "The Hobbit Eternal"). 25 imports, listed below with reasons.
- Game Changers: 6 (One Ring, Bowmasters, Demonic Tutor, Rhystic Study, Cyclonic Rift, Fierce Guardianship). Bracket label: **4-** (uncapped tier).
- Diff vs current deck: keep 57, add 40, cut 42. Unowned adds ≈ **$28 total** (biggest: Great Goblin, Foul-Hearted $21).
- Commander Spellbook on the 99: **0 included combos**; all 15 near-misses need off-theme cards — rejected (reason: theme + no-combo direction).

### Strategy — the war-machine loop
Sauron reads: opponent casts a spell → **amass Orcs 1**; an Army you control connects → **the Ring tempts you**; every tempt → you may discard your hand and **draw 4**.
Trigger frequency (4-player model, DEC-477): the amass trigger fires on every opponent spell, ≈ 4–6 times per turn cycle. The tempt-draw fires ≥1 per turn with any tempt source; Call of the Ring alone makes it every upkeep. Own-attack tempt fires ×1 per combat.
- One giant Orc Army, not many bodies: Mauhúr adds +1 to every amass batch. The Great Goblin turns every batch into 2 damage at an opponent. Gothmog gives it deathtouch, Great Goblin (Foul-Hearted) trample, Warg Rider menace, Corsairs/Rogue's Passage unblockable.
- The discard-hand engine is fuel, not cost: Reanimate, Gathering of Darkness, Along the Crooked Way, Treason of Isengard, and Sauron (LotR)'s mill-5-reanimate all use the bin.
- Wins: (1) Army alpha strike, (2) Assault on Osgiliath X + double strike burst, (3) One Ring to Rule Them All mill-wipe-drain (chapter I mills everyone by Ring-bearer = Army power), (4) Great Goblin pings + Mount Doom.
- Commander-dependency check (DEC-474 L9): under a Darksteel Mutation-class lock, amass continues (Saruman the White Hand, both Great Goblins, March from the Black Gate, Book of Mazarbul, Barad-dûr) and draw continues (One Ring, Palantír, Rhystic, Night's Whisper). Plan survives.
- Hoser coverage (DEC-474 L6): top hate classes are board wipes and token/counter hate, which ride on all types; we answer artifacts (Flame of Anor, Cyclonic Rift) and enchantments (Feed the Swarm, Cyclonic Rift); Orcish Medicine gives the Army indestructible at instant speed.

### Proposed 99
**Creatures (17)**: Orcish Bowmasters (ltr/hoc), Gothmog, Morgul Lieutenant (ltr), Grishnákh, Brash Instigator (ltr), Corsairs of Umbar (ltc), The Mouth of Sauron (ltr), Moria Scavenger (ltc), Mauhúr, Uruk-hai Captain (ltr), The Great Goblin (hob), Great Goblin, Foul-Hearted (hoc), Saruman, the White Hand (ltc), Moria Marauder (ltr), Gorbag of Minas Morgul (ltr), Witch-king of Angmar (ltr/hoc), Warg Rider (ltr), Sauron, Lord of the Rings (ltc), Orcish Siegemaster (ltc/hoc), Nazgûl (ltr)

**Ramp (8)**: Sol Ring (ltc), Arcane Signet (ltc/hoc), Mind Stone (ltc), Thought Vessel (ltc), Relic of Sauron (ltc/hoc), Inherited Envelope (ltr), Talisman of Dominance (import), Talisman of Indulgence (import)

**Card draw (6)**: The One Ring (ltr/hoc), Call of the Ring (ltr), Palantír of Orthanc (ltr/hoc), Rhystic Study (import), Night's Whisper (ltc/hoc), Sauron's Ransom (ltr)

**Tutors (3)**: Demonic Tutor (import), Diabolic Intent (ltc), Ringsight (ltr)

**Amass package (11)**: March from the Black Gate (ltr), Book of Mazarbul (ltr), Treason of Isengard (ltr), Summons of Saruman (ltc), Swarming of Moria (ltr), Gathering of Darkness (hob), Along the Crooked Way (hob), Assault on Osgiliath (ltr), Foray of Orcs (ltr), Orcish Medicine (ltr), In the Darkness Bind Them (ltc)

**Wincon saga (1)**: One Ring to Rule Them All (ltr)

**Counterspells (6)**: Counterspell (import), Mana Drain (import), Fierce Guardianship (import), Saruman's Trickery (ltr), Arcane Denial (ltc), Swan Song (ltc)

**Removal & recursion (8)**: Feed the Swarm (ltc), Claim the Precious (ltr), Flame of Anor (ltr/hoc), Deadly Rollick (import), Cyclonic Rift (import), Toxic Deluge (ltc), Decree of Pain (ltc), Reanimate (ltc)

**Protection (1)**: Lightning Greaves (ltc)

**Lands (38)**: Command Tower (ltc), Exotic Orchard (ltc), Barad-dûr (ltr), Mount Doom (ltr/hoc), The Black Gate (ltc/hoc), Minas Morgul, Dark Fortress (ltc/hoc), Goblin-town (hob), Swamp, Rogue's Passage (ltc/hoc), Bojuka Bog (ltc), Urborg, Tomb of Yawgmoth (ltc), Watery Grave (import), Blood Crypt (import), Steam Vents (import), Morphic Pool (import), Luxury Suite (import), Training Center (import), Sunken Hollow (ltc), Smoldering Marsh (ltc), Drowned Catacomb (ltc), Dragonskull Summit (ltc), Sulfur Falls (ltc), Darkslick Shores (import), Blackcleave Cliffs (import), Gloomlake Verge (import), Underground River (ltc), Sulfurous Springs (ltc), Shivan Reef (import), Bloodstained Mire (import), Polluted Delta (import), Takenuma, Abandoned Mire (import), Otawara, Soaring City (import), Mountain, Swamp, Island, Mountain, Stormcarved Coast (import), Cascade Bluffs (import)
### Board decisions needed (3)
- [ ] **The One Ring** — we own 1 copy and it is committed to gandalf-party-guest (DEC-528 tracker). Options: buy a second (~$106), move it here, or replace with Palantír-class draw (deck works without it; metrics already include it). My recommendation: keep it in the list, board picks sourcing.
- [ ] **Great Goblin, Foul-Hearted — $21.36, unowned** (Hobbit Eternal). Core piece (amass 3 on entry and attack; Armies gain trample). No in-pool equal.
- [ ] **6 power imports** (Counterspell, Mana Drain, Fierce Guardianship, Demonic Tutor, Diabolic Intent, Rhystic Study + Cyclonic Rift/Toxic Deluge/Deadly Rollick/Decree kept from current build): all owned/already committed here, all strictly better than pool equivalents. Veto any to raise theme purity; role coverage drops accordingly (tutor gap reappears without the two tutors).

### Triage log (closing gates)
- EDHREC closing diff (DEC-402), cards ≥40% inclusion not in the 99: **Reanimate 66% → included**; **Orcish Siegemaster 52% → included** (owned, LTC/HOC); **Nazgûl 59% → included ×1** (we own 6; more dilutes the amass plan — defer); Crumbling Necropolis 63% → reject (tapped; manabase strictly better); Blasphemous Act 61% → defer (4 wipes already; Army usually survives it late, revisit after sim); Lord of the Nazgûl 49% → reject (pulls the deck into a wraith-tribal plan); Dark Ritual 49% → reject (battlecruiser, not ritual combo); Anger 47% → defer (haste enabler, binned naturally by tempt discards; candidate for swap round 2).
- Archetype recipe pass (DEC-238, tokens-go-wide live recipe, amass sub-recipe): Dreadhorde Invasion (rk1478) and Lazotep Plating → defer, mechanically strong but zero Tolkien identity; board can pull them in if power > theme.
- Soothing of Sméagol (bounce + tempt) → defer, next protection-slot candidate.
- Cuts include the whole Thoracle/Consultation/Tainted Pact combo shell, 5 tutors, Force of Will, and the draw-go spell suite — that is the strategy change the board asked for, not power leakage.

### Post-approval work plan (next heartbeat after acceptance)
1. Write deck.json (roles per taxonomy, wincon_style combat, new winConditions/synergies/guideContent, sources for every add: scryfall + edhrec + commanderspellbook + ai-inferred as applicable).
2. Run compute_tokens, refresh_card_pool, manabase_check, validate_deck_json, validate_strategy_ceiling, check_game_changers.
3. Rewrite mana_simulation_dark_dominion.py for the amass/tempt engine (old sim models Thoracle draw-go; win_turn above still reads the stale sim — treat it as unknown until re-sim).
4. Recompute metrics.json, re-export sim, stale-reference sweep of all prose.
5. Keep name "Dark Dominion" (strategic-name rule), new subtitle "The Eye of Mordor" — flag if you want a rename.

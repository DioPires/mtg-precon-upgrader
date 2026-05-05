# DEC-148: Mana Base Revision (rev 2)

Author: CEO • Status: **Awaiting board approval (no edits applied)**
Date: 2026-05-05 • Supersedes rev 1

## Board pushback (acknowledged)
1. **I missed the landfall payoffs.** Verdant Tide runs Scute Swarm + Avenger of Zendikar + Elfsworn Giant. Mutant Multiplication runs Scute Swarm + Avenger of Zendikar. Per memory, Fabled Passage triggers landfall **twice**. With Scute Swarm at 6+ lands (token copies *itself*), Fabled Passage = explosive. **Fabled Passage swap is correct in both decks.**
2. **"Appropriate as-is" was a weak framing.** Replaced with concrete upgrades wherever owned, unused lands materially improve consistency.

## Constraints
- New lands must exist in `priv_data/owned_formatted.csv`.
- Must not be claimed by any non-Genesis-Protocol deck.
- Verbatim Scryfall oracle text verified for every proposed add.
- No `deck.json` edits applied. Gated on board approval.

## Pre-flight numbers

| Deck | Cards | Lands | Bracket | Colors | Landfall payoffs |
|---|---|---|---|---|---|
| Mutant Multiplication | 98 | 38 | 4 | Bant (GWU) | Scute Swarm, Avenger of Zendikar |
| Eternal Harvest | 99 | 35 | 4 | Golgari (BG) | Bloodghast |
| Verdant Tide | 99 | 34 | 2 | Mono-G | Scute Swarm, Avenger of Zendikar, Elfsworn Giant |
| Creeping Corruption | 99 | 35 | 4 | 4-color (WUBG) | none |

## Verbatim oracle text for new adds (Scryfall-verified)

- **Fabled Passage** — Land. *"{T}, Sacrifice this land: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle. Then if you control four or more lands, untap that land."*
- **Hall of Oracles** — Land. *"{T}: Add {C}. {1}, {T}: Add one mana of any color. {T}: Put a +1/+1 counter on target creature. Activate only as a sorcery and only if you've cast an instant or sorcery spell this turn."*
- **Path of Ancestry** — Land. *"This land enters tapped. {T}: Add one mana of any color in your commander's color identity. When that mana is spent to cast a creature spell that shares a creature type with your commander, scry 1."*
- **Memorial to Folly** — Land. *"This land enters tapped. {T}: Add {B}. {2}{B}, {T}, Sacrifice this land: Return target creature card from your graveyard to your hand."*
- **Crypt of Agadeem** — Land. *"This land enters tapped. {T}: Add {B}. {2}, {T}: Add {B} for each black creature card in your graveyard."*
- **Seaside Citadel** — Land. *"This land enters tapped. {T}: Add {G}, {W}, or {U}."*

## Per-deck proposal

### 1. Mutant Multiplication — Leonardo, the Balance (Mutant Ninja Turtle), 38 lands → 38

| Cut | Add | Rationale |
|---|---|---|
| 1 Forest | **Fabled Passage** | Triggers landfall **twice** (place + fetched basic). Scute Swarm at 6+ lands = self-copies; Avenger pumps each Plant. Two landfall triggers per drop = exponential growth on Scute Swarm board states. |
| 1 Forest | **Hall of Oracles** | Late-game mana sink that puts a +1/+1 counter on any creature once per turn. Direct fit for Leonardo's "+1/+1 counter on each creature when a token enters" engine. 13 instant/sorcery enablers in deck. |
| 1 Plains | **Path of Ancestry** | Leonardo is Mutant Ninja Turtle. Deck has ~11 Mutant/Ninja/Turtle creatures = 11 scry triggers per game on average. Tapped Bant tritand-equivalent. |

**Net effect:**
- Lands 38 → 38; 6 Forest → 4 Forest; 3 Plains → 2 Plains.
- New synergy lands: 1 landfall enabler, 1 +1/+1 counter sink, 1 tribal scry.
- Tradeoff: 3 untapped basics → 3 ETB-tapped lands. Mitigated by deck's high land count (38) and curve clustering at 3+ CMC.

### 2. Eternal Harvest — Meren of Clan Nel Toth (Human Shaman), 35 lands → 35

| Cut | Add | Rationale |
|---|---|---|
| 1 Swamp | **Memorial to Folly** | Sac to recur creature from yard → hand. Pairs with Meren's end-step yard → battlefield trigger to give the deck a hand-recursion line independent of Meren. |
| 1 Swamp | **Crypt of Agadeem** | Scales with black creatures in yard: a Cabal Coffers-lite for Meren's mid-game where 4–6 black creatures sit in yard. Effectively reads "Add {BBB+}" by turn 5. |

**Net effect:**
- Lands 35 → 35; 7 Swamp → 5 Swamp.
- 2 untapped Swamp → 2 tapped utility lands. Slowdown is real but graveyard-deck mid-game mana spike (Crypt) and recursion redundancy (Memorial) outweigh it.
- Path of Ancestry skipped: only 5 Humans + 4 Shamans (~9 enablers, often overlap). Crypt + Memorial dominate.

### 3. Verdant Tide — Eladamri, Korvecdal (Elf Druid Warrior), 34 lands → 34

| Cut | Add | Rationale |
|---|---|---|
| 1 Snow-Covered Forest | **Fabled Passage** | Two landfall triggers per drop. Scute Swarm at 6+ lands = self-copy on each trigger; Avenger pumps Plants twice; Elfsworn Giant creates 2 Elf Warrior tokens (which then chain into Eladamri's Elf Druid Warrior identity for Path of Ancestry triggers if queued). Snow type is vestigial — verified zero snow synergies in deck. |
| 1 Snow-Covered Forest | **Path of Ancestry** | Eladamri is Elf Druid Warrior. Deck runs 21+ elves. Scry-1 on every elf cast = ~21 scry triggers per game. Highest-density tribal scry of any deck in the project. |

**Net effect:**
- Lands 34 → 34; 28 Snow-Covered Forest → 26 Snow-Covered Forest.
- 2 untapped basics → 2 tapped synergy lands. Bracket 2 deck has tempo slack.
- Mono-G fixing burden = zero, so any fixing-flavored land (Path of Ancestry, Fabled Passage) costs nothing in color sources.

### 4. Creeping Corruption — Atraxa, Praetors' Voice (Phyrexian Angel Horror), 35 lands → 35

| Cut | Add | Rationale |
|---|---|---|
| 1 Forest (2 → 1) | **Path of Ancestry** | Atraxa = Phyrexian Angel Horror. Deck runs **19 Phyrexians + 1 Angel + 4 Horrors = ~24 type-shared creatures** out of 27 creatures. Highest-percentage scry density of any deck (~89% of creatures trigger). |
| 1 Swamp (1 → 0) | **Seaside Citadel** | Adds 3rd triome (Bant WUG) to complement existing Indatha (WBG) + Zagoth (UBG). Atraxa is WUBG; this tritand covers W/U/G simultaneously, smoothing 3-color color requirements for spells like Atraxa (GWUB) and 4-color shocks. |

**Net effect:**
- Lands 35 → 35; basics 4 → 2 (mostly relying on shocks/triomes anyway).
- Strong scry-density add (Path of Ancestry) + 3rd Bant-color tritand for color-source diversity.
- Tradeoff: 2 untapped basics → 2 ETB-tapped lands. Atraxa is a deathtouch/lifelink commander that values mid-game stability over T1 tempo.

## Summary table

| Deck | Cuts | Adds | Land count Δ |
|---|---|---|---|
| Mutant Multiplication | 2 Forest, 1 Plains | Fabled Passage, Hall of Oracles, Path of Ancestry | 0 |
| Eternal Harvest | 2 Swamp | Memorial to Folly, Crypt of Agadeem | 0 |
| Verdant Tide | 2 Snow-Covered Forest | Fabled Passage, Path of Ancestry | 0 |
| Creeping Corruption | 1 Forest, 1 Swamp | Path of Ancestry, Seaside Citadel | 0 |

**Total: 9 swaps. Zero net land count change.**

## Constraint compliance check

| Land | Owned qty | Used in non-GP deck? | Status |
|---|---|---|---|
| Fabled Passage | 6 | 1 (creeping-corruption) | 5 free → 2 needed → ✓ |
| Hall of Oracles | 1 | 0 | ✓ |
| Path of Ancestry | 7 | 0 | 3 needed → ✓ |
| Memorial to Folly | 1 | 0 | ✓ |
| Crypt of Agadeem | 1 | 0 | ✓ |
| Seaside Citadel | 1 | 0 | ✓ |

## Next action (post-approval)
1. Apply 9 swaps across 4 `deck.json` files.
2. Add `sources` entry on each swap citing DEC-148 + ai-inferred mana-base review (with landfall-payoff note for the Fabled Passage adds).
3. Run `python scripts/validate_deck_json.py --deck mutant-multiplication --deck eternal-harvest --deck verdant-tide --deck creeping-corruption`.
4. Re-run `scripts/refresh_card_pool.py` per deck.
5. Commit + push.

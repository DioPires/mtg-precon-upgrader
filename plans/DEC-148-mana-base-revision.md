# DEC-148: Mana Base Revision (Mutant / Eternal Harvest / Verdant Tide / Creeping Corruption)

Author: CEO • Status: **Awaiting board approval (no edits applied)**
Date: 2026-05-05

## Constraints
- New lands must be in `priv_data/owned_formatted.csv`.
- Avoid lands already used in non-Genesis-Protocol decks (genesis-protocol = exempt/shareable).
- Verbatim oracle text per Scryfall (verified for every proposed add).
- No deck.json edits without explicit board approval (per feedback memory).

## Pre-flight numbers (current state)

| Deck | Cards | Lands | % Lands | Bracket | Colors | global_health |
|---|---|---|---|---|---|---|
| Mutant Multiplication | 98 | 38 | 38.8% | 4 | Bant (GWU) | 82 |
| Eternal Harvest | 99 | 35 | 35.4% | 4 | Golgari (BG) | 78 |
| Verdant Tide | 99 | 34 | 34.3% | 2 | Mono-G | 76 |
| Creeping Corruption | 99 | 35 | 35.4% | 4 | 4-color (WUBG) | 86 |

Note: Mutant Multiplication shows 98 in decklist (one card short of 99). Pre-existing accounting issue, **out of scope for this issue** — flag for follow-up.

---

## Per-deck analysis

### 1. Mutant Multiplication — Leonardo, the Balance (Bant tokens, B4)

**Current land slate (38):**
6 Forest / 3 Plains / 1 Island; Command Tower, Exotic Orchard, Mana Confluence, City of Brass, Spara's HQ; Temple Garden, Breeding Pool, Hallowed Fountain; Windswept Heath, Flooded Strand, Prismatic Vista; Sunpetal Grove, Glacial Fortress; Brushland, Adarkar Wastes, Yavimaya Coast; Botanical Sanctum, Razorverge Thicket, Seachrome Coast; Wooded Bastion; Canopy Vista; Otawara, Eiganjo, Reliquary Tower, Rogue's Passage, Scavenger Grounds, Turbulent Wilderness, Horizon Canopy.

**Diagnosis:**
- 38 lands is **above** the typical Bracket-4 Bant target (36–37); fixing density already very high (3 fetches + tritand + 3 shocks + 3 fast + 3 pain + 3 check + filter).
- No landfall payoffs in deck (token / +1/+1 counter strategy).

**Board prompt: "consider Fabled Passage instead of one Forest"** → **Recommend AGAINST.**
Reasoning: deck already has 3 basic-fetchers (Windswept Heath, Flooded Strand, Prismatic Vista). A 4th adds redundancy at the cost of an untapped Turn-1 G source. No landfall payoff to justify the tempo loss. Fabled Passage's value-add is fixing flexibility, which this deck doesn't lack.

**Proposed swap (instead):**
| Cut | Add | Why |
|---|---|---|
| 1 Forest | **Hall of Oracles** (1 owned, free) | Late-game mana sink that buffs Leonardo's +1/+1 counter strategy. Ungated G land replaced by a counter-payoff utility land at 38→37 land count (still safe). |

**Hall of Oracles oracle (verified):** *"{T}: Add {C}. {1}, {T}: Add one mana of any color. {T}: Put a +1/+1 counter on target creature. Activate only as a sorcery and only if you've cast an instant or sorcery spell this turn."*
Synergy fit: deck runs 9 instants + 4 sorceries (13 enablers). Hall converts late-game floating mana into permanent stat growth on Leonardo's tokens.

**Net effect (before/after):**
- Lands: 38 → 37 (−1)
- Untapped G sources: 16 → 15 (−1) — still well above 13-source threshold for {G}{G}{G} curves.
- Counter-producing utility lands: 0 → 1
- 5-color sources via Hall's `{1}, {T}: Add one mana of any color`: +1 (Bant fixing depth).

---

### 2. Eternal Harvest — Meren of Clan Nel Toth (Golgari reanimator, B4)

**Current land slate (35):**
6 Forest / 7 Swamp; Command Tower, Bojuka Bog, Boseiju, Urborg, Castle Locthwain, Takenuma, Dryad Arbor, Phyrexian Tower, High Market; Overgrown Tomb; Verdant Catacombs; Llanowar Wastes; Woodland Cemetery; Blooming Marsh; Nurturing Peatland; Darkbore Pathway; Deathcap Glade; Underground Mortuary; Undergrowth Stadium; Twilight Mire; Vernal Fen; Turbulent Fen.

**Diagnosis:**
- 35 lands is appropriate for Golgari reanimator with on-curve graveyard fillers and 2 sac-lands (Phyrexian Tower, High Market).
- Already utility-saturated: 2 sac outlets, 2 graveyard hate (Bojuka, Scavenger n/a), 2 land-disruption (Boseiju, Strip Mine n/a).

**Proposed swap:**
| Cut | Add | Why |
|---|---|---|
| 1 Swamp (7→6) | **Memorial to Folly** (1 owned, free) | Sac-to-recur from yard → hand. Direct Meren synergy: hand-target replays via mana, complementing Meren's battlefield-target end-step trigger. Doubles as Swamp source. |

**Memorial to Folly oracle (verified):** *"This land enters tapped. {T}: Add {B}. {2}{B}, {T}, Sacrifice this land: Return target creature card from your graveyard to your hand."*

**Net effect (before/after):**
- Lands: 35 → 35 (no change)
- B sources: unchanged (Memorial = Swamp-functional after T1)
- Reanimation outlets: Meren-only → Meren + Memorial (one-shot pseudo-recursion redundancy)
- Tradeoff: 1 untapped Swamp → 1 ETB-tapped land. Mitigated by deck's slower reanimator pivot (curve clusters at 3+ CMC).

---

### 3. Verdant Tide — Eladamri, Korvecdal (Mono-G elfball, B2)

**Current land slate (34):**
28 Snow-Covered Forest, The Shire, Three Tree City, Rogue's Passage, Oran-Rief the Vastwood, Wirewood Lodge, Nykthos Shrine to Nyx.

**Diagnosis:**
- **No snow synergies** in deck. Snow-Covered Forest = vestigial choice; functionally identical to Forest for this build.
- Mono-G has zero color-fixing burden. Tempo-sensitive elfball needs untapped T1.
- 6 utility lands already; basics aggressively tuned for explosive mana via Priest of Titania / Marwyn / Heritage Druid.

**Board prompt: "consider Fabled Passage instead of one Snow-Covered Forest"** → **Recommend AGAINST.**
Reasoning:
1. No landfall payoffs in deck (verified via decklist scan).
2. No snow payoffs to lose by swapping (Snow basics are cosmetic).
3. Fabled Passage ETBs tapped, then fetches a *tapped* Forest, untapping only if 4+ lands controlled. T1–T3 = strict tempo loss with zero upside in a mono-G deck where Forest = perfect mana.
4. Fabled Passage's only edge over a Forest is "shuffle library" (relevant for Sylvan Library / Brainstorm — not in deck) and "double landfall" (no payoffs).

**Proposed swap: NONE.** Mana base is Bracket-2 appropriate.

(Optional consideration noted but **not** included in formal proposal: trim 1 Snow-Covered Forest → +1 Reliquary Tower (2 free copies). Eladamri's hand-cheat ability rewards a fuller hand; Reliquary Tower removes max-hand-size cap. Deferred unless board wants to pursue.)

---

### 4. Creeping Corruption — Atraxa, Praetors' Voice (4-color WUBG proliferate, B4)

**Current land slate (35):**
2 Forest / 1 Swamp / 1 Island; Command Tower, Exotic Orchard, Reflecting Pool, City of Brass, Mana Confluence n/a; 2 triomes (Zagoth, Indatha); 6 shocks (Breeding Pool, Temple Garden, Overgrown Tomb, Watery Grave, Hallowed Fountain, Godless Shrine); 5 fetches (Polluted Delta, Flooded Strand, Verdant Catacombs, Windswept Heath, Marsh Flats); 4 fast lands (Darkslick, Blooming Marsh, Razorverge, Botanical Sanctum); 4 pain lands (Caves of Koilos, Llanowar Wastes, Yavimaya Coast, Underground River); Brushland, Karn's Bastion, Inkmoth Nexus, The Seedcore, Turbulent Moor, Fabled Passage.

**Diagnosis:**
- Excellent 4-color base. 35 lands appropriate.
- Already has Fabled Passage. Has 5 fetches feeding 6 shocks (textbook fetch-shock chain).
- Missing: Spara's HQ (Bant triome — claimed by Mutant), Raffine's Tower (Esper triome — not owned).

**Proposed swap: NONE required.** Mana base is at Bracket-4 standard.

(Optional consideration: +1 Path of Ancestry (7 free) for Atraxa-cast scry-1 trigger. Tradeoff: tapped land for marginal scry. **Not** included in formal proposal — current base is strong; adding tapped utility for low-value scry isn't a clear win.)

---

## Summary of proposed changes

| Deck | Cut | Add | Net land Δ |
|---|---|---|---|
| Mutant Multiplication | 1 Forest | Hall of Oracles | −1 |
| Eternal Harvest | 1 Swamp | Memorial to Folly | 0 |
| Verdant Tide | — | — | 0 |
| Creeping Corruption | — | — | 0 |

**Two swaps total.** Both use lands the user owns and that are free in non-Genesis decks.

## Verification

- [x] Oracle text verified verbatim via Scryfall MCP for every candidate land (Hall of Oracles, Memorial to Folly, Fabled Passage, Path of Ancestry, Reliquary Tower, etc.).
- [x] Cross-deck claim check: Hall of Oracles (1 owned, 0 used in any deck), Memorial to Folly (1 owned, 0 used in any deck).
- [x] Decline-to-swap rationale on both Fabled Passage prompts.
- [ ] Board approval — **gating implementation**.

## Next action (post-approval)
1. Apply two swaps in `data/commanders/{mutant-multiplication,eternal-harvest}/deck.json`.
2. Add `sources` entry citing DEC-148 + ai-inferred mana-base review.
3. Run `python scripts/validate_deck_json.py --deck mutant-multiplication --deck eternal-harvest`.
4. Re-run candidate pool refresh on both decks.
5. Commit + push.

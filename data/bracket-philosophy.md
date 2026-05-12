# Bracket 4/5 Deckbuilding Philosophy

Source: [Command Zone Episode 731](https://www.youtube.com/watch?v=jzeTz9clIC8) (2026-03-17) — Rachel Weekes + Joe Johnson

## Mana Base

- Zero tapped lands turns 1-3. Fetches, shocks, pain lands, fast lands, utility lands only.
- Acceptable tapped lands: Triomes IF fetchable in-deck (they're searchable ramp targets), Bojuka Bog (free graveyard hate from a land slot).
- Cut at B4+: Vivid lands, Thriving lands, bounce lands, Path of Ancestry, Evolving Wilds, tap duals, cycling duals (Canyon Slough etc.), Seaside Citadel-style trilands.
- Filter lands ({1},{T}: Add {C}{C}) are effectively dead on T1 — avoid in B5.

## Fast Mana

**Bracket 4 minimum:**
- Sol Ring (universal)
- Chrome Mox (any deck with colored spells to exile — produces colored mana)
- Ancient Tomb (any deck)
- Green: all 1-mana dorks (Birds of Paradise, Llanowar Elves, Elvish Mystic, Elves of Deep Shadow, etc.)

**Bracket 5 adds:**
- Mana Vault (any deck — strong in colorless/mono, weaker in 3+ color without untap effects)
- Mox Diamond, Lotus Petal, Jeweled Amulet (if budget allows)
- Jeska's Will (red decks — early Jeska's Will is devastating)
- Dark Ritual (black decks)

**Note:** Mana Vault ({C}{C}{C}) is weaker in 3+ color decks without untap effects. Evaluate per-deck.

## Free Spells (Mandatory by Color)

**Bracket 4:**
- Blue: Force of Will, Fierce Guardianship
- Black: Deadly Rollick
- Red: Deflecting Swat

**Bracket 5 adds:**
- Blue: Force of Negation, Pact of Negation
- Black: Snuff Out (4 life, free instant removal)
- Blue: Misdirection (redirect spell)

## Interaction

- Instant speed only for targeted removal. Sorcery-speed spot removal is unplayable at B4+ speed.
- Sorcery-speed board wipes are acceptable. Toxic Deluge is the premier B4+ wipe. Blasphemous Act is a "bracket 3 card" — too slow, often one-sided when boards are large.
- Cultivate / Kodama's Reach are B3 cards — at B4+ use creature ramp (dorks), 2-mana land tutors (Nature's Lore, Three Visits, Rampant Growth), or artifact rocks.

## Card Quality

- Every card must impact the turn it enters. Do not play expensive permanents and pass (e.g., Doubling Season on an empty board = "5 mana, lose").
- Permanent-based > instants/sorceries where possible. Bodies synergize with sacrifice engines, Gaea's Cradle, token doublers, etc.
- Creature tutors feel less threatening than spell tutors — opponents are less likely to counter them.
- Redundancy over unique effects. Multiple cards doing the same job ensures consistency.
- Plan A/B/C resilience: every card should have a role so you never draw dead.

## Threat Assessment

- Know when something is another player's problem. Leave Rest in Peace up if opponents need graveyard more than you.
- "You must bolt the bird" — early removal to disrupt combo setups is mandatory at B4+.
- Blue players get focused down fast at B4. Hard to go one-for-one with counterspells vs 3 opponents.

## Game Pacing (B4)

- Average 45 min to 1.5 hours, 5-7 turns.
- ~50% combo wins, ~50% creature/non-creature damage.
- Turns 1-2: fast mana, dorks, early value.
- Turns 3-4: board established, 7-8 permanents.
- Attempt to kill by turn 6. Stumbling is very hard to recover from.

---

## B4 Reality Check (Operational)

Added from DEC-205 (2026-05-12). The CZ731 principles above tell you HOW to build a B4 deck. This section tells you WHETHER a candidate deck actually qualifies — a quantitative test using the `comboLethal` / `lethalProxy` curves in `data/commanders/{id}/simulation.json`.

### Kill-turn thresholds

Read the proxy curve from the deck's `simulation.json` → `goldfish.byTurn[T].comboLethal` (combo decks) or `lethalProxy` (combat decks):

| Reading | Classification |
|---|---|
| comboLethal/lethalProxy **≥ 50% at T6** | **True B4** — reliable T5-T7 win window |
| < 50% T6, **≥ 50% at T7** | **Soft B4** — CAN win in the window, doesn't always |
| < 50% at T7 | **B3-B4 borderline** — the combo plan exists but isn't reliable; deck plays as a value pile |
| **≥ 60% at T4-T5** | Approaching B5 / cEDH territory |

These cutoffs apply to the proxy as a *floor* (real-game readiness is higher — see caveats below).

### comboLethal proxy schema (cross-link)

The proxy lives in `scripts/export_simulation_results.py`. Its v2 model substitutes for missing combo pieces via: (1) bargain free-cast tutor (Beseech-style), (2) type-matched regular tutor, (3) reanimation for permanent pieces. Decks must tag the right fields to be read correctly:

- `winConditions[].kind: "combo"` + `winConditions[].pieces: [card names]` — without these, comboLethal stays 0.
- `decklist[].tutor_targets: ["instant", "sorcery"]` — restrict tutors that can't fetch creatures/planeswalkers (e.g., Mystical Tutor, Spellseeker). Default `["any"]`.
- `decklist[].tutor_mv_cap: N` — restrict tutors that have an MV cap (e.g., Spellseeker MV ≤ 2). Default `null`.
- `decklist[].tutor_free_cast_via_bargain: true` — Beseech the Mirror and similar bargain-tutor cards.
- `decklist[].primary_role: "recursion"` (or `secondary_role`) — for reanimation spells (Reanimate, Animate Dead, etc.).

Forgetting these tags will under-count comboLethal and make a real B4 deck look weaker than it is.

### Tainted Pact gotcha

If you add **Tainted Pact** as a Consultation-style finisher, the deck must be singleton-name everywhere — including basics. Convention: 1 of each basic + non-basic duals. Pact's "exile two cards with the same name" stop condition fires on duplicate basics and leaves your library mostly intact, breaking the Thoracle/Jace/Lab Maniac win. The same constraint applies to Doomsday-style pile cards. Demonic Consultation does NOT have this constraint.

### Budget tiers (from DEC-205 path negotiation)

When pushing a deck toward B4 reliability, these are the rungs in approximate cost:

- **Tier X — Ultra-budget (~$5):** Laboratory Maniac + cantrips (Brainstorm, Ponder, Preordain, Opt). Adds a 3rd wincon-permanent + deck-thinning dig. Estimated comboLethal T6 gain: +5-10%.
- **Tier Y — Mid (~$30-40):** Tier X + ONE premium universal tutor (Demonic Tutor or Vampiric Tutor). Estimated T6 gain: +10-15%.
- **Tier Z — Premium (~$80-180):** Tier X + BOTH Demonic AND Vampiric Tutor + Tainted Pact + Lab Maniac. Estimated T6 gain: +18-22% — typically clears the 50% B4 bar.
- **Tier W — cEDH-tier ($500+):** Tier Z + Mana Crypt, Mox Diamond, Imperial Seal, Force of Negation, Pact of Negation, Lotus Petal, Jeweled Amulet. Pushes to B5 (cEDH).

Higher tiers don't replace lower ones — they stack.

### Caveats

The comboLethal proxy is a FLOOR. Real-game readiness is higher because the proxy doesn't model:

- Literal graveyard tracking (reanim assumes piece could be in GY without verifying)
- Multi-turn assembly ("tutor T3, hold piece, combo T5")
- Stack-trigger ordering (Thoracle ETB on stack + Consultation response is abstracted)
- Token-state combo enablers beyond the commander-in-play approximation
- Opponent interaction / counter-magic against your combo turn

A deck at 50% comboLethal at T6 in the proxy will typically win the actual game in the T5-T7 window in a 4-player pod where you're not the priority target. Conversely, a deck under 40% at T6 does NOT have a reliable T5-T6 plan, even accounting for these caveats.

### Case study

DEC-205 Dark Dominion retune (commits [`4094952`](https://github.com/DioPires/mtg-precon-upgrader/commit/4094952) through [`a62d993`](https://github.com/DioPires/mtg-precon-upgrader/commit/a62d993)) — slow value-pile B5 (T8+ goldfish lethal, comboLethal not tracked) → tutored combo B4+ (comboLethal T6 48.2%, T7 53.3%, median combo-ready turn T7). DeckHealthScore C(65) → B(67.5), manabase_health 74 → 82, global_health 78 → 85. Total spend: $56. Six combo lines tagged (3 wincon-permanents × 2 finishers).

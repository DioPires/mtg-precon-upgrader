# DEC-210 — Creeping Corruption Bracket Review

**Date**: 2026-05-12
**Question**: Does the deck win consistently on T5/T6 (true B4), or is it labeled B4 only because the `gameChangers` count puts it over the B3 ceiling?

## TL;DR

**Board's intuition is correct, and the data is also wrong.** Two independent findings:

1. **Speed**: simulation median lethal turn = **T8**. Lethal-by-T6 is **21.9%**; lethal-by-T7 is **47.1%**. Per the project's own B4 Reality Check (`data/bracket-philosophy.md`), <50% at T7 classifies a deck as **"B3-B4 borderline — the combo plan exists but isn't reliable; deck plays as a value pile."** This is B3 speed, not B4 speed.
2. **`gameChangers: 5` is wrong**. Only **3** cards in the decklist match the official Game-Changers list: Cyclonic Rift, Rhystic Study, Teferi's Protection. The strategy text claims Force of Will / Fierce Guardianship / Deadly Rollick are in the deck — they are not in the 99. With 3 GCs the deck is *already inside the B3 ceiling*; the B4 label isn't even forced by the rule.

Net: this deck is mis-labeled. The "B4 floor by GC count" reasoning does not apply. The label should change regardless of which strategic option below is chosen.

## Evidence (`simulation.json`, 10,000 goldfish games)

| Turn | Commander cast | Threat down | Meaningful board | **Lethal proxy** |
|------|----------------|-------------|------------------|------------------|
| T3   | 25.8%          | 54.7%       | 37.6%            | 0.0%             |
| T4   | 56.0%          | 77.3%       | 67.0%            | 0.1%             |
| T5   | 69.4%          | 86.2%       | 79.2%            | **4.3%**         |
| T6   | 78.9%          | 91.7%       | 87.4%            | **21.9%**        |
| T7   | 84.7%          | 94.7%       | 91.9%            | 47.1%            |
| T8   | 88.9%          | 96.7%       | 94.9%            | 68.5%            |
| T10  | 94.2%          | 98.8%       | 98.2%            | 90.0%            |

**Median lethal turn = T8.** B4 target is T5–T7. Soft-B4 (50% at T7) is barely missed; true-B4 (50% at T6) is far below.

> Caveat — same as DEC-208: `lethalProxy` is a combat-damage proxy (≥40 pressure) and under-counts infect kills via Triumph of the Hordes. Even granting that, draw-Triumph-by-T6 is ≈ P(seen) × P(have-board+mana) ≈ 35% × 65% ≈ 23%. Adding that to the 22% combat lethal proxy gets you to ~40% T6 — still short of the 50% B4 threshold.

### Why the deck is slow

| Lever | Current | Comment |
|---|---|---|
| Tutors | **0 / 4** target | Sylvan Library is selection, not a tutor. Triumph of the Hordes, Tekuthal, Vorinclex, Necrogen Rotpriest — none are findable on demand. |
| Fast mana | **Sol Ring only** | No Grim Monolith, no Mana Vault, no Chrome Mox, no Lotus Petal, no Ancient Tomb. CZ731 lists these as "B4 minimum" for non-mono decks. |
| Free interaction | **0 / 4** target | Strategy text claims FoW + Fierce Guardianship + Deadly Rollick. None are in the 99. Real interaction = Counterspell, Swan Song, Spell Pierce, Heroic Intervention — all pay-mana. |
| Counterspells | 3 / 6 target (`gaps[].counterspell.score = 50`) | Already flagged as a gap by the metrics computer. |
| Ramp | 8 / 10 (`ramp.score = 80`) | Acceptable. |
| Threat density | 18 threats, median deploy T4 | Healthy for a fair deck, slow for a B4. |

The win plan is **incremental proliferate**: Atraxa ticks +1 poison/opp/end-step (or +2 with Tekuthal). Triumph of the Hordes is the one-shot finisher. Without tutors, you draw Triumph on its natural curve (≈ 35% by T6) — not a B4 reliability floor.

## Game-changer audit

| Declared (`deck.json`) | Actual matches on `data/game-changers.json` |
|---|---|
| `gameChangers: 5` | **3** — Cyclonic Rift, Rhystic Study, Teferi's Protection |

The strategy text says: *"The interaction suite runs the full B4 package — Force of Will, Fierce Guardianship, Deadly Rollick, Cyclonic Rift, Toxic Deluge."* — but none of FoW / Fierce Guardianship / Deadly Rollick are in the 99-card decklist. Strategy text was written aspirationally and never reconciled with `decklist[]`. Should be corrected to `gameChangers: 3` regardless of strategic option chosen.

With 3 GCs, the deck is below the B4-forcing threshold (>3). Labeling it B4 is currently a *user choice*, not a *rule consequence*.

## Three strategic options for the board

### Option A — Reclassify to B3 (honest label) — recommended default

**Premise**: accept the deck as built. It plays like a strong proliferate / infect midrange that wins T7–T9. That's B3.

**Required changes**:
- Flip `bracket` from `"4"` → `"3"` in `data/index.json` and `data/commanders/creeping-corruption/deck.json`.
- Correct `gameChangers: 5` → `3`.
- Update `guideContent.strategyOverview` to remove the false claim that FoW / Fierce Guardianship / Deadly Rollick are in the deck. Replace with the actual interaction list.
- Optional polish: 0–3 small swaps to tighten redundancy (e.g., a second proliferate sweeper, replacing Wurmquake or Phyresis Outbreak if cuts surface).

**Spend**: $0–20.
**Outcome**: deck labeled correctly; pod expectations match reality. Atraxa infect at B3 is a popular, well-respected build — there is no shame in this label.

### Option B — Upgrade speed to a true B4 (DEC-205-style retune) — **board-preferred**

**Premise**: keep the B4 label and earn it. Apply the DEC-205 Dark Dominion playbook — add fast mana + tutors + a tutor-able win condition.

**Revised after 2026-05-12 board feedback**:
- Board prefers Option B but flagged Force of Will as out of budget.
- Verified owned inventory (`priv_data/owned_formatted.csv`): Force of Will **is owned** (×1, currently virtually-shared with Dark Dominion and Genesis Protocol). Listing it in Creeping Corruption's `deck.json` follows the project's existing card-sharing convention — no new purchase required.
- If the board prefers not to expand the FoW share to a 3rd deck, **Force of Negation** ({1}{U}{U}, free on opponents' turns, ~$25-35) is the budget-friendly replacement. It loses the "free on our turn" mode (rare for protection) but is otherwise the closest analog. **Recommendation: list Force of Will (no spend, already owned) and only buy FoN if the board explicitly wants a dedicated 4th copy.**

**Concrete adds — 11 cards** (✅ = owned per `priv_data/owned_formatted.csv` on 2026-05-12):

#### Fast mana (3 pieces)

| Card | Mana / Status | Owned? | Notes |
|---|---|---|---|
| Chrome Mox | {0} artifact | ✅ (shared with dark-dominion, genesis-protocol) | Exile a colored nonland card → that color mox. On GC list (+1 GC). T1 acceleration. |
| Mana Vault | {1} artifact, taps for {C}{C}{C} | ✅ (shared with eternal-agony, genesis-protocol, titan-convergence) | Untap-step lock OK in Atraxa — proliferate doesn't help untap it, but {C}{C}{C} on T2 is huge. On GC list (+1 GC). |
| Ancient Tomb | Land, {T}: {C}{C} | ✅ (shared with genesis-protocol, titan-convergence) | Trades 2 life for explosive mana. On GC list (+1 GC). Replaces a basic or a tapped utility land. |

Skipping **Grim Monolith** for budget (~$80, unowned) and **Lotus Petal** (one-shot, low impact in 4c). All 3 selected pieces are already owned virtually.

#### Tutors (4 pieces)

| Card | Mana | Owned? | What it finds | Notes |
|---|---|---|---|---|
| Demonic Tutor | {1}{B} sorcery | ✅ (shared with dark-dominion, eternal-agony) | Any card → hand | Premier black tutor. On GC list (+1 GC). |
| Vampiric Tutor | {B} instant | ❌ (~$25 buy) | Any card → top of library | Instant-speed, on GC list (+1 GC). Pair with end-step Atraxa proliferate. |
| Eladamri's Call | {G}{W} instant | ❌ (~$10 buy) | Creature card → hand | Instant-speed creature tutor. Fetches Tekuthal, Vorinclex, Necrogen Rotpriest. Cheap, deep redundancy. |
| Worldly Tutor | {G} instant | ❌ (~$25 buy) | Creature card → top of library | Instant-speed, cheaper-than-Eladamri activation, on GC list (+1 GC). Same finder role. |

Alternative if board wants to cut tutor spend further: drop **Worldly Tutor** ($25) — keep 3 tutors (DT + Vamp + Eladamri's Call). Loses one finder; still hits the DEC-205 reliability floor. Or substitute **Enlightened Tutor** ({W} instant, owned, shared with genesis-protocol + the-white-forge) which finds Sylvan Library / Skullclamp / Glistening Sphere / Skrelv's Hive instead of creatures. Worth considering as a 5th tutor slot since it's free (owned).

#### Free interaction / draw (4 pieces)

| Card | Mana | Owned? | Notes |
|---|---|---|---|
| Force of Will | {3}{U}{U}, pitch blue card + 1 life | ✅ (shared with dark-dominion, genesis-protocol) | On GC list (+1 GC). **Or substitute Force of Negation (~$25-35) if board prefers not to triple-share the FoW slot.** |
| Fierce Guardianship | {2}{U}, free if commander in play | ✅ (shared with dark-dominion, genesis-protocol, mutant-multiplication) | On GC list (+1 GC). Atraxa hits play often enough. |
| Deadly Rollick | {3}{B}, free if commander in play | ✅ (×3, shared with dark-dominion, eternal-agony, eternal-harvest) | Adding Creeping Corruption = 4th-deck slot, need 1 more copy (~$25) to satisfy physical inventory — or accept that virtual-share already covers all 4. |
| Necropotence | {B}{B}{B} enchantment | ✅ (shared only with eternal-agony) | On GC list (+1 GC). Premier B4 draw engine. Atraxa's lifelink offsets the life cost. |

#### Required cuts (~11 slots)

Soft-end-of-curve cuts identified for cut-list review:

1. **Wurmquake** — 5-mana sorcery, no body, no proliferate trigger
2. **Phyresis Outbreak** — partial board wipe, redundant with Toxic Deluge
3. **Norn's Choirmaster** — slow proliferate-on-attack, no immediate impact
4. **Expansion Algorithm** — slow proliferate engine, replaceable by Tekuthal-style triggers already in deck
5. **Grateful Apparition** — 1/1 evasive proliferator, weak body
6. **Hand of the Praetors** — anthem-only-for-infect, narrow (Necrogen Rotpriest does the broader job)
7. **Sword of Truth and Justice** — protection equipment, weaker than direct disruption + ramps post-Skullclamp
8. **Glistening Sphere** — slow corrupted payoff
9. **Sword's other slot OR Lightning Greaves** — keep Greaves for Atraxa protection
10. **Skrelv's Hive** — slow build-up
11. **Infectious Bite** — 1-poison-per-opp once, narrow

Final cut list to be picked once swaps are approved; aim for 11 cuts matching 11 adds.

**GC count after**: 3 → **9** (Cyclonic Rift + Rhystic Study + Teferi's Protection + Chrome Mox + Mana Vault + Ancient Tomb + Demonic Tutor + Vampiric Tutor + Worldly Tutor + Force of Will + Fierce Guardianship + Necropotence = **12 GCs**). Well into B4 territory.

**Spend (revised)**:
- Owned (virtual share, no buy): Chrome Mox, Mana Vault, Ancient Tomb, Demonic Tutor, Fierce Guardianship, Necropotence, Force of Will = **$0**
- Likely buy: Vampiric Tutor (~$25) + Eladamri's Call (~$10) + Worldly Tutor (~$25) = **~$60**
- Optional shared-but-tight slots (1 extra copy each if board wants physical not virtual): Deadly Rollick 4th copy (~$25), Force of Negation if FoW share rejected (~$25-35)
- **Net realistic spend: ~$60–120** (versus the ~$400 estimate in the original plan, which had assumed unowned baselines).

**Outcome**: expected median lethal shifts ~T8 → T6 (estimated; needs sim re-run after swap). Brings the deck inside the DEC-205 case-study band of lethalProxy ≥ 50% at T6.

**Risk**: changes the deck's feel from "fair infect midrange" to "tutor the kill." Board has historically pushed back on this style for some decks; confirm this commander gets the tutor treatment.

### Option B-budget — Path B with alternatives within EU pricing + availability rule (2026-05-12 board revision)

**Premise**: Path B's premium suite (Force of Will, Chrome Mox, Mana Vault, Ancient Tomb, Vampiric/Demonic Tutor, etc.) is fully blocked — either in another deck (excl. Genesis Protocol) or above EU € budget. Build the best B4-push achievable with budget-feasible, never-blocked alternatives.

**Honest outcome target**: median lethal T8 → ~T7 (lethalProxy ~35-45% at T6, ~60-65% at T7). This is **soft B4 (DEC-205 classification)**, not true B4. The expensive tutors and Mana Vault / Chrome Mox / Grim Monolith are mandatory for true B4 speed; without them, the deck can't reach the lethalProxy ≥ 50% at T6 threshold.

#### Availability audit performed 2026-05-12

| Candidate | Status |
|---|---|
| Mox Amber | ✅ free (not in any other deck) |
| Talisman of Curiosity / Hierarchy / Resilience | ✅ free |
| Sylvan Tutor, Diabolic Tutor, Profane Tutor | ✅ free |
| Pact of Negation, Slaughter Pact | ✅ free |
| Stubborn Denial, An Offer You Can't Refuse, Daze, Misdirection | ✅ free |
| Veil of Summer, Autumn's Veil | ✅ free |
| Sign in Blood, Read the Bones | ✅ free |
| Glistening Oil, Phyresis | ✅ free |
| Lotus Petal | ❌ blocked (dark-dominion) |
| Eladamri's Call, Worldly Tutor | ❌ blocked (mutant-multiplication) |
| Mystical Tutor | ❌ blocked (dark-dominion, mutant-multiplication) |
| Beseech the Mirror | ❌ blocked (dark-dominion) |
| Phyrexian Arena | ❌ blocked (dark-dominion) |
| Talisman of Indulgence, Fellwar Stone, Mind Stone | ❌ blocked |

#### Proposed adds (10 cards, ~€40-85 EU spread across two tiers)

##### Tier 1 — Core budget retune (~€35-50 EU)

| Card | EU est. | Role | Oracle text condensed |
|---|---|---|---|
| Mox Amber | ~€10-15 | Fast mana | {0} legendary artifact; {T}: add any color from your legendaries' colors. Atraxa is legendary — taps for any of WUBG once she's out. |
| Sylvan Tutor | ~€5-8 | Tutor (creature → top) | {G} sorcery. Finds Tekuthal / Vorinclex / Necrogen Rotpriest / Skithiryx / Triumph (no — Triumph is sorcery, won't grab). Wait — Sylvan only grabs creatures. |
| Diabolic Tutor | ~€1 | Tutor (any → hand) | {2}{B}{B} sorcery. Universal. Slow at 4 mana but unblocked. |
| Profane Tutor | ~€3-5 | Tutor (any → hand) | Suspend 2—{1}{B}. Cast T1, resolves T3 → tutored card by T3-T4. No hard-cast cost (suspend-only). |
| Stubborn Denial | ~€1 | Counter | {U}. Counter noncreature unless {1} paid. **Ferocious (you control 4+ power creature): counters unconditionally.** Atraxa is 4/4 — qualifies natively. |
| An Offer You Can't Refuse | ~€1-3 | Counter | {U} instant. Counter noncreature; opponent makes 2 Treasures. Cheap, fast, on-color. |
| Veil of Summer | ~€10-15 | Free protection | {G} instant. Draw a card if opp cast U/B this turn. Your spells can't be countered. You + perms hexproof from U/B until EOT. Premier B4 protection. |
| Glistening Oil | ~€1-2 | Infect aura | {B}{B} aura, enchanted creature has infect; -1/-1 counter on it each upkeep; **returns to hand from graveyard**. On Atraxa: 2 hits = 8 poison = lethal in 2 attacks. Self-recurs. |
| Phyresis | ~€1-2 | Infect aura | {1}{U} aura, enchanted creature has infect (no downside). Redundancy with Glistening Oil. |
| Sign in Blood | ~€1 | Card draw | {B}{B} sorcery. Target player draws 2; loses 2 life. Cheap, fast. |

**Tier 1 spend: ~€35-55 EU.** Expected outcome: median lethal T8 → T7.3 (lethalProxy ~30% T6, ~55% T7).

##### Tier 2 — Optional upgrade (+~€25-35 EU)

| Card | EU est. | Role | Why |
|---|---|---|---|
| Pact of Negation | ~€25-35 | Free counter | {0} instant. Counter target spell. Next upkeep pay {3}{U}{U} or lose. **Free** on the kill turn — pay-or-lose triggers on a turn that probably ends the game anyway. Closest budget-accessible FoW analog. |

**Tier 1 + Tier 2 spend: ~€60-90 EU.** Expected outcome: median lethal T7.1 (kill-turn protection improves resilience but doesn't accelerate the kill itself).

#### Cuts (10 slots)

| Cut | Reason |
|---|---|
| Wurmquake | 5-mana sorcery, no body, no proliferate trigger |
| Phyresis Outbreak | Partial wipe, redundant with Toxic Deluge |
| Norn's Choirmaster | Slow proliferate-on-attack, weak body |
| Expansion Algorithm | Slow proliferate engine, weaker than already-in Tekuthal |
| Grateful Apparition | 1/1 evasive proliferator, weak |
| Hand of the Praetors | Narrow infect anthem; Necrogen Rotpriest covers broader |
| Sword of Truth and Justice | Equipment, weaker than counters + draw at B4 speed |
| Glistening Sphere | Slow corrupted payoff |
| Skrelv's Hive | Slow build-up |
| Infectious Bite | Narrow 1-poison-per-opp once |

11 add slots vs 10 cuts → cut one of Glistening Oil/Phyresis if board prefers (keep Phyresis: no downside; or keep Glistening Oil: recurs from GY).

#### GC count after Tier 1+2

3 → **4** (adds Pact of Negation if included; otherwise stays at 3). Pact of Negation **is not on the official GC list** — verified via `data/game-changers.json`. So the deck would still be at 3 GCs and the B4 label remains a *user choice* not a *rule consequence*.

If board wants ≥4 GCs to force B4-by-rule, the only budget-feasible candidates with availability would need separate research (e.g., Crop Rotation, Drannith Magistrate, Notion Thief, Orcish Bowmasters, Smothering Tithe — many are >€15 in EU). Surface as a follow-up if desired.

#### Risks / honest caveats

1. **This is soft B4, not true B4.** The promise of T6 median kill needs the premium suite. Don't expect Path B-budget to feel like a real B4 deck against pods that are actually B4.
2. **Mox Amber is conditional**: useless before T3-T4 unless we mulligan for it + Atraxa. Adds variance.
3. **Glistening Oil's downside** (-1/-1 counter on enchanted creature each upkeep) means it's a kill-turn aura on Atraxa, not a permanent buff. Atraxa dies in ~3 upkeeps if no proliferate-counter intervention.
4. **Suspend tutor (Profane Tutor) commits early.** Cast T1, locked into 3 turns of upkeep ticks. Opponents see it coming.
5. **Sim re-run required** after any swaps approved to verify the T8 → T7 projection actually holds. The estimate is a heuristic, not a measurement.

### Option C — Add a tutored Triumph-of-the-Hordes finisher line (mid-budget hybrid)

**Premise**: don't go all the way to cEDH-tier card prices, but specifically address the "draw the finisher" reliability problem. Keep the deck's infect identity intact.

**Concrete adds (~6 cards)**:

| Card | Role | Cost | Why |
|---|---|---|---|
| Vampiric Tutor | Tutor | ~$25 | Finds Triumph or Tekuthal |
| Eladamri's Call | Tutor (creature) | ~$10 | Instant-speed Tekuthal / Vorinclex / lord |
| Worldly Tutor | Tutor (creature) | ~$25 | Same role, redundant for consistency |
| Survival of the Fittest | Tutor (creature) | ~$40 | Repeatable creature dig + GY enabler |
| Chrome Mox | Fast mana | ~$80 | T1 acceleration; adds 1 GC (Force/Fierce optional separately) |
| Grim Monolith | Fast mana | ~$80 | T2 explosive turns |

**Required cuts (~6 slots)**: Wurmquake, Phyresis Outbreak, Thrummingbird or Grateful Apparition, Expansion Algorithm, Norn's Choirmaster, Hand of the Praetors or one redundant lord.

**GC count after**: 3 → ~4 (just over the B4 floor — actually forces B4 by rule).
**Spend**: ~$260.
**Outcome**: expected median lethal shifts ~T8 → T6.5 (estimated). Closer to soft-B4 than true-B4, but earns the label honestly.
**Risk**: middle path — pays the tutor money without fully committing to free-spell defense.

## Recommendation

**Option A** is the lowest-friction path and produces an honest label. The deck is well-built for what it is; the only sin is the `gameChangers: 5` data error and the aspirational strategy text. A B3 Atraxa infect deck with this much proliferate density and 11 pieces of interaction is a strong, respected build — not a downgrade in identity.

**Option B** is the right answer if the board values the B4 label as a deliberate power statement (and is willing to spend ~$400+ to back it up). DEC-205 shows the playbook works.

**Option C** is the compromise: meaningful speed gain at half the budget, but lands as "soft B4" not "true B4."

If the board wants to keep the B4 label without spending — that's a fair user preference, but the `gameChangers` field still needs correcting (5 → 3) and the strategy text still needs fixing (remove false free-spell claims), because both are factual errors independent of the bracket decision.

## Files touched

**Option A**:
- `data/index.json` — `bracket: "4"` → `"3"`
- `data/commanders/creeping-corruption/deck.json` — `bracket`, `gameChangers: 5 → 3`, `guideContent.strategyOverview` cleanup
- Optional re-run: `python scripts/refresh_card_pool.py --deck creeping-corruption`

**Option B / C**:
- All of Option A
- `data/commanders/creeping-corruption/deck.json` — `decklist[]` swaps (6 or 11 cards), `sources[]` entries for each add
- `data/commanders/creeping-corruption/metrics.json` — re-run via `scripts/compute_deck_metrics.py`
- `data/commanders/creeping-corruption/simulation.json` — re-run via `scripts/mana_simulation_creeping_corruption.py` (or generic runner)
- `python scripts/validate_deck_json.py --deck creeping-corruption`
- `python scripts/refresh_card_pool.py --deck creeping-corruption`

## Open decisions for board

1. Bracket label: keep at 4, or reclassify to 3?
2. If keeping at 4: Option B (full retune, ~$400) or Option C (tutored hybrid, ~$260)?
3. Strategy text + `gameChangers` field correction is required regardless — confirm.

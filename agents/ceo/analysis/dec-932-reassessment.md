# DEC-932 — Titan Convergence Trigger-2 re-assessment (PASS, two swaps proposed)

Date: 2026-09-29. Assessor: CEO. Baseline: DEC-931 apply (commit `9d3e67f`, the current HEAD). Pre-DEC-931 state (`0b4dd9f`) is shown as a second reference column because the baseline and the current files are the same commit.

## Verdict

**PASS — the deck meets the fleet bar as it stands.** Global health 65 (normalized 73), sim health 72.3 (B), strategy ceiling ok, GC count 2 (uncapped at 4−), validator clean, no live stale references. Two swaps go to the board on a verdict card because the DEC-931 closing diff deferred both cards to this re-assessment as "first in line" for the removal gaps, and both close a `gaps[]` entry on the in-memory projection:

- **A. +Kozilek's Command / −Worn Powerstone** — removal-spot 4 → 5, card-draw 2 → 2.5, global 65 → 67.
- **B. +Calamity of the Titans / −Wayfarer's Bauble** — removal-board 2 → 3 (closes the gap), global 65 → 68. Both together: global 70 / normalized 75, gaps 4 → 3.

The swap-round counter resets to 0 at the commit that closes this issue (the apply commit if either line is approved, otherwise the report commit).

## Rounds covered (3 board-approved rounds since the DEC-394 relabel)

1. DEC-467 — +Wastes / −Idol of Oblivion (commit `c62dc5c`)
2. DEC-467 — +2 Wastes / −Cloudstone Curio, −Mirage Mirror (commit `44e731d`)
3. DEC-931 — +Emrakul, the Exigent Doom / −It That Betrays (commit `9d3e67f`)

## 1. Card pool refresh + top-50 triage

`refresh_card_pool.py --deck titan-convergence` ran today at 15:56Z: mirror 2026-09-29, EDHREC rates fetched today (246 cards), 200 candidates unchanged, `gaps[]` = card-draw 2/10, removal-spot 4/8, removal-board 2/3, recursion 2/3. Ramp reads 20.5 against a target of 10 and wincon 10 against 2, so any add should come out of a ramp slot, not a cascade trigger (DEC-371 finding: 7+ MV density is the engine; do not cut triggers).

Every top-50 non-deck candidate has a line. Oracle text for each named card was verified on Scryfall today.

**Standing dispositions (not reopened):**
- It That Betrays 79.8% — DEC-931 board cut.
- Flayer of Loyalties 76.4%, Endbringer 61.0% — DEC-371 cuts (win-more threaten; 6-MV no-trigger draw with a {C}{C} tax).
- Idol of Oblivion, Mirage Mirror 41.5% — DEC-467 board cuts.
- Dreamstone Hedron 59.5% — DEC-371 defer (6-MV no-trigger dead zone), stands.
- Hazoret's Monument — DEC-371 reject (red-only reduction; locked in Pyre & Panic).
- Rogue's Passage 69.7% — deliberate earlier cut recorded on the Liquimetal Torque highlight ("unblockable is redundant with menace, trample, flying and annihilator across 8+ Eldrazi"). Stands.
- Palladium Myr 73.5%, Everflowing Chalice 55.5%, Solemn Simulacrum 50.9% — DEC-931 reject class (slower than the fast-mana suite; ramp is at 205% of target). Skittering Cicada 72.5% — reject: a third flash enabler on a 3-MV creature, behind Liberator, Vedalken Orrery and Emergence Zone.

**Include (proposed — see verdict card):**
- **Kozilek's Command** 47.0% ({X}{C}{C} instant, choose two: X Spawn / scry X then draw / exile creature MV ≤ X / exile up to X graveyard cards). Instant-speed exile plus a draw in the deck's two thinnest roles. The Spawn mode is a mana sink and a finisher: with Glaring Fleshraker on the battlefield each Spawn entering deals 1 damage to each opponent, so X Spawn is X damage to each opponent (trigger frequency: once per Spawn, own turn or instant speed). A cascade hit (X = 0) still draws a card. Cut **Worn Powerstone**: enters tapped, weakest of the 11 rocks, zero prose references. Ramp 20.5 → 19.5. Not owned (no price-index entry; information only).
- **Calamity of the Titans** 63.5% ({4}{C}{C} sorcery; reveal a colorless creature card from hand; exile each creature and planeswalker with MV less than the revealed card's). Exile-based, so it clears indestructible bodies, and it hits colorless creatures, artifact creatures and planeswalkers that All Is Dust and both Ugins miss. Reveal uptime (hypergeometric on 99 cards): at least one of the 13 creatures with MV ≥ 7 in hand is 64% with 7 cards seen, 81% at 11, 86% at 13; any of the 19 creatures is 79% to 95% over the same window. Symmetric: it exiles our own creatures and planeswalkers below the reveal, including Zhulodok (MV 6, returns to the command zone, recast at 8), so it is a reset before redeploying; titans at or above the reveal survive. MV 6 means no cascade. Cut **Wayfarer's Bauble**: 3 mana in total for a tapped Wastes on turn 3, the slowest ramp piece; one category list and one highlight are cleaned on apply. Thought Vessel projects identically but produces on turn 2, so Bauble is the cut. Owned, 1 free copy.

**Defer (with note):**
- Ultima, Origin of Oblivion 52.2% — "whenever you tap a land for {C}, add an additional {C}": +1 per land tapped, so +5 to +7 mana a turn on a 5-MV 4/4 flyer, more raw output than Extraplanar Lens's Wastes-only doubling. Creature (DEC-474 L10) and ramp is over target. First in line if the board wants a ramp-for-ramp upgrade over Extraplanar Lens. Not owned.
- Abstruse Archaic 46.1% — {1},{T}: copy an activated or triggered ability from a colorless source: Zhulodok's cascade trigger, titan cast triggers, Ugin −X, Eye of Ugin. Fires once per turn cycle (own untap step). 4-MV creature; engine role already carries 14 cards. Next engine slot. Owned, 1 free copy.
- Tezzeret, Cruel Captain 12.7% — 0: untap Basalt Monolith or Mana Vault each turn (+3 mana, no Vault upkeep tax); −3 tutors Sol Ring, Mana Vault, Voltaic Key or Sensei's Divining Top. Next engine slot, with Archaic.
- Spawnbed Protector 37.4% — 7-MV cascade body; each end step returns an Eldrazi to hand and makes two Scions (2 damage per turn with Fleshraker). Addresses the recursion gap (2/3). Competes with the titan roster for a 7+ slot; second in line after the two proposed lines.
- Null Elemental Blast 54.8% — {C} counter or destroy multicolored. Meta-conditional; uptime is not derivable from deck data. Defer.
- Ulamog, the Infinite Gyre 65.6%, Breaker of Creation 37.1% — titan slots; wincon is 10 against a target of 2 and the Sire of Seven Deaths highlight records Gyre as replaced. Defer.
- Oblivion Sower 57.2% — 6-MV no-trigger ramp, same class as Dreamstone Hedron. Defer.
- Herald's Horn 23.4%, Gathering Stone, Cloud Key, Jhoira's Familiar — cost reducers; Urza's Incubator, It That Heralds the End, Foundry Inspector and Ugin, the Ineffable already cover this. Horn's upkeep draw hits on roughly 17 of 99 cards (Eldrazi creatures and kindred spells). Defer as a class.
- Eldrazi Confluence 28.3%, Skittering Invasion 22.7%, Ingenuity Engine 10.0% (7-MV artifact with its own cascade: three cascades from hand with Zhulodok), Metalworker 18.8% — defer; none beats an incumbent in its role.
- Manabase lands (Tomb of the Spirit Dragon 65.7%, Temple of the False God 61.6%, Arcane Lighthouse 54.7%, Guildless Commons 51.0%, Sea Gate Wreckage 44.4%, Geier Reach Sanitarium 43.1%, Arch of Orazca 42.7%, Mage-Ring Network 41.9%) — see section 5; defer all. Arch of Orazca (owned, 1 free) is first in line if Mirrorpool is ever cut.

**Reject (with reason):**
- Bane of Bala Ged 59.5% — attack-gated (×1 per cycle) exile on a vanilla 7-drop; weaker than every 7+ slot.
- Eldrazi Conscription 31.8% — 8-MV aura, two-for-one against removal, win-more.
- Twins of Discord, Ulamog's Crusher, Pathrazer of Ulamog 44.1%, Desolation Twin, Deathless Behemoth, Eldrazi Ravager, Blight Herder — bodies below the titan roster, no cast trigger of note.
- Omnath, Locus of the Void — 7-MV 6/6 with a landfall ×1 per turn; no cast trigger.
- The Immortal Sun — switches off the deck's own four planeswalkers.
- Gruesome Slaughter — one-shot sorcery-speed fight.
- Millikin, Pearl/Ruby/Sapphire Medallion — colored cost reduction or mill ramp with no payoff.
- Moonring Mirror, Clock of Omens, Phyrexian Devourer — no line in the deck's combos.
- Sword of Forge and Frontier, Nazgûl Battle-Mace — combat-damage-gated equipment.
- Eldritch Immunity 41.9% — protection reads 4/4; Not of This World already counters the targeting for free.
- Expedition Map 43.9% — Urza's Cave and Thespian's Stage already find Tron from the land slots; tutor reads 3.5/4.

## 1b. Archetype recipes

`archetypes` = eldrazi-colorless, ramp-big-mana. `data/archetype-recipes/` holds `ramp-bigmana` (live) but the deck tag is `ramp-big-mana` (tag/recipe id mismatch, see the archetype-tags-vs-recipe-ids note) and there is no eldrazi-colorless recipe. No recipe sweep ran; recorded here per the DEC-238 skip rule.

## 2. Before/after

| Measure | Pre-DEC-931 (`0b4dd9f`) | Baseline = now (`9d3e67f`) | Projection A+B (in memory, no files written) |
|---|---|---|---|
| manabase_health | 69 | 69 | 69 |
| role_coverage | 81 | 81 | 88 |
| curve_health | 0 | 0 | 0 |
| interaction_density | 96 (13.5 / 14) | 96 (13.5 / 14) | 118 (16.5 / 14) |
| gameplan_cohesion | 40 | 40 | 40 |
| resilience_health | 90 | 90 | 90 |
| **global_health** | **65 / norm 73** | **65 / norm 73** | **70 / norm 75** |
| gaps[] | 4 | 4 | 3 (removal-board closed) |
| sim deckHealth (100k) | 72.4 (B) | 72.3 (B) | measured on apply |
| sim manaReliability | 85.4 | 85.2 | expected to dip: rocks 11 → 9 |
| threats / interaction / combo / cmdr-indep | 53.1 / 75.8 / 51.0 / 88.7 | 53.1 / 75.8 / 51.0 / 88.7 | — |
| comboLethal T6/7/8 | 13.5 / 17.9 / 22.4 | 13.6 / 18.1 / 22.7 | — |
| lethalProxy T6/7/8 | 14.1 / 31.0 / 51.5 | 14.7 / 32.0 / 52.4 | — |
| commander cast by T6 | 90.9% | 90.9% | — |
| win_turn best/typical/contested | 7 / 8 / 9 | 7 / 8 / 9 | — |
| Game Changers | 2 | 2 | 2 |

Single lines: A alone gives global 67 / norm 74 (removal-spot 5.0, card-draw 2.5, interaction 104); B alone gives 68 / norm 74 (removal-board 3.0, interaction 111). Curve stays 0 because the metric's 4.2 average-MV target is an archetype mismatch (DEC-371 finding; 7+ density is the engine). Measurement note, no change proposed: Desecrate Reality is tagged recursion but is three-target exile in function; retagging it removal-spot/recursion would read global 66 with recursion 1.5/3.

## 3. Bar check

Bracket 4−, shell 69, payoff 32.0% (lethalProxy at T7); `validate_strategy_ceiling.py` reports ok, no warnings. Fleet bar (≥ B3+/4−) met. `check_game_changers.py --offline`: ts mirror ok (53), fleet recount 0 problems; deck at 2 GCs (Mana Vault, Ancient Tomb), uncapped at 4−. Neither proposed card is a Game Changer.

## 4. Stale-reference sweep

Swept `guideContent`, `categories`, `winConditions`, `highlights`, `synergies` for the four names cut since DEC-394 — Idol of Oblivion, Cloudstone Curio, Mirage Mirror, It That Betrays: **0 live mentions**. The only hit is the dated DEC-931 decision string in the Emrakul, the Exigent Doom highlight `sources`, which stays. `validate_deck_json.py`: 253 references validated, clean.

Numeric and factual claims re-checked against the current 99: "10+ Wastes" (13), "26+ artifacts" (34 including artifact creatures), "5 Urza's lands" (Mine, Power Plant, Tower, Cave, Workshop all present), Portal to Phyrexia "sacrifices 3 creatures" (oracle-true), Karn "retrieve artifacts from exile" (oracle-true). One staleness to correct at the closing commit: the Sire of Seven Deaths highlight says it is the "only lifegain source in colorless"; Ugin, Eye of the Storms (+2: gain 3 life and draw) was added later.

## 5. Deck Review Checklist items

**EDHREC closing diff** (246 rated cards, fetched today). Started from the DEC-931 apply-report list; every absentee at 40% or more has a line above. Names not on that list and triaged today: Abstruse Archaic 46.1% (defer), Sea Gate Wreckage 44.4%, Geier Reach Sanitarium 43.1%, Arch of Orazca 42.7%, Mage-Ring Network 41.9% (lands, defer), Pathrazer of Ulamog 44.1% (reject), Expedition Map 43.9% (reject), Urza's Saga 42.5% (locked to the-white-forge; colorless-only Saga would fit but the untapped count is already 38/39 — defer), Eldritch Immunity 41.9% (reject), Mirage Mirror 41.5% (DEC-467 cut).

**Manabase audit** (`manabase_check.py`): lands 39.0 (board floor from DEC-467; the metric target of 43.2 follows the 5.48 average MV and is not realistic with Tron plus 11 rocks), untapped 38, fetch 0, no colour census (colorless). Mirrorpool is the only land that enters tapped; its copy modes (a Rise of the Eldrazi copy, or a 6-mana Blightsteel token) keep it. Owned utility candidates rank optimistically (cost-gated draw or storage); no deficit to fix. Defer all; Arch of Orazca first in line.

**Hoser coverage.** Top hate classes: artifact hate against the 11-rock and Basalt/Rings/KCI suite, and nonbasic-land hate against Tron, Eldrazi Temple and Ancient Tomb (26 nonbasic lands).
- Enchantment-carried (Stony Silence, Blood Moon, Back to Basics, Rest in Peace): All Is Dust (the controller sacrifices it), Ugin, the Ineffable −3, Ugin, the Spirit Dragon −X, Ugin, Eye of the Storms (exile on cast and on every later colorless cast), Scour from Existence, Spine of Ish Sah, Rise of the Eldrazi, Desecrate Reality (even MV only) — 8 answers.
- Artifact-carried (Null Rod, Grafdigger's Cage, Torpor Orb, Damping Sphere): the Ugins and All Is Dust miss colorless; Scour, Spine, Rise, Desecrate Reality (even MV), Blast Zone (X = 1 or 2) — 5 answers. Calamity of the Titans would add creature-carried colorless hosers (Collector Ouphe) and an opposing Karn to the covered set.
- Under Blood Moon the 13 Wastes and the rocks still produce {C}; the deck is slowed, not locked.
- Creature-carried: Titan's Presence, Warping Wail (power or toughness 1 or less), plus the exile suite. Pass.

**Commander dependency.** Sim commanderIndependence 88.7, commanderDependency low (11.3); no combo line needs Zhulodok. Under a Darksteel Mutation-class lock (Zhulodok stays on the battlefield, CR 903.3d — no zone change, no command-zone return): Not of This World counters the aura spell for free (it targets a creature with power 7), and once resolved the aura is a colored permanent for All Is Dust, either Ugin's minus, Ugin, Eye of the Storms' cast trigger, Scour or Spine. Erratic Portal returns Zhulodok to hand (or the command zone, CR 903.9a) and drops the aura. Pass.

**Permanent-type durability.** Engines sit mainly on artifacts (Rings, Basalt, Forge, Top, KCI, Portal, Clock) and one enchantment (Echoes of Eternity); the creature engines (Fleshraker, Inspector, Liberator, Construct) are known exposure. Both proposed adds are instants or sorceries, so they add no permanent exposure. Pass.

## Disposition

PASS, no card changes. The board answered on 2026-09-30: "no swap for now for this deck" (comment fc5f17b8; verdict card 25851319 cancelled). Lines A (+Kozilek's Command / −Worn Powerstone) and B (+Calamity of the Titans / −Wayfarer's Bauble) move to the deferred list with their projections on record; do not re-propose them without a new trigger. The closing commit carries the Sire of Seven Deaths lifegain prose correction and the web cache bump (v135). The swap-round counter resets to 0 at that commit; the next Trigger-2 fires after three new board-approved rounds.

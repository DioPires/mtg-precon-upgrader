# DEC-548 — Hoard and Bleed full re-assessment (2026-08-22)

Baseline: commit `eccd0bd`, deck at global 96 / gaps 0 / bracket 4- / 0 GC / brewing.
All checks re-run on the fresh Scryfall mirror (2026-08-21 corpus). Zero deck files written.

## Verification summary — the DEC-543 architecture holds

- **Commander oracle re-verified.** Smaug, Wicked Worm: ETB Treasures = opponents' artifact count (tapped); "Whenever you cast a spell, if mana from a Treasure was spent to cast it, you draw a card and lose 1 life." The prose claim (once per spell, not per Treasure) is correct.
- **Loop arithmetic re-verified.** Skeleton + Ashnod's Altar + Pitiless Plunderer nets +1 colorless per iteration. Spellbook `included[]` still 5 combos on corpus 2026-08-21.
- **Payoff gating re-verified** (Mirkwood Bats create-or-sacrifice-token; Marionettes artifact-you-control; Weftstalker "another creature or artifact you control enters" — all live reads).
- **Win-condition 2 math re-verified**: 1 instruction under Xorn→Manufactor ordering = 6 tokens = 12 damage + 6 life loss with the three payoffs out.
- **Metrics on fresh pool**: global 96 ± 2, mana 91, roles 102, curve 99, interaction 120, cohesion 57, resilience 94, gaps 0.
- **Strategy ceiling**: shell 91, payoff 50.8%, no warnings.
- **Manabase**: 91; audit surfaces nothing above the round-9 record (Takenuma rejected round 7; fetch candidates score below current lands). No land change proposed.

## Structural finding — 0 Game Changers is a habit, not a rule

Bracket 4- has no GC cap (DEC-369 caps only verdant-tide and pyre-and-panic; the ≤3 cap applies to brackets ≤3). The deck's 0-GC state accumulated from price-bar-era rejects, before the board's "no budget ceiling, decide card by card" clarification. With ownership resolved (free pool = owned minus non-brewing commitments), three GC upgrades cost EUR 0.00.

## Proposed round-10 swaps (all free owned copies)

| # | IN | OUT | GC | Why | Metric effect (in-memory projection, no writes) |
|---|----|-----|----|-----|--------------------------------------------------|
| S1 | Demonic Tutor (1 free) | Grim Tutor | yes | {1}{B} vs {2}{B}+3 life for the identical effect; strictly better; tutor count stays 4 | global 96, all components unchanged |
| S2 | Bolas's Citadel (1 free) | Night's Whisper | yes | Repeatable card advantage (avg nonland MV 2.85); Sheoldred offsets life; {T}+sac-10-nonland-permanents = 10 drain each opponent, Treasures count; artifact (Hellkite twenty, KCI, Fireweaver) | global 96, curve 99→97 |
| S3 | Orcish Bowmasters (1 free) | Fatal Push | yes | Flash; entry ping + 1 damage per opponent extra draw (3 opponents' wheels/draw engines); Orc Army amass = growing body; Army is a creature token, so its sacrifice fires Mirkwood Bats | global 96, removal-spot 119→112 (9.0 weighted vs target 8), cohesion 57→58 |
| S4 | Fake Your Own Death (3 free) | Lotus Petal | no | Protection is the worst role (3.0/4, score 75). {1}{B} instant saves a combo piece from wipe or spot removal, returns it + a Treasure; the return re-triggers Weftstalker and re-banks a Plunderer Treasure | **global 96→97**, protection 75→100, resilience 94→100, ramp 120→110 (11.0 vs target 10) |

All four together: **global 97, gaps 0, roles 103, curve 96, resilience 100. Cost EUR 0.00. GC 0→3.**

Honest costs, stated:
- Citadel top-casts pay life instead of mana, so they never trigger Smaug (no Treasure mana spent). It is card advantage and a finisher, not a Smaug engine. {B}{B}{B} at MV 5 against 27.1 B sources is castable but the heaviest pip ask in the deck.
- Cutting Fatal Push removes the cheapest instant creature answer; 8 primary spot answers remain (weighted 9.0 vs target 8).
- Cutting Lotus Petal removes a turn-1 ritual; Sol Ring + 5 rocks + Treasure instants remain the fast-mana suite.
- Demonic Tutor cut requires prose edits: strategyOverview life-cost list names Grim Tutor; Tutors category says "none of them a Game Changer".

## Optional purchase tier (0 free copies; price on request, not quoted from memory)

Vampiric Tutor, Jeska's Will, The One Ring. Each is a real power add at bracket 4; each needs a purchase and a cut. Deferred until the board asks.

## GC list triage (Rakdos-relevant, all 53 checked)

INCLUDE: Demonic Tutor, Bolas's Citadel, Orcish Bowmasters (S1–S3).
BUY-OPTIONAL: Vampiric Tutor, Jeska's Will, The One Ring.
DEFER: Necropotence (1 free copy, but skip-draw + heavy life competition; note Necro's put-in-hand is NOT a draw, so no Sheoldred triggers), Mana Vault / Grim Monolith / Chrome Mox / Mox Diamond (colorless or card-disadvantage fast mana, 0 free), Underworld Breach (combo enabler needing a dedicated shell), Gamble (1 owned, committed).
REJECT: Ad Nauseam (avg MV 2.85 is far above Ad Nauseam shells; the deck already bleeds), Imperial Seal (sorcery Vampiric, unowned), Lion's Eye Diamond (only good with Breach lines), Tergrid (forced-sacrifice density ~1 card: Braids), Ancient Tomb (colorless-only land + 2/turn damage in a bleeding deck; committed to titan-convergence).

## Fresh top-50 candidate triage (new names only; DEC-543 verdicts stand unchanged)

INCLUDE: Fake Your Own Death (S4).
DEFER: Soul-Shackled Zombie (3 free; one-shot targeted graveyard hate + 2 drain — the candidate if the board ever wants a second graveyard answer next to Bojuka Bog), Atsushi, the Blazing Sky (1 free; death = 3 Treasures is real outlet fodder; no slot beats it today), Fable of the Mirror-Breaker (0 free; Treasure half attack-gated, Kiki half copies Manufactor — power without a slot), Mogis, God of Slaughter (durable enchantment drain ×3/cycle per DEC-474 L10 durability, but 4 mana off-plan and 0 free).
REJECT — attack/combat-gated (deck does not attack; Smaug-the-Magnificent precedent): Postmortem Professor, Sanguine Syphoner, Typhoid Mary, General Kreat, Kardur (attacking-creature-death), Send in the Pest.
REJECT — creature-death-gated (deck sacrifices Treasures; strategy-record precedent for Blood Artist/Zulaport/Bastion): Blood Artist, Zulaport Cutthroat, Bastion of Remembrance, Grave Venerations (plus monarch liability), Sephiroth (also needs 4 resolutions/turn to flip), Gimli (opponent-creature-death), Lobelia (opponent death-from-battlefield that turn).
REJECT — lifegain-gated (only repeatable gain is Sheoldred, 1 of 99): Marauding Blight-Priest, Starscape Cleric, Leech Collector.
REJECT — rate/uptime: Glóin (once-per-turn Treasure vs uncapped Storm-Kiln), Melancholic Poet (~6 creature-targeting spells in 99), Dimension X Pizzasaur, Hazel's Nocturne (one-shot vs Phyrexian Reclamation), Sinister Monolith, Twinflame, Coin of Mastery, Impulsive Pilferer, Crypt Ghast (~8 Swamp-typed sources), Fall of Cair Andros, Glaring Fleshraker (tokens are not cast; colorless-spell density low), Agate Instigator and Coruscation Mage (Fireweaver's artifact-entering trigger is strictly denser than creature-entering or cast-gated pings), Vivi's Persistence, Witch's Mark.
REJECT — consistency with prior board calls: Carrion Feeder (weak payoff-per-activation, same as Yahenni/Umbral Collar Zealot), One Ring to Rule Them All (chapter II destroys our own nonlegendary payoff board).

## Prose staleness found (fix rider on next approved edit)

1. strategyOverview: "average mana value of the 59 nonland cards is 2.92" — actual is 2.85 after round 9 (Revel 5 MV out, Idol 2 MV in).
2. highlights: Sheoldred `price` reads "97.33" without the currency marker every other entry uses.
3. If S1 lands: Tutors category sentence "none of them a Game Changer" and the strategyOverview Grim Tutor mention.
4. If S3 lands: Interaction category "Eight spot answers" count.

## Post-approval work list (per approved swap)

Apply swaps + prose riders → `refresh_card_pool` → `compute_tokens` (Bowmasters adds an Orc Army token) → three Combo Lab artifacts → `card-metadata.json` + re-sim (`mana_simulation_hoard_and_bleed.py`) → metrics → `validate_deck_json` → EDHREC closing diff on the changed 99 → commit per approval.

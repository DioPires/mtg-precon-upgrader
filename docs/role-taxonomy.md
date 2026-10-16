# Role Taxonomy (DEC-90 P7.1)

Canonical role vocabulary for `decklist[].primary_role` and `decklist[].secondary_role`. Closed set — anything outside this list must be added here first.

The 15 roles are deliberately coarse. They power deterministic deck metrics (manabase health, role coverage, gameplan cohesion); finer distinctions live in the candidate-pool playbook, not in roles.

## The 15 roles

| Role | Definition | Examples |
|---|---|---|
| `land` | Card with `Land` in `type_line`. Includes MDFCs (see `is_mdfc_land`). | Command Tower, Bojuka Bog, Shelldock Isle |
| `ramp` | Adds mana, fetches lands, or accelerates land drops. | Sol Ring, Cultivate, Birds of Paradise |
| `mana-fixing` | Color-fixes without net acceleration (taplands, filter lands as utility, etc.). Use as **secondary** when a card both fixes and ramps. | Reflecting Pool, Path of Ancestry |
| `card-draw` | Nets ≥ +1 card in hand, or draws repeatably. Net-zero loot/filter effects do not qualify (see Card-draw classification). | Rhystic Study, Night's Whisper, Esper Sentinel |
| `tutor` | Searches library for a specific card or category. | Demonic Tutor, Worldly Tutor, Eladamri's Call |
| `removal-spot` | Targeted answer to one permanent. A spell that can target only a land is not `removal-spot`. | Swords to Plowshares, Beast Within, Pongify |
| `removal-board` | Affects multiple permanents (sweeper / mass bounce). | Wrath of God, Cyclonic Rift, Toxic Deluge |
| `counterspell` | Counters a spell. Only counted toward role coverage when blue ∈ color identity. | Counterspell, Force of Will, Mana Drain |
| `protection` | Protects own permanents (hexproof, indestructible grants, regeneration, save effects). | Heroic Intervention, Teferi's Protection, Lightning Greaves |
| `recursion` | Returns cards from graveyard to hand/battlefield/library. | Eternal Witness, Reanimate, Sun Titan |
| `payoff` | Rewards executing the deck's archetype but isn't itself the win. Often the engine's "fuel-burner." | Tendrils of Corruption (in mono-B drain), Coat of Arms (in tribal) |
| `wincon` | Closes the game. See `wincon_style` for category. | Craterhoof Behemoth, Thassa's Oracle, Triumph of the Hordes |
| `engine` | Repeatable value or resource generator. The deck's heart. | Meren of Clan Nel Toth, Esika's Chariot, Smothering Tithe |
| `threat` | Standalone pressure piece — must be answered, but not specifically a wincon or engine. | Questing Beast, Inferno Titan |
| `utility` | Tools that don't fit above (graveyard hate, tax effects, anthems, sac outlets, etc.). | Carrion Feeder, Grafdigger's Cage, Anointed Procession |

## Two roles per card

- `primary_role` — the **single** strongest reason the card is in this deck. Required.
- `secondary_role` — optional second function. Use when the card meaningfully covers a second role (e.g. Sun Titan = `recursion` primary, `threat` secondary; Solemn Simulacrum = `ramp` primary, `card-draw` secondary).

Roles are **deck-contextual**, not card-intrinsic. Eternal Witness in a graveyard-reanimator deck is `engine`; in a value midrange deck it might be `recursion`.

## Tutor classification

Use `tutor` for library-search effects that find a specific card or a non-mana-development category, including hand tutors (Demonic Tutor, Worldly Tutor), graveyard tutors (Entomb, Buried Alive), and battlefield tutors (Finale of Devastation, Whir of Invention). One-shot tutors are usually `primary_role: "tutor"`.

Use `secondary_role: "tutor"` when the card's primary role is structurally dominant:

- Repeatable engine tutors such as Birthing Pod, Oswald Fiddlebender, Fauna Shaman, or Survival of the Fittest are `engine` primary and `tutor` secondary.
- Lands remain `land` primary. Utility lands that tutor a nonland card or unrestricted land card, such as Urza's Saga, Eye of Ugin, Sanctum of Ugin, Inventors' Fair, or Urza's Cave, use `secondary_role: "tutor"`.
- Modal or secondary-use cards keep their main role primary and use `tutor` secondary when the tutor mode is meaningful, such as Muddle the Mixture's transmute mode.

Land-search convention: basic/typed land ramp and fetchlands stay `ramp` or `land`, not `tutor`. Unrestricted land-card search that can find utility lands, such as Crop Rotation, Sylvan Scrying, or Wight of the Reliquary's land mode, counts as `tutor`; add `ramp` secondary when it also accelerates mana by putting the land onto the battlefield.

## Card-draw classification (DEC-478)

`card-draw` as a primary role requires one of:

- **Net ≥ +1 card.** Count the card itself as spent. Night's Whisper spends one card and draws two, so it nets +1 and qualifies. Divination nets +1. A cantrip that draws exactly one card nets 0 and does not qualify. A draw of one card that the card gives once, such as an enters trigger, cycling or one Clue token, nets 0 too.
- **Repeatable draw.** A permanent or engine that draws over multiple turns qualifies regardless of per-trigger netting. Rhystic Study and Esper Sentinel qualify even when a single trigger only draws one card.

**Net-zero loot and filter effects are not `card-draw`.** Faithless Looting-class effects (draw N, discard N) and pure filters (scry/surveil riders) select cards but do not add them. Tag them `utility` by default.

**Graveyard-deck exception.** In a deck that uses the graveyard as a second hand (reanimator, dredge-style value), a looter genuinely adds resources — the cards it discards stay playable. Tag it `engine` in that deck context. This follows the "roles are deck-contextual" rule above, and an `engine` tag feeds the `gy_second_hand` resilience component in [`deck-metrics.md`](deck-metrics.md), which counts exactly the `recursion`/`engine`-tagged cards.

This is a definition change only (DEC-474 review, lesson L2). The role-coverage targets for `card-draw` (8 at B3, 10 at B4, 12 at B5) are unchanged.

## Mapping from existing inconsistent vocab

The current `role` field across `data/commanders/*/deck.json` uses 26 distinct values. Migration rules:

| Old value(s) | New `primary_role` | Notes |
|---|---|---|
| `land`, `lands` | `land` | |
| `ramp` | `ramp` | |
| `card-draw`, `draw` | `card-draw` | |
| `tutor` | `tutor` | |
| `removal` | `removal-spot` | Default; re-tag `removal-board` if the card is a sweeper |
| `board-wipe`, `board-wipes` | `removal-board` | |
| `counter-spells` | `counterspell` | |
| `protection` | `protection` | |
| `recursion`, `reanimation` | `recursion` | `reanimation` may warrant `engine` primary if the card is a repeatable engine (e.g. Meren) |
| `engine` | `engine` | |
| `value` | `engine` | If repeatable; otherwise `card-draw` when it nets ≥ +1 card (see Card-draw classification), else `utility` |
| `enhancer`, `lord` | `payoff` | Anthem effects are payoffs in tribal/tokens decks |
| `tokens`, `token` | `payoff` | Token-makers in a tokens-go-wide deck are payoffs |
| `finisher`, `finishers` | `wincon` | |
| `death-payoff` | `payoff` | |
| `sac-outlet` | `utility` | Sac outlets enable strategies but aren't themselves payoffs |
| `graveyard-setup` | `utility` | Self-mill, dredge enablers |
| `graveyard-hate` | `utility` | |

Where a card's old role is ambiguous (e.g. `value`), the auto-tagger (P7.3, DEC-117) will flag it for human review rather than guess.

## Commander roles

The commander is not in `decklist`; it's in the root `commander` field. To keep role coverage accurate, add a top-level `commanderRoles` object:

```json
{
  "commander": "Meren of Clan Nel Toth",
  "commanderRoles": { "primary": "engine", "secondary": "recursion" }
}
```

Both fields use the same 15-role vocabulary. The metrics computer (P7.5, DEC-119) treats commander roles as part of the deck's role coverage.

## `wincon_style`

`wincon_style` is used in two places. As a **card-level** field on `decklist[]` entries with `primary_role == "wincon"` (or `secondary_role == "wincon"`), it disambiguates the kind of close. As a **deck-level** root field, it summarizes the deck's dominant win plan and feeds the resilience-target tables, the win-turn payoff curve selection, and the DEC-310 confidence margin.

**Closed set** (matches `RESILIENCE_RECURSION_TARGETS` and `RESILIENCE_WINCON_LINE_FLOOR` in [`scripts/compute_deck_metrics.py`](../scripts/compute_deck_metrics.py)):

| Value | Meaning |
|---|---|
| `combat` | Wins via attacks (Craterhoof, Overrun-style, voltron commander damage, infect) |
| `combo` | Wins via assembled combo (Thoracle/Consultation, Food Chain loops, infinite mana → drain) |
| `drain` | Wins via incremental life loss (Bolas's Citadel, Aetherflux, Exsanguinate-style X-spells) |
| `drain-x` | Wins via X-spell drain or life-total swings (Torment of Hailfire, Debt to the Deathless) |
| `discrete-threats` | Wins by stacking discrete must-answer threats that outpace removal (planeswalker ult armies, big-creature midrange) |
| `value-incremental` | Grindy attrition close — incremental advantage compresses to lethal pressure over many turns |
| `burst` | Single-turn-window finishers fired from a built-up board or resource pile (Exsanguinate, Genesis Wave, large X-spells) |
| `tokens` | Wins by wide token swarms — used only on card-level entries; deck-level usually downstreams to `combat` or `discrete-threats` |
| `mill` | Wins by emptying opponent libraries |
| `alt` | Alt wincons (Approach, Coalition Victory, Maze's End) |
| `mixed` | **Deck-level only.** Multiple kinds, no dominant plan (no single `winConditions[].kind` ≥ 60% of the lines). Inherits the same resilience-target row as `null`; the win-turn triple falls through to `max(comboLethal, lethalProxy)`. Use sparingly — most decks have a recognizable top-line plan. |

The metrics computer applies a small penalty to **`combo` wincons in B3 decks** and to **multiple `combo` wincons in B4 decks** (cohesion guardrail — see [`deck-metrics.md`](deck-metrics.md)).

## `is_mdfc_land`

Modal spell//land DFCs like Agadeem's Awakening / Bala Ged Recovery count as partial lands for manabase math and as a non-land role for role coverage. Mark them:

```json
{
  "name": "Bala Ged Recovery // Bala Ged Sanctuary",
  "type": "Sorcery // Land",
  "primary_role": "recursion",
  "is_mdfc_land": true
}
```

The metrics computer gives an MDFC Karsten-calibrated per-card credit (DEC-470): **0.74 land / 0.26 spell** when the back land face can enter untapped (pay-life clause), **0.38 land / 0.62 spell** when it unconditionally enters tapped — classified from the back land face's oracle text only (see `docs/deck-metrics.md`). `primary_role` still drives role coverage on the spell side at full weight.

## Validation

The auto-tagger (P7.3) and metrics computer (P7.5) both reject roles outside this 15-value set with a clear error. Adding a new role requires updating this doc first.

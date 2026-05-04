# Role Taxonomy (DEC-90 P7.1)

Canonical role vocabulary for `decklist[].primary_role` and `decklist[].secondary_role`. Closed set — anything outside this list must be added here first.

The 15 roles are deliberately coarse. They power deterministic deck metrics (manabase health, role coverage, gameplan cohesion); finer distinctions live in the candidate-pool playbook, not in roles.

## The 15 roles

| Role | Definition | Examples |
|---|---|---|
| `land` | Card with `Land` in `type_line`. Includes MDFCs (see `is_mdfc_land`). | Command Tower, Bojuka Bog, Shelldock Isle |
| `ramp` | Adds mana, fetches lands, or accelerates land drops. | Sol Ring, Cultivate, Birds of Paradise |
| `mana-fixing` | Color-fixes without net acceleration (taplands, filter lands as utility, etc.). Use as **secondary** when a card both fixes and ramps. | Reflecting Pool, Path of Ancestry |
| `card-draw` | Draws cards or generates card advantage on a repeatable or burst basis. | Rhystic Study, Night's Whisper, Esper Sentinel |
| `tutor` | Searches library for a specific card or category. | Demonic Tutor, Worldly Tutor, Eladamri's Call |
| `removal-spot` | Targeted answer to one permanent. | Swords to Plowshares, Beast Within, Pongify |
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
| `value` | `engine` | If repeatable; otherwise `card-draw` |
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

When `primary_role == "wincon"` (or `secondary_role == "wincon"`), add `wincon_style` to disambiguate. Closed set:

| Value | Meaning |
|---|---|
| `combat` | Wins via attacks (Craterhoof, Overrun-style, voltron commander damage, infect) |
| `combo` | Wins via assembled combo (Thoracle/Consultation, Food Chain loops, infinite mana → drain) |
| `drain` | Wins via incremental life loss (Bolas's Citadel, Aetherflux, Exsanguinate-style X-spells) |
| `mill` | Wins by emptying opponent libraries |
| `alt` | Alt wincons (Approach, Coalition Victory, Maze's End) |

The metrics computer applies a small penalty to **`combo` wincons in B3 decks** and to **multiple `combo` wincons in B4 decks** (cohesion guardrail — see [`deck-metrics.md`](deck-metrics.md)).

## `is_mdfc_land`

MDFCs (modal double-faced cards) like Shelldock Isle / Bala Ged Recovery count as lands for manabase math and as a non-land role for role coverage. Mark them:

```json
{
  "name": "Bala Ged Recovery // Bala Ged Sanctuary",
  "type": "Sorcery // Land",
  "primary_role": "recursion",
  "is_mdfc_land": true
}
```

The metrics computer counts an MDFC as **0.5 land + 0.5 spell** for curve and manabase calculations, and uses `primary_role` for role coverage on the spell side.

## Validation

The auto-tagger (P7.3) and metrics computer (P7.5) both reject roles outside this 15-value set with a clear error. Adding a new role requires updating this doc first.

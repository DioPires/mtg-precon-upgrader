# DEC-259 — Badgermole Cub canon decision

## Context

DEC-259 ships `data/archetype-recipes/ramp-bigmana.json` v1 (17/17 = 100% canon recall, 8 sub-recipes). Currently `in_review`. Board asked: "should we add Badgermole Cub to canon?"

## Card (Scryfall-verified)

**Badgermole Cub** — `{1}{G}` — Creature — Badger Mole (set TLA)

- ETB: earthbend 1 — animates a land you control into a 1/1 haste creature that's still a land
- "Whenever you tap a creature for mana, add an additional {G}."

## Why this is a decision

Cub's second ability is a **creature-mana-amplifier** idiom. Same family: Circle of Dreams Druid, Wirewood Channeler, Cryptolith Rite. The current recipe has **no sub-recipe** for this idiom — `mana_dorks` catches the dorks themselves, not the payoffs that scale them.

So canon recall is "17/17" only because canon doesn't include this idiom. If we add Cub to canon without a sub-recipe, recall drops or gets papered over.

## Options

### (a) Hold v1 as-is

- 17/17 canon. No Cub. No new sub-recipe.
- Ship now. Defer the creature-mana-payoff idiom to the quarterly audit.
- **Cost**: ramp-bigmana recipe will silently miss Cub + Circle of Dreams Druid + Wirewood Channeler when run against dork-heavy decks (e.g. verdant-tide).

### (b) Add a `creature_mana_payoffs` sub-recipe in v1 ← recommended

- Cub still **NOT** in canon (canon stays universal staples).
- New sub-recipe with queries like:
  - `f:commander o:"tap a creature for mana" o:add`
  - `f:commander o:"creatures you control" o:"add" o:mana mv<=4` (phrasing variant)
- Empirically validate the queries surface Badgermole Cub, Circle of Dreams Druid, Wirewood Channeler before declaring v1 live.
- Closes the systematic gap. ~30 min extra validation.

### (c) Force Cub into canon

- Adds Cub to canon list, recall becomes 18/18 only if (b) is also done.
- **I push back**: niche TLA printing, doesn't generalize across the archetype (e.g. unused in colorless eldrazi ramp like titan-convergence). Canon should be the universal must-surface set, not a "cards we like" list.

## Recommendation

**(b)** — adds the missing idiom systematically, keeps canon disciplined, costs ~30 min validation.

## Decision

Pending board.

Reply on DEC-259 with `a`, `b`, or `c`.

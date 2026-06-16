# Discovery Playbook

**Purpose:** force *retrieval-led* card discovery before any deck build or review. The 14 archetypes below define oracle-text patterns and supporting metadata that sweep the full commander-legal universe (mirrored locally) for candidate cards.

**Source of truth:** [`data/discovery-playbook.json`](../data/discovery-playbook.json) — consumed by `scripts/generate_candidate_pool.py`. This document is a human-readable companion. If they drift, the JSON wins.

## Why this exists (DEC-90)

Discovery without a playbook is recall-led: we query Scryfall for cards we already think of and never sweep the full set of cards matching a deck's criteria. This document mandates a structured archetype → query mapping so that every deck is analysed against the same retrieval lens.

## How to use

1. Tag your deck with one or more archetype IDs in `data/commanders/{id}/deck.json` under the `archetypes` field. **Order matters** — see [Archetype ordering](#archetype-ordering) below.
2. Run `python scripts/refresh_card_pool.py --deck {id}` (or `--all`).
3. Review `data/commanders/{id}/candidates.json` — every card scoring above the configured floor that is **not** in the decklist must be explicitly considered. Cuts require a reason.

## Archetype ordering

The `archetypes` list in each `deck.json` is **ordered by strategic primacy**:

- **Position 1** = the wincon-anchored axis (the strategy that closes games).
- **Position 2** = a strong supporting axis the deck explicitly wants.
- **Position 3+** = ancillary tags that overlap with the deck's tactics but are not load-bearing.

The candidate scorer applies position weights to each archetype's contribution: `1.0×` for position 1, `0.5×` for position 2, `0.25×` for position 3+. A card whose only match is at position 3 contributes a quarter as much density as one whose match is at position 1.

The intent is to keep the wincon axis dominant when archetypes overlap. Example: an Atraxa deck tagged `[infect-poison, plus-one-counters]` wins via poison; +1/+1 enablers like Hardened Scales should not crowd out actual infect cards just because Atraxa proliferates either counter type. Promoting `infect-poison` to position 1 makes the scorer reflect that.

When auditing or adding a deck:
- If the deck has a single clear wincon, put that archetype first.
- If two archetypes are genuinely co-equal (e.g. a tokens-counter deck where both tokens and counters are the wincon), the call is judgment — pick the more specific tag and document the rationale in the commit.

## Archetype index

| ID | Used by | Strategy in 1 line |
|---|---|---|
| `graveyard-reanimator` | eternal-harvest | Mill/sac into yard, return for value |
| `aristocrats` | eternal-harvest, dark-dominion | Sacrifice + death-trigger payoffs |
| `tokens-go-wide` | mutant-multiplication, dark-dominion | Many small tokens + anthems/doublers |
| `plus-one-counters` | mutant-multiplication, creeping-corruption | Place, double, pay off counters |
| `infect-poison` | creeping-corruption | Win via 10 poison counters |
| `voltron` | (latent — none yet) | One creature stacked with auras/equipment |
| `spellslinger` | dark-dominion | Cast many noncreature spells; cost reduction + copy |
| `group-slug` | eternal-agony | Trickle damage on every action |
| `stax-control` | genesis-protocol | Asymmetric resource denial |
| `artifacts-matter` | the-white-forge, genesis-protocol | Artifact density + flicker engines |
| `ramp-big-mana` | titan-convergence, verdant-tide | Cheat oversized threats into play early |
| `elf-tribal` | verdant-tide | Tribal anthems + mana dorks |
| `lands-matter` | (latent) | Landfall + extra-land effects |
| `etb-flicker` | the-white-forge | Re-fire ETB triggers via flicker |

Multiple tags per deck are expected — most decks lean on 2–3 archetypes.

## Deck-level modifiers

`asymmetric_only: true` is an optional root field in `data/commanders/{id}/deck.json`, sibling to `archetypes`. It is not an archetype; it tells the candidate generator that symmetric punisher/resource-denial templates are strategic traps for this deck and should be demoted.

Set it only when the deck has an explicit opponent-only preference. Example: Eternal Agony already prevents opponent lifegain through The Lord of Pain, so cards like Zo-Zu the Punisher, Ankh of Mishra, Sulfuric Vortex, and Manabarbs-style effects that also punish the pilot should fall below asymmetric alternatives. Leave it omitted or `false` for normal group slug, stax, aristocrats, and table-wide pressure decks where symmetric pressure is acceptable.

When enabled, the generator applies a multiplicative anti-synergy penalty to broad symmetric templates such as `each player`, `each player's upkeep`, `each opponent and you`, `whenever a player`, `players can't gain life`, `whenever a land enters the battlefield`, `each player loses N life`, and `each player sacrifices`. Asymmetric templates such as `each opponent`, `target opponent`, and `each other player` are unaffected.

## Per-archetype entry structure (in JSON)

```jsonc
{
  "name": "Human-readable name",
  "summary": "1-line strategic summary",
  "oracle_patterns": ["case-insensitive Python regex"],   // matched against oracle_text
  "type_constraints": ["Equipment", "Aura"],              // optional; substring match against type_line
  "cmc_max": 5,                                           // optional; cards above this are demoted
  "staples": ["Reanimate", "Animate Dead"],              // always-consider list, even if low pattern density
  "anti_patterns": ["graveyard hate"]                    // patterns that disqualify a card despite matches
}
```

## Scoring contract

Each candidate card is scored 0–100 by the generator. Components:

1. **Archetype keyword density (0–40):** count of `oracle_patterns` matched, scaled by total patterns. Two multiplicative dampeners stack on each archetype's contribution:
   - **Saturation curve:** once the existing decklist already has more than 8 cards matching the same archetype tag, that archetype's density contribution is multiplied by `max(0.35, 8 / deck_match_count)`. Example: a 16-card amass package makes the next amass card count at 50% density, while very saturated tags bottom out at 35%.
   - **Position weight:** position 1 = `1.0×`, position 2 = `0.5×`, position 3+ = `0.25×`. See [Archetype ordering](#archetype-ordering).
   `score_breakdown.density` stores the post-dampener value; `density_raw`, `saturation_penalty`, and `saturated_archetypes` are emitted when the saturation curve changes the score; `archetype_position_weights` is emitted listing every matched archetype whose position weight was below 1.0.
2. **CMC fit (0–20):** distance from deck's average CMC; rewards on-curve options.
3. **Owned (0–15):** binary, from `priv_data/owned_formatted.csv`.
4. **Game Changer × bracket (0–15):** Game Changers score full at B5, partial at B4, zero at B3.
5. **Decklist demotion:** cards already in the deck cap at 5, so they still rank but yield to alternatives.
6. **Quality-aware role redundancy:** for each candidate, the scorer looks up the in-deck cards that share the candidate's `primary_role` and computes their median candidate-pool score (scored as fresh candidates, ignoring the decklist cap). If the role bucket is saturated (≥ 8 in-deck cards in that role) **and** the candidate scores below the bucket median, the candidate's total is multiplied by `0.65`. The intent is to stop strictly-worse alternatives bubbling up under tuned decks: a colorless ramp deck running Mana Crypt + Thran Dynamo should not score Dreamstone Hedron above genuine upgrades just because the ramp role is open. Surfaced as `score_breakdown.redundancy_below_roster_median` with role, bucket count, bucket median, and the applied multiplier. The deck-level `role_pool` field on the candidates JSON exposes the per-role count and median used.

Anti-patterns disqualify outright (return score 0).

Deck-context anti-synergy rules are scored separately from playbook `anti_patterns`.
They do not disqualify a card by default; instead, they subtract named point
penalties and emit `score_breakdown.anti_synergy_flags`. Current deterministic
rules catch amass decks that are offered token-ETB payoffs, off-tribe amass
cards in Orc amass shells, sacrifice/reanimation cards in low-sacrifice-support
decks, death-trigger cards without sacrifice density, and symmetric reanimation
in creature-light decks. Decks tagged `asymmetric_only: true` also demote
symmetric punisher/resource-denial templates and emit a
`symmetric-effect-in-asymmetric-only` anti-synergy flag.

## Maintenance

- New archetype: add a key to `data/discovery-playbook.json` with the entry shape above.
- New deck: tag with applicable archetype IDs.
- Pattern tuning: when the generator misses obvious staples or surfaces noise, edit the patterns/staples and re-run. Track tuning rationale in commit messages.

## Out of scope

- Color identity filtering — handled by the generator, not the playbook.
- Bracket gating — handled by the scoring layer.
- Synergy combos — covered by Commander Spellbook MCP, not this playbook.
- **EDHREC synergy score ingestion** — investigated under DEC-312 (2026-05-29) and **cancelled**. EDHREC's Terms of Service prohibit automated queries ("use software or automated agents or scripts to ... generate automated searches, requests, or queries to the Site"), forbid content reproduction ("no part of the Site may be copied, reproduced, distributed, republished, downloaded ... in any form"), and bar building "a similar or competitive website". Using EDHREC's per-commander synergy delta to power our candidate scorer falls inside all three clauses. Do not re-open without ToS change or a licensed data source.

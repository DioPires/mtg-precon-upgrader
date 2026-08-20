# DEC-543 — Smaug, Wicked Worm: strategy analysis (pre-build, sign-off required)

Date: 2026-08-20. Author: CEO. Status: awaiting board sign-off on strategy. No deck files written.

## 1. What the commander actually does

`Smaug, Wicked Worm` — `{3}{B}{R}`, Legendary Creature — Dragon, 5/5, Flying. Set `hob`.
Oracle text (verified via Scryfall):

- "When Smaug enters, create X tapped Treasure tokens, where X is the number of artifacts your opponents control."
- "Whenever you cast a spell, if mana from a Treasure was spent to cast it, you draw a card and lose 1 life."

Three facts drive every build decision:

1. **The ETB is opponent-dependent.** X counts artifacts *opponents* control, not ours. It can be 0. We cannot build a plan on it.
2. **The cast trigger is once per spell, not once per Treasure.** Value scales with the *number of spells cast off Treasure mana*. The deck wants many cheap spells, not a few expensive ones. This argues against a big-dragon top end and for a low curve.
3. **The trigger costs 1 life per spell.** Ten Treasure-cast spells cost 10 life. The deck needs either lifegain stapled to its payoffs or a short game. This is the single most under-appreciated constraint, and it directly favours drain payoffs that gain life (Blood Artist, Zulaport Cutthroat, Bastion of Remembrance) over ones that do not (Mirkwood Bats).

Smaug is a card-advantage engine, not a win condition. The deck must supply its own kill.

## 2. Reference data

- EDHREC: 1,789 decks registered for this commander (`json.edhrec.com`, fetched 2026-08-20).
- Archidekt "JLK's Smaug | Game Knights #87" (deck 22677224): read in full via the Archidekt API.
- Moxfield `lySFoKzhM0KzE3VXYQ6fAw`: **could not read.** The API returned HTTP 403 (Cloudflare). Not analysed. Board can paste the list if they want it considered specifically.
- Commander Spellbook: ran `find_combos` over a 68-card Rakdos Treasure/sacrifice pool. 11 combos fully contained, 254 one-or-two cards away.
- Prices are Scryfall USD, fetched 2026-08-20.
- Ownership is `priv_data/Owned.csv` minus cards committed to non-brewing decks.

### Top EDHREC inclusions (share of 1,789 decks)

| Card | Inclusion | Card | Inclusion |
|---|---|---|---|
| Goldspan Dragon | 82% | Reckless Fireweaver | 62% |
| Mirkwood Bats | 77% | Academy Manufactor | 60% |
| Smaug the Magnificent | 74% | Magda, Brazen Outlaw | 57% |
| Big Score | 74% | Grim Hireling | 56% |
| Professional Face-Breaker | 73% | Alchemist's Talent | 54% |
| Xorn | 73% | Hellkite Tyrant | 54% |
| Mayhem Devil | 69% | Black Market Connections | 51% |
| Deadly Dispute | 67% | Crime Novelist | 50% |
| Rain of Riches | 66% | Marionette Apprentice | 48% |
| Unexpected Windfall | 64% | Nadier's Nightblade | 46% |

### Redundancy in Rakdos (Scryfall counts)

- Drain payoffs on death / sacrifice / token-leaves, MV ≤ 4: **43 cards**.
- Treasure makers, MV ≤ 3, non-land: **143 cards**.

Both axes are deep. Consistency will not be the limiting factor for any of the strategies below.

## 3. Strategy S1 — Treasure Aristocrats ("Hoard and Bleed") — RECOMMENDED

**Plan.** Treasures and creature tokens do triple duty: mana, sacrifice fodder, and damage. Drain payoffs convert every token created and every token sacrificed into life loss. Smaug refills the hand off Treasure spend. The combo is the closer; the drain package wins the long game on its own.

**Verified kill lines** (all from Commander Spellbook, all inside `B/R`):

| Line | Pieces | Result | New spend |
|---|---|---|---|
| Gravecrawler + Pitiless Plunderer + Goblin Bombardment | 3 | Infinite damage | $7.87 |
| Gravecrawler + Pitiless Plunderer + Ashnod's Altar | 3 | Infinite mana + infinite death triggers | $5.36 (Altar owned) |
| Pitiless Plunderer + Ashnod's Altar + Reassembling Skeleton | 3 | Infinite mana + infinite death triggers | $4.32 (Altar owned) |
| Gravecrawler + Phyrexian Altar (+ one other Zombie) | 2 | Infinite death triggers | $56.16 (owned, committed elsewhere) |
| Warren Soultrader + Gravecrawler + Bastion of Remembrance | 3 | Infinite drain, life-neutral | $16.90 |

Each line needs a drain payoff attached to convert the loop into a win. We hold **43** candidates for that slot, so the payoff half is effectively uncounterable by removal.

**The Smaug tax on loops.** Smaug's own trigger costs 1 life per Treasure-cast iteration. The Warren Soultrader line also costs 1 life per activation. A loop built only on Mirkwood Bats (no lifegain) therefore kills us first. A loop built on Zulaport Cutthroat, Blood Artist, or Bastion of Remembrance is life-positive and runs to lethal. **Design rule for this deck: at least three of the drain payoffs must gain life.**

**Non-combo backup — the token multiplier.** Xorn: "If you would create one or more Treasure tokens, instead create those tokens plus an additional Treasure token." Academy Manufactor: "If you would create a Clue, Food, or Treasure token, instead create one of each." Both are replacement effects, and CR 616.1 lets us choose the order. Applying Xorn first turns one Treasure into two, then Manufactor turns that event into 2 Clues + 2 Foods + 2 Treasures — **6 tokens from one Treasure instruction**. With Mirkwood Bats ("Whenever you create or sacrifice a token, each opponent loses 1 life") that is 6 life from each opponent, plus another point per token later sacrificed. *(The 6-token figure is my derivation from CR 616.1 replacement-order choice, not a printed Scryfall ruling. The individual oracle texts are verified.)*

**Game Changers required: zero.** Every piece above is off the official Game Changers list. That lands us cleanly at low Bracket 4 and leaves Game Changer slots as optional tuning knobs rather than load-bearing.

**Speed.** Combo kill in the T5–T7 window. Grind kill T7–T9 when the combo is disrupted.

**Weaknesses.** Graveyard hate answers Gravecrawler and Reassembling Skeleton. Artifact hate answers the Treasure base. Per the hoser-coverage check, the interaction suite must include enchantment removal (for Rest in Peace) and artifact removal (for Grafdigger's Cage), not just creature removal.

**Ownership.** Strong. Free right now: Mirkwood Bats ×6, Blood Artist ×2, Zulaport Cutthroat ×1, Marionette Apprentice ×1, Academy Manufactor ×1, Mayhem Devil ×1, Ashnod's Altar ×1, Pitiless Plunderer ×1, Deadly Dispute ×1, Big Score ×5, Black Market Connections ×2, Toxic Deluge ×3, Dauthi Voidwalker ×2, Bolas's Citadel ×1, Hellkite Tyrant ×1, and Smaug himself.

**Estimated new spend: $40–70** for the engine, before mana base.

## 4. Strategy S2 — Treasure Storm / cast-trigger burn (most on-theme)

**Plan.** Mirror Smaug's own trigger with damage instead of cards. `Alchemist's Talent` Level 3: "Whenever you cast a spell, if mana from a Treasure was spent to cast it, this Class deals damage equal to that spell's mana value to each opponent." `Rain of Riches`: "The first spell you cast each turn that mana from a Treasure was spent to cast has cascade."

**Support.** Alchemist's Talent 54% inclusion, Rain of Riches 66%. Both are well-tested by the player base.

**The problem is the clock.** Alchemist's Talent costs `{3}{R}` to cast, `{1}{R}` for Level 2, and `{4}{R}` for Level 3 — **11 mana total**, and the levels are sorcery-speed. It deals zero damage until all 11 are paid. After that, killing three opponents from 40 needs roughly 40 mana value of Treasure-cast spells. Rain of Riches caps at one cascade per turn.

**Verdict.** Realistically a turn-8-plus kill. That is Bracket 3 speed, not Bracket 4. The theme is excellent and the cards are good; **the right move is to graft Alchemist's Talent, Rain of Riches, Reckless Fireweaver, Ingenious Artillerist and Weftstalker Ardent into S1 as a damage sub-package**, not to run this as the primary plan.

## 5. Strategy S3 — Artifact-count alternate win

**Plan.** `Revel in Riches` (win on upkeep with 10+ Treasures) or `Hellkite Tyrant` (win on upkeep with 20+ artifacts).

**Support.** Revel 44%, Hellkite Tyrant 54%.

**The problem is telegraphing.** Both check on our upkeep, which gives the table a full turn cycle to answer a known threat, and both die to any removal spell. Revel also does not build its own count: it makes a Treasure only when an *opponent's* creature dies. Commander Spellbook confirms `Brass's Bounty + Revel in Riches` wins, but that needs 10+ lands and 12 mana across the two cards.

**Verdict.** Good as a one- or two-card top end inside S1. Not a primary plan at Bracket 4.

## 6. Strategy S4 — Treasure ramp into big dragons (the Game Knights list)

The Archidekt list is a ramp-and-value pile: roughly 24 ramp pieces, 18 removal spells, and a top end of Hellkite Tyrant, Ancient Copper Dragon and Cavern-Hoard Dragon. It contains no deterministic kill.

**Verdict.** Bracket 3, not Bracket 4. Rejected as the primary plan. Its removal suite (Terminate, Abrade, Go for the Throat, Dismember, Toxic Deluge, Snuff Out, Feed the Swarm) and its Treasure-ramp core are worth harvesting for S1.

## 7. Recommendation

Build **S1 with the S2 damage sub-package grafted on**. Working name: **"Hoard and Bleed"**.

The case in one paragraph: Smaug rewards spending Treasures, and an aristocrats shell is the only one of the four that makes spending a Treasure *itself* a damage event. Treasures become mana, fodder and burn at the same time, so no slot is dead. The kill is deterministic and cheap, the payoff half is 43 cards deep so removal cannot break it, and it needs no Game Changers to reach low Bracket 4. The lifegain drain payoffs pay Smaug's 1-life-per-spell tax back with interest.

Proposed archetype tags for `deck.json`: `aristocrats` (primary), `artifacts-matter`, `tokens-go-wide`.

## 8. Open questions for the board

1. Which strategy do we build?
2. What is the ceiling on new-card spend?
3. Several strong pieces are owned but locked into built decks — Phyrexian Altar, Storm-Kiln Artist, Jeska's Will, Ancient Tomb, Underworld Breach, Goldspan Dragon. Do we buy second copies, or build strictly from the free pool plus new purchases?

Nothing is written to `data/` until the board answers question 1.

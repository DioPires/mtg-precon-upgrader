# DEC-543 — Smaug, Wicked Worm: strategy analysis, revision 2

Date: 2026-08-20. Author: CEO. Status: awaiting board sign-off on strategy. No deck files written.

Revision 2 re-derives the strategy after the board supplied the Moxfield list that revision 1 could not fetch.
Revision 1 is at [`dec543-strategy-analysis.md`](dec543-strategy-analysis.md). Read this file instead of it.

**Headline: the recommendation does not change, but one of its supporting rules was wrong.** Revision 1 told us to
build the drain package on Blood Artist, Zulaport Cutthroat and Bastion of Remembrance. All three trigger on
*creature* death only. A Treasure is a noncreature artifact, so none of them fire when we sacrifice one. The
Moxfield list runs none of those three, and that is correct construction, not an oversight. Section 4 replaces the
rule.

## 0. Two cards in the supplied list do not exist

I checked both against live Scryfall, not the local mirror.

| Entry as pasted | Result |
|---|---|
| `S.H.I.E.L.D. Spy Satellite` | No Magic card contains "Satellite" in its name. The `msh` S.H.I.E.L.D. cycle is 8 cards; none is a Spy Satellite. Nearest real card is S.H.I.E.L.D. Spy Kit — `{W}`, color identity W. |
| `Zidane Tribal` | No card by that name. The only Zidane is Zidane, Tantalus Thief — `{3}{R}{W}`, color identity R/W. |

Both nearest real matches sit outside Smaug's B/R identity, so neither is legal here under any reading. The list is
therefore 98 real cards plus 2 entries I cannot resolve. Everything below treats it as a 98-card list. **Board: can
you confirm what those two slots actually are?** They do not change the strategic verdict.

The other 98 entries all verify: Commander-legal, and every color identity is a subset of B/R. Zero color-identity
violations. 35 lands (Treasure Vault included), plus 2 modal spell//land backs (Fell the Profane, Malakir Rebirth).

## 1. What the commander does (unchanged, re-verified)

`Smaug, Wicked Worm` — `{3}{B}{R}`, Legendary Creature — Dragon, 5/5, Flying.

- "When Smaug enters, create X tapped Treasure tokens, where X is the number of artifacts your opponents control."
- "Whenever you cast a spell, if mana from a Treasure was spent to cast it, you draw a card and lose 1 life."

The three facts from revision 1 still hold: the ETB is opponent-dependent and can be 0; the cast trigger is once per
*spell*, not per Treasure, so the deck wants many cheap spells; the trigger costs 1 life every time and is not
optional. Smaug is a card-advantage engine. The deck must supply its own kill.

## 2. What the Moxfield list confirms

**It is a Treasure aristocrats deck.** That is the same archetype revision 1 recommended, reached independently by
another builder. Its payoff suite is Disciple of the Vault, Marionette Apprentice, Marionette Master, Mirkwood Bats,
Nadier's Nightblade, Agent of the Iron Throne, The Sackville-Bagginses, Reckless Fireweaver, Ingenious Artillerist,
Weftstalker Ardent and Mayhem Devil. Every one of those converts Treasure movement into life loss or damage. That
is strategy S1.

**It confirms the free-spell requirement.** It runs Deadly Rollick and Deflecting Swat, which
[`data/bracket-philosophy.md`](../../../data/bracket-philosophy.md) names as the mandatory Bracket 4 free spells for
black and red. We hold 1 of each in the free pool.

**It runs zero Game Changers.** I checked all 98 resolvable entries against `data/game-changers.json` (53 cards,
2026-02-09 baseline). No hits. This confirms revision 1's claim that the archetype reaches its power level without
spending Game Changer slots.

## 3. What the Moxfield list teaches that revision 1 missed

### 3a. Treasures pay twice — revision 1 only counted one half

Revision 1 valued Treasures as sacrifice fodder. The Moxfield list also runs three artifacts-entering payoffs, and
they are the better half. Verified oracle text:

- Reckless Fireweaver — "Whenever an artifact you control enters, this creature deals 1 damage to each opponent."
  One trigger per artifact.
- Ingenious Artillerist — "Whenever one or more artifacts you control enter, this creature deals that much damage
  to each opponent." One batched trigger, damage equal to the count.
- Weftstalker Ardent — "Whenever another creature or artifact you control enters, this creature deals 1 damage to
  each opponent."

So a Treasure deals damage on the way in *and* drains on the way out. Revision 1 undervalued Xorn and Academy
Manufactor badly as a result, because those two multiply the entering half.

### 3b. The Xorn + Academy Manufactor number, now properly sourced

Revision 1 claimed 6 tokens from one Treasure instruction and flagged the figure as my own derivation. It holds, and
part of it is now backed by a printed ruling.

Scryfall ruling on Academy Manufactor: "If you control one Academy Manufactor and would create some number of Clue,
Food, or Treasure tokens, you will instead create that many Clue tokens, that many Food tokens, and that many
Treasure tokens." Xorn reads "If you would create one or more Treasure tokens, instead create those tokens plus an
additional Treasure token."

Both are replacement effects applying to the same event, so CR 616.1 lets us choose the order. Applying Xorn first
turns "create 1 Treasure" into "create 2 Treasures"; Manufactor then turns that into 2 Clues + 2 Foods + 2 Treasures
= **6 tokens**. The reverse order yields 4. The 6-token figure depends on our ordering choice — that step is my
CR 616.1 derivation, not a printed ruling. The per-card texts and the Manufactor multiplication are printed.

With Fireweaver, Artillerist and Mirkwood Bats also on board, that single Treasure instruction deals 6 + 6 + 6 = **18
to each opponent**, 54 across the table. State the basis plainly: that number needs five specific permanents in play.
With only Fireweaver and Bats it is 2 to each opponent. The engine is steeply nonlinear in Xorn and Manufactor.

### 3c. Karn, the Great Creator + Mycosynth Lattice is a hard lock I did not consider

Mycosynth Lattice: "All permanents are artifacts in addition to their other types." Karn: "Activated abilities of
artifacts your opponents control can't be activated." Together, every opponent permanent becomes an artifact, so
opponents cannot activate anything — including the mana abilities of their lands. Commander Spellbook confirms the
pair and tags it "Lock; Mass Land Denial". Commander Spellbook also lists Mycosynth Lattice + Hellkite Tyrant as a
two-card win: Lattice makes all permanents artifacts, so Hellkite's combat damage steals every permanent that player
controls and the 20-artifact upkeep check fires.

This is a genuine option, not a curiosity. It is also a social-contract decision, not just a power one. See
section 7, question 3.

## 4. The correction: payoff gating

This is the substantive error in revision 1. Verified oracle text:

- Blood Artist — "Whenever this creature or another **creature** dies…"
- Zulaport Cutthroat — "Whenever this creature or another **creature you control** dies…"
- Bastion of Remembrance — "Whenever a **creature you control** dies…"

None of the three fires when we sacrifice a Treasure. Revision 1's design rule — "at least three of the drain
payoffs must gain life", naming exactly those three — was built on a false premise for a Treasure shell.

The correct payoff set, all oracle-verified, with the Scryfall ruling on Marionette Master confirming that Treasure
tokens count ("Artifact tokens that are sacrificed or destroyed are put into their owner's graveyard before ceasing
to exist. If you controlled the token, Marionette Master's last ability will trigger"):

| Card | Trigger | Fires on Treasure | Gains us life |
|---|---|---|---|
| Marionette Master (1/3, fabricate 3 → 4/6) | artifact you control → graveyard; one opponent loses life equal to its power | sacrifice | no |
| Mayhem Devil | a player sacrifices a **permanent**; 1 damage any target | sacrifice | no |
| Marionette Apprentice | another creature **or artifact** you control → graveyard | sacrifice | no |
| Disciple of the Vault | any artifact → graveyard; one opponent loses 1 | sacrifice | no |
| Mirkwood Bats | you **create or sacrifice** a token | **both halves** | no |
| Nadier's Nightblade | a token you control leaves the battlefield | sacrifice | **yes, +1** |
| Ingenious Artillerist | one or more artifacts enter; damage equal to count | create | no |
| Reckless Fireweaver | an artifact you control enters | create | no |
| Weftstalker Ardent | another creature or artifact enters | create | no |
| Agent of the Iron Throne | grants our commander the artifact-or-creature death drain | sacrifice | no |
| The Sackville-Bagginses | you sacrifice a token; one opponent loses 1 | sacrifice | no |
| Crime Novelist | you sacrifice an artifact; +1/+1 counter and add `{R}` | sacrifice | no (ramps) |

**Replacement design rule.** Smaug's own trigger costs 1 life per Treasure-cast spell and is not optional. The
lifegain that pays for it must come from cards that actually fire in this shell. That means **Nadier's Nightblade**
and **Exsanguinate**, not Blood Artist. Nadier's Nightblade is the only life-positive drain in the corrected table.

**Bridge payoffs.** Every deterministic kill available to Rakdos at this budget is a *creature* recursion loop
(section 6), so the deck needs payoffs that fire on both axes. Three do: **Mayhem Devil** ("sacrifices a
permanent"), **Marionette Apprentice** ("creature or artifact"), and **Agent of the Iron Throne** ("artifact or
creature"). Mayhem Devil is the best of them — it costs $0.30, we hold 1 free, and it also taxes opponents' fetch
lands.

## 5. Why the Moxfield list is Bracket 3, not low Bracket 4

The board asked for low Bracket 4. The supplied list does not reach it. Four reasons, in order of weight.

1. **No free sacrifice outlet.** Stated precisely: Treasures sacrifice themselves for mana, so the drains do fire in
   ordinary play. What is missing is a *free, unbounded* outlet. Without one, the number of Treasures we can
   sacrifice per turn is capped by the number of mana sinks we have, and there is no loop, so there is no
   deterministic kill. Krark-Clan Ironworks ("Sacrifice an artifact: Add `{C}{C}`") fixes this exactly: free,
   repeatable, artifact-only, and it turns a Treasure into 2 mana instead of 1.
2. **No tutors at all.** Zero in 98 cards, against three narrow alternate win conditions. Note that Demonic Tutor,
   Vampiric Tutor, Imperial Seal, Gamble, Mystical Tutor and Enlightened Tutor are all Game Changers — but
   **Diabolic Intent is not** (we hold 2 free) and **Wishclaw Talisman is not** ($1.70). We can add consistency
   without spending Game Changer slots.
3. **Three telegraphed upkeep win conditions.** Revel in Riches (10 Treasures), Hellkite Tyrant (20 artifacts) and
   Knuckles the Echidna (30 artifacts) all check at our upkeep, which gives the table a full turn cycle to answer a
   known threat, and all three die to one removal spell. Knuckles at 30 artifacts is strictly the hardest and should
   not make our list.
4. **Three mana rocks.** Sol Ring, Arcane Signet, Talisman of Indulgence. Treasures partly cover this, but the deck
   leans on 35 lands to function.

Realistic kill turn for that list is turn 9 or later by incremental drain, or whenever Hellkite Tyrant or
Cavern-Hoard Dragon connects. That is Bracket 3 speed. The Karn + Lattice lock is the one Bracket 4 element in it,
and at 10 mana across two cards it is not a fast one.

## 6. Deterministic kills available to us

I ran Commander Spellbook over a 67-card pool shaped to the corrected strategy: 20 combos fully contained, 219 one
or two cards away. The load-bearing finding:

**There is no infinite Treasure loop in Rakdos at this budget.** Every deterministic line is a creature recursion
loop or an artifact recursion loop. This is why section 4's bridge payoffs matter.

| Line | Pieces | Result | Free pool status |
|---|---|---|---|
| Pitiless Plunderer + Ashnod's Altar + Reassembling Skeleton | 3 | infinite mana, infinite death triggers | all 3 free |
| Gravecrawler + Pitiless Plunderer + Ashnod's Altar | 3 | infinite mana, infinite death triggers | Gravecrawler 0 free |
| Gravecrawler + Pitiless Plunderer + Goblin Bombardment | 3 | infinite damage | Gravecrawler 0 free |
| Warren Soultrader + Gravecrawler + Bastion of Remembrance | 3 | infinite drain, life-neutral | Gravecrawler 0 free |
| Karn, the Great Creator + Mycosynth Lattice | 2 | lock, mass land denial | Karn 0 free, Lattice unowned |
| Mycosynth Lattice + Hellkite Tyrant | 2 | win at next upkeep | Lattice unowned |
| Crime Novelist + Krark-Clan Ironworks + Myr Retriever + Junk Diver | 4 | infinite mana, infinite death triggers | KCI 0 free |

**Pitiless Plunderer + Ashnod's Altar + Reassembling Skeleton is the line to build on.** All three are in the free
pool today, it needs no new purchase, and it is the only fully-owned deterministic kill. Attach any creature-death
drain and it wins; attach Mayhem Devil and it wins on the "sacrifices a permanent" clause too.

## 7. Recommendation and open questions

**Build strategy S1, "Hoard and Bleed", with the section 4 payoff table replacing revision 1's.** The Moxfield list
validates the archetype and supplies the correct payoff gating. Our version differs from it in four deliberate ways:
add a free sacrifice outlet, add two non-Game-Changer tutors, cut from three telegraphed upkeep win conditions to
one, and build on the fully-owned Plunderer/Altar/Skeleton kill.

Proposed archetype tags: `aristocrats` (primary), `artifacts-matter`, `tokens-go-wide`.

**Known weakness, stated up front.** Nine of the payoff cards in section 4 are creatures. A board wipe resets the
whole engine. Per the permanent-type durability heuristic we should prefer the enchantment and artifact versions
where they exist, and the deck needs a real answer to sorcery-speed wipes. I will address this in the 99, not the
strategy.

### Questions I need answered before I draft the 99

1. **Do you sign off on S1 as corrected?**
2. **What is the ceiling on new-card spend?** This is now the decisive number, and it is still unanswered from
   revision 1. The engine cards that separate Bracket 3 from low Bracket 4 are Krark-Clan Ironworks ($17.16),
   Xorn ($10.42) and Academy Manufactor ($7.59, 1 free — already owned). Payoffs are cheap: Disciple of the Vault
   $0.93, Nadier's Nightblade $0.27, Reckless Fireweaver $0.55, Agent of the Iron Throne $0.48, Marionette Master
   $3.92, Ingenious Artillerist $1.74, Weftstalker Ardent $1.75. A working engine plus payoffs lands near $45–60
   before the mana base.
3. **Do we want the Karn + Mycosynth Lattice lock?** My recommendation is **no**. It costs $36 for Lattice plus a
   third Karn at $4.88, needs 10 mana across two cards, and does not itself win — we still have to kill three
   players afterwards. Mass land denial is a Bracket 4 marker, so including it would push us above "low Bracket 4"
   on feel more than on speed. This is your call, not mine, because it is a play-experience question.
4. **Second copies.** These are owned but committed to built decks, so the free pool shows 0: Krark-Clan Ironworks,
   Phyrexian Altar, Karn the Great Creator, Gravecrawler, Goldspan Dragon. Do we buy second copies, or build
   strictly from the free pool plus new purchases? This decides whether the Gravecrawler lines are available.
5. **Price bar check.** You excluded Grim Monolith, Chrome Mox, Mox Opal and Mox Diamond on price. Two cards in the
   supplied list are in similar territory: **Deflecting Swat ($68.90)** and **Deadly Rollick ($26.68)**. We hold 1
   of each in the free pool, so they cost us nothing to include. Confirm that owned-but-expensive cards are fine.

### Method notes

- Prices are Scryfall USD, fetched 2026-08-20.
- Free pool is `priv_data/Owned.csv` minus cards committed to non-brewing decks. Eight decks are currently tagged
  brewing and their cards count as free; if any of those are firm builds, the free pool above is optimistic.
- Dockside Extortionist is **banned** in Commander and is not an option.
- Every card named in this document was verified against Scryfall oracle text. No card effect here is quoted from
  memory.

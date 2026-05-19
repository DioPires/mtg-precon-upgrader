# DEC-282 — Hedron Storm: missed-card re-scan & swap proposals

**Deck**: `zada-hedron-grinder` ("Hedron Storm")
**Commander**: Zada, Hedron Grinder
**Bracket**: 3 / mono-R / archetypes: spellslinger + tokens-go-wide
**Date**: 2026-05-19

## Methodology

Re-ran 10 Scryfall queries against the current Zada build + EDHREC-signal candidates.json (top-200). Cross-checked vs decklist, candidates.json, owned inventory, Game Changers list, and board exclusion list (Wheel of Fortune, Grim Monolith, Mana Vault, Ancient Tomb, Mox Diamond + banned: Mana Crypt / Dockside / Jeweled Lotus / Nadu).

**Result**: 8 missed cards meet the bar. None are Game Changers → bracket stays at 3.

## Verification

All card text quoted from Scryfall (verbatim, oracle current 2026-05-19):

- **Harmonic Prodigy** {1}{R} Human Wizard — "Prowess. If a triggered ability of a Shaman or another Wizard you control triggers, that ability triggers an additional time." Doubles Storm-Kiln Artist (Dwarf Shaman) Magecraft + Vivi's Persistence Wizard token's noncreature-spell trigger.
- **Young Pyromancer** {1}{R} Human Shaman — "Whenever you cast an instant or sorcery spell, create a 1/1 red Elemental creature token." Free creature per I/S → more Zada copies + Empty the Warrens scaling. (Pyromancer is itself a Shaman → Harmonic Prodigy combos.)
- **Reverberate** {R}{R} Instant — "Copy target instant or sorcery spell. You may choose new targets for the copy." Hard copy redundancy for Zada-cantrip fan-out.
- **Twinning Staff** {3} Artifact — "If you would copy a spell one or more times, instead copy it that many times plus an additional time." Multiplicative copy upgrade — every Zada trigger that copies N times now copies N+1.
- **Goblin Engineer** {1}{R} Goblin Artificer — "When this creature enters, you may search your library for an artifact card, put it into your graveyard, then shuffle. {R}, {T}, Sacrifice an artifact: Return target artifact card with mana value 3 or less from your graveyard to the battlefield." Mono-R artifact tutor — fetches Skullclamp/Sol Ring/Goblin Bombardment, recurs them later.
- **Krenko, Tin Street Kingpin** {2}{R} Legendary Goblin — "Whenever Krenko attacks, put a +1/+1 counter on it, then create a number of 1/1 red Goblin creature tokens equal to Krenko's power." Exponential goblin production at 3 cmc.
- **Reiterate** {1}{R}{R} Instant — "Buyback {3}. Copy target instant or sorcery spell. You may choose new targets for the copy." With Birgi + Storm-Kiln Artist infinite-mana, buyback-Reiterate on Grapeshot = win. As pure copy: copies Bonus Round / Past in Flames / Mana Geyser.
- **Fable of the Mirror-Breaker // Reflection of Kiki-Jiki** {2}{R} Saga → Goblin Shaman — Chapter I makes a Treasure-attacking Goblin Shaman token, III flips into a non-legendary haste-Kiki. Snoop+Reflection works without Kiki legend conflict. (Reflection is a SHAMAN → Harmonic Prodigy multi-stack.)

**Owned (€0)**: Harmonic Prodigy.
**Buy**: rest (€1-15 each).

## Proposed swaps — 8 adds, each with 2-3 alternate cuts

Board picks one cut per accepted add. All cuts are non-must-keep cards. Each cut is justified head-to-head against the closest non-cut card.

---

### ADD 1: Harmonic Prodigy (owned, €0)

**Why**: Doubles Storm-Kiln Artist Magecraft (4 Treasures per spell+copy with Bonus Round, was 2) and Vivi's Persistence Wizard-token trigger (2 dmg per noncreature spell to each opp, was 1). Compounding effect on the only two recurring drain triggers tied to creature types. Itself a Prowess body — fine on 2.

**Alternate cuts** (pick 1):

- **Hexing Squelcher** — 3-cmc Goblin Sorcerer with "{2}{R}, sacrifice this: counter target spell" effective body, requires sac + 2R AND a target. Slow countermagic in a deck with Deflecting Swat + Bolt Bend + Red Elemental Blast already. *Beats keeping it because*: deck already has 3 protection slots; Harmonic Prodigy adds two damage axes on every storm turn — far higher EV.
- **Goblin Lackey** — 1-cmc 1/1 with combat-trigger Goblin cheat. Almost always dies to a removal spell, board wipe, or 1/1 body before swinging in B3 metas; the cheat is value-only on hit. *Beats keeping it because*: Lackey is a "win-more on T1" card; Harmonic Prodigy compounds every turn from T2 onward.
- **Renegade Tactics** — Sorcery cantrip target #7. Deck already has 7 cantrip targets; one more is duplication, not redundancy on a key role. *Beats keeping it because*: Harmonic Prodigy is a *new effect type* (trigger-doubling) rather than slot duplication.

---

### ADD 2: Young Pyromancer (€1-3)

**Why**: 2-cmc Shaman that prints a 1/1 per I/S cast. Every token is another Zada-copy target — turn 4 with 3 spells cast = +3 board width = next cantrip copies 3 more times. Direct multiplier on the cantrip engine. Tokens also feed Empty the Warrens swing, Skullclamp draws, Goblin Bombardment sacs.

**Alternate cuts** (pick 1):

- **Wild Ride** — 2-cmc sorcery with harmonize replay. Cantrip target that gives "play with top revealed" effect — slow, doesn't accelerate combo turns. *Beats keeping it because*: Young Pyromancer turns spell-density into board-density on the same turn; Wild Ride is a slow Impulse-style card.
- **Witch's Mark** — 2-cmc cantrip target #8. Deck has 7 cantrip targets already. *Beats keeping it because*: One fewer cantrip-target ≠ broken engine; one fewer board-width body IS a smaller storm chain.
- **Renegade Tactics** — Sorcery cantrip target #7. Same logic — duplication of a saturated role. *Beats keeping it because*: token production widens *every other* Zada-target's value, not just adds one cantrip slot.

---

### ADD 3: Reverberate (€1-3)

**Why**: 2-mana hard copy. Cast on Zada-targeted cantrip post-resolution → another full N-copy fan-out. Copies Bonus Round, Past in Flames, Mana Geyser, Grapeshot, Empty the Warrens. Compresses storm chains and creates an alternate Bonus Round line (Reverberate-on-Grapeshot copies the full storm-counted Grapeshot).

**Alternate cuts** (pick 1):

- **Flaring Pain** — Niche anti-Glacial Chasm / anti-Fog effect. Useful in ~3 specific board states. *Beats keeping it because*: Reverberate is a generally-applicable storm-chain multiplier; Flaring Pain is meta-conditional.
- **Haze of Rage** — 2-cmc storm-counted +1/+0 + haste finisher. Wins only via combat after a storm-prep turn — and Empty the Warrens already does the wide-haste line better with Chieftain/Warchief. *Beats keeping it because*: Reverberate scales every kill line; Haze of Rage scales only the alpha-strike line.
- **Hexing Squelcher** — Slow situational counter. *Beats keeping it because*: Reverberate doubles as protection (copy a removal spell of theirs / your own protection spell) while also being offense.

---

### ADD 4: Twinning Staff (€2-4)

**Why**: "If you would copy a spell one or more times, instead copy it that many times plus an additional time. {7}, {T}: copy I/S you control." Multiplicative on every Zada trigger (5 other creatures → 6 copies, was 5). Stacks with Roaming Throne (each of the two Zada copies becomes +1). Single-card +20% storm-chain efficiency.

**Alternate cuts** (pick 1):

- **Bedlam Reveler** — 8-cmc {6}{R}{R} base, mid-game often costs {2}{R} as 3/4 ETB-draw-3. Dependent on heavy yard density already, often dead in opener. *Beats keeping it because*: Twinning Staff is active turn 4+; Reveler is purely a refill card that storm chains already produce via Past in Flames / Underworld Breach.
- **Spinerock Tyrant** — 5-cmc copy-on-cast Dragon. Second copier — overlaps with what Twinning Staff does at 3 cmc. *Beats keeping it because*: Tyrant is a 5-cmc 6/6 body; Staff is a 3-cmc artifact that affects ALL copy effects (Zada + Tyrant + Reverberate + Bonus Round). Lower curve, broader effect.
- **Great Train Heist** — 1-cmc Spree instant + 2 modes (Treasure / extra combat). Conditional value; modes need additional mana. *Beats keeping it because*: Twinning Staff is a flat passive; Great Train Heist's Treasure mode is single-use and combat mode is a finisher-only utility.

---

### ADD 5: Goblin Engineer (€3-6)

**Why**: 2-cmc Goblin Artificer. ETB tutors any artifact (Skullclamp, Sol Ring, Goblin Bombardment, Roaming Throne, Twinning Staff, Idol of Oblivion) to graveyard. Then {R}, {T}, sac artifact: recur a CMC≤3 artifact from yard to play. Tutors Skullclamp consistently, doubles as artifact recursion vs Vandalblast metas. Mono-R artifact tutor is rare.

**Alternate cuts** (pick 1):

- **Mogg War Marshal** — 2-cmc echo Goblin Warrior, generates 2 tokens over its lifetime (ETB + echo death). *Beats keeping it because*: Engineer is a tutor (1-of effect) while Mogg is a body generator already redundant with Krenko's Command + Empty the Warrens + Goblin Recruiter stacking.
- **Goblin Lackey** — 1-cmc 1/1 with combat-trigger Goblin cheat. *Beats keeping it because*: Engineer fixes Skullclamp consistency (which then draws cards off Lackey-style 1/1s anyway); Lackey is a value-only when unblocked card.
- **Searslicer Goblin** — 3-cmc raid-token-at-EOS Goblin. Generates a token only on attack-end-step trigger. *Beats keeping it because*: Engineer enables a key artifact-tutor lane this deck currently lacks; Searslicer's tokens are already produced more reliably by Krenko / Pashalik / Siege-Gang line. (Note: Searslicer's slot loss reduces Goblin density — see below.)

---

### ADD 6: Krenko, Tin Street Kingpin (€1-3)

**Why**: 3-cmc Goblin — attacks → +1/+1 counter, then makes N goblins where N = its post-counter power. T4 attack → 1 counter → 1 goblin. T5 → 2 → 2 goblins. T6 → 3 → 3 goblins. Exponential attack-based scaling on a body that can be cast turn 3 (Krenko Mob Boss costs {2}{R}{R} = T4). Faster ramp on the goblin axis.

**Alternate cuts** (pick 1):

- **Siege-Gang Lieutenant** — 4-cmc Goblin (creates 2 tokens, sac-for-burn outlet). Tin Street Kingpin is a 3-cmc threat that scales faster on combat. *Beats keeping it because*: 3-cmc T3 play > 4-cmc T4 play in a storm deck where turn-4 mana goes to Krenko Mob / Roaming Throne / Bonus Round. Siege-Gang Commander stays as the 5-cmc bigger version.
- **Mogg War Marshal** — 2-cmc echo Goblin. *Beats keeping it because*: Tin Street Kingpin's 3rd attack alone makes more tokens (3) than Mogg's lifetime output (2).
- **Searslicer Goblin** — 3-cmc raid token producer. Same slot, faster scale: Searslicer = 1 token per attack regardless of board; Tin Street = scales with prior attacks. *Beats keeping it because*: Tin Street Kingpin's tokens stack into Krenko-Mob-Boss's untap line; Searslicer's single token does not.

---

### ADD 7: Reiterate (€3-5)

**Why**: {1}{R}{R} buyback {3} copy. Pure copy at 3 cmc. **Combo win**: with Birgi-out-and-running storm mana (Storm-Kiln Treasure print rate ≥ 1 per spell with Bonus Round), buyback Seething Song or Mana Geyser indefinitely → infinite mana → Reiterate-Grapeshot for table kill. Even without infinite, copies Past in Flames / Bonus Round / Mana Geyser for huge swings.

**Alternate cuts** (pick 1):

- **Haze of Rage** — Storm-counted +1/+0 haste finisher. Reiterate-Empty-the-Warrens or Reiterate-Grapeshot replaces Haze's role with a higher-ceiling line. *Beats keeping it because*: Reiterate is a win-the-game button under infinite mana; Haze is a combat win-more.
- **Spinerock Tyrant** — 5-cmc second copier. Reiterate competes with Tyrant for "copy a key spell" role but at 3 cmc instead of 5. *Beats keeping it because*: Reiterate's instant speed + buyback dwarfs Tyrant's once-per-cast trigger; Tyrant's body advantage is a 6/6 flier with wither — not core to the gameplan.
- **Bedlam Reveler** — Burst draw, mid-game cost reducer. *Beats keeping it because*: Reiterate accelerates kills; Reveler refills hand for future kill turns. In a deck with Past in Flames + Underworld Breach + Faithless Looting, hand refill is already saturated.

---

### ADD 8: Fable of the Mirror-Breaker (€8-15)

**Why**: 3-cmc Saga + transformed creature. Chapter I makes a 2/2 Goblin Shaman token with "attacks → Treasure" (ramp). Chapter II discard-up-to-2 → draw 2 (yard fuel for Past in Flames / Underworld Breach). Chapter III flips into Reflection of Kiki-Jiki: "{1}, {T}: create haste-copy of nonlegendary creature you control, sac at next EOS." This is a **second Kiki-style combo enabler that doesn't clash with Kiki-Jiki via legend rule** because Reflection is non-legendary. Snoop + Reflection assembles the same infinite-haste-copy line.

**Alternate cuts** (pick 1):

- **Spinerock Tyrant** — 5-cmc second copier. Fable is a 3-cmc Saga that becomes a 3-cmc copier *and* makes a body, draws cards, ramps. *Beats keeping it because*: Fable is a strictly higher-value 3-stage card at lower cost; Tyrant overlaps with the copier role at 5 cmc.
- **Bedlam Reveler** — Hand refill. Fable Chapter II = discard 2 + draw 2 (yard-loading + cycling). *Beats keeping it because*: Fable refills hand AND adds two other modes (Treasure ramp + Kiki combo); Reveler is single-mode.
- **Siege-Gang Lieutenant** — 4-cmc token producer. *Beats keeping it because*: Fable Chapter I matches Siege-Gang Lt token output (2-2 over time) at 3 cmc, then adds two more chapters of value. Pure curve and ceiling upgrade.

---

## Acceptance request

I will not edit `deck.json` until the board accepts. **Reply with the adds you accept and the cut for each.** Format:

```
ACCEPT: 1 (cut Hexing Squelcher), 3 (cut Flaring Pain), 5 (cut Mogg War Marshal)
REJECT: 2, 4, 6, 7, 8
```

Or "accept all with my picks" + the cut for each. Or reject the whole slate.

After acceptance I will:
1. Update `deck.json` (decklist + highlights + synergies + sources + categories where new adds belong).
2. Run `python scripts/validate_deck_json.py --deck zada-hedron-grinder`.
3. Run `python scripts/refresh_card_pool.py --deck zada-hedron-grinder` to regenerate metrics + candidates.
4. Report before/after metrics + closed-loop confirmation.

## Cards explicitly considered and REJECTED

For audit transparency:

- **Mizzix's Mastery** — one-shot free-cast all I/S in yard. Strong but: (a) doesn't beat Past in Flames + Underworld Breach already in deck, (b) 4-cmc sorcery, (c) only one shot vs. Past in Flames recursive use. Net slot value lower than ADDs 1-8.
- **Pyromancer's Goggles** — 5-cmc copy-on-cast-with-R artifact. Slow, doesn't copy 0/1/2-cmc cantrips reliably (needs to spend R from Goggles).
- **Stormsplitter** — 3-cmc Dragon, copies itself per spell. High ceiling but is a creature-spell payoff (Spinerock Tyrant occupies adjacent role at a higher CMC; Stormsplitter is *worth flagging as honorable mention 9th* — let me know if you want this in the slate).
- **Galvanic Relay** — Storm-counted "play next turn" exile. Card-advantage delayed; not a kill enabler.
- **Crackling Spellslinger** — 5-cmc "next I/S has storm" flash. Slow setup.
- **Strike It Rich** — Treasure + flashback. Decent ritual but redundant with Brightstone / Pyretic / Rite of Flame / Battle Hymn / Seething Song already covering 5+ ritual slots. Honorable mention only.
- **Thermo-Alchemist** — 1R untap-on-I/S Defender pinger. Strong but defender prevents Zada-copy targeting from making it useful as an attacker. Honorable mention.
- **Squee, the Immortal** — Yard-or-exile recur. Already have Goblin Lackey-quality body; recur not crucial here.
- **Electro, Assaulting Battery** — Second Birgi-style {R}-per-spell. Strict redundancy with Birgi; only matters if Birgi is dead.
- **Legion Warboss** — Token-per-combat goblin. Strong on swing decks, but storm deck rarely attacks until the kill turn.

Any of these can be re-introduced if you want a different cut philosophy.

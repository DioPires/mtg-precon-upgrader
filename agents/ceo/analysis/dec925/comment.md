**Tier 2. Recommendation: run a two-part process.** Part 1 is a pre-event set analysis that ranks the 10 color pairs by the probability that 6 boosters hand you a working deck. Part 2 is a day-of pool evaluator that you run on the cards you actually open. I grade the cards (DEC-461). The simulator and evaluator scripts go to an engineer as a child issue once you confirm the approach below.

**Why two parts.** In Sealed you do not choose a strategy in advance. The pool chooses. So "which strategies are most viable" only has a sound answer as a probability: P(a 6-pack pool supports pair X at deck quality Y). That is a Monte Carlo over the published booster collation with graded cards. The day-of tool turns the same grades into a build for the real pool. Pre-work that stops at "BR is the best archetype" would be a guess about a pool you have not opened.

## What I verified today

Sources: Scryfall API and WotC's "Collecting Reality Fracture" article unless noted.

- **Set.** Code `fra`, release 2026-10-02. Prerelease window 2026-09-25 to 2026-10-01 (WPN event page). Arena release 2026-09-29.
- **Preview status: fully previewed, not almost.** Scryfall holds 285 unique cards = 270 main set + 10 common dual lands + 5 basics. Every card of WotC's stated 71 C / 109 U / 64 R / 26 M is present. The 5 gaps in collector numbers (1, 20, 38, 53, 110) are mythics whose showcase printing Scryfall listed first. Nothing is missing.
- **Prerelease pack.** 6 Play Boosters + 1 foil promo + die + deck box. The promo's rarity pool is not stated on the WotC or WPN pages. Assumption to verify: one date-stamped rare or mythic from the set.
- **Booster collation** (14 game cards; WotC and the mtgscribe fact sheet agree): 5 commons; slot 6 common 98.18% or Special Guest 1.82%; slot 7 non-paired uncommon; slot 8 about 23% common / 74% uncommon; slots 9 to 11 are 3 echoed-pairs cards, and 2 of the 3 are the two halves of one pair at the same rarity (88.9% U / 6.7% R / 1.4% M); slot 12 rare 74.4% / mythic 14.8% / booster-fun rest; slot 13 foil of any rarity (49.5% C / 40.5% U / 6% R / 1.2% M); slot 14 a land, 43.6% a dual.
- **Expected 6-pack pool** (my arithmetic on that table; per pack C 6.71 / U 4.81 / R+M 1.31 / land 1): about 40 commons, 29 uncommons, 8 rares or mythics, 6 lands with about 2.6 duals, plus the promo. Uncommons are about a third of the pool. A normal Play Booster set gives about 3 uncommons in 14. This is the most important structural fact: signpost uncommons and echoed pairs are far more reliable here than usual, and the pairs arrive together.
- **Mechanics by card count** (oracle text, case-insensitive): Surveil 47 cards, Empower Jace 35, Prepared 24 (21 are two-faced "prepare" layout), Prowess 9, Threshold 5, basic landcycling 5 commons. 77 cards mention planeswalkers. The 10 common duals enter untapped only if you control a planeswalker, so a Jace token is also mana fixing.
- **Archetypes.** 10 two-color pairs. Ally pairs are the Hexhaven colleges: Fatehold WU surveil, Theorix UB graveyard, Stingerquill BR damage, Konstrari RG artifacts and Heartwood tokens, Vigorbloom GW lifegain. Enemy pairs key on planeswalkers. Scryfall shows 25 two-color uncommons, so every pair has 2 to 3 signposts; each ally pair has a Charm plus a prepared DFC plus one more.
- **Echoed pairs.** WotC says 86 cards = 43 pairs (66 U / 14 R / 6 M). Scryfall marks one half with a watermark (`echoverse` or `desparked`, 46 cards). A first-name-plus-rarity match pairs 33 of them; 13 differ in name (example: Gideon the Oathless / Gideon's Memorial) and the "Way of the ..." cycle needs a manual table. The simulator needs that table because the pairs come together.
- **External priors, cited not adopted.** limitedmtg.com ranks BR first ("no colour has more removal at common than red or black"), flags GU as the trap (least removal), and counts removal B 14 / R 11 / W 7 / U 5 / G 5 across all rarities. My rough oracle-text regex at common plus uncommon gives the same order (B and R deepest, G thinnest). Draftsim has a full-set 0 to 10 review and an archetype guide dated 2026-09-15.

**Correction made during verification.** My first Empower Jace count was 16 because the search was case-sensitive; reminder text uses lowercase "empower Jace". The correct count is 35 and matches the external source. Every number above was re-derived after that fix.

## Proposed process

1. **Data (draft done).** All 285 FRA cards pulled from Scryfall with oracle text, rarity, colors, watermark and layout. Saved under `agents/ceo/analysis/dec925/`.
2. **Collation model.** Encode the slot table above. Monte Carlo 6-pack pools (100k, seeded). Report per pool: cards per color, playables per pair, removal per color, rare/mythic count, dual count. Include the "pair comes together" rule and the manual echoed-pair table.
3. **Card grades.** I grade all 270 main-set cards for Sealed on a 0 to 10 scale with role tags (removal, evasive threat, bomb, filler, synergy-only) and a "needs" tag (needs Jace token, needs graveyard, needs Heartwood). Every grade comes from oracle text via Scryfall. Cross-check against Draftsim and limitedmtg; log every disagreement of 3 or more points with a reason.
4. **Archetype viability.** For each pair: P(pool supports a deck with at least 23 playables at grade 4 or higher, at least 3 removal spells, at least 1 bomb) and the expected deck grade. Rank the pairs. Also report color depth on its own, because in Sealed the best deck is often the two deepest colors plus a splash, not a named archetype. The 5 basic-landcycling commons and the duals set the splash rule.
5. **Day-of evaluator.** Paste the pool as card names. Output: cards sorted by color, playables / removal / bombs per pair, the top 3 builds with a 17-land, 23-spell split and a splash suggestion. A CLI script, not the web app.
6. **Deliverables.** The ranking with its probabilities, a one-page cheat sheet (key commons per color, combat tricks to respect, the Jace-token and dual-land interaction), and the evaluator.
7. **Optional check.** If your event is on or after 2026-09-30, we add early 17Lands Arena data as a sanity check on the grades. Arena launches 2026-09-29.

## Open decisions

The interaction below asks: your event date; which deliverable matters most; whether steps 2 and 5 go to an engineer; and whether I grade blind first and compare after, or start from Draftsim's grades and correct them.

Delegation gate: no implementation started. Verification notes: `agents/ceo/analysis/dec925/notes.md`.
